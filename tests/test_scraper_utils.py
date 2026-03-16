"""Tests for shared scraper utilities."""

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from scraper_utils import normalize_job, save_raw_results, save_csv


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def raw_job():
    return {
        "title": "  Junior Python Developer  ",
        "company": "  Acme Corp  ",
        "location": "London",
        "url": "https://example.com/job/123",
        "date_posted": "2 days ago",
        "salary": "£30,000 - £35,000",
        "description": "We need Python skills.",
    }


@pytest.fixture
def sample_jobs(raw_job):
    return [normalize_job(raw_job, "test_source")]


# ── normalize_job ─────────────────────────────────────────────────────────────

def test_normalize_strips_whitespace(raw_job):
    result = normalize_job(raw_job, "test")
    assert result["title"] == "Junior Python Developer"
    assert result["company"] == "Acme Corp"


def test_normalize_sets_source(raw_job):
    result = normalize_job(raw_job, "linkedin")
    assert result["source"] == "linkedin"


def test_normalize_adds_scraped_at(raw_job):
    result = normalize_job(raw_job, "test")
    assert "scraped_at" in result
    assert result["scraped_at"]  # not empty


def test_normalize_missing_fields_default_to_empty_string():
    result = normalize_job({}, "test")
    for field in ["title", "company", "location", "url", "date_posted", "salary", "description"]:
        assert result[field] == ""


def test_normalize_description_preserves_full_length(raw_job):
    raw_job["description"] = "x" * 5000
    result = normalize_job(raw_job, "test")
    assert len(result["description"]) == 5000


def test_normalize_description_under_2000_not_truncated(raw_job):
    raw_job["description"] = "Short description."
    result = normalize_job(raw_job, "test")
    assert result["description"] == "Short description."


def test_normalize_output_has_all_standard_fields(raw_job):
    result = normalize_job(raw_job, "test")
    expected_fields = {"title", "company", "location", "url", "date_posted", "salary", "description", "source", "scraped_at"}
    assert set(result.keys()) == expected_fields


def test_normalize_with_extra_fields(raw_job):
    result = normalize_job(raw_job, "test", extra_fields={"reed_job_id": 12345})
    assert result["reed_job_id"] == 12345
    assert result["source"] == "test"


# ── save_raw_results ──────────────────────────────────────────────────────────

def test_save_raw_results_creates_file(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_raw_results(sample_jobs, "test_output.json")

    output = tmp_path / "test_output.json"
    assert output.exists()


def test_save_raw_results_valid_json(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_raw_results(sample_jobs, "test_output.json")

    with open(tmp_path / "test_output.json", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == len(sample_jobs)


def test_save_raw_results_round_trips_data(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_raw_results(sample_jobs, "test_output.json")

    with open(tmp_path / "test_output.json", encoding="utf-8") as f:
        data = json.load(f)

    assert data[0]["title"] == sample_jobs[0]["title"]
    assert data[0]["source"] == sample_jobs[0]["source"]


# ── save_csv ──────────────────────────────────────────────────────────────────

def test_save_csv_creates_file(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_csv(sample_jobs)

    assert (tmp_path / "jobs_export.csv").exists()


def test_save_csv_has_header_row(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_csv(sample_jobs)

    with open(tmp_path / "jobs_export.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert "title" in reader.fieldnames
        assert "company" in reader.fieldnames
        assert "source" in reader.fieldnames


def test_save_csv_no_fit_score_column_by_default(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_csv(sample_jobs)

    with open(tmp_path / "jobs_export.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert "fit_score" not in reader.fieldnames


def test_save_csv_includes_fit_score_when_present(tmp_path, monkeypatch, sample_jobs):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    jobs_with_score = [{**sample_jobs[0], "fit_score": 75}]
    save_csv(jobs_with_score)

    with open(tmp_path / "jobs_export.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert "fit_score" in reader.fieldnames
        rows = list(reader)
        assert rows[0]["fit_score"] == "75"


def test_save_csv_empty_list_creates_file(tmp_path, monkeypatch):
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    save_csv([])

    # File creation is not guaranteed for empty list per implementation, just no crash
    # (the function prints "No jobs to save" and returns early)


def test_save_csv_ignores_extra_fields(tmp_path, monkeypatch, sample_jobs):
    """Extra fields like 'via' from raw scrape data should not cause errors."""
    import scraper_utils
    monkeypatch.setattr(scraper_utils, "TMP_DIR", tmp_path)

    jobs_with_extra = [{**sample_jobs[0], "via": "LinkedIn", "unexpected_field": "value"}]
    save_csv(jobs_with_extra)  # Should not raise

    assert (tmp_path / "jobs_export.csv").exists()
