"""Job Scraper Dashboard - Streamlit UI (Minimalist Design)

Run with: streamlit run app.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import streamlit as st
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
TMP_DIR = PROJECT_ROOT / ".tmp"
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
CONFIG_PATH = PROJECT_ROOT / "job_search_config.yaml"
QA_DATABANK_PATH = PROJECT_ROOT / "qa_databank.yaml"
REPORTS_PATH = TMP_DIR / "company_reports.json"
TOOLS_DIR = PROJECT_ROOT / "tools"

# Page config
st.set_page_config(
    page_title="Job Scraper",
    page_icon="briefcase",
    layout="wide",
)

# Minimal CSS
st.markdown("""
<style>
/* Compact metrics */
[data-testid="stMetric"] {
    background: #f8f9fa;
    padding: 0.5rem 1rem;
    border-radius: 8px;
}
[data-testid="stMetricValue"] { font-size: 1.5rem; }
[data-testid="stMetricLabel"] { font-size: 0.8rem; }

/* Score colors */
.score-high { color: #28a745; font-weight: 600; }
.score-med { color: #ffc107; font-weight: 600; }
.score-low { color: #6c757d; }

/* Compact expanders */
.streamlit-expanderHeader { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


# === Data Loading Functions ===

def load_jobs():
    """Load jobs from scored_jobs.json."""
    scored_path = TMP_DIR / "scored_jobs.json"
    if scored_path.exists():
        with open(scored_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_profile():
    """Load user profile."""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"profile": {"skills": {"required": [], "preferred": []}, "locations": {"preferred": [], "acceptable": []}, "salary": {"minimum": 20000, "preferred": 30000}, "dealbreakers": []}, "scoring": {"weights": {}}}


def save_profile(profile_data):
    """Save user profile."""
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)


def load_config():
    """Load job search config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"search_params": {"titles": [], "location": "London", "posted_within_days": 7}, "api": {"max_results": 50, "pages": 3}}


def save_config(config_data):
    """Save job search config."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


def load_qa_databank():
    """Load Q&A databank."""
    if QA_DATABANK_PATH.exists():
        with open(QA_DATABANK_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"personal_info": {}, "work_authorization": {}, "salary": {}, "questions": {}, "cover_letter": {}}


def save_qa_databank(databank):
    """Save Q&A databank."""
    with open(QA_DATABANK_PATH, "w", encoding="utf-8") as f:
        yaml.dump(databank, f, default_flow_style=False, allow_unicode=True)


def load_company_reports():
    """Load saved company reports."""
    if REPORTS_PATH.exists():
        with open(REPORTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_company_report(company_name, report):
    """Save a company report."""
    reports = load_company_reports()
    reports[company_name] = report
    TMP_DIR.mkdir(exist_ok=True)
    with open(REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)


def run_tool(script_name):
    """Run a Python script from the tools directory."""
    script_path = TOOLS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(TOOLS_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def generate_company_report(company_name, job_title=None):
    """Generate a research report on a company using Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return f"""**API Key Required**

Add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

**Research {company_name} manually:**
- [Google](https://www.google.com/search?q={company_name.replace(' ', '+')})
- [LinkedIn](https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')})
- [Glassdoor](https://www.glassdoor.co.uk/Reviews/{company_name.replace(' ', '-')}-Reviews)
"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": f"""Brief company research report (under 200 words) for {company_name}.
Job: {job_title or 'Not specified'}

Include:
1. What the company does
2. Key things to research before applying
3. 2-3 potential interview questions
4. Red flags to watch for

Be concise and actionable."""}]
        )
        return f"## {company_name}\n\n{message.content[0].text}"
    except Exception as e:
        return f"**Error:** {str(e)}\n\n[Google {company_name}](https://www.google.com/search?q={company_name.replace(' ', '+')})"


def check_backend_status():
    """Check if the Flask backend is running."""
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


# === Navigation ===

st.sidebar.title("Job Scraper")
page = st.sidebar.radio("Navigation", ["Jobs", "Settings", "Actions"], label_visibility="collapsed")


# ============================================================
# PAGE 1: JOBS (Main View)
# ============================================================

if page == "Jobs":
    jobs = load_jobs()

    # Stats row - compact
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(jobs))
    c2.metric("Matching", len([j for j in jobs if j.get("fit_score", 0) > 0]))
    if jobs:
        c3.metric("Top Score", max(j.get("fit_score", 0) for j in jobs))
        c4.metric("Avg Score", f"{sum(j.get('fit_score', 0) for j in jobs) / len(jobs):.0f}")
    else:
        c3.metric("Top Score", "-")
        c4.metric("Avg Score", "-")

    st.divider()

    if not jobs:
        st.info("No jobs found. Go to **Actions** to scrape jobs.")
    else:
        # Filters - single compact row
        f1, f2, f3 = st.columns([1, 2, 1])
        with f1:
            min_score = st.selectbox("Min Score", [0, 20, 40, 60, 80], index=0, label_visibility="collapsed")
        with f2:
            search = st.text_input("Search", placeholder="Search jobs...", label_visibility="collapsed")
        with f3:
            show_zero = st.checkbox("Show 0", value=False, help="Include jobs with score=0")

        # Filter jobs
        filtered = [
            j for j in jobs
            if (j.get("fit_score", 0) >= min_score or (show_zero and j.get("fit_score", 0) == 0))
            and (not search or search.lower() in j.get("title", "").lower() or search.lower() in j.get("company", "").lower())
        ]
        filtered.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

        st.caption(f"Showing {len(filtered)} of {len(jobs)} jobs")

        if filtered:
            # Initialize selection
            if 'sel_idx' not in st.session_state:
                st.session_state.sel_idx = 0

            # Two columns: list + details
            list_col, detail_col = st.columns([1, 1.2])

            with list_col:
                with st.container(height=450):
                    for idx, job in enumerate(filtered):
                        score = job.get('fit_score', 0)
                        emoji = "🟢" if score >= 70 else "🟡" if score >= 40 else "⚪"
                        is_sel = st.session_state.sel_idx == idx

                        if st.button(
                            f"{emoji} {score} | {job['title'][:28]}... @ {job['company'][:18]}",
                            key=f"j{idx}",
                            use_container_width=True,
                            type="primary" if is_sel else "secondary",
                        ):
                            st.session_state.sel_idx = idx
                            st.rerun()

            # Keep selection in bounds
            sel_idx = min(st.session_state.sel_idx, len(filtered) - 1)
            job = filtered[sel_idx]

            with detail_col:
                score = job.get('fit_score', 0)
                score_color = "green" if score >= 70 else "orange" if score >= 40 else "gray"

                st.markdown(f"### {job['title']}")
                st.markdown(f"**{job['company']}** · :{score_color}[Score: {score}]")
                st.caption(f"📍 {job['location']} · 📅 {job.get('date_posted', 'N/A')} · 💰 {job.get('salary', 'Not listed')}")

                # Action buttons
                b1, b2 = st.columns(2)
                job_url = job.get('url', '#')

                with b1:
                    if job_url and job_url != '#':
                        st.link_button("Apply", job_url, type="primary", use_container_width=True)

                with b2:
                    company = job.get('company', '')
                    reports = load_company_reports()

                    if company in reports:
                        if st.button("View Report", use_container_width=True):
                            st.session_state['show_report'] = company
                    else:
                        if st.button("Research", use_container_width=True):
                            with st.spinner("Researching..."):
                                report = generate_company_report(company, job.get('title'))
                                save_company_report(company, report)
                            st.session_state['show_report'] = company
                            st.rerun()

                # Show report if requested
                if st.session_state.get('show_report') == job.get('company'):
                    reports = load_company_reports()
                    if job.get('company') in reports:
                        st.markdown("---")
                        st.markdown(reports[job.get('company')])
                        if st.button("Close", key="close_rep"):
                            st.session_state['show_report'] = None
                            st.rerun()

            # Job description - full width below
            with st.expander("Job Description", expanded=False):
                st.write(job.get("description", "No description available."))


# ============================================================
# PAGE 2: SETTINGS (All Configuration)
# ============================================================

elif page == "Settings":
    st.title("Settings")

    # Load all data
    profile = load_profile()
    config = load_config()
    databank = load_qa_databank()

    user = profile.get("profile", {})
    skills = user.get("skills", {})
    locations = user.get("locations", {})
    salary = user.get("salary", {})
    search_params = config.get("search_params", {})

    # --- Personal Info ---
    with st.expander("Personal Info", expanded=True):
        personal = databank.get("personal_info", {})

        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Name", value=personal.get("full_name", ""), key="p_name")
            new_email = st.text_input("Email", value=personal.get("email", ""), key="p_email")
            new_phone = st.text_input("Phone", value=personal.get("phone", ""), key="p_phone")
        with c2:
            new_city = st.text_input("City", value=personal.get("city", ""), key="p_city")
            new_postcode = st.text_input("Postcode", value=personal.get("postcode", ""), key="p_postcode")
            new_country = st.text_input("Country", value=personal.get("country", ""), key="p_country")

        new_linkedin = st.text_input("LinkedIn", value=personal.get("linkedin", ""), key="p_li")

        # Auto-save personal info
        new_personal = {
            "full_name": new_name, "email": new_email, "phone": new_phone,
            "city": new_city, "postcode": new_postcode, "country": new_country,
            "linkedin": new_linkedin,
            "github": personal.get("github", ""), "portfolio": personal.get("portfolio", "")
        }
        if new_personal != databank.get("personal_info", {}):
            databank["personal_info"] = new_personal
            save_qa_databank(databank)

    # --- Job Preferences ---
    with st.expander("Job Preferences", expanded=True):
        c1, c2 = st.columns(2)

        with c1:
            new_req = st.text_area(
                "Required Skills (one per line)",
                value="\n".join(skills.get("required", [])),
                height=100, key="s_req"
            )
            new_locs = st.text_area(
                "Preferred Locations (one per line)",
                value="\n".join(locations.get("preferred", [])),
                height=80, key="s_locs"
            )

        with c2:
            new_pref = st.text_area(
                "Preferred Skills (one per line)",
                value="\n".join(skills.get("preferred", [])),
                height=100, key="s_pref"
            )
            c2a, c2b = st.columns(2)
            with c2a:
                new_min_sal = st.number_input("Min Salary", value=salary.get("minimum", 20000), step=1000, key="s_min")
            with c2b:
                new_pref_sal = st.number_input("Pref Salary", value=salary.get("preferred", 30000), step=1000, key="s_pref_sal")

        # Auto-save job preferences
        new_profile = {
            "profile": {
                "name": user.get("name", new_name),
                "skills": {
                    "required": [s.strip() for s in new_req.split("\n") if s.strip()],
                    "preferred": [s.strip() for s in new_pref.split("\n") if s.strip()],
                },
                "locations": {
                    "preferred": [s.strip() for s in new_locs.split("\n") if s.strip()],
                    "acceptable": locations.get("acceptable", []),
                },
                "salary": {"minimum": int(new_min_sal), "preferred": int(new_pref_sal)},
                "dealbreakers": user.get("dealbreakers", []),
            },
            "scoring": profile.get("scoring", {}),
        }
        if new_profile != profile:
            save_profile(new_profile)
            profile = new_profile

    # --- Search Queries ---
    with st.expander("Search Queries", expanded=True):
        c1, c2 = st.columns(2)

        with c1:
            new_titles = st.text_area(
                "Job Titles to Search (one per line)",
                value="\n".join(search_params.get("titles", [])),
                height=100, key="q_titles"
            )

        with c2:
            new_search_loc = st.text_input("Search Location", value=search_params.get("location", "London"), key="q_loc")
            new_days = st.selectbox(
                "Posted Within",
                options=[1, 3, 7, 14, 30],
                index=[1, 3, 7, 14, 30].index(search_params.get("posted_within_days", 7)) if search_params.get("posted_within_days", 7) in [1, 3, 7, 14, 30] else 2,
                format_func=lambda x: f"{x} day{'s' if x > 1 else ''}",
                key="q_days"
            )

        # Auto-save search config
        new_config = {
            "search_params": {
                "titles": [t.strip() for t in new_titles.split("\n") if t.strip()],
                "keywords": search_params.get("keywords", []),
                "location": new_search_loc,
                "remote": search_params.get("remote", False),
                "experience_level": search_params.get("experience_level", ""),
                "posted_within_days": new_days,
            },
            "api": config.get("api", {"max_results": 50, "pages": 3}),
        }
        if new_config != config:
            save_config(new_config)

    # --- Dealbreakers ---
    with st.expander("Dealbreakers", expanded=False):
        new_deal = st.text_area(
            "Keywords that disqualify a job (one per line)",
            value="\n".join(user.get("dealbreakers", [])),
            height=80, key="deal"
        )

        # Auto-save dealbreakers
        new_dealbreakers = [s.strip() for s in new_deal.split("\n") if s.strip()]
        if new_dealbreakers != user.get("dealbreakers", []):
            profile["profile"]["dealbreakers"] = new_dealbreakers
            save_profile(profile)

    # --- Q&A Bank ---
    with st.expander("Q&A Bank", expanded=False):
        st.caption("Saved answers for the Chrome extension")

        questions = databank.get("questions", {})
        updated_questions = {}

        for question, answer in questions.items():
            updated_questions[question] = st.text_area(
                question, value=answer or "", height=80,
                key=f"qa_{hash(question)}", label_visibility="visible"
            )

        # Auto-save Q&A changes
        if updated_questions != questions:
            databank["questions"] = updated_questions
            save_qa_databank(databank)

        # Add new question
        st.markdown("---")
        st.markdown("**Add New Question**")
        c1, c2 = st.columns([1, 2])
        with c1:
            new_q = st.text_input("Question", key="new_q", label_visibility="collapsed", placeholder="Question...")
        with c2:
            new_a = st.text_input("Answer", key="new_a", label_visibility="collapsed", placeholder="Your answer...")

        if st.button("Add", key="add_qa"):
            if new_q:
                databank["questions"][new_q] = new_a
                save_qa_databank(databank)
                st.rerun()

    # --- Work Authorization ---
    with st.expander("Work Authorization", expanded=False):
        work_auth = databank.get("work_authorization", {})

        c1, c2, c3 = st.columns(3)
        with c1:
            new_uk = st.selectbox(
                "Eligible to work in UK?",
                ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("eligible_to_work_uk", "")),
                key="wa_uk"
            )
        with c2:
            new_sponsor = st.selectbox(
                "Require sponsorship?",
                ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("require_sponsorship", "")),
                key="wa_sp"
            )
        with c3:
            new_notice = st.text_input("Notice Period", value=work_auth.get("notice_period", ""), key="wa_np")

        # Auto-save work auth
        new_work_auth = {
            "eligible_to_work_uk": new_uk,
            "require_sponsorship": new_sponsor,
            "notice_period": new_notice,
            "availability": work_auth.get("availability", "")
        }
        if new_work_auth != work_auth:
            databank["work_authorization"] = new_work_auth
            save_qa_databank(databank)

    st.caption("All changes are saved automatically")


# ============================================================
# PAGE 3: ACTIONS (Tools & Extension)
# ============================================================

elif page == "Actions":
    st.title("Actions")

    # Main action buttons
    st.subheader("Scrape & Score Jobs")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Scrape New Jobs", type="primary", use_container_width=True):
            with st.spinner("Scraping jobs..."):
                code, stdout, stderr = run_tool("run_job_scrape.py")
            if code == 0:
                st.success("Done!")
            else:
                st.error("Failed")
            with st.expander("Output", expanded=code != 0):
                st.code(stdout + stderr)

    with c2:
        if st.button("Re-score Jobs", use_container_width=True):
            with st.spinner("Scoring..."):
                code, stdout, stderr = run_tool("score_job_fit.py")
            if code == 0:
                st.success("Done!")
            else:
                st.error("Failed")
            with st.expander("Output", expanded=code != 0):
                st.code(stdout + stderr)

    # Quick stats
    jobs = load_jobs()
    if jobs:
        st.caption(f"Jobs: {len(jobs)} total · {len([j for j in jobs if j.get('fit_score', 0) > 0])} matching")

    st.divider()

    # Chrome Extension
    with st.expander("Chrome Extension", expanded=True):
        backend_running = check_backend_status()

        c1, c2 = st.columns([2, 1])
        with c1:
            if backend_running:
                st.success("Backend running on localhost:5000")
            else:
                st.warning("Backend not running")

        with c2:
            if not backend_running:
                if st.button("Start Backend", type="primary", use_container_width=True):
                    subprocess.Popen(
                        [sys.executable, str(TOOLS_DIR / "answer_questions_api.py")],
                        cwd=str(TOOLS_DIR),
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                    )
                    st.info("Starting... refresh in a few seconds")
                    time.sleep(2)
                    st.rerun()

        st.markdown("""
**Setup:** `chrome://extensions` → Developer mode → Load unpacked → select `chrome-extension/`

**Usage:** Open job application → Click extension → Copy Page → Parse & Get Answers → Copy answers to form
        """)

        # Q&A stats
        databank = load_qa_databank()
        questions_count = len([q for q, a in databank.get("questions", {}).items() if a])
        st.caption(f"Q&A Bank: {questions_count} saved answers")

    # Test API
    if check_backend_status():
        with st.expander("Test API", expanded=False):
            test_text = st.text_area("Paste application text:", height=100, placeholder="Paste text to test...")

            if st.button("Test"):
                if test_text:
                    try:
                        response = requests.post(
                            "http://localhost:5000/api/parse-and-answer",
                            json={"pageText": test_text, "context": {}},
                            timeout=30
                        )
                        if response.ok:
                            data = response.json()
                            st.success(f"Found {data.get('total_questions', 0)} questions")
                            for item in data.get("answers", []):
                                st.markdown(f"**Q:** {item['question']}")
                                st.markdown(f"**A:** {item['answer']}")
                                st.caption(f"Source: {item['source']}")
                                st.markdown("---")
                    except Exception as e:
                        st.error(str(e))
