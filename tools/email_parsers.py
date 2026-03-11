"""Recruiter email HTML parsers.

Each parser extracts job listings from the HTML body of emails
sent by a specific recruiter. Uses BeautifulSoup for robust
HTML parsing.

Registry pattern: use @register_parser("name") decorator.
"""

import re

from bs4 import BeautifulSoup

# Parser registry
PARSERS = {}


def register_parser(name):
    """Decorator to register a parser function by name."""
    def wrapper(fn):
        PARSERS[name] = fn
        return fn
    return wrapper


def get_parser(name):
    """Get parser by name, falling back to generic."""
    return PARSERS.get(name, PARSERS.get("generic"))


def _clean_text(text):
    """Normalise whitespace in extracted text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _extract_jobs_from_links(soup, url_pattern, site_name):
    """Generic helper: find job links matching a URL pattern,
    walk up to parent container, extract surrounding text.

    Returns list of {title, company, location, salary, url, description}.
    """
    jobs = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not re.search(url_pattern, href, re.I):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)

        title = _clean_text(link.get_text())
        if not title or len(title) < 3:
            continue

        # Walk up to find a container with more info
        container = link.parent
        for _ in range(5):
            if container.parent and container.parent.name not in ("body", "html", "[document]"):
                # Stop if the parent contains other job links (we've gone too far)
                other_links = container.parent.find_all("a", href=re.compile(url_pattern, re.I))
                if len(other_links) > 1:
                    break
                container = container.parent

        container_text = _clean_text(container.get_text())

        # Try to extract structured fields from container text
        company = ""
        location = ""
        salary = ""

        # Look for salary patterns
        salary_match = re.search(
            r"£[\d,]+(?:\s*[-–]\s*£[\d,]+)?(?:\s*(?:per\s+)?(?:annum|year|p\.?a\.?|day|hour))?",
            container_text, re.I,
        )
        if salary_match:
            salary = salary_match.group(0)

        # Look for location patterns (common UK cities/regions or "Remote")
        loc_match = re.search(
            r"(?:London|Manchester|Birmingham|Leeds|Bristol|Edinburgh|Glasgow|"
            r"Liverpool|Sheffield|Cardiff|Belfast|Remote|Hybrid|"
            r"[A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?)",
            container_text,
        )
        if loc_match:
            location = loc_match.group(0)

        # Description is remaining container text minus title
        description = container_text.replace(title, "", 1).strip()
        if len(description) > 500:
            description = description[:497] + "..."

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "url": href,
            "description": description,
        })

    return jobs


# ── Michael Page ─────────────────────────────────────────────────────────────

@register_parser("michael_page")
def parse_michael_page(html):
    """Parse Michael Page job alert emails.

    Michael Page emails contain job cards with links to
    michaelpage.co.uk/job-detail/ or michaelpage.co.uk/jobs/
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen = set()

    # Find all job links
    job_links = soup.find_all(
        "a", href=re.compile(r"michaelpage\.co\.uk/(job-detail|jobs)/", re.I)
    )

    for link in job_links:
        href = link["href"]
        # Normalise tracking URLs — extract the actual URL if wrapped
        clean_url = href.split("?")[0] if "?" in href else href

        if clean_url in seen:
            continue
        seen.add(clean_url)

        title = _clean_text(link.get_text())
        if not title or len(title) < 3:
            continue

        # Walk up to the job card container (usually a <td> or <div>)
        container = link.parent
        for _ in range(6):
            if container.parent and container.parent.name not in ("body", "html", "[document]"):
                sibling_links = container.parent.find_all(
                    "a", href=re.compile(r"michaelpage\.co\.uk/(job-detail|jobs)/", re.I)
                )
                if len(sibling_links) > 1:
                    break
                container = container.parent

        # Extract text blocks from the container
        text_blocks = [_clean_text(t) for t in container.stripped_strings]
        full_text = " ".join(text_blocks)

        company = ""
        location = ""
        salary = ""

        # Michael Page often has: title, location, salary, brief description
        for block in text_blocks:
            if block == title:
                continue
            if re.search(r"£[\d,]", block):
                salary = block
            elif re.search(r"(?:London|Remote|Hybrid|UK|England|Scotland|Wales)", block, re.I):
                location = block
            elif not company and len(block) > 3 and block != title:
                company = block

        description = full_text[:500]

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "url": clean_url,
            "description": description,
        })

    return jobs


# ── Reed ─────────────────────────────────────────────────────────────────────

@register_parser("reed")
def parse_reed_email(html):
    """Parse Reed.co.uk job alert emails.

    Reed emails contain job cards with links to reed.co.uk/jobs/
    """
    soup = BeautifulSoup(html, "html.parser")
    return _extract_jobs_from_links(soup, r"reed\.co\.uk/jobs/", "Reed")


# ── Indeed ───────────────────────────────────────────────────────────────────

@register_parser("indeed")
def parse_indeed(html):
    """Parse Indeed job alert emails.

    Indeed emails link to indeed.co.uk/viewjob or indeed.com/viewjob
    """
    soup = BeautifulSoup(html, "html.parser")
    return _extract_jobs_from_links(soup, r"indeed\.co(?:\.uk|m)/(?:viewjob|rc/clk)", "Indeed")


# ── Totaljobs ────────────────────────────────────────────────────────────────

@register_parser("totaljobs")
def parse_totaljobs(html):
    """Parse Totaljobs job alert emails."""
    soup = BeautifulSoup(html, "html.parser")
    return _extract_jobs_from_links(soup, r"totaljobs\.com/job/", "Totaljobs")


# ── CV-Library ───────────────────────────────────────────────────────────────

@register_parser("cv_library")
def parse_cv_library(html):
    """Parse CV-Library job alert emails."""
    soup = BeautifulSoup(html, "html.parser")
    return _extract_jobs_from_links(soup, r"cv-library\.co\.uk/job/", "CV-Library")


# ── Generic fallback ─────────────────────────────────────────────────────────

@register_parser("generic")
def parse_generic(html):
    """Fallback parser for unknown recruiter email formats.

    Finds all links that look like job URLs and extracts surrounding text.
    """
    soup = BeautifulSoup(html, "html.parser")
    return _extract_jobs_from_links(
        soup,
        r"/(job[s\-]?|vacancy|vacanc|career|apply|position|opening)[/\-]",
        "email",
    )
