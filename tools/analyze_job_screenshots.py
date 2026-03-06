"""Analyze job listing screenshots using Claude vision.

Extracts job details from screenshots and scores them against the user profile.

Usage:
    python analyze_job_screenshots.py <image1> [image2 ...]
    python analyze_job_screenshots.py --dir <directory>

Output: JSON array of scored job results written to stdout and
        saved to .tmp/screenshot_results.json
"""

import base64
import json
import os
import sys
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
TMP_DIR = PROJECT_ROOT / ".tmp"
RESULTS_PATH = TMP_DIR / "screenshot_results.json"

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def load_profile():
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(f"User profile not found: {PROFILE_PATH}")
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_fit_score(job, profile):
    """Score a job dict against the user profile (0-100)."""
    user = profile.get("profile", {})
    scoring = profile.get("scoring", {})
    weights = scoring.get("weights", {
        "required_skills": 0.30,
        "preferred_skills": 0.35,
        "location": 0.25,
        "title_relevance": 0.10,
    })

    text = (job.get("description", "") + " " + job.get("title", "")).lower()

    # Dealbreakers
    for dealbreaker in user.get("dealbreakers", []):
        if dealbreaker.lower() in text:
            return 0

    scores = {}

    required_skills = user.get("skills", {}).get("required", [])
    if required_skills:
        matches = sum(1 for s in required_skills if s.lower() in text)
        scores["required_skills"] = (matches / len(required_skills)) * 100
    else:
        scores["required_skills"] = 50

    preferred_skills = user.get("skills", {}).get("preferred", [])
    if preferred_skills:
        matches = sum(1 for s in preferred_skills if s.lower() in text)
        scores["preferred_skills"] = (matches / len(preferred_skills)) * 100
    else:
        scores["preferred_skills"] = 50

    job_location = job.get("location", "").lower()
    preferred_locs = user.get("locations", {}).get("preferred", [])
    acceptable_locs = user.get("locations", {}).get("acceptable", [])
    if any(loc.lower() in job_location for loc in preferred_locs):
        scores["location"] = 100
    elif any(loc.lower() in job_location for loc in acceptable_locs):
        scores["location"] = 50
    else:
        scores["location"] = 0

    # Title relevance — admin/office/coordinator roles preferred
    job_title = job.get("title", "").lower()
    relevant_title_keywords = [
        "admin", "assistant", "coordinator", "manager", "officer",
        "analyst", "support", "executive", "office", "pmo", "project",
    ]
    if any(kw in job_title for kw in relevant_title_keywords):
        scores["title_relevance"] = 100
    else:
        scores["title_relevance"] = 50

    return round(sum(scores.get(k, 0) * weights.get(k, 0) for k in weights))


def extract_job_from_image(client, image_path: Path) -> dict:
    """Use Claude vision to extract structured job data from a screenshot."""
    media_type = MEDIA_TYPES.get(image_path.suffix.lower(), "image/png")
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "Extract job listing details from this screenshot. "
                        "Return only a JSON object with these exact keys:\n"
                        "{\n"
                        '  "title": "job title",\n'
                        '  "company": "company name",\n'
                        '  "location": "location shown (city, remote, hybrid, etc.)",\n'
                        '  "salary": "salary or salary range if shown, else null",\n'
                        '  "description": "all visible job description and responsibilities text",\n'
                        '  "requirements": "all visible requirements, skills, and qualifications text"\n'
                        "}\n"
                        "If a field is not visible, use null. Return only valid JSON."
                    ),
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def analyze_screenshots(image_paths: list[Path]) -> list[dict]:
    """Extract and score jobs from a list of image paths."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    profile = load_profile()
    results = []

    for img_path in image_paths:
        print(f"  Analysing {img_path.name}...", file=sys.stderr)
        try:
            job = extract_job_from_image(client, img_path)
            # Merge description + requirements for scoring
            combined = f"{job.get('description', '')} {job.get('requirements', '')}"
            job["description"] = combined
            job["fit_score"] = calculate_fit_score(job, profile)
            job["source_image"] = img_path.name
            results.append(job)
        except Exception as exc:
            results.append({
                "title": img_path.name,
                "company": "Unknown",
                "location": "",
                "salary": None,
                "description": "",
                "requirements": "",
                "fit_score": 0,
                "source_image": img_path.name,
                "error": str(exc),
            })

    results.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    TMP_DIR.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python analyze_job_screenshots.py <image1> [image2 ...]", file=sys.stderr)
        sys.exit(1)

    if args[0] == "--dir":
        directory = Path(args[1])
        paths = [p for p in sorted(directory.iterdir()) if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    else:
        paths = [Path(a) for a in args]

    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"Files not found: {missing}", file=sys.stderr)
        sys.exit(1)

    print(f"Analysing {len(paths)} screenshot(s)...", file=sys.stderr)
    results = analyze_screenshots(paths)
    print(json.dumps(results, indent=2))
