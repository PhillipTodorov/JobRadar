"""Tests for cover_letter_critic pure functions.

All tests are deterministic — no AI calls, no network access.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from cover_letter_critic import (
    check_company_mentioned,
    check_keywords_present,
    check_length,
    detect_ai_phrases,
    opening_is_generic,
    run_quality_checks,
    word_count,
    MIN_WORDS,
    MAX_WORDS,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

CLEAN_LETTER = (
    "Dear Hiring Manager,\n\n"
    "Having coordinated IT project portfolios at Knight Frank and streamlined "
    "administrative workflows at Jacobs Engineering Group, I was immediately drawn to "
    "this Office Administrator role at Haringey Council. The combination of diary "
    "management responsibilities and cross-departmental stakeholder communication aligns "
    "directly with the work I have done across both organisations over the past four years.\n\n"
    "At Knight Frank, I coordinated documentation for multiple concurrent IT projects, "
    "facilitated cross-functional team meetings, and maintained comprehensive status "
    "reports for senior stakeholders. I also set up user profiles and access for Power "
    "Apps, supporting employees across several departments. At Jacobs Engineering Group, "
    "I prepared reports and dashboards for senior management, trained colleagues in data "
    "visualisation techniques, and streamlined administrative workflows in ways that "
    "measurably improved efficiency and turnaround times. In both roles, proficiency in "
    "Microsoft Office and consistent stakeholder management were central to delivery. "
    "These experiences have given me a strong foundation in the kind of organised, "
    "detail-focused administration this role requires.\n\n"
    "I would welcome the opportunity to discuss how my background fits your team's needs. "
    "I am available for interview at short notice and can be reached at any time.\n\n"
    "Yours sincerely,\nPhillip Todorov"
)

AI_HEAVY_LETTER = (
    "Dear Hiring Manager,\n\n"
    "I am writing to express my interest in this role. I am passionate about "
    "administration and believe I would be a great fit for your team. As a "
    "results-oriented professional with a proven track record of success, I am "
    "highly motivated and excited to join your dynamic environment.\n\n"
    "I am a team player with a strong work ethic who goes above and beyond in "
    "everything I do. I am confident that my experience would make me an excellent "
    "addition to your organisation.\n\n"
    "I look forward to hearing from you.\n\nKind regards,\nPhillip Todorov"
)


# ── detect_ai_phrases ─────────────────────────────────────────────────────────

def test_detects_proven_track_record():
    assert "proven track record" in detect_ai_phrases("I have a proven track record.")


def test_detects_passionate_about():
    assert "i am passionate about" in detect_ai_phrases("I am passionate about this role.")


def test_detects_results_oriented():
    assert "results-oriented" in detect_ai_phrases("As a results-oriented professional.")


def test_detects_i_am_writing_to_express():
    assert "i am writing to express" in detect_ai_phrases("I am writing to express my interest.")


def test_detects_team_player():
    assert "team player" in detect_ai_phrases("I am a team player with strong skills.")


def test_detects_highly_motivated():
    assert "highly motivated" in detect_ai_phrases("I am highly motivated and hard-working.")


def test_clean_letter_returns_empty_list():
    assert detect_ai_phrases(CLEAN_LETTER) == []


def test_ai_heavy_letter_returns_multiple_phrases():
    found = detect_ai_phrases(AI_HEAVY_LETTER)
    assert len(found) >= 3


def test_case_insensitive_detection():
    assert "proven track record" in detect_ai_phrases("PROVEN TRACK RECORD of success.")


def test_empty_text_returns_empty_list():
    assert detect_ai_phrases("") == []


def test_returns_list_type():
    assert isinstance(detect_ai_phrases("some text"), list)


def test_no_duplicate_phrases_returned():
    text = "proven track record. Yes, a proven track record."
    found = detect_ai_phrases(text)
    assert found.count("proven track record") == 1


# ── word_count ────────────────────────────────────────────────────────────────

def test_empty_string_returns_zero():
    assert word_count("") == 0


def test_whitespace_only_returns_zero():
    assert word_count("   \n\t  ") == 0


def test_single_word():
    assert word_count("hello") == 1


def test_known_word_count():
    assert word_count("one two three four five") == 5


def test_counts_across_newlines():
    assert word_count("word1\nword2\nword3") == 3


def test_returns_integer():
    assert isinstance(word_count("some text here"), int)


def test_punctuation_does_not_split_words():
    # "hello," is one token when splitting on whitespace
    assert word_count("hello, world.") == 2


# ── check_length ──────────────────────────────────────────────────────────────

def test_too_short_below_min():
    short = " ".join(["word"] * (MIN_WORDS - 1))
    assert check_length(short) == "too_short"


def test_ok_at_min_boundary():
    at_min = " ".join(["word"] * MIN_WORDS)
    assert check_length(at_min) == "ok"


def test_ok_in_target_range():
    ok = " ".join(["word"] * 280)
    assert check_length(ok) == "ok"


def test_ok_at_max_boundary():
    at_max = " ".join(["word"] * MAX_WORDS)
    assert check_length(at_max) == "ok"


def test_too_long_above_max():
    long = " ".join(["word"] * (MAX_WORDS + 1))
    assert check_length(long) == "too_long"


def test_returns_string():
    assert isinstance(check_length("some text"), str)


def test_empty_string_is_too_short():
    assert check_length("") == "too_short"


# ── check_company_mentioned ───────────────────────────────────────────────────

def test_company_present():
    text = "I am excited to apply to Haringey Council for this role."
    assert check_company_mentioned(text, "Haringey Council") is True


def test_company_absent():
    text = "I am applying for the administrative role here."
    assert check_company_mentioned(text, "Haringey Council") is False


def test_case_insensitive():
    text = "working at haringey council has always appealed to me."
    assert check_company_mentioned(text, "Haringey Council") is True


def test_empty_company_returns_false():
    assert check_company_mentioned("some letter text", "") is False


def test_empty_text_returns_false():
    assert check_company_mentioned("", "Some Company") is False


def test_partial_company_name_match():
    # "Council" alone should still match "Haringey Council" if substring present
    text = "I was drawn to the Council's commitment to local residents."
    assert check_company_mentioned(text, "Council") is True


# ── check_keywords_present ───────────────────────────────────────────────────

def test_missing_keyword_returned():
    text = "I have experience in stakeholder management."
    missing = check_keywords_present(text, ["diary management", "stakeholder management"])
    assert "diary management" in missing
    assert "stakeholder management" not in missing


def test_all_present_returns_empty_list():
    text = "Experience in diary management and Microsoft Office."
    missing = check_keywords_present(text, ["diary management", "microsoft office"])
    assert missing == []


def test_empty_keywords_returns_empty_list():
    assert check_keywords_present("some letter text", []) == []


def test_case_insensitive_keyword_check():
    text = "Proficient in Microsoft Office Suite."
    missing = check_keywords_present(text, ["microsoft office"])
    assert "microsoft office" not in missing


def test_all_keywords_missing():
    missing = check_keywords_present("Hello world.", ["diary management", "microsoft office"])
    assert len(missing) == 2


def test_returns_list_type():
    assert isinstance(check_keywords_present("text", ["keyword"]), list)


# ── opening_is_generic ────────────────────────────────────────────────────────

def test_i_am_writing_to_is_generic():
    assert opening_is_generic("I am writing to apply for the role of Administrator.") is True


def test_i_wish_to_apply_is_generic():
    assert opening_is_generic("I wish to apply for the position advertised on Reed.") is True


def test_i_would_like_to_apply_is_generic():
    assert opening_is_generic("I would like to apply for this role.") is True


def test_i_am_applying_for_is_generic():
    assert opening_is_generic("I am applying for the Office Administrator position.") is True


def test_specific_opener_not_generic():
    text = "Having managed complex stakeholder portfolios at Knight Frank, this role stood out immediately."
    assert opening_is_generic(text) is False


def test_clean_letter_opening_not_generic():
    assert opening_is_generic(CLEAN_LETTER) is False


def test_empty_text_returns_false():
    assert opening_is_generic("") is False


def test_generic_check_only_looks_at_first_sentence():
    # Generic phrase is in second sentence only — should not trigger
    text = "This role at Haringey Council aligns with my background. I am writing to express further interest."
    # Opening sentence is specific, so result should be False
    assert opening_is_generic(text) is False


# ── run_quality_checks ────────────────────────────────────────────────────────

def test_result_contains_all_expected_keys():
    result = run_quality_checks("Some letter text.", "Company", [])
    expected = {"ai_phrases", "missing_keywords", "length_status", "word_count",
                "generic_opening", "company_present", "passes"}
    assert expected.issubset(result.keys())


def test_clean_letter_passes():
    ats = ["microsoft office", "stakeholder management", "document management"]
    result = run_quality_checks(CLEAN_LETTER, "Haringey Council", ats)
    assert result["passes"] is True
    assert result["ai_phrases"] == []
    assert result["generic_opening"] is False
    assert result["company_present"] is True


def test_ai_heavy_letter_fails():
    result = run_quality_checks(AI_HEAVY_LETTER, "Acme Corp", [])
    assert result["passes"] is False
    assert len(result["ai_phrases"]) > 0
    assert result["generic_opening"] is True


def test_word_count_in_result_is_accurate():
    text = " ".join(["word"] * 50)
    result = run_quality_checks(text, "Company", [])
    assert result["word_count"] == 50


def test_missing_keywords_reported():
    text = " ".join(["word"] * 250)  # ok length, company not present
    result = run_quality_checks(text, "Absent Company", ["diary management"])
    assert "diary management" in result["missing_keywords"]


def test_passes_false_when_no_company():
    text = "Dear Hiring Manager,\n\n" + " ".join(["word"] * 280) + "\n\nYours sincerely,\nPhillip"
    result = run_quality_checks(text, "TargetCorp Ltd", [])
    assert result["company_present"] is False
    assert result["passes"] is False


def test_passes_false_when_too_short():
    short = "This is a very short letter. TargetCorp."
    result = run_quality_checks(short, "TargetCorp", [])
    assert result["length_status"] == "too_short"
    assert result["passes"] is False
