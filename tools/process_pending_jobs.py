"""Process job URLs sent from iPhone via the Gist inbox.

Reads pending_jobs.json from the GitHub Gist, scrapes each URL,
extracts job details, scores them, merges into scored_jobs.json,
and clears the pending list.

Usage:
    python process_pending_jobs.py
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from fetch_full_descriptions import scrape_job_page, USER_AGENT, SCRAPE_TIMEOUT
from gist_sync import read_gist_file, update_gist_file, auto_push
from scraper_utils import normalize_job, TMP_DIR

PENDING_FILE = "pending_job.txt"


def fetch_pending():
    """Read pending_jobs.txt from the gist. Returns list of URL strings."""
    raw = read_gist_file(PENDING_FILE)
    if not raw:
        return []
    # Simple text format: one URL per line
    urls = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    return urls


def extract_job_from_url(url):
    """Scrape a job URL and extract structured job data.

    Returns a normalized job dict or None on failure.
    """
    if not url or not url.startswith("http"):
        return None

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9",
    }

    try:
        resp = requests.get(
            url, headers=headers, timeout=SCRAPE_TIMEOUT, allow_redirects=True
        )
        resp.raise_for_status()

        if "text/html" not in resp.headers.get("Content-Type", ""):
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  Failed to fetch {url[:80]}: {e}")
        return None

    # Extract metadata from the page
    title = _extract_title(soup, url)
    company = _extract_company(soup)
    location = _extract_location(soup)
    salary = _extract_salary(soup)

    # Get description using the existing enrichment logic
    description = scrape_job_page(url) or ""

    raw = {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "date_posted": "",
        "salary": salary,
        "description": description,
    }

    return normalize_job(raw, source="iphone")


def _extract_title(soup, url):
    """Extract job title from page."""
    # Site-specific selectors
    selectors = [
        ("h1", {"class": re.compile(r"job.?title", re.I)}),
        (None, {"itemprop": "title"}),
        (None, {"data-testid": re.compile(r"title", re.I)}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs) if tag else soup.find(attrs=attrs)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)

    # Fallback: first h1
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        text = h1.get_text(strip=True)
        if len(text) < 200:
            return text

    # Fallback: og:title or <title> tag
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()

    title_tag = soup.find("title")
    if title_tag:
        # Often "Job Title - Company - Site", take first part
        parts = title_tag.get_text().split(" - ")
        return parts[0].strip() if parts else ""

    return ""


def _extract_company(soup):
    """Extract company name from page."""
    selectors = [
        (None, {"itemprop": "hiringOrganization"}),
        (None, {"class": re.compile(r"company.?name", re.I)}),
        (None, {"data-testid": re.compile(r"company", re.I)}),
        (None, {"class": re.compile(r"employer", re.I)}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs) if tag else soup.find(attrs=attrs)
        if el:
            # Might be a nested structure
            name_el = el.find("name") or el
            text = name_el.get_text(strip=True)
            if text and len(text) < 200:
                return text

    # Fallback: og:site_name sometimes has the company
    return ""


def _extract_location(soup):
    """Extract location from page."""
    selectors = [
        (None, {"itemprop": "jobLocation"}),
        (None, {"class": re.compile(r"location", re.I)}),
        (None, {"data-testid": re.compile(r"location", re.I)}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs) if tag else soup.find(attrs=attrs)
        if el:
            text = el.get_text(strip=True)
            if text and len(text) < 200:
                return text
    return ""


def _extract_salary(soup):
    """Extract salary from page."""
    selectors = [
        (None, {"itemprop": "baseSalary"}),
        (None, {"class": re.compile(r"salary", re.I)}),
        (None, {"data-testid": re.compile(r"salary", re.I)}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs) if tag else soup.find(attrs=attrs)
        if el:
            text = el.get_text(strip=True)
            if text and len(text) < 200:
                return text
    return ""


def clear_pending():
    """Reset pending_jobs.txt in the gist to empty."""
    return update_gist_file(PENDING_FILE, "")


def process_pending_jobs():
    """Main pipeline: fetch pending URLs, scrape, score, merge, clear, push."""
    pending = fetch_pending()
    if not pending:
        print("No pending jobs from phone.")
        return {"processed": 0, "added": 0, "failed": 0}

    print(f"Found {len(pending)} pending job(s) from phone")

    # Load existing jobs for dedup
    scored_path = TMP_DIR / "scored_jobs.json"
    existing_jobs = []
    if scored_path.exists():
        try:
            with open(scored_path, "r", encoding="utf-8") as f:
                existing_jobs = json.load(f)
        except Exception:
            existing_jobs = []

    seen = set()
    for ej in existing_jobs:
        key = (ej.get("title", "").lower().strip(), ej.get("company", "").lower().strip())
        if key != ("", ""):
            seen.add(key)

    # Also dedup by URL
    seen_urls = {ej.get("url", "").rstrip("/").lower() for ej in existing_jobs}

    new_jobs = []
    failed_urls = []

    for url in pending:
        url = url.strip()
        if not url:
            continue

        # Skip if URL already in jobs
        if url.rstrip("/").lower() in seen_urls:
            print(f"  SKIP (already exists): {url[:80]}")
            continue

        print(f"  Scraping: {url[:80]}...")
        job = extract_job_from_url(url)

        if job and job.get("title"):
            key = (job["title"].lower().strip(), job["company"].lower().strip())
            if key not in seen or key == ("", ""):
                seen.add(key)
                seen_urls.add(url.rstrip("/").lower())
                new_jobs.append(job)
                print(f"    -> {job['title']} @ {job['company'] or '(unknown)'}")
            else:
                print(f"    SKIP (duplicate): {job['title']}")
        else:
            # Create minimal entry so user can still see/open the URL
            minimal = normalize_job(
                {"title": f"(Review needed)", "url": url, "description": ""},
                source="iphone",
            )
            new_jobs.append(minimal)
            failed_urls.append(url)
            print(f"    -> Could not extract details, added for manual review")

    # Score new jobs
    if new_jobs:
        profile_path = PROJECT_ROOT / "user_profile.yaml"
        if profile_path.exists():
            try:
                from score_job_fit import score_jobs
                print(f"\nScoring {len(new_jobs)} new job(s)...")
                new_jobs = score_jobs(new_jobs)
            except Exception as e:
                print(f"Scoring failed: {e}")

    # Merge and save
    merged = existing_jobs + new_jobs
    merged.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    TMP_DIR.mkdir(exist_ok=True)
    with open(scored_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\nMerged: {len(existing_jobs)} existing + {len(new_jobs)} new = {len(merged)} total")

    # Clear pending list in gist
    clear_pending()
    print("Cleared pending_jobs.json in gist")

    # Push updated scored_jobs.json to gist
    try:
        auto_push()
        print("Synced to gist")
    except Exception:
        pass

    summary = {
        "processed": len(pending),
        "added": len(new_jobs),
        "failed": len(failed_urls),
    }
    print(f"\nDone: {summary['added']} added, {summary['failed']} need review")
    return summary


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    process_pending_jobs()
