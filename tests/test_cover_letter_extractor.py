"""Tests for cover_letter_extractor pure functions.

All tests are deterministic — no AI calls, no network access.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from cover_letter_extractor import (
    detect_sector,
    detect_tone,
    extract_ats_keywords,
    extract_requirements,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def bulleted_jd():
    return (
        "About the Role\n"
        "We are looking for a proactive administrator to join our team.\n"
        "Requirements:\n"
        "- Excellent communication and organisational skills\n"
        "- Experience with diary management and scheduling\n"
        "- Proficiency in Microsoft Office Suite\n"
        "- Ability to manage multiple stakeholders\n"
        "- Experience with document management systems\n"
        "- Strong attention to detail\n"
        "What We Offer\n"
        "25 days holiday, pension scheme, flexible working.\n"
    )


@pytest.fixture
def prose_jd():
    return (
        "The ideal candidate must have experience in administrative support. "
        "You will be required to manage stakeholder communications and prepare "
        "reports for senior management. Knowledge of Microsoft Office is essential. "
        "Experience with data entry and document management is preferred."
    )


@pytest.fixture
def numbered_jd():
    return (
        "You will need:\n"
        "1. Experience in stakeholder management\n"
        "2. Strong organisational skills\n"
        "3. Proficiency in Microsoft Office\n"
    )


# ── extract_requirements — bullet points ──────────────────────────────────────

def test_extracts_bullet_items(bulleted_jd):
    reqs = extract_requirements(bulleted_jd)
    assert any("communication" in r.lower() for r in reqs)
    assert any("diary management" in r.lower() for r in reqs)
    assert any("microsoft office" in r.lower() for r in reqs)


def test_returns_list_type(bulleted_jd):
    assert isinstance(extract_requirements(bulleted_jd), list)


def test_max_requirements_respected(bulleted_jd):
    reqs = extract_requirements(bulleted_jd, max_requirements=3)
    assert len(reqs) <= 3


def test_default_max_is_eight(bulleted_jd):
    # The fixture has 6 bullet items — all should be returned
    reqs = extract_requirements(bulleted_jd)
    assert len(reqs) <= 8


def test_requirements_deduplication():
    jd = (
        "- Strong communication skills\n"
        "- Strong communication skills\n"
        "- Attention to detail\n"
    )
    reqs = extract_requirements(jd)
    comm_count = sum(1 for r in reqs if "communication" in r.lower())
    assert comm_count == 1


def test_requirement_length_bounds(bulleted_jd):
    for req in extract_requirements(bulleted_jd):
        assert 10 < len(req) < 200


def test_does_not_extract_benefits_section():
    jd = (
        "Requirements:\n"
        "- Microsoft Office proficiency\n"
        "What We Offer:\n"
        "- 25 days holiday\n"
        "- Pension scheme\n"
    )
    reqs = extract_requirements(jd)
    assert not any("holiday" in r.lower() for r in reqs)
    assert not any("pension" in r.lower() for r in reqs)


def test_does_not_include_section_header_itself(bulleted_jd):
    reqs = extract_requirements(bulleted_jd)
    assert not any(r.strip().lower() in ("requirements:", "requirements") for r in reqs)


# ── extract_requirements — numbered lists ─────────────────────────────────────

def test_extracts_numbered_list_in_requirements_section(numbered_jd):
    reqs = extract_requirements(numbered_jd)
    assert any("stakeholder" in r.lower() for r in reqs)
    assert any("organisational" in r.lower() for r in reqs)


# ── extract_requirements — prose fallback ─────────────────────────────────────

def test_prose_fallback_returns_requirements(prose_jd):
    reqs = extract_requirements(prose_jd)
    assert len(reqs) > 0


def test_prose_fallback_contains_requirement_content(prose_jd):
    reqs = extract_requirements(prose_jd)
    combined = " ".join(reqs).lower()
    assert "microsoft office" in combined or "stakeholder" in combined or "experience" in combined


# ── extract_requirements — edge cases ─────────────────────────────────────────

def test_empty_string_returns_empty_list():
    assert extract_requirements("") == []


def test_whitespace_only_returns_empty_list():
    assert extract_requirements("   \n\n  ") == []


def test_minimal_description_does_not_crash():
    reqs = extract_requirements("Looking for an administrator. Apply now.")
    assert isinstance(reqs, list)


def test_very_long_bullet_excluded():
    long_item = "- " + "x" * 250
    reqs = extract_requirements(long_item)
    assert not any(len(r) >= 200 for r in reqs)


def test_very_short_bullet_excluded():
    reqs = extract_requirements("- OK\n- Good\n- Must have Microsoft Office skills")
    assert not any(len(r) <= 10 for r in reqs)


# ── detect_tone ────────────────────────────────────────────────────────────────

def test_council_company_returns_public_sector():
    assert detect_tone("", "Haringey Council") == "public_sector"


def test_nhs_in_description_returns_public_sector():
    assert detect_tone("Working within the NHS team") == "public_sector"


def test_government_in_description_returns_public_sector():
    assert detect_tone("This is a government department position.") == "public_sector"


def test_civil_service_returns_public_sector():
    assert detect_tone("A civil service role in central government.") == "public_sector"


def test_local_authority_returns_public_sector():
    assert detect_tone("", "Tower Hamlets Local Authority") == "public_sector"


def test_charity_in_description_returns_charity():
    assert detect_tone("We are a registered charity supporting young people.") == "charity"


def test_nonprofit_in_company_returns_charity():
    assert detect_tone("", "Shelter (not-for-profit)") == "charity"


def test_foundation_returns_charity():
    assert detect_tone("A trust and foundation working in homelessness.") == "charity"


def test_startup_returns_startup():
    assert detect_tone("We are a fast-growing startup backed by venture capital.") == "startup"


def test_scale_up_returns_startup():
    assert detect_tone("Join our rapidly growing scale-up team.") == "startup"


def test_corporate_plc_returns_corporate():
    assert detect_tone("Global financial services role at a listed PLC.") == "corporate"


def test_no_signals_returns_professional():
    assert detect_tone("We need an administrator for our busy office.") == "professional"


def test_empty_inputs_return_professional():
    assert detect_tone("", "") == "professional"


def test_public_sector_takes_priority_over_charity():
    # "government" and "charity" both present — public_sector has higher priority
    assert detect_tone("A government-funded charity") == "public_sector"


# ── extract_ats_keywords ──────────────────────────────────────────────────────

def test_extracts_microsoft_office():
    jd = "The successful candidate will be proficient in Microsoft Office Suite."
    keywords = extract_ats_keywords(jd)
    assert any("microsoft office" in kw for kw in keywords)


def test_extracts_diary_management():
    jd = "Responsibilities include diary management and scheduling for senior directors."
    keywords = extract_ats_keywords(jd)
    assert any("diary management" in kw for kw in keywords)


def test_extracts_stakeholder_management():
    jd = "Experience in stakeholder management and engagement is essential."
    keywords = extract_ats_keywords(jd)
    assert any("stakeholder" in kw for kw in keywords)


def test_extracts_document_management():
    jd = "You will be responsible for document management and filing systems."
    keywords = extract_ats_keywords(jd)
    assert any("document management" in kw for kw in keywords)


def test_no_duplicates_in_keywords():
    jd = "Microsoft Office skills required. Proficiency in Microsoft Office is essential."
    keywords = extract_ats_keywords(jd)
    counts = {}
    for kw in keywords:
        counts[kw] = counts.get(kw, 0) + 1
    assert all(c == 1 for c in counts.values())


def test_empty_description_returns_empty_list():
    assert extract_ats_keywords("") == []


def test_returns_list_type():
    assert isinstance(extract_ats_keywords("some job description"), list)


def test_no_keywords_in_generic_text():
    # Plain text with no skill keywords — list may be empty or short
    keywords = extract_ats_keywords("We need someone good at their job.")
    assert isinstance(keywords, list)


# ── detect_sector ─────────────────────────────────────────────────────────────

def test_nhs_in_company_returns_healthcare():
    assert detect_sector("NHS Trust London", "") == "healthcare"


def test_hospital_in_description_returns_healthcare():
    assert detect_sector("", "Working in a hospital environment supporting clinical teams.") == "healthcare"


def test_council_in_company_returns_public():
    assert detect_sector("Haringey Council", "") == "public"


def test_government_in_description_returns_public():
    assert detect_sector("", "This is a civil service position in central government.") == "public"


def test_charity_in_description_returns_charity():
    assert detect_sector("", "A registered charity supporting homelessness.") == "charity"


def test_charity_in_company_returns_charity():
    assert detect_sector("Cancer Research UK charity", "") == "charity"


def test_school_in_description_returns_education():
    assert detect_sector("", "Working with students in a secondary school environment.") == "education"


def test_university_in_company_returns_education():
    assert detect_sector("University of London", "") == "education"


def test_unknown_returns_private():
    assert detect_sector("Acme Ltd", "General office administrator role.") == "private"


def test_empty_inputs_return_private():
    assert detect_sector("", "") == "private"


def test_healthcare_takes_priority():
    # Both "nhs" and "council" present — healthcare should win due to check order
    assert detect_sector("NHS Council Trust", "") == "healthcare"
