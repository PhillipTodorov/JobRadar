"""Tests for job fit scoring logic."""

import sys
from pathlib import Path

import pytest

# Add tools/ to path so we can import without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from score_job_fit import calculate_fit_score, extract_years_required


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def base_profile():
    return {
        "profile": {
            "skills": {
                "required": ["Python", "Git"],
                "preferred": ["React", "Docker", "AWS"],
            },
            "locations": {
                "preferred": ["London", "Remote"],
                "acceptable": ["Manchester"],
            },
            "dealbreakers": ["senior", "10+ years", "lead"],
        },
        "scoring": {
            "weights": {
                "required_skills": 0.40,
                "preferred_skills": 0.25,
                "location": 0.20,
                "title_relevance": 0.15,
            }
        },
    }


@pytest.fixture
def good_job():
    return {
        "title": "Junior Software Engineer",
        "company": "Acme Corp",
        "location": "London, UK",
        "description": "We need Python and Git experience. React and Docker are a plus.",
    }


# ── Dealbreakers ──────────────────────────────────────────────────────────────

def test_dealbreaker_in_title_returns_zero(base_profile):
    job = {"title": "Senior Developer", "description": "Python Git", "location": "London"}
    assert calculate_fit_score(job, base_profile) == 0


def test_dealbreaker_in_description_returns_zero(base_profile):
    job = {"title": "Developer", "description": "10+ years of Python required", "location": "London"}
    assert calculate_fit_score(job, base_profile) == 0


def test_dealbreaker_case_insensitive(base_profile):
    job = {"title": "SENIOR Developer", "description": "Python Git", "location": "London"}
    assert calculate_fit_score(job, base_profile) == 0


def test_no_dealbreaker_does_not_return_zero(base_profile, good_job):
    assert calculate_fit_score(good_job, base_profile) > 0


def test_empty_dealbreakers_list(good_job):
    profile = {
        "profile": {
            "skills": {"required": ["Python"], "preferred": []},
            "locations": {"preferred": ["London"], "acceptable": []},
            "dealbreakers": [],
        },
        "scoring": {"weights": {"required_skills": 0.40, "preferred_skills": 0.25, "location": 0.20, "title_relevance": 0.15}},
    }
    assert calculate_fit_score(good_job, profile) > 0


# ── Required Skills ───────────────────────────────────────────────────────────

def test_all_required_skills_matched(base_profile):
    job = {"title": "Developer", "description": "Must know Python and Git", "location": "London"}
    score = calculate_fit_score(job, base_profile)
    # required_skills component = 100% * 0.40 = 40 points (minimum from this factor)
    assert score >= 40


def test_no_required_skills_matched(base_profile):
    job = {"title": "Developer", "description": "Must know Java and C++", "location": "London"}
    score = calculate_fit_score(job, base_profile)
    # required_skills component = 0% * 0.40 = 0 points from this factor
    # score will be lower than a fully matching job
    full_match_job = {"title": "Developer", "description": "Python Git", "location": "London"}
    assert score < calculate_fit_score(full_match_job, base_profile)


def test_partial_required_skills_score_is_proportional(base_profile):
    # "version control" avoids the substring "git" appearing in the text
    job_one_match = {"title": "Developer", "description": "Python only, version control not required", "location": "Remote"}
    job_two_match = {"title": "Developer", "description": "Python and Git required", "location": "Remote"}
    score_one = calculate_fit_score(job_one_match, base_profile)
    score_two = calculate_fit_score(job_two_match, base_profile)
    assert score_two > score_one


def test_empty_required_skills_gives_neutral_50(good_job):
    profile = {
        "profile": {
            "skills": {"required": [], "preferred": []},
            "locations": {"preferred": ["London"], "acceptable": []},
            "dealbreakers": [],
        },
        "scoring": {"weights": {"required_skills": 0.40, "preferred_skills": 0.25, "location": 0.20, "title_relevance": 0.15}},
    }
    # required and preferred both neutral (50), location preferred (100), title neutral (50, no keywords configured)
    # = 50*0.40 + 50*0.25 + 100*0.20 + 50*0.15 = 20 + 12.5 + 20 + 7.5 = 60
    score = calculate_fit_score(good_job, profile)
    assert score == 60


# ── Preferred Skills ──────────────────────────────────────────────────────────

def test_preferred_skills_boost_score(base_profile):
    job_no_preferred = {"title": "Developer", "description": "Python Git", "location": "London"}
    job_with_preferred = {"title": "Developer", "description": "Python Git React Docker AWS", "location": "London"}
    assert calculate_fit_score(job_with_preferred, base_profile) > calculate_fit_score(job_no_preferred, base_profile)


def test_empty_preferred_skills_gives_neutral_50():
    profile = {
        "profile": {
            "skills": {"required": ["Python"], "preferred": []},
            "locations": {"preferred": ["London"], "acceptable": []},
            "dealbreakers": [],
        },
        "scoring": {"weights": {"required_skills": 0.40, "preferred_skills": 0.25, "location": 0.20, "title_relevance": 0.15}},
    }
    job = {"title": "Software Engineer", "description": "Python required", "location": "London"}
    score = calculate_fit_score(job, profile)
    # required=100*0.40, preferred neutral=50*0.25, location=100*0.20, title neutral=50*0.15
    # = 40 + 12.5 + 20 + 7.5 = 80
    assert score == 80


# ── Location Scoring ──────────────────────────────────────────────────────────

def test_preferred_location_scores_100(base_profile):
    job = {"title": "Software Engineer", "description": "Python Git React Docker AWS", "location": "London, UK"}
    score = calculate_fit_score(job, base_profile)
    # location factor = 100 * 0.20 = 20 points
    # confirm it's higher than acceptable
    job_acceptable = {**job, "location": "Manchester, UK"}
    assert score > calculate_fit_score(job_acceptable, base_profile)


def test_remote_counts_as_preferred(base_profile):
    job = {"title": "Software Engineer", "description": "Python Git", "location": "Remote"}
    score = calculate_fit_score(job, base_profile)
    assert score > 0
    # Same job with unknown location should score lower
    job_unknown = {**job, "location": "Edinburgh"}
    assert score > calculate_fit_score(job_unknown, base_profile)


def test_acceptable_location_scores_between_preferred_and_none(base_profile):
    job_preferred = {"title": "Developer", "description": "Python Git", "location": "London"}
    job_acceptable = {"title": "Developer", "description": "Python Git", "location": "Manchester"}
    job_other = {"title": "Developer", "description": "Python Git", "location": "Edinburgh"}
    assert calculate_fit_score(job_preferred, base_profile) > calculate_fit_score(job_acceptable, base_profile)
    assert calculate_fit_score(job_acceptable, base_profile) > calculate_fit_score(job_other, base_profile)


def test_unknown_location_scores_zero_for_location_factor(base_profile):
    job = {"title": "Software Engineer", "description": "Python Git React Docker AWS", "location": "Edinburgh"}
    # location factor = 0 * 0.20 = 0 points
    # required=100*0.40, preferred cap=4 so 3 matches=75%→75*0.25, location=0*0.20, title neutral=50*0.15
    # = 40 + 18.75 + 0 + 7.5 = 66.25 → 66
    assert calculate_fit_score(job, base_profile) == 66


def test_missing_location_field_scores_zero(base_profile):
    job = {"title": "Software Engineer", "description": "Python Git"}
    score = calculate_fit_score(job, base_profile)
    job_preferred = {**job, "location": "London"}
    assert score < calculate_fit_score(job_preferred, base_profile)


# ── Title Relevance ───────────────────────────────────────────────────────────

def test_title_neutral_when_no_keywords_configured(base_profile):
    # Without relevant_title_keywords in the profile, all titles score 50 (neutral)
    job_dev = {"title": "Software Developer", "description": "Python Git", "location": "London"}
    job_coord = {"title": "Marketing Coordinator", "description": "Python Git", "location": "London"}
    assert calculate_fit_score(job_dev, base_profile) == calculate_fit_score(job_coord, base_profile)


def test_irrelevant_title_keywords_score_zero():
    profile = {
        "profile": {
            "skills": {"required": ["Python"], "preferred": []},
            "locations": {"preferred": ["London"], "acceptable": []},
            "dealbreakers": [],
            "irrelevant_title_keywords": ["developer", "engineer"],
            "relevant_title_keywords": ["coordinator", "assistant"],
        },
        "scoring": {"weights": {"required_skills": 0.40, "preferred_skills": 0.25, "location": 0.20, "title_relevance": 0.15}},
    }
    job_irrelevant = {"title": "Junior Power Platform Developer", "description": "Python required", "location": "London"}
    job_relevant = {"title": "Project Coordinator", "description": "Python required", "location": "London"}
    assert calculate_fit_score(job_irrelevant, profile) < calculate_fit_score(job_relevant, profile)
    # Developer title should score 0 for title factor
    # required=100*0.40, preferred neutral=50*0.25, location=100*0.20, title=0*0.15
    # = 40 + 12.5 + 20 + 0 = 72.5 → 72
    assert calculate_fit_score(job_irrelevant, profile) == 72


def test_configured_keywords_boost_relevant_title():
    profile_with_kws = {
        "profile": {
            "skills": {"required": ["Python"], "preferred": []},
            "locations": {"preferred": ["London"], "acceptable": []},
            "dealbreakers": [],
            "relevant_title_keywords": ["developer", "engineer"],
        },
        "scoring": {"weights": {"required_skills": 0.40, "preferred_skills": 0.25, "location": 0.20, "title_relevance": 0.15}},
    }
    job_relevant = {"title": "Software Developer", "description": "Python required", "location": "London"}
    job_irrelevant = {"title": "Marketing Manager", "description": "Python required", "location": "London"}
    assert calculate_fit_score(job_relevant, profile_with_kws) > calculate_fit_score(job_irrelevant, profile_with_kws)


def test_irrelevant_title_scores_50_not_zero(base_profile):
    # Title relevance is 50 (not 0) for any title when no keywords configured — neutral, not a penalty
    job = {"title": "Marketing Coordinator", "description": "Python Git React Docker AWS", "location": "London"}
    score = calculate_fit_score(job, base_profile)
    # required=100*0.40, preferred cap=4 so 3 matches=75%→75*0.25, location=100*0.20, title neutral=50*0.15
    # = 40 + 18.75 + 20 + 7.5 = 86.25 → 86
    assert score == 86


# ── Weighted Calculation ──────────────────────────────────────────────────────

def test_custom_weights_applied_correctly():
    profile = {
        "profile": {
            "skills": {"required": ["Python"], "preferred": []},
            "locations": {"preferred": [], "acceptable": []},
            "dealbreakers": [],
        },
        "scoring": {
            "weights": {
                "required_skills": 1.0,  # Only required skills matter
                "preferred_skills": 0.0,
                "location": 0.0,
                "title_relevance": 0.0,
            }
        },
    }
    job_match = {"title": "Anything", "description": "Python is required", "location": "Anywhere"}
    job_no_match = {"title": "Anything", "description": "Java only", "location": "Anywhere"}
    assert calculate_fit_score(job_match, profile) == 100
    assert calculate_fit_score(job_no_match, profile) == 0


def test_score_is_integer(base_profile, good_job):
    score = calculate_fit_score(good_job, base_profile)
    assert isinstance(score, int)


def test_score_bounded_0_to_100(base_profile):
    job = {"title": "Software Engineer", "description": "Python Git React Docker AWS", "location": "London"}
    score = calculate_fit_score(job, base_profile)
    assert 0 <= score <= 100


def test_minimal_job_dict(base_profile):
    """Should not crash on a job with no fields."""
    score = calculate_fit_score({}, base_profile)
    assert 0 <= score <= 100


# ── extract_years_required ────────────────────────────────────────────────────

class TestExtractYearsRequired:
    def test_plus_suffix(self):
        assert extract_years_required("3+ years experience required") == 3

    def test_plus_with_space(self):
        assert extract_years_required("5 + years in a similar role") == 5

    def test_years_experience(self):
        assert extract_years_required("2 years experience in administration") == 2

    def test_years_possessive(self):
        assert extract_years_required("3 years' experience in a busy office") == 3

    def test_years_of_experience(self):
        assert extract_years_required("4 years of experience required") == 4

    def test_minimum_of(self):
        assert extract_years_required("Minimum of 2 years in a similar role") == 2

    def test_minimum_without_of(self):
        assert extract_years_required("minimum 3 years administration") == 3

    def test_at_least(self):
        assert extract_years_required("at least 5 years relevant experience") == 5

    def test_range_hyphen(self):
        assert extract_years_required("2-4 years experience") == 4

    def test_range_to(self):
        assert extract_years_required("3 to 5 years in a coordinator role") == 5

    def test_multiple_requirements_takes_max(self):
        assert extract_years_required("2 years admin experience and 5+ years customer service experience") == 5

    def test_no_years_mentioned(self):
        assert extract_years_required("Excellent communication skills required") == 0

    def test_experience_without_number(self):
        assert extract_years_required("experience in Microsoft Office preferred") == 0

    def test_proven_experience(self):
        assert extract_years_required("3 years proven experience in administration") == 3

    def test_relevant_experience(self):
        assert extract_years_required("2 years relevant experience required") == 2

    def test_case_insensitive(self):
        assert extract_years_required("MINIMUM 3 YEARS EXPERIENCE") == 3

    def test_en_dash_range(self):
        assert extract_years_required("2\u20134 years experience") == 4

    def test_zero_returned_for_no_match(self):
        assert extract_years_required("No prior experience necessary") == 0


# ── Experience filter in calculate_fit_score ──────────────────────────────────

@pytest.fixture
def admin_profile():
    """Phillip-style admin profile with experience limit and title keywords."""
    return {
        "profile": {
            "skills": {
                "required": ["communication"],
                "preferred": ["Microsoft Office", "administration"],
            },
            "locations": {"preferred": ["London"], "acceptable": []},
            "experience": {"years_total": 4, "max_years_required": 4},
            "relevant_title_keywords": ["administrator", "coordinator", "assistant", "analyst"],
            "senior_title_prefixes": ["senior ", "lead ", "head of"],
            "dealbreakers": [],
        },
        "scoring": {
            "weights": {
                "required_skills": 0.30,
                "preferred_skills": 0.35,
                "location": 0.25,
                "title_relevance": 0.10,
            }
        },
    }


def _job(title="Office Administrator", description="communication", location="London"):
    return {"title": title, "description": description, "location": location}


class TestExperienceFilter:
    def test_within_limit_passes(self, admin_profile):
        assert calculate_fit_score(_job(description="3+ years experience. communication skills."), admin_profile) > 0

    def test_exactly_at_limit_passes(self, admin_profile):
        assert calculate_fit_score(_job(description="4 years experience required. communication."), admin_profile) > 0

    def test_exceeds_limit_returns_zero(self, admin_profile):
        assert calculate_fit_score(_job(description="5+ years experience required. communication."), admin_profile) == 0

    def test_large_requirement_filtered(self, admin_profile):
        assert calculate_fit_score(_job(description="minimum 8 years in a similar role"), admin_profile) == 0

    def test_no_years_requirement_not_filtered(self, admin_profile):
        assert calculate_fit_score(_job(description="Good communication skills."), admin_profile) > 0

    def test_no_experience_key_allows_all(self, admin_profile):
        p = {**admin_profile, "profile": {k: v for k, v in admin_profile["profile"].items() if k != "experience"}}
        assert calculate_fit_score(_job(description="10+ years of experience required"), p) > 0

    def test_experience_filter_beats_skill_match(self, admin_profile):
        job = _job(description="communication Microsoft Office administration 10+ years experience")
        assert calculate_fit_score(job, admin_profile) == 0


class TestTitleRelevance:
    def test_admin_title_scores_higher(self, admin_profile):
        admin = calculate_fit_score(_job(title="Office Administrator"), admin_profile)
        chef = calculate_fit_score(_job(title="Head Chef"), admin_profile)
        assert admin > chef

    def test_coordinator_relevant(self, admin_profile):
        assert calculate_fit_score(_job(title="Project Coordinator"), admin_profile) > 0

    def test_senior_prefix_penalised(self, admin_profile):
        admin = calculate_fit_score(_job(title="Office Administrator"), admin_profile)
        senior = calculate_fit_score(_job(title="Senior Office Administrator"), admin_profile)
        assert senior < admin

    def test_lead_prefix_penalised(self, admin_profile):
        admin = calculate_fit_score(_job(title="Administrator"), admin_profile)
        lead = calculate_fit_score(_job(title="Lead Administrator"), admin_profile)
        assert lead < admin

    def test_no_title_keywords_configured_gives_neutral(self):
        profile = {
            "profile": {
                "skills": {"required": [], "preferred": []},
                "locations": {"preferred": ["London"], "acceptable": []},
                "dealbreakers": [],
                # no relevant_title_keywords → neutral 50
            },
            "scoring": {"weights": {"required_skills": 0.30, "preferred_skills": 0.35, "location": 0.25, "title_relevance": 0.10}},
        }
        score_admin = calculate_fit_score(_job(title="Office Administrator"), profile)
        score_chef = calculate_fit_score(_job(title="Head Chef"), profile)
        assert score_admin == score_chef  # both neutral when no keywords configured
