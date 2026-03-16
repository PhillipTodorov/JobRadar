"""Fetch job listings from Jooble via their REST API.

Jooble API docs: https://jooble.org/api/about
Free tier with API key.

Get your key at https://jooble.org/api/about
Add to .env:  JOOBLE_API_KEY=your-key-here
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from scraper_utils import load_config, normalize_job, save_raw_results

JOOBLE_BASE = "https://jooble.org/api"


def _parse_date(date_str):
    """Parse a Jooble date string into a timezone-aware datetime, or None."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def fetch_jobs_for_query(query, config):
    """Call Jooble search API for one query."""
    api_key = os.getenv("JOOBLE_API_KEY", "")
    if not api_key:
        print("Error: JOOBLE_API_KEY not set in .env")
        return []

    params_cfg = config.get("search_params", {})
    api_cfg = config.get("api", {})
    max_results = api_cfg.get("max_results", 100)
    posted_within = params_cfg.get("posted_within_days", 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within)

    location = params_cfg.get("location", "London")
    location = location.replace(", United Kingdom", "").strip()
    salary = config.get("salary", {})

    all_jobs = []
    page = 1
    per_page = 20  # Jooble typical page size

    while len(all_jobs) < max_results:
        body = {
            "keywords": query,
            "location": location,
            "page": page,
            "ResultOnPage": per_page,
        }
        if salary.get("minimum"):
            body["salary"] = salary["minimum"]

        try:
            resp = requests.post(
                f"{JOOBLE_BASE}/{api_key}",
                json=body,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"  Jooble API error: {e.response.status_code} — {e.response.text[:200]}")
            break
        except Exception as exc:
            print(f"  Request failed: {exc}")
            break

        results = data.get("jobs", [])
        if not results:
            break

        # Filter by date and stop early if most are too old
        old_count = 0
        for r in results:
            posted = _parse_date(r.get("updated"))
            if posted and posted < cutoff:
                old_count += 1
                continue
            all_jobs.append(r)

        recent = len(results) - old_count
        print(f"  Page {page}: {len(results)} results, {recent} recent, {old_count} skipped")

        if old_count > len(results) // 2:
            print(f"  Stopping early — most results older than {posted_within} days")
            break

        if len(results) < per_page:
            break
        page += 1

    return all_jobs


def map_jooble_job(raw):
    """Convert Jooble API result to standard job dict."""
    return {
        "title": raw.get("title", ""),
        "company": raw.get("company", ""),
        "location": raw.get("location", ""),
        "url": raw.get("link", ""),
        "date_posted": raw.get("updated", ""),
        "salary": raw.get("salary", ""),
        "description": raw.get("snippet", ""),
    }


def scrape():
    """Run the Jooble scraper using job_search_config.yaml settings."""
    config = load_config()
    params = config.get("search_params", {})

    titles = params.get("titles", [])
    keywords = params.get("keywords", [])
    queries = titles if titles else ([" ".join(keywords)] if keywords else [])
    if not queries:
        print("Error: No titles or keywords in job_search_config.yaml")
        return []

    all_jobs = []
    seen = set()
    posted_within = params.get("posted_within_days", 7)

    for query in queries:
        location = params.get("location", "London").replace(", United Kingdom", "")
        print(f'\nSearching Jooble: "{query}" in {location} (last {posted_within} days)')
        raw_results = fetch_jobs_for_query(query, config)

        for raw in raw_results:
            job = map_jooble_job(raw)
            key = (job["title"].lower(), job["company"].lower())
            if key not in seen:
                seen.add(key)
                all_jobs.append(job)

    if not all_jobs:
        print("No jobs found on Jooble.")
        return []

    normalized = [normalize_job(j, "jooble.org") for j in all_jobs]
    print(f"\nTotal unique Jooble jobs: {len(normalized)}")
    return normalized


if __name__ == "__main__":
    jobs = scrape()
    if jobs:
        save_raw_results(jobs, "jooble_raw.json")
        print("\nTop 10:")
        for j in jobs[:10]:
            print(f"  {j['title']} @ {j['company']} — {j['salary']}")
