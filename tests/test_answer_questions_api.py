"""Tests for answer_questions_api pure logic functions.

Flask app and AI calls are NOT tested here — only pure Python functions
that don't require network access or API keys.
"""

import sys
from pathlib import Path

import pytest

# answer_questions_api.py imports Flask at module level, so we add tools/ to path
# and import only the functions we need directly
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# Patch Flask before importing so it doesn't fail if flask isn't installed
import importlib
import types

# Import the functions directly by loading the module
import answer_questions_api as api


# ── calculate_similarity ──────────────────────────────────────────────────────

def test_similarity_identical_strings():
    assert api.calculate_similarity("hello world", "hello world") == 1.0


def test_similarity_completely_different_strings():
    assert api.calculate_similarity("hello world", "foo bar baz") == 0.0


def test_similarity_partial_overlap():
    score = api.calculate_similarity("python developer job", "senior python engineer")
    assert 0.0 < score < 1.0


def test_similarity_case_insensitive():
    score_lower = api.calculate_similarity("python developer", "Python Developer")
    assert score_lower == 1.0


def test_similarity_ignores_punctuation():
    score = api.calculate_similarity("hello, world!", "hello world")
    assert score == 1.0


def test_similarity_empty_strings_returns_zero():
    assert api.calculate_similarity("", "hello") == 0.0
    assert api.calculate_similarity("hello", "") == 0.0
    assert api.calculate_similarity("", "") == 0.0


def test_similarity_symmetric():
    a = "machine learning engineer"
    b = "software engineer python"
    assert api.calculate_similarity(a, b) == api.calculate_similarity(b, a)


# ── is_job_description ────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Experience with Python and JavaScript required",
    "Must have 3 years of experience in React",
    "Knowledge of cloud platforms preferred",
    "You will be responsible for backend services",
    "The ideal candidate should have a degree in CS",
    "We are looking for a talented engineer",
    "Required: proficiency in SQL",
    "Ability to work in agile teams",
])
def test_is_job_description_returns_true_for_job_desc(text):
    assert api.is_job_description(text) is True


@pytest.mark.parametrize("text", [
    "First Name",
    "Email Address",
    "Why are you interested in this role?",
    "Tell us about yourself",
    "Expected Salary",
    "Cover Letter",
    "Phone Number",
    "LinkedIn Profile",
])
def test_is_job_description_returns_false_for_form_fields(text):
    assert api.is_job_description(text) is False


# ── match_to_databank ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_databank():
    return {
        "personal_info": {
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "+44 7700 000000",
            "location": "London, UK",
            "linkedin": "linkedin.com/in/janesmith",
        },
        "salary": {
            "expected_salary": "£35,000",
        },
        "work_authorization": {
            "eligible_to_work_uk": "Yes, I have the right to work in the UK",
            "require_sponsorship": "No",
            "notice_period": "Immediately available",
        },
        "questions": {
            "Why are you interested in this role?": "I am passionate about software development.",
            "Tell us about a challenge you overcame": "I led a migration project...",
        },
    }


def test_match_first_name(sample_databank):
    answer, score = api.match_to_databank("first name", sample_databank)
    assert answer == "Jane"
    assert score == 1.0


def test_match_last_name(sample_databank):
    answer, score = api.match_to_databank("last name", sample_databank)
    assert answer == "Smith"
    assert score == 1.0


def test_match_surname(sample_databank):
    answer, score = api.match_to_databank("surname", sample_databank)
    assert answer == "Smith"
    assert score == 1.0


def test_match_full_name(sample_databank):
    answer, score = api.match_to_databank("your name", sample_databank)
    assert answer == "Jane Smith"
    assert score == 1.0


def test_match_email(sample_databank):
    answer, score = api.match_to_databank("email address", sample_databank)
    assert answer == "jane@example.com"
    assert score == 1.0


def test_match_phone(sample_databank):
    answer, score = api.match_to_databank("phone number", sample_databank)
    assert answer == "+44 7700 000000"
    assert score == 1.0


def test_match_mobile(sample_databank):
    answer, score = api.match_to_databank("mobile number", sample_databank)
    assert answer == "+44 7700 000000"
    assert score == 1.0


def test_match_location(sample_databank):
    answer, score = api.match_to_databank("city", sample_databank)
    assert answer == "London, UK"
    assert score == 1.0


def test_match_linkedin(sample_databank):
    answer, score = api.match_to_databank("linkedin profile", sample_databank)
    assert answer == "linkedin.com/in/janesmith"
    assert score == 1.0


def test_match_salary(sample_databank):
    answer, score = api.match_to_databank("expected salary", sample_databank)
    assert answer == "£35,000"
    assert score == 1.0


def test_match_right_to_work(sample_databank):
    answer, score = api.match_to_databank("right to work in the UK", sample_databank)
    assert answer == "Yes, I have the right to work in the UK"
    assert score == 1.0


def test_match_sponsorship(sample_databank):
    answer, score = api.match_to_databank("do you require visa sponsorship", sample_databank)
    assert answer == "No"
    assert score == 1.0


def test_match_notice_period(sample_databank):
    answer, score = api.match_to_databank("notice period", sample_databank)
    assert answer == "Immediately available"
    assert score == 1.0


def test_match_stored_question_high_similarity(sample_databank):
    # Close paraphrase of stored question
    answer, score = api.match_to_databank("Why are you interested in this position?", sample_databank)
    assert answer is not None
    assert score > 0.3


def test_match_no_match_returns_none(sample_databank):
    answer, score = api.match_to_databank("what is your favourite colour", sample_databank)
    assert answer is None
    assert score == 0


def test_match_empty_databank():
    answer, score = api.match_to_databank("email address", {})
    assert answer is None
    assert score == 0


def test_match_databank_missing_personal_info(sample_databank):
    """Should not crash if personal_info key is absent."""
    del sample_databank["personal_info"]
    answer, score = api.match_to_databank("email address", sample_databank)
    # No personal info — no match
    assert answer is None


# ── extract_questions_regex ───────────────────────────────────────────────────

def test_regex_extracts_direct_questions():
    text = "Why are you interested in this role? Please tell us about yourself."
    questions = api.extract_questions_regex(text)
    assert any("why are you interested" in q.lower() for q in questions)


def test_regex_extracts_common_form_fields():
    text = "Please fill in your details below.\nFirst Name\nLast Name\nEmail\nPhone"
    questions = api.extract_questions_regex(text)
    assert "First Name" in questions
    assert "Email" in questions


def test_regex_extracts_uk_form_fields():
    """UK job sites use Forename/Surname rather than First/Last Name."""
    text = "Title\nForename\nSurname\nEmail Address\nPassword\nConfirm Password"
    questions = api.extract_questions_regex(text)
    assert "Forename" in questions
    assert "Surname" in questions
    assert "Password" in questions
    assert "Confirm Password" in questions


def test_regex_handles_required_suffix():
    """'Forename * (required)' should still match 'Forename'."""
    text = "Forename * (required)\nSurname * (required)\nEmail address * (required)"
    questions = api.extract_questions_regex(text)
    assert "Forename" in questions
    assert "Surname" in questions
    assert "Email Address" in questions


def test_regex_no_false_positive_address_from_email_address():
    """'Address' must NOT be extracted when only 'Email address' appears on the line."""
    text = "Email address * (required)\nConfirm email address * (required)"
    questions = api.extract_questions_regex(text)
    assert "Address" not in questions


def test_regex_extracts_address_fields():
    """UK address fields: Number/Street, Local Area, Posttown, Address Type, Mailing Address."""
    text = "Number/Street\nLocal Area\nPosttown\nPOSTCODE\nAddress type\nMailing address"
    questions = api.extract_questions_regex(text)
    assert "Number/Street" in questions
    assert "Local Area" in questions
    assert "Posttown" in questions
    assert "Postcode" in questions
    assert "Address Type" in questions
    assert "Mailing Address" in questions


def test_regex_extracts_preferred_name():
    """'Preferred name' is a common UK form field."""
    text = "Forename\nPreferred name\nSurname"
    questions = api.extract_questions_regex(text)
    assert "Preferred Name" in questions


def test_regex_deduplicates_questions():
    text = "First Name\nFirst Name\nEmail\nEmail"
    questions = api.extract_questions_regex(text)
    assert questions.count("First Name") == 1
    assert questions.count("Email") == 1


def test_regex_returns_all_fields_no_cap():
    # All distinct fields should be returned — no artificial limit
    text = "\n".join([f"Why do you want to work here reason {i}?" for i in range(5)])
    text += "\nFirst Name\nLast Name\nEmail\nPhone\nLinkedIn\nAddress\nCity\nPostcode\nCountry\nNationality\nGender"
    questions = api.extract_questions_regex(text)
    assert "First Name" in questions
    assert "Nationality" in questions
    assert "Gender" in questions
    assert len(questions) >= 10


def test_regex_returns_list():
    questions = api.extract_questions_regex("Some page text with no questions")
    assert isinstance(questions, list)


def test_regex_empty_text_returns_empty_list():
    questions = api.extract_questions_regex("")
    assert questions == []


# ── match_to_databank — forename/surname ─────────────────────────────────────

def test_match_forename_returns_first_name(sample_databank):
    answer, score = api.match_to_databank("forename", sample_databank)
    assert answer == "Jane"
    assert score == 1.0


def test_match_given_name_returns_first_name(sample_databank):
    answer, score = api.match_to_databank("given name", sample_databank)
    assert answer == "Jane"
    assert score == 1.0
