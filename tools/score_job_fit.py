"""Score jobs against user profile for fit matching.

Uses keyword matching to score how well each job matches
the user's skills, location preferences, and other criteria.
"""

import json
from pathlib import Path

import yaml

from scraper_utils import TMP_DIR

PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"


def load_profile():
    """Load user profile from YAML file."""
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"User profile not found: {PROFILE_PATH}\n"
            "Create user_profile.yaml with your skills and preferences."
        )
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_fit_score(job, profile):
    """Calculate fit score (0-100) for a single job.

    Args:
        job: Dict with job data (title, description, location, etc.)
        profile: Dict with user profile data

    Returns:
        int: Score from 0-100, or 0 if dealbreaker found
    """
    scores = {}
    user = profile.get("profile", {})
    scoring = profile.get("scoring", {})
    weights = scoring.get("weights", {
        "required_skills": 0.40,
        "preferred_skills": 0.25,
        "location": 0.20,
        "title_relevance": 0.15,
    })

    # Combine description and title for matching
    text = (job.get("description", "") + " " + job.get("title", "")).lower()

    # Check dealbreakers first - if found, return 0 immediately
    dealbreakers = user.get("dealbreakers", [])
    for dealbreaker in dealbreakers:
        if dealbreaker.lower() in text:
            return 0

    # Required skills score (0-100)
    required_skills = user.get("skills", {}).get("required", [])
    if required_skills:
        required_matches = sum(1 for skill in required_skills if skill.lower() in text)
        scores["required_skills"] = (required_matches / len(required_skills)) * 100
    else:
        scores["required_skills"] = 50  # Neutral if no required skills defined

    # Preferred skills score (0-100)
    preferred_skills = user.get("skills", {}).get("preferred", [])
    if preferred_skills:
        preferred_matches = sum(1 for skill in preferred_skills if skill.lower() in text)
        scores["preferred_skills"] = (preferred_matches / len(preferred_skills)) * 100
    else:
        scores["preferred_skills"] = 50  # Neutral if no preferred skills defined

    # Location score (0, 50, or 100)
    job_location = job.get("location", "").lower()
    preferred_locations = user.get("locations", {}).get("preferred", [])
    acceptable_locations = user.get("locations", {}).get("acceptable", [])

    if any(loc.lower() in job_location for loc in preferred_locations):
        scores["location"] = 100
    elif any(loc.lower() in job_location for loc in acceptable_locations):
        scores["location"] = 50
    else:
        scores["location"] = 0

    # Title relevance score (0-100)
    job_title = job.get("title", "").lower()
    relevant_keywords = ["developer", "engineer", "software", "programmer", "coding"]
    if any(kw in job_title for kw in relevant_keywords):
        scores["title_relevance"] = 100
    else:
        scores["title_relevance"] = 50

    # Calculate weighted average
    final_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)

    return round(final_score)


def score_jobs(jobs=None):
    """Score all jobs and return sorted by fit score.

    Args:
        jobs: List of job dicts, or None to load from .tmp/

    Returns:
        List of jobs with fit_score field, sorted descending
    """
    # Load jobs if not provided
    if jobs is None:
        jobs = []
        for json_file in TMP_DIR.glob("*_raw.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                jobs.extend(json.load(f))

    if not jobs:
        print("No jobs to score.")
        return []

    # Load user profile
    profile = load_profile()

    # Score each job
    scored_jobs = []
    for job in jobs:
        score = calculate_fit_score(job, profile)
        job_with_score = {**job, "fit_score": score}
        scored_jobs.append(job_with_score)

    # Sort by fit score descending
    scored_jobs.sort(key=lambda x: x["fit_score"], reverse=True)

    # Print summary
    total = len(scored_jobs)
    with_score = len([j for j in scored_jobs if j["fit_score"] > 0])
    avg_score = sum(j["fit_score"] for j in scored_jobs) / total if total else 0

    print(f"\nScored {total} jobs:")
    print(f"  Jobs with score > 0: {with_score}")
    print(f"  Jobs filtered (dealbreakers): {total - with_score}")
    print(f"  Average score: {avg_score:.1f}")
    if scored_jobs:
        print(f"  Top score: {scored_jobs[0]['fit_score']} - {scored_jobs[0]['title']} at {scored_jobs[0]['company']}")

    return scored_jobs


def save_scored_jobs(jobs, filename="scored_jobs.json"):
    """Save scored jobs to JSON file."""
    TMP_DIR.mkdir(exist_ok=True)
    filepath = TMP_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs)} scored jobs to {filepath}")
    return filepath


if __name__ == "__main__":
    scored = score_jobs()
    if scored:
        save_scored_jobs(scored)
        print("\nTop 10 jobs by fit score:")
        for i, job in enumerate(scored[:10], 1):
            print(f"  {i}. [{job['fit_score']}] {job['title']} at {job['company']}")
