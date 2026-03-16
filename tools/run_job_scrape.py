"""Job scraping pipeline orchestrator.

Loads config, runs scrapers for each configured site,
merges results, saves to CSV, and optionally pushes to Google Sheets.
"""

import importlib
import json
import sys
from pathlib import Path

from scraper_utils import load_config, save_csv, save_raw_results, TMP_DIR

# Map site names to their scraper modules
SCRAPERS = {
    "linkedin": "scrape_serpapi",
    "google_jobs": "scrape_serpapi",
    "reed": "scrape_reed",
    "adzuna": "scrape_adzuna",
    "jooble": "scrape_jooble",
    "careerjet": "scrape_careerjet",
    "email": "fetch_email_jobs",
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

    # Enrich partial/truncated descriptions before dedup and scoring
    print(f"\n{'=' * 50}")
    print("Enriching job descriptions...")
    print(f"{'=' * 50}")
    try:
        from fetch_full_descriptions import enrich_descriptions
        all_jobs = enrich_descriptions(all_jobs)
    except Exception as e:
        print(f"Description enrichment failed: {e}")
        print("Continuing with original descriptions...")

    # Merge with existing scored_jobs.json so we add to total, not replace
    scored_path = TMP_DIR / "scored_jobs.json"
    existing_jobs = []
    if scored_path.exists():
        try:
            with open(scored_path, "r", encoding="utf-8") as f:
                existing_jobs = json.load(f)
            print(f"\nLoaded {len(existing_jobs)} existing jobs from scored_jobs.json")
        except Exception:
            existing_jobs = []

    # Build dedup set from existing jobs (title + company)
    seen = set()
    for ej in existing_jobs:
        key = (ej.get("title", "").lower().strip(), ej.get("company", "").lower().strip())
        seen.add(key)

    # Only add genuinely new jobs
    new_jobs = []
    for job in all_jobs:
        key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
        if key not in seen:
            seen.add(key)
            new_jobs.append(job)

    print(f"New jobs to add: {len(new_jobs)} (skipped {len(all_jobs) - len(new_jobs)} duplicates)")

    # Score new jobs against user profile if profile exists
    profile_path = Path(__file__).parent.parent / "user_profile.yaml"
    if profile_path.exists() and new_jobs:
        try:
            from score_job_fit import score_jobs, save_scored_jobs
            print(f"\n{'=' * 50}")
            print("Scoring new jobs against user profile...")
            print(f"{'=' * 50}")
            new_jobs = score_jobs(new_jobs)
        except Exception as e:
            print(f"Job scoring failed: {e}")
            print("Continuing without scores...")

    # Merge: existing + new, then save
    merged = existing_jobs + new_jobs
    merged.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    if profile_path.exists():
        try:
            from score_job_fit import save_scored_jobs
            save_scored_jobs(merged)
        except Exception:
            pass
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
