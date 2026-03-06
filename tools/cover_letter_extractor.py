"""Pure functions for extracting structured data from job descriptions.

No AI calls — all logic is deterministic and fully testable.
"""

import re

# Tone detection keyword sets (checked in priority order)
_PUBLIC_SECTOR = {
    "council", "borough", "nhs", "civil service", "government",
    "local authority", "hmrc", "public sector", "ministry", "department for",
}
_CHARITY = {
    "charity", "charitable", "nonprofit", "not-for-profit", "ngo",
    "hospice", "voluntary sector", "foundation", "trust",
}
_STARTUP = {
    "startup", "start-up", "scale-up", "scaleup", "fast-growing",
    "series a", "series b", "venture-backed", "seed stage",
}
_CORPORATE = {
    "plc", "financial services", "global", "multinational",
    "consulting", "professional services", "investment bank",
}

# Section headers that introduce requirement lists
_REQUIREMENT_HEADERS = re.compile(
    r"(essential|required|requirements|you will have|you must have|"
    r"you will need|you should have|key skills|what we.re looking for|"
    r"the ideal candidate|minimum qualifications|about you|skills and experience)",
    re.IGNORECASE,
)

# Section headers that signal we should stop extracting requirements
_NOISE_HEADERS = re.compile(
    r"^(about us|about the (company|role|team)|what we offer|"
    r"benefits|salary|package|we offer|in return|"
    r"how to apply|application process|closing date|apply now)",
    re.IGNORECASE,
)

# Signals used in fallback sentence-level extraction
_REQUIREMENT_SIGNALS = re.compile(
    r"\b(must|required|essential|experience in|knowledge of|"
    r"ability to|proficient|familiar with)\b",
    re.IGNORECASE,
)

# Known skill/tool patterns to scan for ATS keyword extraction
_SKILL_PATTERNS = [
    r"microsoft (?:office|word|excel|outlook|powerpoint|teams|project|sharepoint)",
    r"google (?:docs|drive|sheets|workspace)",
    r"(?:diary|calendar) management",
    r"stakeholder (?:management|engagement|liaison|communication)",
    r"project (?:management|coordination|support|administration)",
    r"document management",
    r"data (?:entry|analysis|visualisation|visualization)",
    r"minute[- ]taking",
    r"travel (?:arrangements|booking|coordination)",
    r"expense[s]? (?:processing|management)",
    r"meeting (?:coordination|scheduling|facilitation)",
    r"budget management",
    r"office management",
    r"administrative support",
    r"customer service",
    r"communication skills?",
    r"organisational skills?",
    r"attention to detail",
    r"multitasking",
    r"time management",
]


def extract_requirements(description: str, max_requirements: int = 8) -> list:
    """Extract key requirements from a job description.

    Looks for bullet-pointed items in requirement sections first. Falls back
    to sentences containing requirement signals if no bullets are found.

    Args:
        description: Raw job description text.
        max_requirements: Maximum number of requirements to return.

    Returns:
        List of requirement strings, capped at max_requirements.
    """
    if not description or not description.strip():
        return []

    lines = description.splitlines()
    requirements = []
    in_requirements_section = False
    in_noise_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Entering a requirements section (resets noise flag too)
        if _REQUIREMENT_HEADERS.search(stripped):
            in_requirements_section = True
            in_noise_section = False
            continue

        # Entering a noise section (benefits, how to apply, etc.)
        if _NOISE_HEADERS.match(stripped):
            in_noise_section = True
            in_requirements_section = False
            continue

        # Skip everything inside a noise section
        if in_noise_section:
            continue

        # Bullet point items (-, *, •, ·, ▪, ▸, ►)
        bullet = re.match(r"^[\-\*\•·▪▸►]\s+(.+)$", stripped)
        if bullet:
            item = bullet.group(1).strip()
            if 10 < len(item) < 200:
                requirements.append(item)
            continue

        # Numbered list items — only inside a known requirements section
        numbered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if numbered and in_requirements_section:
            item = numbered.group(1).strip()
            if 10 < len(item) < 200:
                requirements.append(item)

    # Fallback: sentence-level extraction when no bullets found
    if not requirements:
        for sentence in re.split(r"(?<=[.!?])\s+", description):
            sentence = sentence.strip()
            if _REQUIREMENT_SIGNALS.search(sentence) and 15 < len(sentence) < 200:
                requirements.append(sentence)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for req in requirements:
        key = req.lower()[:50]
        if key not in seen:
            seen.add(key)
            unique.append(req)

    return unique[:max_requirements]


def detect_tone(description: str, company: str = "") -> str:
    """Detect the organisational tone from the job description and company name.

    Returns one of: 'public_sector', 'charity', 'startup', 'corporate', 'professional'
    Priority: public_sector > charity > startup > corporate > professional
    """
    combined = (description + " " + company).lower()

    if any(signal in combined for signal in _PUBLIC_SECTOR):
        return "public_sector"
    if any(signal in combined for signal in _CHARITY):
        return "charity"
    if any(signal in combined for signal in _STARTUP):
        return "startup"
    if any(signal in combined for signal in _CORPORATE):
        return "corporate"
    return "professional"


def extract_ats_keywords(description: str) -> list:
    """Extract keywords from a job description for ATS optimisation.

    Scans for known skill/tool multi-word phrases. Returns a deduplicated list.

    Args:
        description: Raw job description text.

    Returns:
        Deduplicated list of matched keyword phrases.
    """
    if not description:
        return []

    desc_lower = description.lower()
    found = []
    for pattern in _SKILL_PATTERNS:
        for match in re.findall(pattern, desc_lower):
            found.append(match)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for kw in found:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique


def detect_sector(company: str, description: str) -> str:
    """Infer the sector of the employer from company name and description.

    Returns one of: 'healthcare', 'education', 'public', 'charity', 'private'
    """
    combined = (company + " " + description).lower()

    if any(w in combined for w in ["nhs", "hospital", "clinical", "healthcare", "health service"]):
        return "healthcare"
    if any(w in combined for w in ["school", "university", "college", "academy", "education", "students"]):
        return "education"
    if any(w in combined for w in ["council", "government", "civil service", "local authority", "borough", "hmrc"]):
        return "public"
    if any(w in combined for w in ["charity", "charitable", "nonprofit", "ngo", "voluntary", "foundation"]):
        return "charity"
    return "private"
