"""Fetch job listings from Adzuna via their REST API.

Adzuna API docs: https://developer.adzuna.com/docs/search
Free tier: 250 requests/month

Get your keys at https://developer.adzuna.com/
Add to .env:
    ADZUNA_APP_ID=your-app-id
    ADZUNA_APP_KEY=your-app-key
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from scraper_utils import load_config, normalize_job, save_raw_results

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


def _parse_date(date_str):
    """Parse an Adzuna date string into a timezone-aware datetime, or None."""
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
    """Call Adzuna search API for one query."""
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        print("Error: ADZUNA_APP_ID and ADZUNA_APP_KEY not set in .env")
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
    per_page = 50  # Adzuna max per page

    while len(all_jobs) < max_results:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "where": location,
            "results_per_page": min(per_page, max_results - len(all_jobs)),
            "content-type": "application/json",
            "max_days_old": posted_within,
            "sort_by": "date",
        }
        if salary.get("minimum"):
            params["salary_min"] = salary["minimum"]

        try:
            resp = requests.get(
                f"{ADZUNA_BASE}/gb/search/{page}",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"  Adzuna API error: {e.response.status_code} — {e.response.text[:200]}")
            break
        except Exception as exc:
            print(f"  Request failed: {exc}")
            break

        results = data.get("results", [])
        if not results:
            break

        # Filter by date and stop early if most are too old
        old_count = 0
        for r in results:
            posted = _parse_date(r.get("created"))
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


def map_adzuna_job(raw):
    """Convert Adzuna API result to standard job dict."""
    min_sal = raw.get("salary_min")
    max_sal = raw.get("salary_max")
    if min_sal and max_sal:
        salary = f"£{int(min_sal):,}–£{int(max_sal):,} a year"
    elif min_sal:
        salary = f"£{int(min_sal):,}+ a year"
    else:
        salary = ""

    location = raw.get("location", {})
    loc_parts = location.get("display_name", "") if isinstance(location, dict) else str(location)

    return {
        "title": raw.get("title", ""),
        "company": raw.get("company", {}).get("display_name", "") if isinstance(raw.get("company"), dict) else "",
        "location": loc_parts,
        "url": raw.get("redirect_url", ""),
        "date_posted": raw.get("created", ""),
        "salary": salary,
        "description": raw.get("description", ""),
    }


def scrape():
    """Run the Adzuna scraper using job_search_config.yaml settings."""
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
        print(f'\nSearching Adzuna: "{query}" in {location} (last {posted_within} days)')
        raw_results = fetch_jobs_for_query(query, config)

        for raw in raw_results:
            job = map_adzuna_job(raw)
            key = (job["title"].lower(), job["company"].lower())
            if key not in seen:
                seen.add(key)
                all_jobs.append(job)

    if not all_jobs:
        print("No jobs found on Adzuna.")
        return []

    normalized = [normalize_job(j, "adzuna.co.uk") for j in all_jobs]
    print(f"\nTotal unique Adzuna jobs: {len(normalized)}")
    return normalized


if __name__ == "__main__":
    jobs = scrape()
    if jobs:
        save_raw_results(jobs, "adzuna_raw.json")
        print("\nTop 10:")
        for j in jobs[:10]:
            print(f"  {j['title']} @ {j['company']} — {j['salary']}")
