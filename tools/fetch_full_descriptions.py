"""Fetch full job descriptions for jobs with partial/truncated descriptions.

Strategies by source:
  - Reed: Use detail API endpoint GET /api/1.0/jobs/{jobId}
  - Adzuna, Jooble, others: Scrape the job URL page
  - SerpAPI/Google Jobs, Careerjet: Skip (already full)

Rate limiting: configurable per source, defaults to 1s between requests.
"""

import os
import re
import time

import requests
from bs4 import BeautifulSoup

from scraper_utils import load_config

# Sources that typically return full descriptions — skip enrichment
FULL_DESCRIPTION_SOURCES = {"google_jobs", "careerjet.co.uk"}

# Minimum description length to consider "full enough"
MIN_FULL_LENGTH = 500

# Rate limit: seconds between requests per source
RATE_LIMITS = {
    "reed.co.uk": 0.5,
    "adzuna.co.uk": 1.5,
    "jooble.org": 1.5,
    "default": 1.0,
}

SCRAPE_TIMEOUT = 15

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def needs_enrichment(job):
    """Determine if a job needs its description enriched."""
    source = job.get("source", "")
    desc = job.get("description", "")

    # Skip sources known to have full descriptions
    if any(full_src in source for full_src in FULL_DESCRIPTION_SOURCES):
        return False

    if not desc or len(desc.strip()) < 50:
        return True

    if desc.rstrip().endswith("..."):
        return True

    if len(desc) < MIN_FULL_LENGTH:
        return True

    return False


def strip_html(html_string):
    """Convert HTML to clean plain text."""
    if not html_string:
        return ""

    soup = BeautifulSoup(html_string, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def fetch_reed_detail(job):
    """Fetch full description from Reed detail API.

    Uses GET /api/1.0/jobs/{jobId} which returns full HTML description.
    Returns cleaned plain text, or None on failure.
    """
    job_id = job.get("reed_job_id")
    if not job_id:
        return None

    api_key = os.getenv("REED_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.get(
            f"https://www.reed.co.uk/api/1.0/jobs/{job_id}",
            auth=(api_key, ""),
            timeout=SCRAPE_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        html_desc = data.get("jobDescription", "")
        if html_desc:
            return strip_html(html_desc)
    except Exception as e:
        print(f"    Reed detail API failed for job {job_id}: {e}")

    return None


def scrape_job_page(url):
    """Scrape a job posting page and extract the description text.

    Returns cleaned text, or None on failure.
    """
    if not url or not url.startswith("http"):
        return None

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9",
    }

    try:
        resp = requests.get(
            url, headers=headers, timeout=SCRAPE_TIMEOUT, allow_redirects=True
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Strategy 1: Look for common job description containers
        desc_element = None
        selectors = [
            {"class": re.compile(r"job.?desc", re.I)},
            {"class": re.compile(r"description", re.I)},
            {"class": re.compile(r"job.?detail", re.I)},
            {"class": re.compile(r"job.?content", re.I)},
            {"id": re.compile(r"job.?desc", re.I)},
            {"id": re.compile(r"description", re.I)},
            {"itemprop": "description"},
        ]

        for selector in selectors:
            desc_element = soup.find(attrs=selector)
            if desc_element:
                break

        # Strategy 2: Find the largest text block on the page
        if not desc_element:
            desc_element = _find_largest_text_block(soup)

        if desc_element:
            text = desc_element.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)
            return text.strip() if len(text) > 100 else None

    except requests.RequestException as e:
        print(f"    Scrape failed for {url[:80]}: {e}")
    except Exception as e:
        print(f"    Parse error for {url[:80]}: {e}")

    return None


def _find_largest_text_block(soup):
    """Find the DOM element with the most text content as a fallback."""
    best = None
    best_len = 0

    for element in soup.find_all(["div", "article", "section", "main"]):
        text = element.get_text(strip=True)
        if len(text) > best_len and len(text) > 200:
            best = element
            best_len = len(text)

    return best


def enrich_descriptions(jobs):
    """Enrich job descriptions for jobs with partial/truncated descriptions.

    Modifies jobs in-place. Returns the same list with updated descriptions.
    """
    to_enrich = [(i, job) for i, job in enumerate(jobs) if needs_enrichment(job)]

    if not to_enrich:
        print("All jobs have full descriptions — skipping enrichment.")
        return jobs

    print(f"\nEnriching {len(to_enrich)} of {len(jobs)} job descriptions...")

    last_request_time = {}
    success = 0
    failed = 0
    skipped = 0

    for idx, job in to_enrich:
        source = job.get("source", "default")
        rate_limit = RATE_LIMITS.get(source, RATE_LIMITS["default"])

        # Rate limiting
        now = time.time()
        last = last_request_time.get(source, 0)
        wait = rate_limit - (now - last)
        if wait > 0:
            time.sleep(wait)

        title = job.get("title", "Unknown")[:50]
        company = job.get("company", "Unknown")[:30]
        old_len = len(job.get("description", ""))

        # Choose enrichment strategy
        full_desc = None

        if "reed" in source:
            full_desc = fetch_reed_detail(job)
            strategy = "Reed API"
        else:
            full_desc = scrape_job_page(job.get("url", ""))
            strategy = "web scrape"

        last_request_time[source] = time.time()

        if full_desc and len(full_desc) > old_len:
            jobs[idx]["description"] = full_desc
            new_len = len(full_desc)
            print(f"  OK [{strategy}] {title} @ {company}: {old_len} -> {new_len} chars")
            success += 1
        elif full_desc:
            print(
                f"  SKIP [{strategy}] {title} @ {company}: "
                f"fetched {len(full_desc)} chars <= existing {old_len}"
            )
            skipped += 1
        else:
            print(f"  FAIL [{strategy}] {title} @ {company}: could not fetch full description")
            failed += 1

    print(f"\nEnrichment complete: {success} enriched, {skipped} skipped, {failed} failed")
    return jobs


if __name__ == "__main__":
    import json
    from scraper_utils import TMP_DIR, save_raw_results

    all_jobs = []
    for json_file in TMP_DIR.glob("*_raw.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            all_jobs.extend(json.load(f))

    if all_jobs:
        print(f"Loaded {len(all_jobs)} jobs from .tmp/ raw files")
        enrich_descriptions(all_jobs)
        save_raw_results(all_jobs, "enriched_jobs.json")
    else:
        print("No jobs found in .tmp/ to enrich.")
