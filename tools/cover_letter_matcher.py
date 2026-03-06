"""Pure functions for matching job requirements to user experience.

No AI calls — all logic is deterministic and fully testable.
"""

import re

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "that",
    "this", "these", "those", "i", "you", "we", "they", "it", "its",
    "our", "your", "their", "as", "such", "any", "all", "both", "each",
    "within", "across", "including", "through", "into", "during", "about",
}


def _tokenise(text: str) -> set:
    """Lowercase, strip punctuation, split into tokens, remove stop words."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}


def _strength_label(score: float) -> str:
    """Convert numeric Jaccard score to a human-readable strength label."""
    if score >= 0.35:
        return "strong"
    if score >= 0.15:
        return "partial"
    if score > 0.0:
        return "weak"
    return "none"


def score_match_strength(requirement: str, text: str) -> float:
    """Score how well a requirement is covered by a block of text.

    Uses Jaccard similarity on content tokens (stop words removed).

    Args:
        requirement: The job requirement string.
        text: The text to match against (e.g. employment history entry).

    Returns:
        Float 0.0–1.0. 0.0 = no overlap, 1.0 = perfect token match.
    """
    req_tokens = _tokenise(requirement)
    text_tokens = _tokenise(text)

    if not req_tokens or not text_tokens:
        return 0.0

    intersection = req_tokens & text_tokens
    union = req_tokens | text_tokens
    return len(intersection) / len(union)


def match_requirement_to_history(requirement: str, employment_history: list) -> dict:
    """Find the best matching snippet from employment history entries.

    Scores each entry's job_description against the requirement and returns
    the entry with the highest Jaccard score.

    Args:
        requirement: Single requirement string.
        employment_history: List of dicts with keys: company, job_title, job_description.

    Returns:
        Dict with keys: snippet, company, job_title, score, strength.
        strength='none' when no useful match is found.
    """
    best = {
        "snippet": "",
        "company": "",
        "job_title": "",
        "score": 0.0,
        "strength": "none",
    }

    for entry in employment_history:
        description = entry.get("job_description", "")
        if not description:
            continue

        score = score_match_strength(requirement, description)
        if score > best["score"]:
            best = {
                "snippet": description,
                "company": entry.get("company", ""),
                "job_title": entry.get("job_title", ""),
                "score": score,
                "strength": _strength_label(score),
            }

    return best


def match_requirement_to_qa(requirement: str, qa_bank: dict) -> dict:
    """Find the best matching answer from the Q&A bank.

    Scores both the question and the answer against the requirement,
    taking the higher of the two scores per entry.

    Args:
        requirement: Single requirement string.
        qa_bank: Dict mapping question strings to answer strings.

    Returns:
        Dict with keys: answer, question, score, strength.
        strength='none' when no useful match is found.
    """
    best = {
        "answer": "",
        "question": "",
        "score": 0.0,
        "strength": "none",
    }

    for question, answer in qa_bank.items():
        if not answer:
            continue

        score = max(
            score_match_strength(requirement, question),
            score_match_strength(requirement, str(answer)),
        )
        if score > best["score"]:
            best = {
                "answer": str(answer),
                "question": question,
                "score": score,
                "strength": _strength_label(score),
            }

    return best


def build_match_report(requirements: list, employment_history: list, qa_bank: dict) -> dict:
    """For each requirement, find the best match from employment history or Q&A bank.

    Employment history is preferred when its score is equal to or higher than the
    Q&A match. Requirements with strength 'none' or 'weak' are listed as unmatched.

    Args:
        requirements: List of requirement strings extracted from the job description.
        employment_history: List of employment entry dicts.
        qa_bank: Dict of Q&A pairs.

    Returns:
        Dict with keys:
            matches:         list of per-requirement match dicts (includes 'requirement' key)
            unmatched:       list of requirement strings with no good match
            overall_quality: float 0.0–1.0 — mean match score across all requirements
    """
    matches = []
    unmatched = []
    scores = []

    for req in requirements:
        history_match = match_requirement_to_history(req, employment_history)
        qa_match = match_requirement_to_qa(req, qa_bank)

        # Prefer employment history when scores are tied or history wins
        if history_match["score"] >= qa_match["score"]:
            best = {**history_match, "source": "employment_history", "requirement": req}
        else:
            best = {**qa_match, "source": "qa_bank", "requirement": req}

        matches.append(best)
        scores.append(best["score"])

        if best["strength"] in ("none", "weak"):
            unmatched.append(req)

    overall_quality = round(sum(scores) / len(scores), 2) if scores else 0.0

    return {
        "matches": matches,
        "unmatched": unmatched,
        "overall_quality": overall_quality,
    }
