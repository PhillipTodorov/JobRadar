"""Tests for cover_letter_matcher pure functions.

All tests are deterministic — no AI calls, no network access.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from cover_letter_matcher import (
    build_match_report,
    match_requirement_to_history,
    match_requirement_to_qa,
    score_match_strength,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def employment_history():
    return [
        {
            "company": "Knight Frank",
            "job_title": "PMO Analyst",
            "job_description": (
                "Coordinated IT project documentation, facilitated cross-functional "
                "team meetings, managed stakeholder communications, supported resource "
                "allocation across departments."
            ),
        },
        {
            "company": "Jacobs Engineering",
            "job_title": "V&V Analyst",
            "job_description": (
                "Prepared comprehensive reports and dashboards for senior management. "
                "Streamlined administrative workflows, significantly improving efficiency "
                "and turnaround times. Trained colleagues in data visualisation."
            ),
        },
    ]


@pytest.fixture
def qa_bank():
    return {
        "Describe your administrative experience": (
            "Experienced in document management, scheduling, and stakeholder liaison."
        ),
        "What are your key skills?": (
            "Microsoft Office, project coordination, communication."
        ),
        "Describe yourself": (
            "Proactive and organised professional with exceptional attention to detail."
        ),
    }


# ── score_match_strength ──────────────────────────────────────────────────────

def test_identical_texts_score_one():
    assert score_match_strength("stakeholder management", "stakeholder management") == 1.0


def test_no_content_word_overlap_scores_zero():
    assert score_match_strength("python programming", "diary management") == 0.0


def test_partial_overlap_between_zero_and_one():
    score = score_match_strength("stakeholder communication", "managed stakeholder relationships")
    assert 0.0 < score < 1.0


def test_empty_requirement_returns_zero():
    assert score_match_strength("", "some job description text") == 0.0


def test_empty_text_returns_zero():
    assert score_match_strength("diary management", "") == 0.0


def test_both_empty_returns_zero():
    assert score_match_strength("", "") == 0.0


def test_score_is_symmetric():
    a = "meeting coordination and scheduling"
    b = "scheduling meetings for senior management"
    assert score_match_strength(a, b) == score_match_strength(b, a)


def test_score_bounded_zero_to_one():
    score = score_match_strength("administration coordination", "administrative support role")
    assert 0.0 <= score <= 1.0


def test_case_insensitive():
    assert score_match_strength("Stakeholder Management", "stakeholder management") == 1.0


def test_stop_words_only_requirement_returns_zero():
    # After removing stop words, no content tokens remain
    assert score_match_strength("the a of in on at", "administration team") == 0.0


def test_shared_content_words_increase_score():
    base = score_match_strength("administration", "office administration role")
    higher = score_match_strength("administration office", "office administration role")
    assert higher >= base


# ── match_requirement_to_history ──────────────────────────────────────────────

def test_returns_dict_with_all_keys(employment_history):
    result = match_requirement_to_history("stakeholder communication", employment_history)
    for key in ("snippet", "company", "job_title", "score", "strength"):
        assert key in result


def test_finds_better_matching_entry(employment_history):
    # "reports dashboards senior management" maps strongly to Jacobs
    result = match_requirement_to_history("reports dashboards senior management", employment_history)
    assert result["company"] == "Jacobs Engineering"


def test_strength_partial_or_better_for_reasonable_match(employment_history):
    result = match_requirement_to_history("stakeholder communications meetings", employment_history)
    assert result["strength"] in ("strong", "partial")


def test_no_match_returns_strength_none(employment_history):
    result = match_requirement_to_history("python machine learning neural networks", employment_history)
    assert result["strength"] == "none"
    assert result["score"] == 0.0


def test_no_match_returns_empty_strings(employment_history):
    result = match_requirement_to_history("blockchain cryptography", employment_history)
    assert result["snippet"] == ""
    assert result["company"] == ""


def test_empty_history_returns_none_strength():
    result = match_requirement_to_history("any requirement", [])
    assert result["strength"] == "none"


def test_entry_missing_job_description_is_skipped():
    history = [{"company": "NoDesc Corp", "job_title": "Admin"}]
    result = match_requirement_to_history("stakeholder management", history)
    assert result["strength"] == "none"


def test_entry_with_empty_job_description_is_skipped():
    history = [{"company": "Corp", "job_title": "Admin", "job_description": ""}]
    result = match_requirement_to_history("any requirement", history)
    assert result["strength"] == "none"


def test_score_is_float(employment_history):
    result = match_requirement_to_history("document management", employment_history)
    assert isinstance(result["score"], float)


def test_score_non_negative(employment_history):
    result = match_requirement_to_history("anything", employment_history)
    assert result["score"] >= 0.0


# ── match_requirement_to_qa ───────────────────────────────────────────────────

def test_returns_dict_with_all_keys(qa_bank):
    result = match_requirement_to_qa("scheduling and document management", qa_bank)
    for key in ("answer", "question", "score", "strength"):
        assert key in result


def test_finds_relevant_qa_answer(qa_bank):
    result = match_requirement_to_qa("document management scheduling", qa_bank)
    assert result["strength"] in ("strong", "partial")
    combined = (result["answer"] + " " + result["question"]).lower()
    assert "scheduling" in combined or "document" in combined


def test_no_match_returns_none_strength(qa_bank):
    result = match_requirement_to_qa("blockchain cryptography solidity", qa_bank)
    assert result["strength"] == "none"


def test_empty_qa_bank_returns_none_strength():
    result = match_requirement_to_qa("stakeholder management", {})
    assert result["strength"] == "none"


def test_empty_answers_are_skipped():
    qa = {
        "What are your skills?": "",
        "Tell us about yourself": "Organised and highly proactive.",
    }
    result = match_requirement_to_qa("organised proactive", qa)
    assert result["strength"] != "none"
    assert result["answer"] == "Organised and highly proactive."


def test_scores_both_question_and_answer():
    # The answer has the overlap, the question does not
    qa = {"Irrelevant question text": "Extensive experience in stakeholder management and coordination."}
    result = match_requirement_to_qa("stakeholder coordination management", qa)
    assert result["strength"] in ("strong", "partial")


def test_score_non_negative(qa_bank):
    result = match_requirement_to_qa("anything", qa_bank)
    assert result["score"] >= 0.0


# ── build_match_report ────────────────────────────────────────────────────────

def test_returns_dict_with_required_keys(employment_history, qa_bank):
    reqs = ["stakeholder management", "document management"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert "matches" in report
    assert "unmatched" in report
    assert "overall_quality" in report


def test_matches_count_equals_requirements(employment_history, qa_bank):
    reqs = ["stakeholder management", "document management", "python programming"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert len(report["matches"]) == 3


def test_each_match_contains_requirement_field(employment_history, qa_bank):
    reqs = ["document management", "team meetings"]
    report = build_match_report(reqs, employment_history, qa_bank)
    for match in report["matches"]:
        assert "requirement" in match
        assert match["requirement"] in reqs


def test_unmatched_contains_weak_requirements(employment_history, qa_bank):
    reqs = ["blockchain development", "stakeholder management"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert "blockchain development" in report["unmatched"]


def test_strong_match_not_in_unmatched(employment_history, qa_bank):
    reqs = ["stakeholder communications meetings"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert "stakeholder communications meetings" not in report["unmatched"]


def test_overall_quality_between_zero_and_one(employment_history, qa_bank):
    reqs = ["stakeholder management", "python programming"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert 0.0 <= report["overall_quality"] <= 1.0


def test_empty_requirements_returns_zero_quality(employment_history, qa_bank):
    report = build_match_report([], employment_history, qa_bank)
    assert report["overall_quality"] == 0.0
    assert report["matches"] == []
    assert report["unmatched"] == []


def test_all_unmatched_requirements_reported(employment_history, qa_bank):
    reqs = ["blockchain", "machine learning", "quantum computing"]
    report = build_match_report(reqs, employment_history, qa_bank)
    assert len(report["unmatched"]) == 3


def test_prefers_employment_history_when_score_equal_or_higher(employment_history, qa_bank):
    # "project documentation facilitated meetings" is very specific to Knight Frank's
    # history and doesn't appear in the QA bank answers, so history should win clearly
    report = build_match_report(["project documentation facilitated meetings departments"], employment_history, qa_bank)
    assert report["matches"][0]["source"] == "employment_history"


def test_falls_back_to_qa_bank_when_history_has_no_match(qa_bank):
    thin_history = [{"company": "Corp", "job_title": "Admin", "job_description": ""}]
    report = build_match_report(["document management scheduling"], thin_history, qa_bank)
    assert report["matches"][0]["source"] == "qa_bank"


def test_overall_quality_rounded_to_two_decimals(employment_history, qa_bank):
    reqs = ["stakeholder management", "document management", "reporting"]
    report = build_match_report(reqs, employment_history, qa_bank)
    # Should be rounded to 2 decimal places
    assert report["overall_quality"] == round(report["overall_quality"], 2)
