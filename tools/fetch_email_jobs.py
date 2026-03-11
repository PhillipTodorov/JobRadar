"""Fetch job listings from recruiter email alerts via IMAP.

Connects to configured email account, finds emails from known recruiter
senders, parses job cards from the HTML body, and returns normalized
job dicts matching the standard scraper schema.

Requires in .env:
    EMAIL_IMAP_HOST=imap.mail.yahoo.com
    EMAIL_IMAP_PORT=993
    EMAIL_ADDRESS=user@yahoo.co.uk
    EMAIL_APP_PASSWORD=your-yahoo-app-password

Usage:
    # As part of the scraper pipeline (via run_job_scrape.py):
    from fetch_email_jobs import scrape
    jobs = scrape()

    # CLI test:
    python fetch_email_jobs.py
"""

import email
import email.policy
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from email_parsers import get_parser
from scraper_utils import load_config, normalize_job

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH, override=True)

# Default recruiter senders (used if none configured in job_search_config.yaml)
DEFAULT_SENDERS = [
    {"name": "Michael Page", "email_from": "noreply@michaelpage.co.uk", "parser": "michael_page"},
    {"name": "Michael Page", "email_from": "noreply@page.com", "parser": "michael_page"},
    {"name": "Reed", "email_from": "jobalerts@reed.co.uk", "parser": "reed"},
    {"name": "Reed", "email_from": "alerts@reed.co.uk", "parser": "reed"},
    {"name": "Indeed", "email_from": "jobalerts-noreply@indeed.com", "parser": "indeed"},
    {"name": "Indeed", "email_from": "alert@indeed.com", "parser": "indeed"},
    {"name": "Totaljobs", "email_from": "jobalerts@totaljobs.com", "parser": "totaljobs"},
    {"name": "CV-Library", "email_from": "alerts@cv-library.co.uk", "parser": "cv_library"},
]


def connect_imap():
    """Connect and authenticate to IMAP server.

    Returns authenticated IMAP4_SSL connection.
    Raises ConnectionError if credentials missing or connection fails.
    """
    host = os.getenv("EMAIL_IMAP_HOST", "imap.mail.yahoo.com")
    port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    address = os.getenv("EMAIL_ADDRESS", "")
    password = os.getenv("EMAIL_APP_PASSWORD", "")

    if not address or not password:
        raise ConnectionError(
            "EMAIL_ADDRESS and EMAIL_APP_PASSWORD must be set in .env"
        )

    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(address, password)
        return conn
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"IMAP login failed: {e}")
    except Exception as e:
        raise ConnectionError(f"Could not connect to {host}:{port}: {e}")


def get_recruiter_senders():
    """Load configured recruiter email senders.

    Returns list of dicts: {name, email_from, parser}.
    Falls back to DEFAULT_SENDERS if none configured.
    """
    try:
        config = load_config()
        email_cfg = config.get("email_alerts", {})
        senders = email_cfg.get("senders", [])
        if senders:
            return senders
    except Exception:
        pass
    return DEFAULT_SENDERS


def fetch_emails_from_sender(conn, sender_email, since_days=7, max_emails=20):
    """Fetch recent emails from a specific sender.

    Returns list of email.message.Message objects.
    """
    conn.select("INBOX", readonly=True)

    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")

    # IMAP search: FROM sender, SINCE date
    search_criteria = f'(FROM "{sender_email}" SINCE {since_date})'

    try:
        status, data = conn.search(None, search_criteria)
    except imaplib.IMAP4.error:
        return []

    if status != "OK" or not data[0]:
        return []

    msg_ids = data[0].split()

    # Limit to most recent emails
    msg_ids = msg_ids[-max_emails:]

    messages = []
    for msg_id in msg_ids:
        try:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status == "OK" and msg_data[0]:
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw, policy=email.policy.default)
                messages.append(msg)
        except Exception:
            continue
        time.sleep(0.1)  # Be courteous to the IMAP server

    return messages


def extract_html_body(msg):
    """Extract HTML body from an email message.

    Handles multipart messages, charset detection, etc.
    Returns HTML string or empty string if no HTML found.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:
                    continue
        # Fallback: try plain text
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        except Exception:
            pass

    return ""


def parse_email_jobs(html_body, parser_name, sender_name):
    """Parse job listings from email HTML using the appropriate parser.

    Returns list of raw job dicts.
    """
    parser_fn = get_parser(parser_name)
    if not parser_fn:
        return []

    try:
        return parser_fn(html_body)
    except Exception as e:
        print(f"  Parser error ({parser_name}): {e}")
        return []


def scrape():
    """Main entry point matching the scraper pipeline interface.

    1. Connect to IMAP
    2. For each configured recruiter sender:
       a. Fetch recent emails
       b. Parse each email for job cards
       c. Normalize to standard schema
    3. Deduplicate
    4. Return list of normalized job dicts
    """
    try:
        config = load_config()
    except Exception:
        config = {}

    email_cfg = config.get("email_alerts", {})
    if email_cfg.get("enabled") is False:
        print("Email alerts disabled in config.")
        return []

    check_days = email_cfg.get("check_days", 7)
    max_emails = email_cfg.get("max_emails_per_sender", 20)

    senders = get_recruiter_senders()
    if not senders:
        print("No recruiter senders configured.")
        return []

    print(f"Connecting to email ({os.getenv('EMAIL_ADDRESS', '???')})...")
    try:
        conn = connect_imap()
    except ConnectionError as e:
        print(f"Email connection failed: {e}")
        return []

    all_jobs = []
    seen = set()

    try:
        for sender in senders:
            name = sender.get("name", "Unknown")
            email_from = sender.get("email_from", "")
            parser_name = sender.get("parser", "generic")

            if not email_from:
                continue

            print(f"  Checking emails from {name} ({email_from})...")
            messages = fetch_emails_from_sender(
                conn, email_from, since_days=check_days, max_emails=max_emails
            )

            if not messages:
                print(f"    No recent emails found.")
                continue

            print(f"    Found {len(messages)} emails.")

            for msg in messages:
                html_body = extract_html_body(msg)
                if not html_body:
                    continue

                raw_jobs = parse_email_jobs(html_body, parser_name, name)

                for raw in raw_jobs:
                    # Deduplicate by title + company
                    key = (raw.get("title", "").lower(), raw.get("company", "").lower())
                    if key in seen:
                        continue
                    seen.add(key)

                    # Normalize to standard schema
                    job = normalize_job(raw, source=f"email ({name})")
                    all_jobs.append(job)

            print(f"    Extracted {len([j for j in all_jobs if name in j.get('source', '')])} jobs from {name}.")

    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

    print(f"\nTotal email jobs: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 50)
    print("Email Job Alert Fetcher")
    print("=" * 50)

    jobs = scrape()

    if jobs:
        print(f"\nExtracted {len(jobs)} jobs:")
        for j in jobs[:10]:
            print(f"  - {j['title']} at {j['company'] or '?'} ({j['source']})")
        if len(jobs) > 10:
            print(f"  ... and {len(jobs) - 10} more")
    else:
        print("\nNo jobs extracted from email alerts.")
        print("Make sure:")
        print("  1. EMAIL_ADDRESS and EMAIL_APP_PASSWORD are set in .env")
        print("  2. You've signed up for email alerts from recruiters")
        print("  3. There are recent alert emails in your inbox")
