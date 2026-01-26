"""Job scraping pipeline orchestrator.

Loads config, runs scrapers for each configured site,
merges results, saves to CSV, and optionally pushes to Google Sheets.
"""

import importlib
import sys
from pathlib import Path

from scraper_utils import load_config, save_csv, save_raw_results

# Map site names to their scraper modules
SCRAPERS = {
    "linkedin": "scrape_serpapi",
    "google_jobs": "scrape_serpapi",
}


def run_pipeline():
    """Run the full scraping pipeline."""
    config = load_config()
    sites = config.get("sites", [])

    if not sites:
        print("No sites configured in job_search_config.yaml")
        sys.exit(1)

    all_jobs = []

    for site in sites:
        if site not in SCRAPERS:
            print(f"Warning: No scraper found for '{site}', skipping.")
            continue

        print(f"\n{'=' * 50}")
        print(f"Scraping: {site}")
        print(f"{'=' * 50}")

        try:
            module = importlib.import_module(SCRAPERS[site])
            jobs = module.scrape()
            if jobs:
                save_raw_results(jobs, f"{site}_raw.json")
                all_jobs.extend(jobs)
            else:
                print(f"No jobs returned from {site}")
        except Exception as e:
            print(f"Error running {site} scraper: {e}")
            continue

    if not all_jobs:
        print("\nNo jobs scraped from any site.")
        sys.exit(1)

    # Score jobs against user profile if profile exists
    profile_path = Path(__file__).parent.parent / "user_profile.yaml"
    if profile_path.exists():
        try:
            from score_job_fit import score_jobs, save_scored_jobs
            print(f"\n{'=' * 50}")
            print("Scoring jobs against user profile...")
            print(f"{'=' * 50}")
            all_jobs = score_jobs(all_jobs)
            save_scored_jobs(all_jobs)
        except Exception as e:
            print(f"Job scoring failed: {e}")
            print("Continuing without scores...")
    else:
        print("\nNo user_profile.yaml found - skipping job fit scoring.")

    # Save combined CSV
    save_csv(all_jobs)

    # Try pushing to Google Sheets if credentials exist
    creds_path = Path(__file__).parent.parent / "credentials.json"
    if creds_path.exists():
        try:
            from push_to_sheets import push_jobs
            push_jobs(all_jobs, config)
        except Exception as e:
            print(f"Google Sheets push failed: {e}")
            print("Results are still saved locally in .tmp/")
    else:
        print("\nNo credentials.json found - skipping Google Sheets push.")
        print("Results saved to .tmp/jobs_export.csv")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"DONE: {len(all_jobs)} total jobs scraped")
    sources = {}
    for job in all_jobs:
        sources[job["source"]] = sources.get(job["source"], 0) + 1
    for source, count in sources.items():
        print(f"  - {source}: {count} jobs")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_pipeline()
