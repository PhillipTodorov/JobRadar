"""Score jobs against user profile for fit matching.

Uses smart keyword matching to score how well each job matches
the user's skills, title preferences, salary, location, and
experience level.
"""

import json
import re
from pathlib import Path

import yaml

from scraper_utils import TMP_DIR

PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
CONFIG_PATH = PROJECT_ROOT / "job_search_config.yaml"

# ---------------------------------------------------------------------------
# Helpers: years-of-experience extraction
# ---------------------------------------------------------------------------

_YEARS_PATTERNS = [
    re.compile(r'(\d+)\s*\+\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s*years?[\'s]?\s*(?:\w+\s+){0,2}experience', re.IGNORECASE),
    re.compile(r'minimum\s+(?:of\s+)?(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'at\s+least\s+(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s*[-\u2013]\s*(\d+)\s*years?', re.IGNORECASE),
    re.compile(r'(\d+)\s+to\s+(\d+)\s*years?', re.IGNORECASE),
]


def extract_years_required(text: str) -> int:
    """Return the maximum years of experience required found in *text*."""
    max_years = 0
    for pattern in _YEARS_PATTERNS:
        for match in pattern.finditer(text):
            groups = [int(g) for g in match.groups() if g is not None]
            if groups:
                max_years = max(max_years, max(groups))
    return max_years


# ---------------------------------------------------------------------------
# Helpers: smart skill matching
# ---------------------------------------------------------------------------

# Common synonyms so "Microsoft Office" also matches "MS Office", etc.
_SKILL_ALIASES = {
    "microsoft office": ["ms office", "office 365", "microsoft 365", "m365"],
    "google workspace": ["g suite", "gsuite", "google docs", "google sheets"],
    "ci/cd": ["ci cd", "cicd", "continuous integration", "continuous deployment"],
    "html/css": ["html", "css"],
    "written communication": ["written communication", "writing skills", "written skills"],
}


def _expand_skill(skill: str) -> list[str]:
    """Expand a skill name into a list of matchable terms.

    Handles compound skills (HTML/CSS → html, css), ampersand splits
    (Administration & Office Management → administration, office management),
    and known aliases.
    """
    s = skill.lower().strip()
    terms = {s}

    # Check alias table first
    for key, aliases in _SKILL_ALIASES.items():
        if s == key:
            terms.update(aliases)
            return list(terms)

    # Split on "/" for compound skills
    if "/" in s:
        for part in s.split("/"):
            p = part.strip()
            if len(p) >= 2:
                terms.add(p)

    # Split on "&" for grouped skills
    if "&" in s:
        for part in s.split("&"):
            p = part.strip()
            if len(p) >= 2:
                terms.add(p)

    return list(terms)


def _skill_in_text(skill: str, text: str) -> bool:
    """Check if a skill (or any of its expanded forms) appears in text.

    Uses word-boundary matching for short terms (<=4 chars) to avoid
    false positives like 'css' matching 'access'.
    """
    for term in _expand_skill(skill):
        if len(term) <= 4:
            if re.search(r'\b' + re.escape(term) + r'\b', text):
                return True
        else:
            if term in text:
                return True
    return False


# ---------------------------------------------------------------------------
# Helpers: salary parsing
# ---------------------------------------------------------------------------

_SALARY_RE = re.compile(r'[\d,]+')


def _parse_salary(salary_str: str) -> tuple:
    """Extract (min_salary, max_salary) from a salary string.

    Returns (None, None) if no usable salary found.
    Handles formats like '£30,000–£33,000 a year', '£35,000+ a year',
    '&pound;37949 per year'.
    """
    if not salary_str:
        return None, None

    cleaned = salary_str.replace("£", "").replace("&pound;", "").replace("\u00a3", "")
    nums = _SALARY_RE.findall(cleaned)
    nums = [int(n.replace(",", "")) for n in nums if n.replace(",", "").isdigit()]

    # Filter to plausible annual salaries (>= 10k)
    # If salary string contains "hour" or "day", skip — we can't compare fairly
    if "hour" in salary_str.lower() or "per hour" in salary_str.lower():
        return None, None
    if "day" in salary_str.lower() and "per day" in salary_str.lower():
        return None, None

    nums = [n for n in nums if n >= 10000]
    if not nums:
        return None, None
    return min(nums), max(nums)


# ---------------------------------------------------------------------------
# Helpers: title keywords from search config
# ---------------------------------------------------------------------------

# Words to ignore when deriving title keywords from search config
_TITLE_STOPWORDS = {"entry", "level", "junior", "senior", "the", "and", "for", "with"}


def _load_title_keywords_from_config() -> list[str]:
    """Derive title-matching keywords from job_search_config.yaml titles."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        titles = cfg.get("search_params", {}).get("titles", [])
        # Return the full title phrases (lowered) for matching
        return [t.lower().strip() for t in titles if t]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main scoring
# ---------------------------------------------------------------------------

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

    Scoring dimensions:
        skills (30%)      – How many of your skills appear in the job
        title (25%)       – Does the job title match what you're looking for
        salary (15%)      – Does the pay meet your expectations
        location (15%)    – Is it in the right place / remote
        experience (15%)  – Is it the right seniority level

    Returns 0 immediately if a dealbreaker is found.
    """
    scores = {}
    user = profile.get("profile", {})
    scoring = profile.get("scoring", {})
    weights = scoring.get("weights", {
        "skills": 0.30,
        "title": 0.25,
        "salary": 0.15,
        "location": 0.15,
        "experience": 0.15,
    })

    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    job_title = job.get("title", "").lower()

    # ── Dealbreakers (instant 0) ────────────────────────────────────────
    for db in user.get("dealbreakers", []):
        if db.lower() in text:
            return 0

    max_years_ok = user.get("experience", {}).get("max_years_required", 99)
    years_required = extract_years_required(text)
    if years_required > max_years_ok:
        return 0

    # ── SKILLS (30%) ────────────────────────────────────────────────────
    # Required matches are worth 2 points, preferred 1 point.
    # Threshold sets how many points = 100%.
    required = user.get("skills", {}).get("required", [])
    preferred = user.get("skills", {}).get("preferred", [])

    req_hits = sum(1 for s in required if _skill_in_text(s, text))
    pref_hits = sum(1 for s in preferred if _skill_in_text(s, text))

    skill_points = req_hits * 2 + pref_hits
    threshold = scoring.get("skill_match_threshold", 10)
    scores["skills"] = min(skill_points / threshold, 1.0) * 100

    # ── TITLE (25%) ─────────────────────────────────────────────────────
    # Check explicit keywords from profile, falling back to search config.
    relevant_kws = [k.lower() for k in user.get("relevant_title_keywords", [])]
    irrelevant_kws = [k.lower() for k in user.get("irrelevant_title_keywords", [])]

    if not relevant_kws:
        relevant_kws = _load_title_keywords_from_config()

    # Irrelevant title → 0
    if irrelevant_kws and any(kw in job_title for kw in irrelevant_kws):
        scores["title"] = 0
    elif relevant_kws:
        # Check for phrase-level matches first (e.g. "administrative assistant")
        phrase_match = any(kw in job_title for kw in relevant_kws)
        if phrase_match:
            scores["title"] = 100
        else:
            # Fall back to individual word matching
            all_words = set()
            for kw in relevant_kws:
                all_words.update(w for w in kw.split() if w not in _TITLE_STOPWORDS and len(w) > 2)
            title_words = set(job_title.split())
            overlap = len(all_words & title_words)
            if overlap >= 2:
                scores["title"] = 80
            elif overlap == 1:
                scores["title"] = 50
            else:
                scores["title"] = 15
    else:
        scores["title"] = 50  # No keywords at all → neutral

    # ── LOCATION (15%) ──────────────────────────────────────────────────
    job_loc = job.get("location", "").lower()
    preferred_locs = [l.lower() for l in user.get("locations", {}).get("preferred", [])]
    acceptable_locs = [l.lower() for l in user.get("locations", {}).get("acceptable", [])]

    # Detect remote/hybrid in location field OR description
    remote_terms = ["remote", "work from home", "wfh", "hybrid", "home based", "home-based"]
    is_remote = any(t in job_loc for t in remote_terms) or any(t in text for t in ["fully remote", "work from home", "remote position", "remote role"])
    is_preferred = any(loc in job_loc for loc in preferred_locs if loc != "remote")
    is_acceptable = any(loc in job_loc for loc in acceptable_locs)
    has_remote_pref = "remote" in preferred_locs

    if is_preferred and (is_remote and has_remote_pref):
        scores["location"] = 100  # Best of both worlds
    elif is_preferred:
        scores["location"] = 100
    elif is_remote and has_remote_pref:
        scores["location"] = 90
    elif is_acceptable:
        scores["location"] = 50
    elif is_remote:
        scores["location"] = 60  # Remote but user didn't list it as preferred
    else:
        scores["location"] = 0

    # ── SALARY (15%) ────────────────────────────────────────────────────
    sal_prefs = user.get("salary", {})
    min_sal = sal_prefs.get("minimum", 0)
    pref_sal = sal_prefs.get("preferred", 0)

    job_sal_min, job_sal_max = _parse_salary(job.get("salary", ""))

    if job_sal_max is not None:
        # Use the higher end of the range for comparison
        job_sal = job_sal_max
        if pref_sal and job_sal >= pref_sal:
            scores["salary"] = 100
        elif min_sal and job_sal >= min_sal:
            if pref_sal and pref_sal > min_sal:
                ratio = (job_sal - min_sal) / (pref_sal - min_sal)
                scores["salary"] = 40 + round(ratio * 50)
            else:
                scores["salary"] = 70
        elif min_sal and job_sal < min_sal:
            scores["salary"] = 10
        else:
            scores["salary"] = 50
    else:
        scores["salary"] = 50  # No salary info → neutral

    # ── EXPERIENCE LEVEL (15%) ──────────────────────────────────────────
    exp_level = user.get("experience", {}).get("level", "")

    entry_terms = ["entry level", "entry-level", "junior", "graduate",
                   "no experience required", "no experience needed",
                   "trainee", "apprentice", "starter"]
    senior_terms = ["senior", "lead", "principal", "head of",
                    "director", "manager", "vp", "vice president", "chief"]

    has_entry_text = any(t in text for t in entry_terms)
    has_senior_title = any(t in job_title for t in senior_terms)

    if exp_level == "entry":
        if has_senior_title:
            scores["experience"] = 0
        elif has_entry_text or years_required <= 1:
            scores["experience"] = 100
        elif years_required <= 2:
            scores["experience"] = 70
        elif years_required <= 3:
            scores["experience"] = 40
        else:
            scores["experience"] = 10
    elif exp_level == "mid":
        if has_senior_title:
            scores["experience"] = 30
        elif years_required <= 5:
            scores["experience"] = 100
        else:
            scores["experience"] = 50
    else:
        scores["experience"] = 60  # No level set → slightly positive

    # ── FINAL WEIGHTED SCORE ────────────────────────────────────────────
    final = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)

    # Store breakdown for debugging
    job["_score_breakdown"] = scores

    return round(final)


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------

def score_jobs(jobs=None):
    """Score all jobs and return sorted by fit score.

    Args:
        jobs: List of job dicts, or None to load from .tmp/

    Returns:
        List of jobs with fit_score field, sorted descending
    """
    if jobs is None:
        jobs = []
        for json_file in TMP_DIR.glob("*_raw.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                jobs.extend(json.load(f))

    if not jobs:
        print("No jobs to score.")
        return []

    profile = load_profile()

    scored_jobs = []
    for job in jobs:
        score = calculate_fit_score(job, profile)
        job_with_score = {**job, "fit_score": score}
        scored_jobs.append(job_with_score)

    scored_jobs.sort(key=lambda x: x["fit_score"], reverse=True)

    # Summary
    total = len(scored_jobs)
    with_score = len([j for j in scored_jobs if j["fit_score"] > 0])
    avg_score = sum(j["fit_score"] for j in scored_jobs) / total if total else 0

    print(f"\nScored {total} jobs:")
    print(f"  Jobs with score > 0: {with_score}")
    print(f"  Jobs filtered (dealbreakers): {total - with_score}")
    print(f"  Average score: {avg_score:.1f}")
    if scored_jobs:
        top = scored_jobs[0]
        print(f"  Top score: {top['fit_score']} - {top['title']} at {top['company']}")
        bd = top.get("_score_breakdown", {})
        if bd:
            parts = ", ".join(f"{k}={v:.0f}" for k, v in bd.items())
            print(f"  Breakdown: {parts}")

    return scored_jobs


def save_scored_jobs(jobs, filename="scored_jobs.json"):
    """Save scored jobs to JSON file."""
    TMP_DIR.mkdir(exist_ok=True)
    filepath = TMP_DIR / filename

    # Strip debug breakdowns before saving
    clean_jobs = []
    for job in jobs:
        j = {k: v for k, v in job.items() if not k.startswith("_")}
        clean_jobs.append(j)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean_jobs, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(clean_jobs)} scored jobs to {filepath}")
    return filepath


if __name__ == "__main__":
    scored = score_jobs()
    if scored:
        save_scored_jobs(scored)
        print("\nTop 10 jobs by fit score:")
        for i, job in enumerate(scored[:10], 1):
            bd = job.get("_score_breakdown", {})
            parts = " | ".join(f"{k}:{v:.0f}" for k, v in bd.items())
            print(f"  {i}. [{job['fit_score']}] {job['title']} at {job['company']}")
            if parts:
                print(f"      {parts}")
