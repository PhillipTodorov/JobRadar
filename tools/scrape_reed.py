"""Fetch job listings from Reed.co.uk via their free Jobs API.

Reed API docs: https://www.reed.co.uk/developers/jobseeker
Free tier: 500 requests/day
Auth: Basic auth — API key as username, empty password

Get a free key at https://www.reed.co.uk/developers/jobseeker
Add to .env:  REED_API_KEY=your-key-here
"""

import os
import sys
from datetime import datetime, timezone

import requests

from scraper_utils import load_config, normalize_job, save_raw_results

REED_BASE = "https://www.reed.co.uk/api/1.0"


def fetch_jobs_for_query(query: str, config: dict) -> list[dict]:
    """Call Reed search API for one query, paginating up to max_results."""
    api_key = os.getenv("REED_API_KEY")
    if not api_key:
        print("Error: REED_API_KEY not set in .env")
        print("Get a free key at https://www.reed.co.uk/developers/jobseeker")
        sys.exit(1)

    auth = (api_key, "")  # Reed uses Basic auth: key as username, blank password
    params_cfg = config.get("search_params", {})
    api_cfg = config.get("api", {})
    max_results = api_cfg.get("max_results", 100)
    posted_within = params_cfg.get("posted_within_days", 30)

    # Reed location: strip ", United Kingdom" suffix if present
    location = params_cfg.get("location", "London")
    location = location.replace(", United Kingdom", "").strip()

    salary = config.get("salary", {})

    all_jobs = []
    skip = 0
    page_size = 100  # Reed max per request

    while len(all_jobs) < max_results:
        params = {
            "keywords": query,
            "locationName": location,
            "distancefromLocation": 10,
            "resultsToTake": min(page_size, max_results - len(all_jobs)),
            "resultsToSkip": skip,
        }
        if salary.get("minimum"):
            params["minimumSalary"] = salary["minimum"]
        if posted_within <= 1:
            params["postedByRecruitmentAgency"] = False  # not a filter but signals freshness intent

        try:
            resp = requests.get(
                f"{REED_BASE}/search",
                auth=auth,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"  Reed API error: {e.response.status_code} — {e.response.text[:200]}")
            break
        except Exception as exc:
            print(f"  Request failed: {exc}")
            break

        results = data.get("results", [])
        if not results:
            break

        all_jobs.extend(results)
        print(f"  Got {len(results)} jobs (total: {len(all_jobs)})")

        if len(results) < page_size:
            break  # No more pages
        skip += len(results)

    return all_jobs


def map_reed_job(raw: dict) -> dict:
    """Convert Reed API result to our standard job dict."""
    min_sal = raw.get("minimumSalary")
    max_sal = raw.get("maximumSalary")
    if min_sal and max_sal:
        salary = f"£{int(min_sal):,}–£{int(max_sal):,} a year"
    elif min_sal:
        salary = f"£{int(min_sal):,}+ a year"
    else:
        salary = ""

    return {
        "title": raw.get("jobTitle", ""),
        "company": raw.get("employerName", ""),
        "location": raw.get("locationName", ""),
        "url": raw.get("jobUrl", ""),
        "date_posted": raw.get("date", ""),
        "salary": salary,
        "description": raw.get("jobDescription", ""),
        "reed_job_id": raw.get("jobId"),
    }


def scrape() -> list[dict]:
    """Run the Reed scraper using job_search_config.yaml settings."""
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

    for query in queries:
        location = params.get("location", "London").replace(", United Kingdom", "")
        print(f'\nSearching Reed: "{query}" in {location}')
        raw_results = fetch_jobs_for_query(query, config)

        for raw in raw_results:
            job = map_reed_job(raw)
            key = (job["title"].lower(), job["company"].lower())
            if key not in seen:
                seen.add(key)
                all_jobs.append(job)

    if not all_jobs:
        print("No jobs found on Reed.")
        return []

    normalized = [normalize_job(j, "reed.co.uk") for j in all_jobs]
    print(f"\nTotal unique Reed jobs: {len(normalized)}")
    return normalized


if __name__ == "__main__":
    jobs = scrape()
    if jobs:
        save_raw_results(jobs, "reed_raw.json")
        print("\nTop 10:")
        for j in jobs[:10]:
            print(f"  {j['title']} @ {j['company']} — {j['salary']}")
