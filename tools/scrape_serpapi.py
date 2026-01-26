"""Fetch job listings via SerpAPI's Google Jobs engine.

Uses the Google Jobs search results which aggregate listings
from LinkedIn, Indeed, Glassdoor, and other job boards.
"""

import os
import sys
from serpapi import GoogleSearch

from scraper_utils import load_config, normalize_job, save_raw_results, TMP_DIR


# Map config's posted_within_days to SerpAPI chip values
DATE_POSTED_MAP = {
    1: "today",
    3: "3days",
    7: "week",
    30: "month",
}


def get_date_posted_chip(days):
    """Convert days to SerpAPI date_posted chip value."""
    if days <= 1:
        return "today"
    elif days <= 3:
        return "3days"
    elif days <= 7:
        return "week"
    else:
        return "month"


def fetch_jobs_for_query(query, location, config):
    """Fetch jobs from SerpAPI for a single search query."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("Error: SERPAPI_KEY not set in .env file.")
        print("Get a free API key at https://serpapi.com/")
        sys.exit(1)

    api_config = config.get("api", {})
    max_results = api_config.get("max_results", 50)
    pages = api_config.get("pages", 3)

    params = config.get("search_params", {})
    posted_within = params.get("posted_within_days", 30)
    date_chip = get_date_posted_chip(posted_within)

    all_jobs = []
    next_page_token = None

    for page_num in range(pages):
        search_params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "chips": f"date_posted:{date_chip}",
            "api_key": api_key,
        }

        if next_page_token:
            search_params["next_page_token"] = next_page_token

        print(f"  Fetching page {page_num + 1}/{pages}...")

        try:
            search = GoogleSearch(search_params)
            results = search.get_dict()
        except Exception as e:
            print(f"  API error on page {page_num + 1}: {e}")
            break

        jobs_results = results.get("jobs_results", [])

        if not jobs_results:
            print(f"  No more results on page {page_num + 1}.")
            break

        for job in jobs_results:
            all_jobs.append({
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("location", ""),
                "url": job.get("share_link", "") or job.get("job_id", ""),
                "date_posted": job.get("detected_extensions", {}).get("posted_at", ""),
                "salary": job.get("detected_extensions", {}).get("salary", ""),
                "description": job.get("description", ""),
                "via": job.get("via", ""),
            })

        print(f"  Got {len(jobs_results)} jobs (total: {len(all_jobs)})")

        if len(all_jobs) >= max_results:
            all_jobs = all_jobs[:max_results]
            break

        # Get next page token for pagination
        pagination = results.get("serpapi_pagination", {})
        next_page_token = pagination.get("next_page_token")
        if not next_page_token:
            break

    return all_jobs


def scrape():
    """Run the SerpAPI Google Jobs scraper using config settings."""
    config = load_config()
    params = config.get("search_params", {})

    titles = params.get("titles", [])
    keywords = params.get("keywords", [])
    location = params.get("location", "London, United Kingdom")

    # Build search queries from titles
    queries = []
    if titles:
        queries = titles
    elif keywords:
        queries = [" ".join(keywords)]
    else:
        print("Error: No titles or keywords configured.")
        return []

    all_jobs = []
    seen_titles_companies = set()  # Deduplicate across queries

    for query in queries:
        print(f"\nSearching: \"{query}\" in {location}")
        jobs = fetch_jobs_for_query(query, location, config)

        for job in jobs:
            # Deduplicate by title + company combo
            key = (job["title"].lower(), job["company"].lower())
            if key not in seen_titles_companies:
                seen_titles_companies.add(key)
                all_jobs.append(job)

    if not all_jobs:
        print("\nNo jobs found.")
        return []

    # Normalize all jobs
    normalized = [normalize_job(job, f"google_jobs ({job.get('via', '')})") for job in all_jobs]

    print(f"\nTotal unique jobs found: {len(normalized)}")
    return normalized


if __name__ == "__main__":
    jobs = scrape()
    if jobs:
        save_raw_results(jobs, "serpapi_raw.json")
