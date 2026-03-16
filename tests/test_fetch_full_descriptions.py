"""Tests for full description fetching."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from fetch_full_descriptions import needs_enrichment, strip_html, enrich_descriptions


# ── needs_enrichment ─────────────────────────────────────────────────────────


def test_needs_enrichment_empty_description():
    job = {"source": "reed.co.uk", "description": ""}
    assert needs_enrichment(job) is True


def test_needs_enrichment_short_description():
    job = {"source": "jooble.org", "description": "A short snippet about the job."}
    assert needs_enrichment(job) is True


def test_needs_enrichment_truncated_description():
    job = {"source": "adzuna.co.uk", "description": "This is a description that ends with..."}
    assert needs_enrichment(job) is True


def test_needs_enrichment_full_google_jobs_description():
    job = {"source": "google_jobs (via LinkedIn)", "description": "x" * 600}
    assert needs_enrichment(job) is False


def test_needs_enrichment_long_description_non_google():
    job = {"source": "reed.co.uk", "description": "x" * 600}
    assert needs_enrichment(job) is False


def test_needs_enrichment_careerjet_skipped():
    job = {"source": "careerjet.co.uk", "description": "x" * 100}
    assert needs_enrichment(job) is False


def test_needs_enrichment_no_description_key():
    job = {"source": "jooble.org"}
    assert needs_enrichment(job) is True


# ── strip_html ───────────────────────────────────────────────────────────────


def test_strip_html_basic():
    result = strip_html("<p>Hello <b>world</b></p>")
    assert "Hello" in result
    assert "world" in result


def test_strip_html_preserves_paragraph_breaks():
    html = "<p>First paragraph</p><p>Second paragraph</p>"
    result = strip_html(html)
    assert "First paragraph" in result
    assert "Second paragraph" in result


def test_strip_html_removes_scripts():
    html = "<p>Text</p><script>alert('xss')</script>"
    result = strip_html(html)
    assert "alert" not in result
    assert "Text" in result


def test_strip_html_removes_styles():
    html = "<style>.cls{color:red}</style><p>Content</p>"
    result = strip_html(html)
    assert "color" not in result
    assert "Content" in result


def test_strip_html_empty():
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_strip_html_plain_text():
    assert strip_html("Just plain text") == "Just plain text"


# ── enrich_descriptions ──────────────────────────────────────────────────────


def test_enrich_skips_full_descriptions():
    jobs = [{"source": "google_jobs (via Indeed)", "description": "x" * 600}]
    result = enrich_descriptions(jobs)
    assert result[0]["description"] == "x" * 600


def test_enrich_skips_when_all_full():
    jobs = [
        {"source": "careerjet.co.uk", "description": "Full description here."},
        {"source": "google_jobs (via LinkedIn)", "description": "Another full one."},
    ]
    result = enrich_descriptions(jobs)
    assert len(result) == 2
    assert result[0]["description"] == "Full description here."


@patch("fetch_full_descriptions.fetch_reed_detail")
def test_enrich_calls_reed_api_for_reed_jobs(mock_reed):
    mock_reed.return_value = "Full reed description " * 50
    jobs = [{"source": "reed.co.uk", "description": "Short", "reed_job_id": 123, "title": "Dev", "company": "Co", "url": ""}]
    result = enrich_descriptions(jobs)
    mock_reed.assert_called_once()
    assert len(result[0]["description"]) > len("Short")


@patch("fetch_full_descriptions.scrape_job_page")
def test_enrich_calls_scraper_for_non_reed_jobs(mock_scrape):
    mock_scrape.return_value = "Full scraped description " * 50
    jobs = [{"source": "jooble.org", "description": "Snippet", "title": "Dev", "company": "Co", "url": "https://example.com/job"}]
    result = enrich_descriptions(jobs)
    mock_scrape.assert_called_once_with("https://example.com/job")
    assert len(result[0]["description"]) > len("Snippet")


@patch("fetch_full_descriptions.scrape_job_page")
def test_enrich_keeps_original_if_fetch_fails(mock_scrape):
    mock_scrape.return_value = None
    jobs = [{"source": "adzuna.co.uk", "description": "Partial desc...", "title": "Dev", "company": "Co", "url": "https://example.com"}]
    result = enrich_descriptions(jobs)
    assert result[0]["description"] == "Partial desc..."


@patch("fetch_full_descriptions.scrape_job_page")
def test_enrich_keeps_original_if_fetched_is_shorter(mock_scrape):
    mock_scrape.return_value = "Short"
    original = "This is a longer original description that should be kept"
    jobs = [{"source": "adzuna.co.uk", "description": original, "title": "Dev", "company": "Co", "url": "https://example.com"}]
    result = enrich_descriptions(jobs)
    assert result[0]["description"] == original
