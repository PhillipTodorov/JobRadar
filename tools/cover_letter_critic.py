"""Pure functions for quality-checking a cover letter draft.

No AI calls — all checks are deterministic and fully testable.
These run on the draft *before* and *after* the AI critique to give
an objective quality signal without spending an extra API call.
"""

import re

# Phrases that appear frequently in AI-generated cover letters.
# Checked case-insensitively.
AI_PHRASES = [
    "proven track record",
    "results-oriented",
    "i am passionate about",
    "highly motivated",
    "team player",
    "i am excited to",
    "i would be a great fit",
    "i am confident that",
    "i am writing to express",
    "to whom it may concern",
    "in today's fast-paced",
    "synergistic",
    "leverage my",
    "hard-working professional",
    "go above and beyond",
    "detail-oriented professional",
    "strong work ethic",
    "i believe i would be",
    "dynamic environment",
    "i am thrilled",
    "i am delighted",
    "exceptional opportunity",
]

# Openers that read as generic / auto-generated
_GENERIC_OPENERS = [
    "i am writing to",
    "i wish to apply",
    "please find enclosed",
    "i would like to apply",
    "i am applying for",
    "i am interested in",
    "i am excited to apply",
    "i am thrilled to",
    "i am delighted to",
    "with great enthusiasm",
    "i have recently come across",
]

# Word-count targets for a UK admin/coordinator cover letter
MIN_WORDS = 180
MAX_WORDS = 450


def detect_ai_phrases(text: str) -> list:
    """Return a list of AI cliché phrases found in the cover letter.

    Case-insensitive substring search against the AI_PHRASES list.

    Args:
        text: Cover letter text.

    Returns:
        List of matched phrases exactly as they appear in AI_PHRASES.
    """
    if not text:
        return []
    text_lower = text.lower()
    return [phrase for phrase in AI_PHRASES if phrase.lower() in text_lower]


def word_count(text: str) -> int:
    """Count words by splitting on whitespace.

    Args:
        text: Any text string.

    Returns:
        Integer word count. Empty / whitespace-only strings return 0.
    """
    if not text or not text.strip():
        return 0
    return len(text.split())


def check_length(text: str) -> str:
    """Classify the cover letter's length.

    Args:
        text: Cover letter text.

    Returns:
        'too_short' if < MIN_WORDS (180)
        'too_long'  if > MAX_WORDS (450)
        'ok'        otherwise
    """
    count = word_count(text)
    if count < MIN_WORDS:
        return "too_short"
    if count > MAX_WORDS:
        return "too_long"
    return "ok"


def check_company_mentioned(text: str, company: str) -> bool:
    """Check whether the company name appears in the cover letter.

    Args:
        text: Cover letter text.
        company: Company name to look for.

    Returns:
        True if found (case-insensitive). False if company is empty or not found.
    """
    if not company or not text:
        return False
    return company.lower() in text.lower()


def check_keywords_present(text: str, keywords: list) -> list:
    """Return ATS keywords from the job description that are absent from the letter.

    Args:
        text: Cover letter text.
        keywords: List of ATS keyword strings extracted from the job description.

    Returns:
        List of keywords NOT found in text (case-insensitive).
    """
    if not keywords:
        return []
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() not in text_lower]


def opening_is_generic(text: str) -> bool:
    """Check whether the cover letter opens with a known generic phrase.

    Only inspects the first sentence.

    Args:
        text: Cover letter text.

    Returns:
        True if the first sentence matches a known generic opener pattern.
    """
    if not text or not text.strip():
        return False
    first_sentence = re.split(r"[.!?]", text.strip())[0].lower()
    return any(opener in first_sentence for opener in _GENERIC_OPENERS)


def run_quality_checks(text: str, company: str, ats_keywords: list) -> dict:
    """Run all pure quality checks on a cover letter draft.

    Args:
        text: Cover letter text.
        company: Target company name.
        ats_keywords: ATS keywords extracted from the job description.

    Returns:
        Dict with keys:
            ai_phrases:      list of AI clichés found
            missing_keywords: ATS keywords absent from the letter
            length_status:   'too_short' | 'ok' | 'too_long'
            word_count:      integer word count
            generic_opening: bool — True if opening is generic
            company_present: bool — True if company name found
            passes:          bool — True if no critical issues
    """
    ai_phrases = detect_ai_phrases(text)
    missing_keywords = check_keywords_present(text, ats_keywords)
    length_status = check_length(text)
    generic_opening = opening_is_generic(text)
    company_present = check_company_mentioned(text, company)
    wc = word_count(text)

    passes = (
        len(ai_phrases) == 0
        and length_status == "ok"
        and not generic_opening
        and company_present
    )

    return {
        "ai_phrases": ai_phrases,
        "missing_keywords": missing_keywords,
        "length_status": length_status,
        "word_count": wc,
        "generic_opening": generic_opening,
        "company_present": company_present,
        "passes": passes,
    }
