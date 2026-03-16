"""Validate job listings — remove expired posts and dead links.

Two-pass cleanup:
  1. Date check  — drop jobs posted more than N days ago
  2. URL check   — HEAD-request each link, drop 404s / timeouts / errors

Usage:
    python validate_jobs.py              # default 30-day cutoff
    python validate_jobs.py --days 14    # custom cutoff
    python validate_jobs.py --skip-urls  # date cleanup only (fast)
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from scraper_utils import TMP_DIR

SCORED_PATH = TMP_DIR / "scored_jobs.json"

# ── Date parsing ────────────────────────────────────────────────────────────

_RFC2822_RE = re.compile(
    r'\w+,\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
)
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(date_str: str):
    """Best-effort parse of the various date formats across scrapers."""
    if not date_str:
        return None

    # ISO 8601: "2026-03-12T17:09:21Z"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    # RFC 2822-ish: "Thu, 12 Mar 2026 07:59:12 GMT"
    m = _RFC2822_RE.search(date_str)
    if m:
        day, mon_str, year = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
        mon = _MONTH_MAP.get(mon_str)
        if mon:
            return datetime(year, mon, day, tzinfo=timezone.utc)

    # dd/mm/yyyy: "09/03/2026"
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d %b %Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


# ── URL validation ──────────────────────────────────────────────────────────

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (JobRadar link checker)",
})
# Follow redirects, but cap at 5
_SESSION.max_redirects = 5


def _check_url(url: str) -> bool:
    """Return True if the URL appears to be alive (2xx/3xx)."""
    if not url:
        return False
    try:
        resp = _SESSION.head(url, timeout=8, allow_redirects=True)
        # Some servers reject HEAD — retry with GET
        if resp.status_code == 405:
            resp = _SESSION.get(url, timeout=8, allow_redirects=True, stream=True)
            resp.close()
        return resp.status_code < 400
    except Exception:
        return False


def validate_jobs(max_age_days: int = 30, check_urls: bool = True, workers: int = 15):
    """Load scored_jobs.json, remove stale/dead jobs, save back.

    Returns (kept, removed_date, removed_url) counts.
    """
    if not SCORED_PATH.exists():
        print("No scored_jobs.json found.")
        return 0, 0, 0

    with open(SCORED_PATH, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    total = len(jobs)
    print(f"Loaded {total} jobs from scored_jobs.json")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    # ── Pass 1: date-based cleanup ──────────────────────────────────────
    date_kept = []
    removed_date = 0

    for job in jobs:
        # Try date_posted first, fall back to scraped_at
        dt = _parse_date(job.get("date_posted", ""))
        if dt is None:
            dt = _parse_date(job.get("scraped_at", ""))

        if dt and dt < cutoff:
            removed_date += 1
        else:
            date_kept.append(job)

    print(f"Date check: removed {removed_date} jobs older than {max_age_days} days")

    # ── Pass 2: URL validation ──────────────────────────────────────────
    if not check_urls:
        kept = date_kept
        removed_url = 0
    else:
        print(f"Checking {len(date_kept)} URLs (this may take a minute)...")
        alive = [None] * len(date_kept)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for i, job in enumerate(date_kept):
                fut = pool.submit(_check_url, job.get("url", ""))
                futures[fut] = i

            done = 0
            for fut in as_completed(futures):
                idx = futures[fut]
                alive[idx] = fut.result()
                done += 1
                if done % 50 == 0:
                    print(f"  ...checked {done}/{len(date_kept)}")

        kept = []
        removed_url = 0
        for job, is_alive in zip(date_kept, alive):
            if is_alive:
                kept.append(job)
            else:
                removed_url += 1

        print(f"URL check: removed {removed_url} dead links")

    # ── Save ────────────────────────────────────────────────────────────
    kept.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    with open(SCORED_PATH, "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {len(kept)} jobs kept, {removed_date + removed_url} removed")
    print(f"  Expired (>{max_age_days} days old): {removed_date}")
    if check_urls:
        print(f"  Dead links: {removed_url}")

    return len(kept), removed_date, removed_url


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean stale/dead jobs")
    parser.add_argument("--days", type=int, default=30, help="Max age in days (default 30)")
    parser.add_argument("--skip-urls", action="store_true", help="Skip URL validation")
    args = parser.parse_args()

    validate_jobs(max_age_days=args.days, check_urls=not args.skip_urls)
