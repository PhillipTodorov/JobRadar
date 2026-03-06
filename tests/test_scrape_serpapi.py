"""Tests for SerpAPI scraper — pure functions only (no API calls)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from scrape_serpapi import get_date_posted_chip, fetch_jobs_for_query


# ── get_date_posted_chip ──────────────────────────────────────────────────────

def test_1_day_returns_today():
    assert get_date_posted_chip(1) == "today"


def test_0_days_returns_today():
    assert get_date_posted_chip(0) == "today"


def test_3_days_returns_3days():
    assert get_date_posted_chip(3) == "3days"


def test_2_days_returns_3days():
    assert get_date_posted_chip(2) == "3days"


def test_7_days_returns_week():
    assert get_date_posted_chip(7) == "week"


def test_5_days_returns_week():
    assert get_date_posted_chip(5) == "week"


def test_30_days_returns_month():
    assert get_date_posted_chip(30) == "month"


def test_14_days_returns_month():
    assert get_date_posted_chip(14) == "month"


def test_large_value_returns_month():
    assert get_date_posted_chip(365) == "month"


# ── fetch_jobs_for_query (mocked) ─────────────────────────────────────────────

def test_fetch_jobs_exits_without_api_key(monkeypatch):
    """Should call sys.exit when SERPAPI_KEY is missing."""
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    monkeypatch.setenv("SERPAPI_KEY", "")

    config = {"api": {"max_results": 10, "pages": 1}, "search_params": {"posted_within_days": 7}}

    with pytest.raises(SystemExit):
        fetch_jobs_for_query("Python Developer", "London", config)


def test_fetch_jobs_returns_list_on_api_error(monkeypatch):
    """Should return partial results (empty list) when API raises an error."""
    monkeypatch.setenv("SERPAPI_KEY", "fake_key_12345")

    # Mock GoogleSearch to raise immediately
    import scrape_serpapi

    class MockSearch:
        def __init__(self, params):
            raise ConnectionError("No network")

    monkeypatch.setattr(scrape_serpapi, "GoogleSearch", MockSearch)

    config = {"api": {"max_results": 10, "pages": 1}, "search_params": {"posted_within_days": 7}}
    result = fetch_jobs_for_query("Python Developer", "London", config)

    assert isinstance(result, list)


def test_fetch_jobs_respects_max_results(monkeypatch):
    """Should truncate results to max_results."""
    monkeypatch.setenv("SERPAPI_KEY", "fake_key_12345")

    import scrape_serpapi

    fake_jobs = [
        {"title": f"Job {i}", "company_name": "Acme", "location": "London",
         "share_link": f"https://example.com/{i}", "detected_extensions": {}, "description": ""}
        for i in range(20)
    ]

    class MockSearch:
        def __init__(self, params):
            pass
        def get_dict(self):
            return {"jobs_results": fake_jobs, "serpapi_pagination": {}}

    monkeypatch.setattr(scrape_serpapi, "GoogleSearch", MockSearch)

    config = {"api": {"max_results": 5, "pages": 3}, "search_params": {"posted_within_days": 7}}
    result = fetch_jobs_for_query("Python Developer", "London", config)

    assert len(result) <= 5


def test_fetch_jobs_stops_when_no_more_results(monkeypatch):
    """Should stop paginating when API returns empty jobs_results."""
    monkeypatch.setenv("SERPAPI_KEY", "fake_key_12345")

    import scrape_serpapi

    call_count = {"n": 0}

    class MockSearch:
        def __init__(self, params):
            pass
        def get_dict(self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {
                    "jobs_results": [
                        {"title": "Job 1", "company_name": "Acme", "location": "London",
                         "share_link": "https://example.com/1", "detected_extensions": {}, "description": ""}
                    ],
                    "serpapi_pagination": {"next_page_token": "token_abc"}
                }
            return {"jobs_results": [], "serpapi_pagination": {}}

    monkeypatch.setattr(scrape_serpapi, "GoogleSearch", MockSearch)

    config = {"api": {"max_results": 50, "pages": 5}, "search_params": {"posted_within_days": 7}}
    result = fetch_jobs_for_query("Python Developer", "London", config)

    # Should have stopped after page 2 returned empty
    assert call_count["n"] == 2
    assert len(result) == 1
