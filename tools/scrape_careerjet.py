"""Fetch job listings from Careerjet via their public API.

Careerjet API docs: https://www.careerjet.co.uk/partners/api
Uses HTTP requests directly (no pip package needed).

Get an affiliate ID at https://www.careerjet.co.uk/partners/
Add to .env:  CAREERJET_AFFID=your-affiliate-id
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from scraper_utils import load_config, normalize_job, save_raw_results

CAREERJET_URL = "http://public.api.careerjet.net/search"


def _parse_date(date_str):
    """Parse a date string into a timezone-aware datetime, or None."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    # Try dd/mm/yyyy format
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d %b %Y"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch_jobs_for_query(query, config):
    """Call Careerjet search API for one query."""
    affid = os.getenv("CAREERJET_AFFID", "")
    if not affid:
        print("Error: CAREERJET_AFFID not set in .env")
        return []

    params_cfg = config.get("search_params", {})
    api_cfg = config.get("api", {})
    max_results = api_cfg.get("max_results", 100)
    posted_within = params_cfg.get("posted_within_days", 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within)

    location = params_cfg.get("location", "London")
    location = location.replace(", United Kingdom", "").strip()

    all_jobs = []
    page = 1
    per_page = 20

    while len(all_jobs) < max_results:
        params = {
            "keywords": query,
            "location": location,
            "affid": affid,
            "user_ip": "127.0.0.1",
            "user_agent": "Mozilla/5.0 (JobRadar)",
            "url": "http://localhost",
            "locale_code": "en_GB",
            "sort": "date",
            "pagesize": per_page,
            "page": page,
        }

        headers = {
            "Referer": "http://www.jobradar.local/search",
            "User-Agent": "Mozilla/5.0 (JobRadar)",
        }

        try:
            resp = requests.get(
                CAREERJET_URL,
                params=params,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"  Careerjet API error: {e.response.status_code} — {e.response.text[:200]}")
            break
        except Exception as exc:
            print(f"  Request failed: {exc}")
            break

        if data.get("type") == "ERROR":
            print(f"  Careerjet error: {data.get('error', 'unknown')}")
            break

        results = data.get("jobs", [])
        if not results:
            break

        # Filter by date and stop early if most are too old
        old_count = 0
        for r in results:
            posted = _parse_date(r.get("date"))
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


def map_careerjet_job(raw):
    """Convert Careerjet API result to standard job dict."""
    return {
        "title": raw.get("title", ""),
        "company": raw.get("company", ""),
        "location": raw.get("locations", ""),
        "url": raw.get("url", ""),
        "date_posted": raw.get("date", ""),
        "salary": raw.get("salary", ""),
        "description": raw.get("description", ""),
    }


def scrape():
    """Run the Careerjet scraper using job_search_config.yaml settings."""
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
        print(f'\nSearching Careerjet: "{query}" in {location} (last {posted_within} days)')
        raw_results = fetch_jobs_for_query(query, config)

        for raw in raw_results:
            job = map_careerjet_job(raw)
            key = (job["title"].lower(), job["company"].lower())
            if key not in seen:
                seen.add(key)
                all_jobs.append(job)

    if not all_jobs:
        print("No jobs found on Careerjet.")
        return []

    normalized = [normalize_job(j, "careerjet.co.uk") for j in all_jobs]
    print(f"\nTotal unique Careerjet jobs: {len(normalized)}")
    return normalized


if __name__ == "__main__":
    jobs = scrape()
    if jobs:
        save_raw_results(jobs, "careerjet_raw.json")
        print("\nTop 10:")
        for j in jobs[:10]:
            print(f"  {j['title']} @ {j['company']} — {j['salary']}")
