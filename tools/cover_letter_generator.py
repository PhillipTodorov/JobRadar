"""AI-powered cover letter generation pipeline.

Uses Claude to draft, critique (separate call), and refine cover letters.

Pipeline:
    1. extract_requirements / detect_tone / extract_ats_keywords / detect_sector
    2. build_match_report — match requirements to employment history + Q&A bank
    3. draft_cover_letter  — Claude call #1
    4. critique_cover_letter — Claude call #2 (isolated so critique is unbiased)
    5. refine_cover_letter — Claude call #3 (only if critique flags issues)
"""

import json
import re

import anthropic

from cover_letter_extractor import (
    detect_sector,
    detect_tone,
    extract_ats_keywords,
    extract_requirements,
)
from cover_letter_matcher import build_match_report
from cover_letter_critic import run_quality_checks

_MODEL = "claude-sonnet-4-6"

_TONE_INSTRUCTIONS = {
    "public_sector": (
        "formal and measured, public-service oriented. "
        "Show reliability, process-focus, and commitment to serving the public."
    ),
    "charity": (
        "warm, values-driven, and mission-aligned. "
        "Show genuine interest in the cause and collaborative ethos."
    ),
    "startup": (
        "energetic but professional and direct. "
        "Show adaptability, initiative, and comfort with a fast-moving environment."
    ),
    "corporate": (
        "polished and professional. "
        "Show precision, commercial awareness, and ability to work at scale."
    ),
    "professional": (
        "professional and personable — balance warmth with competence."
    ),
}

_SIGN_OFF = {
    "public": "Yours sincerely",
    "charity": "Yours sincerely",
    "healthcare": "Yours sincerely",
    "education": "Yours sincerely",
    "private": "Kind regards",
}

# Phrases that must never appear in the final letter
_BANNED_PHRASES = (
    '"proven track record", "I am passionate", "results-oriented", '
    '"team player", "I am excited to", "I would be a great fit", '
    '"I am confident that", "highly motivated", "detail-oriented professional", '
    '"I am delighted", "I am thrilled", "I am writing to express"'
)


def _format_matches_for_prompt(matches: list) -> str:
    """Format match report into a readable block for the draft prompt."""
    lines = []
    for m in matches:
        req = m.get("requirement", "")
        strength = m.get("strength", "none")
        source = m.get("source", "")

        if source == "employment_history":
            snippet = m.get("snippet", "")[:200]
            company = m.get("company", "")
            role = m.get("job_title", "")
            lines.append(
                f"• {req}  [{strength} match]\n"
                f"  → {role} at {company}: {snippet}"
            )
        elif source == "qa_bank":
            answer = m.get("answer", "")[:200]
            lines.append(
                f"• {req}  [{strength} match]\n"
                f"  → Q&A bank: {answer}"
            )
        else:
            lines.append(f"• {req}  [no match — omit or address only if possible]")

    return "\n".join(lines)


def draft_cover_letter(extracted: dict, matches: dict, company_research: str = "") -> str:
    """Call Claude to produce a first draft of the cover letter.

    Args:
        extracted: Output of cover_letter_extractor functions (job_title, company,
                   tone, sector, ats_keywords, requirements).
        matches:   Output of build_match_report (matches list, unmatched list).
        company_research: Optional cached company research text (used for specificity).

    Returns:
        Raw cover letter text string (stripped).
    """
    client = anthropic.Anthropic()

    job_title = extracted.get("job_title", "the role")
    company = extracted.get("company", "the company")
    tone = extracted.get("tone", "professional")
    sector = extracted.get("sector", "private")

    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["professional"])
    sign_off = _SIGN_OFF.get(sector, "Kind regards")
    matched_text = _format_matches_for_prompt(matches.get("matches", []))

    unmatched = matches.get("unmatched", [])
    unmatched_text = (
        "\n".join(f"• {r}" for r in unmatched) if unmatched else "None"
    )

    company_section = ""
    if company_research:
        company_section = (
            f"\nCOMPANY CONTEXT (weave in 1–2 specific details to show genuine research):\n"
            f"{company_research[:400]}\n"
        )

    prompt = f"""You are writing a cover letter for Phillip Todorov applying to {job_title} at {company}.

TONE: {tone_instruction}

REQUIREMENTS AND HOW PHILLIP MATCHES THEM:
{matched_text}

REQUIREMENTS WITH NO STRONG MATCH (omit, or address only if you can do so honestly):
{unmatched_text}
{company_section}
PHILLIP'S BACKGROUND (use only what is here — do not invent facts):
- PMO Analyst, Knight Frank (Sep 2022 – Jan 2024): coordinated IT project \
documentation, facilitated cross-functional meetings, managed stakeholder \
communications across departments, set up Power Apps user access.
- Verification & Validation Analyst, Jacobs Engineering Group (Jun 2020 – Sep 2022): \
prepared reports and dashboards for senior management, streamlined administrative \
workflows improving efficiency and turnaround times, trained colleagues in data \
visualisation.

WRITING RULES — follow every one:
1. Exactly 3 paragraphs, 260–320 words total.
2. Paragraph 1: A specific, engaging opener referencing this exact role and company. \
   NOT a generic "I am writing to express my interest" opener.
3. Paragraph 2: 2–3 concrete examples from Phillip's real experience mapped to the \
   job requirements — name the company and role each time.
4. Paragraph 3: Brief confident close with a call to action.
5. Vary sentence length — mix short sentences (under 10 words) with longer ones.
6. Use the exact wording of requirements where it fits naturally (ATS matching).
7. Sign off: {sign_off},\\nPhillip Todorov
8. NEVER use any of these phrases: {_BANNED_PHRASES}
9. Write for a human who has read 200 of these today — make it feel specific and genuine.

Output only the cover letter text. Nothing else."""

    message = client.messages.create(
        model=_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def critique_cover_letter(draft: str, extracted: dict, matches: dict) -> dict:
    """Call Claude to critique the draft — this is a separate API call so the
    critique is not biased by having generated the draft itself.

    Args:
        draft:     The draft cover letter text.
        extracted: Extracted job info (job_title, company, ats_keywords).
        matches:   Match report (matches list).

    Returns:
        Dict with keys: ai_phrases, unsupported_claims, missing_keywords,
        word_count, generic_opening, company_mentioned, needs_revision,
        revision_instructions.
        Returns a safe fallback dict if the response cannot be parsed.
    """
    client = anthropic.Anthropic()

    job_title = extracted.get("job_title", "the role")
    company = extracted.get("company", "the company")
    requirements = [m.get("requirement", "") for m in matches.get("matches", [])]
    ats_keywords = extracted.get("ats_keywords", [])

    prompt = f"""You are a critical reviewer of cover letters. Review this cover letter \
for {job_title} at {company}:

---
{draft}
---

Requirements the letter should address:
{chr(10).join(f'- {r}' for r in requirements)}

ATS keywords from the job description that should appear naturally:
{', '.join(ats_keywords) if ats_keywords else 'None specified'}

Check for:
1. Generic AI phrases (e.g. "proven track record", "I am passionate", \
"results-oriented", "I am writing to express")
2. Vague claims not backed by a specific named example
3. ATS keywords from the list above that are absent from the letter
4. Word count — target 260–320 words
5. Whether the opening line is generic or specific to this role/company
6. Whether "{company}" appears by name

Respond in this exact JSON format, no other text:
{{
  "ai_phrases": ["list of any generic AI phrases found, empty if none"],
  "unsupported_claims": ["list of vague unsupported claims, empty if none"],
  "missing_keywords": ["ATS keywords not present, empty if none"],
  "word_count": 0,
  "generic_opening": false,
  "company_mentioned": true,
  "needs_revision": false,
  "revision_instructions": "Specific fix instructions, or empty string if nothing to fix"
}}"""

    message = client.messages.create(
        model=_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text.strip()

    # Extract JSON — model sometimes wraps in markdown fences
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Safe fallback — don't crash if parsing fails
    return {
        "ai_phrases": [],
        "unsupported_claims": [],
        "missing_keywords": [],
        "word_count": 0,
        "generic_opening": False,
        "company_mentioned": True,
        "needs_revision": False,
        "revision_instructions": "",
    }


def refine_cover_letter(draft: str, critique: dict) -> str:
    """Call Claude to fix targeted issues identified by the critique.

    Only called when critique["needs_revision"] is True. Makes surgical
    fixes only — does not rewrite content that passed the critique.

    Args:
        draft:   The draft cover letter text.
        critique: The critique dict from critique_cover_letter.

    Returns:
        Improved cover letter text, or the original draft if no revision needed.
    """
    if not critique.get("needs_revision"):
        return draft

    client = anthropic.Anthropic()

    ai_phrases = critique.get("ai_phrases", [])
    missing_keywords = critique.get("missing_keywords", [])
    revision_instructions = critique.get("revision_instructions", "")

    issues = []
    if ai_phrases:
        issues.append(f"Remove these generic phrases and replace with specific language: {', '.join(ai_phrases)}")
    if missing_keywords:
        issues.append(f"Weave in these missing keywords naturally: {', '.join(missing_keywords)}")
    if revision_instructions:
        issues.append(revision_instructions)

    prompt = f"""Here is a cover letter that needs targeted improvements:

---
{draft}
---

Fix only these specific issues:
{chr(10).join(f'- {issue}' for issue in issues)}

Rules:
- Keep everything else exactly as written — do not paraphrase or restructure.
- Do not add new information that is not already in the letter.
- Maintain the same approximate length and structure.
- Output only the revised letter text, nothing else."""

    message = client.messages.create(
        model=_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_cover_letter(job: dict, databank: dict, company_research: str = "") -> dict:
    """Full five-step pipeline: extract → match → draft → critique → refine.

    Args:
        job:              Job dict (keys: title, company, description, location, ...).
        databank:         User's qa_databank dict (employment_history, questions, ...).
        company_research: Optional cached company research text.

    Returns:
        Dict with keys:
            cover_letter:    Final cover letter text
            match_quality:   Float 0–1 — how well requirements were matched
            unmatched:       List of requirements with no good match
            word_count:      Word count of the final letter
            quality_checks:  Output of run_quality_checks on the final letter
            steps:           List of pipeline steps completed
    """
    description = job.get("description", "")
    job_title = job.get("title", "")
    company = job.get("company", "")

    # Step 1 — Extract
    requirements = extract_requirements(description)
    tone = detect_tone(description, company)
    ats_keywords = extract_ats_keywords(description)
    sector = detect_sector(company, description)

    extracted = {
        "job_title": job_title,
        "company": company,
        "requirements": requirements,
        "tone": tone,
        "ats_keywords": ats_keywords,
        "sector": sector,
    }

    # Step 2 — Match
    employment_history = databank.get("employment_history", [])
    qa_bank = databank.get("questions", {})
    matches = build_match_report(requirements, employment_history, qa_bank)

    # Step 3 — Draft
    draft = draft_cover_letter(extracted, matches, company_research)
    steps = ["extract", "match", "draft"]

    # Step 4 — Critique (separate call — isolated from generation)
    critique = critique_cover_letter(draft, extracted, matches)
    steps.append("critique")

    # Step 5 — Refine (only if critique flagged issues)
    final_letter = draft
    if critique.get("needs_revision"):
        final_letter = refine_cover_letter(draft, critique)
        steps.append("refine")

    quality = run_quality_checks(final_letter, company, ats_keywords)

    return {
        "cover_letter": final_letter,
        "match_quality": matches["overall_quality"],
        "unmatched": matches["unmatched"],
        "word_count": quality["word_count"],
        "quality_checks": quality,
        "steps": steps,
    }
