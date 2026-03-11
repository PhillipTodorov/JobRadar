"""ATS Keyword Matcher - Extract skills from job descriptions and compare to user profile.

Deterministic skill extraction using a built-in dictionary of common
skills and their aliases. No LLM required.

Usage:
    # As a module (from app.py):
    from tools.ats_matcher import match_job, extract_skills, get_user_skills

    # CLI test:
    python ats_matcher.py "job description text here"
"""

import json
import re
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
CV_PATH = PROJECT_ROOT / ".tmp" / "cv_extracted.json"

# ── Skills dictionary ─────────────────────────────────────────────────────────
# Maps canonical skill name → list of aliases/variations to search for.
# All matching is case-insensitive.

SKILLS_DB = {
    # Programming languages
    "Python": ["python"],
    "JavaScript": ["javascript", "js ", "node.js", "nodejs"],
    "TypeScript": ["typescript"],
    "Java": ["java "],  # trailing space to avoid matching "javascript"
    "C#": ["c#", "c-sharp", "csharp", ".net"],
    "C++": ["c++", "cpp"],
    "Go": ["golang", " go "],
    "Rust": ["rust "],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "R": [" r ", "r programming"],
    "Scala": [" scala ", "scala "],
    "SQL": ["sql"],

    # Web / Frontend
    "HTML/CSS": ["html", "css"],
    "React": ["react", "reactjs", "react.js"],
    "Angular": ["angular"],
    "Vue.js": ["vue", "vuejs", "vue.js"],
    "Next.js": ["next.js", "nextjs"],
    "Tailwind CSS": ["tailwind"],
    "Bootstrap": ["bootstrap"],
    "Sass/SCSS": ["sass", "scss"],
    "jQuery": ["jquery"],

    # Backend / Frameworks
    "Flask": ["flask"],
    "Django": ["django"],
    "FastAPI": ["fastapi"],
    "Express": ["express.js", "expressjs", "express "],
    "Spring": ["spring boot", "spring framework"],
    "ASP.NET": ["asp.net"],
    "Ruby on Rails": ["rails", "ruby on rails"],
    "Laravel": ["laravel"],

    # Databases
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "SQLite": ["sqlite"],
    "Oracle": ["oracle db", "oracle database"],
    "SQL Server": ["sql server", "mssql"],
    "DynamoDB": ["dynamodb"],
    "Elasticsearch": ["elasticsearch", "elastic search"],

    # Cloud / DevOps
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "ci cd", "continuous integration", "continuous deployment"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],
    "Jenkins": ["jenkins"],
    "GitHub Actions": ["github actions"],
    "Linux": ["linux"],
    "Nginx": ["nginx"],

    # Data / Analytics
    "Data Analysis": ["data analysis", "data analyst"],
    "Data Science": ["data science"],
    "Machine Learning": ["machine learning", "ml "],
    "Deep Learning": ["deep learning"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Excel": ["excel", "spreadsheet"],
    "Data Entry": ["data entry"],
    "Data Visualisation": ["data visualisation", "data visualization"],
    "Reporting": ["reporting", "report writing"],
    "Statistics": ["statistics", "statistical analysis"],

    # Project Management / Methodologies
    "Agile": ["agile"],
    "Scrum": ["scrum"],
    "Kanban": ["kanban"],
    "Jira": ["jira"],
    "Confluence": ["confluence"],
    "Trello": ["trello"],
    "Asana": ["asana"],
    "Project Management": ["project management"],
    "PRINCE2": ["prince2"],
    "Six Sigma": ["six sigma"],
    "Lean": ["lean methodology", "lean management"],
    "Waterfall": ["waterfall"],

    # Design / Creative
    "Figma": ["figma"],
    "Photoshop": ["photoshop"],
    "Illustrator": ["illustrator"],
    "Adobe Creative Suite": ["adobe creative suite", "adobe cc"],
    "InDesign": ["indesign"],
    "Canva": ["canva"],
    "UI/UX": ["ui/ux", "ux design", "ui design", "user experience"],
    "Wireframing": ["wireframing", "wireframe"],

    # Office / Productivity
    "Microsoft Office": ["microsoft office", "ms office", "office 365", "microsoft 365"],
    "Word": ["microsoft word", "ms word"],
    "PowerPoint": ["powerpoint", "presentations"],
    "Outlook": ["outlook"],
    "Google Workspace": ["google workspace", "gsuite", "g suite", "google docs", "google sheets"],
    "SharePoint": ["sharepoint"],
    "SAP": ["sap "],
    "Salesforce": ["salesforce"],
    "HubSpot": ["hubspot"],
    "CRM": ["crm"],
    "ERP": ["erp"],

    # Soft Skills
    "Communication": ["communication", "communicate effectively"],
    "Written Communication": ["written communication", "writing skills", "report writing"],
    "Team Collaboration": ["teamwork", "team collaboration", "team player", "collaborative"],
    "Problem Solving": ["problem solving", "problem-solving", "analytical thinking"],
    "Critical Thinking": ["critical thinking"],
    "Leadership": ["leadership", "team lead"],
    "Time Management": ["time management", "prioritisation", "prioritization"],
    "Attention to Detail": ["attention to detail", "detail-oriented", "detail oriented"],
    "Adaptability": ["adaptability", "flexible", "adaptable"],
    "Organisation": ["organisational", "organizational", "organisation", "organization"],
    "Customer Service": ["customer service", "client facing", "client-facing", "customer support"],
    "Stakeholder Management": ["stakeholder management", "stakeholder engagement"],
    "Presentation Skills": ["presentation skills", "presenting"],
    "Negotiation": ["negotiation", "negotiating"],
    "Multitasking": ["multitasking", "multi-tasking"],
    "Initiative": ["self-starter", "initiative", "proactive"],

    # Admin / Operations
    "Administration": ["administration", "administrative", "admin support", "office management"],
    "Scheduling": ["scheduling", "diary management", "calendar management"],
    "Email Management": ["email management", "inbox management", "correspondence"],
    "Meeting Coordination": ["meeting coordination", "minutes", "minute taking"],
    "Filing": ["filing", "document management", "records management"],
    "Reception": ["reception", "front desk", "front of house"],
    "Travel Arrangements": ["travel arrangements", "travel booking"],
    "Procurement": ["procurement", "purchasing"],
    "Invoicing": ["invoicing", "invoice processing"],
    "Bookkeeping": ["bookkeeping", "accounts payable", "accounts receivable"],

    # Version Control / Tools
    "Git": ["git ", "github", "gitlab", "bitbucket"],
    "REST APIs": ["rest api", "restful", "api development", "api integration"],
    "GraphQL": ["graphql"],
    "Testing": ["unit testing", "test-driven", "tdd", "automated testing", "pytest", "jest"],

    # Security / Compliance
    "GDPR": ["gdpr", "data protection"],
    "Cybersecurity": ["cybersecurity", "information security", "infosec"],
    "ISO": ["iso 27001", "iso 9001"],

    # Other
    "Typing": ["typing speed", "wpm"],
    "DBS Check": ["dbs check", "dbs checked", "crb check"],
    "Driving Licence": ["driving licence", "driving license", "full uk driving"],
}

# Experience patterns (reused from score_job_fit.py)
_YEARS_PATTERNS = [
    re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", re.I),
    re.compile(r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)", re.I),
    re.compile(r"minimum\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?)", re.I),
    re.compile(r"at\s+least\s+(\d+)\s*(?:years?|yrs?)", re.I),
]


def extract_skills(text):
    """Extract skills mentioned in a text using the skills dictionary.

    Returns a set of canonical skill names found in the text.
    """
    text_lower = text.lower()
    found = set()

    for skill, aliases in SKILLS_DB.items():
        for alias in aliases:
            if alias in text_lower:
                found.add(skill)
                break

    return found


def extract_years_required(text):
    """Extract years of experience required from text."""
    max_years = 0
    for pattern in _YEARS_PATTERNS:
        for match in pattern.finditer(text):
            groups = [int(g) for g in match.groups() if g is not None]
            if groups:
                max_years = max(max_years, max(groups))
    return max_years


def get_user_skills():
    """Load user skills from profile YAML and CV extracted data.

    Returns a set of canonical skill names the user has.
    """
    user_skills = set()

    # From user_profile.yaml
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
        skills = profile.get("profile", {}).get("skills", {})
        for skill in skills.get("required", []):
            user_skills.add(skill)
        for skill in skills.get("preferred", []):
            user_skills.add(skill)

    # From CV extracted data — match CV text against skills DB
    if CV_PATH.exists():
        try:
            with open(CV_PATH, "r", encoding="utf-8") as f:
                cv_data = json.load(f)
            extracted = cv_data.get("extracted", {})

            # Build searchable text from CV
            cv_text_parts = [extracted.get("summary", "")]
            for exp in extracted.get("experience", []):
                cv_text_parts.append(exp.get("role", ""))
                cv_text_parts.extend(exp.get("achievements", []))
            for edu in extracted.get("education", []):
                cv_text_parts.append(edu.get("field", "") or "")

            cv_text = " ".join(cv_text_parts)
            cv_skills = extract_skills(cv_text)
            user_skills.update(cv_skills)
        except (json.JSONDecodeError, KeyError):
            pass

    return user_skills


def match_job(job_description, job_title=""):
    """Match a job against the user's skills.

    Returns dict with match_pct, matched, missing, experience info.
    """
    text = f"{job_title} {job_description}"
    job_skills = extract_skills(text)
    user_skills = get_user_skills()

    # Normalise for comparison (case-insensitive matching of canonical names)
    user_lower = {s.lower(): s for s in user_skills}
    job_lower = {s.lower(): s for s in job_skills}

    matched_keys = set(user_lower.keys()) & set(job_lower.keys())
    missing_keys = set(job_lower.keys()) - set(user_lower.keys())

    matched = sorted(job_lower[k] for k in matched_keys)
    missing = sorted(job_lower[k] for k in missing_keys)

    total = len(job_skills)
    match_pct = round((len(matched) / total) * 100) if total > 0 else 0

    years_required = extract_years_required(text)

    return {
        "match_pct": match_pct,
        "matched": matched,
        "missing": missing,
        "job_skills_count": total,
        "user_skills_count": len(user_skills),
        "experience_required": f"{years_required}+ years" if years_required else "",
    }


def skills_gap_analysis(jobs):
    """Aggregate skill demand across all jobs and compare to user profile.

    Args:
        jobs: List of job dicts with 'description' and 'title' fields.

    Returns dict with frequency counts and gap analysis.
    """
    from collections import Counter

    user_skills = get_user_skills()
    user_lower = {s.lower() for s in user_skills}

    skill_counts = Counter()

    for job in jobs:
        text = f"{job.get('title', '')} {job.get('description', '')}"
        job_skills = extract_skills(text)
        for skill in job_skills:
            skill_counts[skill] += 1

    total_jobs = len(jobs) if jobs else 1

    # Build ranked list
    ranked = []
    for skill, count in skill_counts.most_common():
        ranked.append({
            "skill": skill,
            "count": count,
            "pct": round((count / total_jobs) * 100),
            "have": skill.lower() in user_lower,
        })

    have_count = sum(1 for r in ranked[:20] if r["have"])
    top_20 = ranked[:20]
    coverage = round((have_count / len(top_20)) * 100) if top_20 else 0

    return {
        "ranked": ranked,
        "top_20_coverage": coverage,
        "total_skills_found": len(skill_counts),
        "user_skills_count": len(user_skills),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ats_matcher.py \"<job description>\"")
        sys.exit(1)

    sys.stdout.reconfigure(encoding="utf-8")
    result = match_job(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
