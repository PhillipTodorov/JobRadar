"""Shared utilities for job scrapers."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root is one level up from tools/
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "job_search_config.yaml"
TMP_DIR = PROJECT_ROOT / ".tmp"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


def load_config():
    """Load and return the job search configuration."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_job(raw_data, source):
    """Ensure a job dict has all standard fields."""
    return {
        "title": raw_data.get("title", "").strip(),
        "company": raw_data.get("company", "").strip(),
        "location": raw_data.get("location", "").strip(),
        "url": raw_data.get("url", "").strip(),
        "date_posted": raw_data.get("date_posted", "").strip(),
        "salary": raw_data.get("salary", "").strip(),
        "description": raw_data.get("description", "").strip()[:2000],
        "source": source,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def save_raw_results(jobs, filename):
    """Save job list as JSON to .tmp/ directory."""
    TMP_DIR.mkdir(exist_ok=True)
    filepath = TMP_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs)} jobs to {filepath}")
    return filepath


def save_csv(jobs, filename="jobs_export.csv"):
    """Save job list as CSV to .tmp/ directory."""
    import csv

    TMP_DIR.mkdir(exist_ok=True)
    filepath = TMP_DIR / filename
    if not jobs:
        print("No jobs to save.")
        return filepath

    fieldnames = ["title", "company", "location", "url", "date_posted",
                  "salary", "description", "source", "scraped_at"]

    # Add fit_score column if any job has it
    if any("fit_score" in job for job in jobs):
        fieldnames.append("fit_score")

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)
    print(f"Saved {len(jobs)} jobs to {filepath}")
    return filepath


