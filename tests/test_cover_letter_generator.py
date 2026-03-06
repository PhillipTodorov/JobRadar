"""Tests for cover_letter_generator — Claude API calls are mocked.

Pure pipeline logic is tested here. AI call content is not evaluated
(that is the job of the critic tests and real-world use).
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import cover_letter_generator as gen


# ── Helpers ────────────────────────────────────────────────────────────────────

def _claude_response(text: str) -> MagicMock:
    """Build a mock Anthropic messages.create() return value."""
    msg = MagicMock()
    msg.content = [MagicMock()]
    msg.content[0].text = text
    return msg


def _critique_json(needs_revision: bool = False, ai_phrases=None, missing_keywords=None) -> str:
    return json.dumps({
        "ai_phrases": ai_phrases or [],
        "unsupported_claims": [],
        "missing_keywords": missing_keywords or [],
        "word_count": 290,
        "generic_opening": False,
        "company_mentioned": True,
        "needs_revision": needs_revision,
        "revision_instructions": "Fix flagged issues." if needs_revision else "",
    })


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_extracted():
    return {
        "job_title": "Office Administrator",
        "company": "Haringey Council",
        "requirements": ["diary management", "stakeholder communication", "Microsoft Office"],
        "tone": "public_sector",
        "ats_keywords": ["diary management", "microsoft office"],
        "sector": "public",
    }


@pytest.fixture
def sample_matches():
    return {
        "matches": [
            {
                "requirement": "diary management",
                "snippet": "managed stakeholder communications at Knight Frank",
                "company": "Knight Frank",
                "job_title": "PMO Analyst",
                "score": 0.3,
                "strength": "partial",
                "source": "employment_history",
            }
        ],
        "unmatched": ["blockchain development"],
        "overall_quality": 0.6,
    }


@pytest.fixture
def sample_job():
    return {
        "title": "Office Administrator",
        "company": "Haringey Council",
        "description": (
            "- Diary management for senior directors\n"
            "- Stakeholder communication\n"
            "- Proficiency in Microsoft Office required"
        ),
        "location": "London",
    }


@pytest.fixture
def sample_databank():
    return {
        "employment_history": [
            {
                "company": "Knight Frank",
                "job_title": "PMO Analyst",
                "job_description": (
                    "Coordinated IT project documentation, facilitated meetings, "
                    "managed stakeholder communications."
                ),
            }
        ],
        "questions": {
            "Describe your administrative experience": (
                "Experienced in document management and scheduling."
            ),
        },
    }


_DRAFT_TEXT = (
    "Dear Hiring Manager,\n\n"
    "Having coordinated IT project portfolios at Knight Frank, this Office "
    "Administrator role at Haringey Council stood out immediately. The combination "
    "of diary management and stakeholder communication aligns directly with my "
    "experience across two organisations.\n\n"
    "At Knight Frank I managed documentation for concurrent IT projects and "
    "facilitated cross-functional meetings. At Jacobs Engineering Group I "
    "streamlined administrative workflows, improving efficiency and turnaround "
    "times for senior management. Microsoft Office was central to delivery in "
    "both roles.\n\n"
    "I would welcome the opportunity to discuss further. I am available at "
    "short notice.\n\n"
    "Yours sincerely,\nPhillip Todorov"
)


# ── draft_cover_letter ────────────────────────────────────────────────────────

def test_draft_returns_string(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(_DRAFT_TEXT)
        result = gen.draft_cover_letter(sample_extracted, sample_matches)
    assert isinstance(result, str)
    assert len(result) > 0


def test_draft_calls_claude_exactly_once(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(_DRAFT_TEXT)
        gen.draft_cover_letter(sample_extracted, sample_matches)
    MockClient.return_value.messages.create.assert_called_once()


def test_draft_strips_surrounding_whitespace(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(
            "   \n\nLetter text here.\n\n   "
        )
        result = gen.draft_cover_letter(sample_extracted, sample_matches)
    assert not result.startswith((" ", "\n"))
    assert not result.endswith((" ", "\n"))


def test_draft_passes_company_research_when_provided(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(_DRAFT_TEXT)
        gen.draft_cover_letter(sample_extracted, sample_matches, company_research="Great company info.")
    call_kwargs = MockClient.return_value.messages.create.call_args
    prompt_text = call_kwargs[1]["messages"][0]["content"]
    assert "Great company info." in prompt_text


def test_draft_omits_company_research_section_when_empty(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(_DRAFT_TEXT)
        gen.draft_cover_letter(sample_extracted, sample_matches, company_research="")
    call_kwargs = MockClient.return_value.messages.create.call_args
    prompt_text = call_kwargs[1]["messages"][0]["content"]
    assert "COMPANY CONTEXT" not in prompt_text


# ── critique_cover_letter ─────────────────────────────────────────────────────

def test_critique_returns_dict(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(
            _critique_json(needs_revision=False)
        )
        result = gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    assert isinstance(result, dict)


def test_critique_parses_needs_revision_true(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(
            _critique_json(needs_revision=True, ai_phrases=["proven track record"])
        )
        result = gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    assert result["needs_revision"] is True
    assert "proven track record" in result["ai_phrases"]


def test_critique_parses_needs_revision_false(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(
            _critique_json(needs_revision=False)
        )
        result = gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    assert result["needs_revision"] is False


def test_critique_handles_json_in_markdown_fence(sample_extracted, sample_matches):
    fenced = "```json\n" + _critique_json() + "\n```"
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(fenced)
        result = gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    assert "needs_revision" in result


def test_critique_returns_safe_fallback_on_malformed_response(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(
            "Sorry, I cannot complete this critique."
        )
        result = gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    assert isinstance(result, dict)
    assert "needs_revision" in result
    assert result["needs_revision"] is False  # safe default


def test_critique_calls_claude_exactly_once(sample_extracted, sample_matches):
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response(_critique_json())
        gen.critique_cover_letter(_DRAFT_TEXT, sample_extracted, sample_matches)
    MockClient.return_value.messages.create.assert_called_once()


# ── refine_cover_letter ───────────────────────────────────────────────────────

def test_refine_returns_original_when_no_revision_needed():
    critique = {"needs_revision": False, "revision_instructions": "", "ai_phrases": [], "missing_keywords": []}
    result = gen.refine_cover_letter("Original letter text.", critique)
    assert result == "Original letter text."


def test_refine_does_not_call_claude_when_no_revision_needed():
    critique = {"needs_revision": False, "revision_instructions": "", "ai_phrases": [], "missing_keywords": []}
    with patch("anthropic.Anthropic") as MockClient:
        gen.refine_cover_letter("Original.", critique)
    MockClient.return_value.messages.create.assert_not_called()


def test_refine_calls_claude_when_revision_needed():
    critique = {
        "needs_revision": True,
        "revision_instructions": "Remove generic phrases.",
        "ai_phrases": ["proven track record"],
        "missing_keywords": [],
    }
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response("Refined letter.")
        result = gen.refine_cover_letter("Original draft.", critique)
    MockClient.return_value.messages.create.assert_called_once()
    assert result == "Refined letter."


def test_refine_returns_string():
    critique = {
        "needs_revision": True,
        "revision_instructions": "Fix opening",
        "ai_phrases": [],
        "missing_keywords": ["diary management"],
    }
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response("Improved text.")
        result = gen.refine_cover_letter("Draft.", critique)
    assert isinstance(result, str)


def test_refine_includes_ai_phrases_in_prompt():
    critique = {
        "needs_revision": True,
        "revision_instructions": "",
        "ai_phrases": ["proven track record", "team player"],
        "missing_keywords": [],
    }
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response("Refined.")
        gen.refine_cover_letter("Draft with proven track record.", critique)
    prompt = MockClient.return_value.messages.create.call_args[1]["messages"][0]["content"]
    assert "proven track record" in prompt


def test_refine_includes_missing_keywords_in_prompt():
    critique = {
        "needs_revision": True,
        "revision_instructions": "",
        "ai_phrases": [],
        "missing_keywords": ["diary management", "microsoft office"],
    }
    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _claude_response("Refined.")
        gen.refine_cover_letter("Draft.", critique)
    prompt = MockClient.return_value.messages.create.call_args[1]["messages"][0]["content"]
    assert "diary management" in prompt


# ── generate_cover_letter — full pipeline ─────────────────────────────────────

def test_pipeline_returns_all_required_fields(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    for key in ("cover_letter", "match_quality", "unmatched", "word_count", "quality_checks", "steps"):
        assert key in result


def test_pipeline_steps_include_extract_match_draft_critique(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert "extract" in result["steps"]
    assert "match" in result["steps"]
    assert "draft" in result["steps"]
    assert "critique" in result["steps"]


def test_pipeline_adds_refine_step_when_needed(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value="Draft."), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": True,
             "revision_instructions": "Fix it.",
             "ai_phrases": ["proven track record"],
             "missing_keywords": [],
         }), \
         patch("cover_letter_generator.refine_cover_letter", return_value="Refined.") as mock_refine:
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert "refine" in result["steps"]
    mock_refine.assert_called_once()


def test_pipeline_skips_refine_when_not_needed(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }), \
         patch("cover_letter_generator.refine_cover_letter") as mock_refine:
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert "refine" not in result["steps"]
    mock_refine.assert_not_called()


def test_pipeline_uses_refined_letter_as_final_output(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value="Draft text."), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": True, "revision_instructions": "Fix.",
             "ai_phrases": ["team player"], "missing_keywords": [],
         }), \
         patch("cover_letter_generator.refine_cover_letter", return_value="Refined final text."):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert result["cover_letter"] == "Refined final text."


def test_pipeline_uses_draft_as_final_when_no_revision(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert result["cover_letter"] == _DRAFT_TEXT


def test_pipeline_match_quality_between_zero_and_one(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert 0.0 <= result["match_quality"] <= 1.0


def test_pipeline_word_count_is_integer(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert isinstance(result["word_count"], int)


def test_pipeline_unmatched_is_list(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert isinstance(result["unmatched"], list)


def test_pipeline_passes_company_research_to_draft(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT) as mock_draft, \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        gen.generate_cover_letter(sample_job, sample_databank, company_research="Council info here.")

    args, kwargs = mock_draft.call_args
    # company_research is the third positional arg (extracted, matches, company_research)
    company_research_passed = args[2] if len(args) > 2 else kwargs.get("company_research", "")
    assert "Council info here." in company_research_passed


def test_pipeline_quality_checks_dict_in_result(sample_job, sample_databank):
    with patch("cover_letter_generator.draft_cover_letter", return_value=_DRAFT_TEXT), \
         patch("cover_letter_generator.critique_cover_letter", return_value={
             "needs_revision": False, "ai_phrases": [], "missing_keywords": [],
         }):
        result = gen.generate_cover_letter(sample_job, sample_databank)

    assert isinstance(result["quality_checks"], dict)
    assert "passes" in result["quality_checks"]
