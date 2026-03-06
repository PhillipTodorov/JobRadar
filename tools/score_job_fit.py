"""Score jobs against user profile for fit matching.

Uses keyword matching to score how well each job matches
the user's skills, location preferences, and other criteria.
"""

import json
import re
from pathlib import Path

import yaml

from scraper_utils import TMP_DIR

# Patterns that extract the number of years required from a job description.
# Each pattern captures one or two groups; we take the maximum found.
_YEARS_PATTERNS = [
    re.compile(r'(\d+)\s*\+\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s*years?[\'s]?\s*(?:\w+\s+){0,2}experience', re.IGNORECASE),
    re.compile(r'minimum\s+(?:of\s+)?(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'at\s+least\s+(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s*[-\u2013]\s*(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s+to\s+(\d+)\s*years?', re.IGNORECASE),
]



def extract_years_required(text: str) -> int:
    """Return the maximum years of experience required found in *text*.

    Returns 0 if no years requirement is detected.
    """
    max_years = 0
    for pattern in _YEARS_PATTERNS:
        for match in pattern.finditer(text):
            groups = [int(g) for g in match.groups() if g is not None]
            if groups:
                max_years = max(max_years, max(groups))
    return max_years

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

    # Check experience requirement against user's max acceptable
    max_years_acceptable = user.get("experience", {}).get("max_years_required", 99)
    years_required = extract_years_required(text)
    if years_required > max_years_acceptable:
        return 0

    # Required skills score (0-100)
    required_skills = user.get("skills", {}).get("required", [])
    if required_skills:
        required_matches = sum(1 for skill in required_skills if skill.lower() in text)
        scores["required_skills"] = (required_matches / len(required_skills)) * 100
    else:
        scores["required_skills"] = 50  # Neutral if no required skills defined

    # Preferred skills score (0-100)
    # Capped at preferred_skills_cap matches = 100%, so a job doesn't need to mention
    # every skill to score well — just enough to demonstrate strong overlap.
    preferred_skills = user.get("skills", {}).get("preferred", [])
    preferred_cap = scoring.get("preferred_skills_cap", 4)
    if preferred_skills:
        preferred_matches = sum(1 for skill in preferred_skills if skill.lower() in text)
        scores["preferred_skills"] = min(preferred_matches / preferred_cap, 1.0) * 100
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
    # Keywords are configured in user_profile.yaml; defaults to neutral (50) if not set.
    job_title = job.get("title", "").lower()
    relevant_title_kws = [k.lower() for k in user.get("relevant_title_keywords", [])]
    irrelevant_title_kws = [k.lower() for k in user.get("irrelevant_title_keywords", [])]
    senior_prefixes = [p.lower() for p in user.get("senior_title_prefixes", [])]

    if senior_prefixes and any(job_title.startswith(p) for p in senior_prefixes):
        scores["title_relevance"] = 0
    elif irrelevant_title_kws and any(kw in job_title for kw in irrelevant_title_kws):
        scores["title_relevance"] = 0
    elif relevant_title_kws and any(kw in job_title for kw in relevant_title_kws):
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
