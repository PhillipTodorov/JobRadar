"""Push scraped job data to Google Sheets.

Authenticates via OAuth (credentials.json/token.json),
opens or creates the target spreadsheet, deduplicates by URL,
and appends new job rows.

First-time setup:
1. Create a Google Cloud project
2. Enable Google Sheets API and Google Drive API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download as credentials.json into project root
5. Run this script once - it will open a browser for login
"""

import json
import sys
from pathlib import Path

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from scraper_utils import TMP_DIR, load_config

PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = ["title", "company", "location", "url", "date_posted",
           "salary", "description", "source", "scraped_at", "fit_score"]


def get_google_creds():
    """Get or refresh Google OAuth credentials."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"Error: {CREDENTIALS_PATH} not found.")
                print("Download OAuth credentials from Google Cloud Console.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def push_jobs(jobs, config=None):
    """Push job list to Google Sheets, deduplicating by URL."""
    if config is None:
        config = load_config()

    output_config = config.get("output", {})
    spreadsheet_name = output_config.get("spreadsheet_name", "Job Scraping Results")
    worksheet_name = output_config.get("worksheet_name", "Jobs")

    creds = get_google_creds()
    gc = gspread.authorize(creds)

    # Open or create spreadsheet
    try:
        spreadsheet = gc.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        spreadsheet = gc.create(spreadsheet_name)
        print(f"Created new spreadsheet: {spreadsheet_name}")

    # Open or create worksheet
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=len(HEADERS))
        worksheet.append_row(HEADERS)
        print(f"Created new worksheet: {worksheet_name}")

    # Get existing URLs for deduplication
    existing_data = worksheet.get_all_values()
    if existing_data:
        # Check if first row looks like a header (contains "url")
        first_row = existing_data[0]
        if "url" in first_row:
            url_col_idx = first_row.index("url")
            existing_urls = {row[url_col_idx] for row in existing_data[1:] if len(row) > url_col_idx}
            # Update headers if they've changed (e.g., added fit_score)
            if first_row != HEADERS:
                worksheet.update(values=[HEADERS], range_name="A1")
        else:
            worksheet.insert_row(HEADERS, 1)
            existing_urls = set()
    else:
        worksheet.append_row(HEADERS)
        existing_urls = set()

    # Filter out duplicates and prepare rows
    new_jobs = [job for job in jobs if job.get("url") not in existing_urls]

    if not new_jobs:
        print("No new jobs to add (all duplicates).")
        return

    # Sort by fit_score descending (if available)
    new_jobs.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    # Append rows
    rows = [[job.get(h, "") for h in HEADERS] for job in new_jobs]
    worksheet.append_rows(rows)

    print(f"Added {len(new_jobs)} new jobs to '{spreadsheet_name}' / '{worksheet_name}'")
    print(f"Skipped {len(jobs) - len(new_jobs)} duplicates")


if __name__ == "__main__":
    # Load most recent scraped data from .tmp/
    config = load_config()
    all_jobs = []

    # Prefer scored_jobs.json if it exists (has fit_score)
    scored_path = TMP_DIR / "scored_jobs.json"
    if scored_path.exists():
        with open(scored_path, "r", encoding="utf-8") as f:
            all_jobs = json.load(f)
        print(f"Loaded {len(all_jobs)} scored jobs from scored_jobs.json")
    else:
        # Fall back to raw files
        for json_file in TMP_DIR.glob("*_raw.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                all_jobs.extend(json.load(f))

    if not all_jobs:
        print("No scraped data found in .tmp/ directory. Run a scraper first.")
        sys.exit(1)

    print(f"Found {len(all_jobs)} jobs to push.")
    push_jobs(all_jobs, config)
