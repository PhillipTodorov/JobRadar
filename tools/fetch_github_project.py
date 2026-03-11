"""Fetch project info from a public GitHub repository URL.

Uses the GitHub REST API (no authentication needed for public repos)
to extract repo metadata, languages, and dependencies. Returns
structured JSON that can pre-fill the Projects form.

Usage:
    python fetch_github_project.py https://github.com/owner/repo
"""

import base64
import json
import re
import sys

import requests

# Map common npm package names to display names
JS_PACKAGE_MAP = {
    "react": "React",
    "react-dom": "React",
    "next": "Next.js",
    "vue": "Vue.js",
    "nuxt": "Nuxt.js",
    "angular": "Angular",
    "@angular/core": "Angular",
    "svelte": "Svelte",
    "express": "Express",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "vite": "Vite",
    "webpack": "Webpack",
    "prisma": "Prisma",
    "@prisma/client": "Prisma",
    "mongoose": "MongoDB",
    "pg": "PostgreSQL",
    "redis": "Redis",
    "ioredis": "Redis",
    "socket.io": "Socket.IO",
    "graphql": "GraphQL",
    "@apollo/client": "Apollo GraphQL",
    "jest": "Jest",
    "vitest": "Vitest",
    "typescript": "TypeScript",
    "electron": "Electron",
    "three": "Three.js",
    "d3": "D3.js",
    "firebase": "Firebase",
    "supabase": "Supabase",
    "@supabase/supabase-js": "Supabase",
    "axios": "Axios",
    "zustand": "Zustand",
    "@reduxjs/toolkit": "Redux",
    "redux": "Redux",
    "styled-components": "Styled Components",
    "@emotion/react": "Emotion",
    "framer-motion": "Framer Motion",
    "shadcn-ui": "shadcn/ui",
    "@radix-ui/react-dialog": "Radix UI",
    "lucide-react": "Lucide Icons",
    "drizzle-orm": "Drizzle ORM",
    "trpc": "tRPC",
    "@trpc/server": "tRPC",
}

# Map common Python package names to display names
PY_PACKAGE_MAP = {
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "streamlit": "Streamlit",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "redis": "Redis",
    "psycopg2": "PostgreSQL",
    "psycopg2-binary": "PostgreSQL",
    "pymongo": "MongoDB",
    "boto3": "AWS SDK",
    "requests": "Requests",
    "beautifulsoup4": "BeautifulSoup",
    "selenium": "Selenium",
    "playwright": "Playwright",
    "pydantic": "Pydantic",
    "pytest": "Pytest",
    "anthropic": "Anthropic API",
    "openai": "OpenAI API",
    "serpapi": "SerpAPI",
    "pyyaml": "YAML",
    "pillow": "Pillow",
    "matplotlib": "Matplotlib",
    "scipy": "SciPy",
}

# Languages to skip unless they're dominant
TRIVIAL_LANGUAGES = {"Shell", "Dockerfile", "Makefile", "Batchfile", "Nix", "Procfile"}

API_BASE = "https://api.github.com"


def clean_markdown(text):
    """Strip markdown formatting and leading emoji from text."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Strip leading emoji/symbols (non-ASCII at start)
    text = re.sub(r'^[^\x20-\x7E]+\s*', '', text)
    return text.strip()


def parse_github_url(url):
    """Extract owner and repo name from a GitHub URL."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def github_get(endpoint):
    """Make a GET request to the GitHub API. Returns (data, error)."""
    try:
        resp = requests.get(
            f"{API_BASE}{endpoint}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
    except requests.RequestException as e:
        return None, f"Network error: {e}"

    if resp.status_code == 404:
        return None, None  # Not found is not an error for optional endpoints
    if resp.status_code == 403:
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        if remaining == "0":
            reset = resp.headers.get("X-RateLimit-Reset", "")
            return None, f"GitHub API rate limit exceeded. Try again later."
        return None, f"GitHub API forbidden (status 403)"
    if resp.status_code != 200:
        return None, f"GitHub API returned status {resp.status_code}"

    return resp.json(), None


def extract_languages(owner, repo):
    """Get languages sorted by usage, filtering trivial ones."""
    data, err = github_get(f"/repos/{owner}/{repo}/languages")
    if err or not data:
        return []

    total_bytes = sum(data.values())
    if total_bytes == 0:
        return []

    languages = []
    for lang, byte_count in sorted(data.items(), key=lambda x: x[1], reverse=True):
        pct = byte_count / total_bytes * 100
        if lang in TRIVIAL_LANGUAGES and pct < 10:
            continue
        if pct < 2:
            continue
        languages.append(lang)

    return languages


def extract_js_technologies(owner, repo):
    """Extract technology names from package.json dependencies."""
    data, err = github_get(f"/repos/{owner}/{repo}/contents/package.json")
    if err or not data:
        return []

    try:
        content = base64.b64decode(data["content"]).decode("utf-8")
        pkg = json.loads(content)
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return []

    techs = set()
    for dep_key in ("dependencies", "devDependencies"):
        deps = pkg.get(dep_key, {})
        for package_name in deps:
            display = JS_PACKAGE_MAP.get(package_name)
            if display:
                techs.add(display)

    return sorted(techs)


def extract_py_technologies(owner, repo):
    """Extract technology names from requirements.txt."""
    data, err = github_get(f"/repos/{owner}/{repo}/contents/requirements.txt")
    if err or not data:
        return []

    try:
        content = base64.b64decode(data["content"]).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return []

    techs = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip version specifiers: package>=1.0 -> package
        package_name = re.split(r"[>=<!\[;]", line)[0].strip().lower()
        display = PY_PACKAGE_MAP.get(package_name)
        if display:
            techs.add(display)

    return sorted(techs)


def extract_readme_content(owner, repo):
    """Extract description and key features from README.

    Returns (description, highlights) where description is intro text
    and highlights is newline-separated "- feature" lines.
    """
    data, err = github_get(f"/repos/{owner}/{repo}/readme")
    if err or not data:
        return "", ""

    try:
        content = base64.b64decode(data["content"]).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return "", ""

    lines = content.split("\n")

    # --- Extract description from intro (before first ## heading) ---
    desc_parts = []
    past_title = False

    for line in lines:
        stripped = line.strip()

        # Skip the main title heading
        if stripped.startswith("# ") and not past_title:
            past_title = True
            continue
        if not past_title:
            continue

        # Stop at first section heading or horizontal rule after content
        if stripped.startswith("## "):
            break
        if stripped == "---" and desc_parts:
            break

        # Skip badges, images, HTML
        if stripped.startswith(("![", "[![", "<img", "<p", "<!--", "<div")):
            continue
        # Skip code blocks
        if stripped.startswith("```"):
            continue
        # Skip empty lines
        if not stripped:
            continue

        cleaned = clean_markdown(stripped)
        # Skip short fragments, bare URLs, and link reference lines
        if len(cleaned) <= 10 or cleaned.startswith("http"):
            continue
        if re.search(r'\w+\.\w+\.\w+', cleaned) and ':' in cleaned:
            continue
        desc_parts.append(cleaned)

    description = " ".join(desc_parts)
    if len(description) > 500:
        description = description[:497] + "..."

    # --- Extract features from README sections ---
    features = []
    feature_keywords = {
        "what it does", "features", "key features", "highlights",
        "capabilities", "overview",
    }

    in_feature_section = False
    past_table_header = False

    for line in lines:
        stripped = line.strip()

        # Check for feature section headings
        if stripped.startswith("#"):
            heading = re.sub(
                r'[^\w\s]', '',
                stripped.lstrip("#").strip()
            ).strip().lower()
            if heading in feature_keywords:
                in_feature_section = True
                past_table_header = False
                continue
            elif in_feature_section:
                break  # Hit next section

        if not in_feature_section:
            continue

        # Extract bullet points
        bullet = re.match(r'^[-*•]\s+(.+)', stripped)
        if bullet:
            feature = clean_markdown(bullet.group(1))
            if feature and len(feature) > 5:
                features.append(f"- {feature}")
            continue

        # Extract table rows
        if stripped.startswith("|"):
            # Skip separator rows
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue

            cells = [c.strip() for c in stripped.split("|")]
            cells = [c for c in cells if c]

            if len(cells) >= 2:
                if not past_table_header:
                    past_table_header = True
                    continue  # Skip header row

                name = clean_markdown(cells[0])
                desc = clean_markdown(cells[1])
                if name and desc:
                    features.append(f"- {name}: {desc}")
            continue

    highlights = "\n".join(features[:10])
    return description, highlights


def fetch_github_project(url):
    """Fetch project info from a GitHub URL. Returns a dict."""
    owner, repo = parse_github_url(url)
    if not owner or not repo:
        return {"error": "Invalid GitHub URL. Expected: https://github.com/owner/repo"}

    # Fetch repo metadata
    repo_data, err = github_get(f"/repos/{owner}/{repo}")
    if err:
        return {"error": err}
    if not repo_data:
        return {"error": "Repository not found. Make sure it's a public repository."}

    # Build project info
    name = repo_data.get("name", repo)
    repo_url = repo_data.get("html_url", url)
    demo_url = repo_data.get("homepage", "") or ""
    topics = repo_data.get("topics", [])

    # Extract description and highlights from README
    readme_desc, highlights = extract_readme_content(owner, repo)
    description = readme_desc or (repo_data.get("description", "") or "")

    # Build technologies list
    techs = []

    # 1. Languages from API
    languages = extract_languages(owner, repo)
    techs.extend(languages)

    # 2. Dependencies from package.json
    js_techs = extract_js_technologies(owner, repo)
    for t in js_techs:
        if t not in techs:
            techs.append(t)

    # 3. Dependencies from requirements.txt
    py_techs = extract_py_technologies(owner, repo)
    for t in py_techs:
        if t not in techs:
            techs.append(t)

    # 4. Topics that look like technologies (lowercase, no spaces)
    for topic in topics:
        # Capitalize topic as a potential tech name
        display = topic.replace("-", " ").title()
        if display not in techs and len(topic) > 1:
            techs.append(display)

    # Cap at 15 technologies
    techs = techs[:15]

    return {
        "name": name,
        "url": repo_url,
        "demo_url": demo_url,
        "technologies": ", ".join(techs),
        "description": description,
        "highlights": highlights,
        "error": None,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch_github_project.py <github_url>"}))
        sys.exit(1)

    result = fetch_github_project(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False))
