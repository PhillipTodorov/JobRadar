"""Job Scraper Dashboard - Streamlit UI

Run with: streamlit run app.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Project paths
PROJECT_ROOT = Path(__file__).parent
TMP_DIR = PROJECT_ROOT / ".tmp"
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
CONFIG_PATH = PROJECT_ROOT / "job_search_config.yaml"
QA_DATABANK_PATH = PROJECT_ROOT / "qa_databank.yaml"
REPORTS_PATH = TMP_DIR / "company_reports.json"
TOOLS_DIR = PROJECT_ROOT / "tools"

sys.path.insert(0, str(TOOLS_DIR))
from cover_letter_generator import generate_cover_letter as _generate_cover_letter

# Page config
st.set_page_config(
    page_title="JobRadar",
    page_icon="briefcase",
    layout="wide",
)

st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
/* Keep toolbar in DOM (expand button lives inside it) — just make it invisible */
[data-testid="stToolbar"] { background: transparent !important; border: none !important; }
header { background: transparent !important; }
.block-container { padding-top: 1.5rem; padding-bottom: 0; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }

/* Sidebar nav buttons */
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    border: none !important;
    border-radius: 6px !important;
    text-align: left !important;
    padding: 0.45rem 0.75rem !important;
    font-size: 0.875rem !important;
    width: 100% !important;
    justify-content: flex-start !important;
    transition: background 0.15s !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    color: #888 !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #e0e0e0 !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: rgba(79,142,247,0.15) !important;
    color: #4f8ef7 !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
    background: rgba(79,142,247,0.22) !important;
}

.stat-card {
    background: #1e1e2e;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    text-align: left;
}
.stat-card .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.stat-card .stat-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #555;
}
.job-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid #1a1a28;
}
.job-row:last-child { border-bottom: none; }
.score-badge {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 10px;
    min-width: 30px;
    text-align: center;
    flex-shrink: 0;
}
.job-row-title { font-size: 0.82rem; color: #d0d0d0; font-weight: 500; }
.job-row-sub { font-size: 0.7rem; color: #555; margin-top: 1px; }
.kanban-card {
    background: #1e1e2e;
    border: 1px solid #2a2a3e;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
}
.kanban-card .kc-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e0e0e0;
    margin-bottom: 2px;
    overflow-wrap: break-word;
}
.kanban-card .kc-company {
    font-size: 0.75rem;
    color: #888;
    margin-bottom: 6px;
}
.kanban-card .kc-meta {
    font-size: 0.7rem;
    color: #555;
}
.streamlit-expanderHeader { font-size: 0.9rem; }
/* Override Streamlit bordered containers to match dark theme */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #2a2a3e !important;
    background: #161622 !important;
    border-radius: 8px !important;
}
.detail-header {
    background: #1e1e2e;
    border: 1px solid #2a2a3e;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.dh-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 4px; }
.dh-title { font-size: 1rem; font-weight: 700; color: #e0e0e0; line-height: 1.3; }
.dh-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.dh-company { font-size: 0.82rem; color: #aaa; font-weight: 500; }
.dh-meta { font-size: 0.72rem; color: #555; margin-top: 4px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data
def _load_jobs_cached(mtime: float):
    scored_path = TMP_DIR / "scored_jobs.json"
    with open(scored_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jobs():
    scored_path = TMP_DIR / "scored_jobs.json"
    if not scored_path.exists():
        return []
    return _load_jobs_cached(scored_path.stat().st_mtime)


def load_profile():
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"profile": {"skills": {"required": [], "preferred": []},
                        "locations": {"preferred": [], "acceptable": []},
                        "salary": {"minimum": 20000, "preferred": 30000},
                        "dealbreakers": []},
            "scoring": {"weights": {}}}


def _gist_auto_push():
    """Silent gist sync after save. Never raises."""
    try:
        from tools.gist_sync import auto_push
        auto_push()
    except Exception:
        pass


def save_profile(profile_data):
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)
    _gist_auto_push()


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"search_params": {"titles": [], "location": "London", "posted_within_days": 7},
            "api": {"max_results": 50, "pages": 3}}


def save_config(config_data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    _gist_auto_push()


def load_qa_databank():
    if QA_DATABANK_PATH.exists():
        with open(QA_DATABANK_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"personal_info": {}, "work_authorization": {}, "salary": {}, "questions": {}, "cover_letter": {}}


def save_qa_databank(databank):
    with open(QA_DATABANK_PATH, "w", encoding="utf-8") as f:
        yaml.dump(databank, f, default_flow_style=False, allow_unicode=True)
    _gist_auto_push()


def load_company_reports():
    if REPORTS_PATH.exists():
        with open(REPORTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_company_report(company_name, report):
    reports = load_company_reports()
    reports[company_name] = report
    TMP_DIR.mkdir(exist_ok=True)
    with open(REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)
    _gist_auto_push()


def run_tool(script_name):
    script_path = TOOLS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(TOOLS_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def generate_company_report(company_name, job_title=None):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return (f"**Research {company_name} manually:**\n"
                f"- [Google](https://www.google.com/search?q={company_name.replace(' ', '+')})\n"
                f"- [LinkedIn](https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')})\n"
                f"- [Glassdoor](https://www.glassdoor.co.uk/Reviews/{company_name.replace(' ', '-')}-Reviews)")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content":
                f"Brief company research report (under 200 words) for {company_name}. "
                f"Job: {job_title or 'Not specified'}. Include: what they do, key things "
                "to research before applying, 2-3 likely interview questions, red flags."}]
        )
        return f"## {company_name}\n\n{message.content[0].text}"
    except Exception as e:
        return f"**Error:** {str(e)}"


TRACKER_PATH = TMP_DIR / "application_tracker.json"
HIDDEN_JOBS_PATH = TMP_DIR / "hidden_jobs.json"
TRACKER_STATUSES = ["Saved", "Applied", "Interview", "Offer", "Rejected"]
STATUS_COLOURS = {
    "Saved": "#4f8ef7", "Applied": "#aaa",
    "Interview": "#ffc107", "Offer": "#28a745", "Rejected": "#dc3545",
}


def load_tracker() -> list:
    if TRACKER_PATH.exists():
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_tracker(entries: list):
    TMP_DIR.mkdir(exist_ok=True)
    with open(TRACKER_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    _gist_auto_push()


def load_hidden_jobs() -> set:
    if HIDDEN_JOBS_PATH.exists():
        with open(HIDDEN_JOBS_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_hidden_jobs(hidden: set):
    TMP_DIR.mkdir(exist_ok=True)
    with open(HIDDEN_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(hidden), f, indent=2)
    _gist_auto_push()


def add_to_tracker(job: dict):
    import uuid
    tracker = load_tracker()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "salary": job.get("salary", ""),
        "url": job.get("url", ""),
        "fit_score": job.get("fit_score", 0),
        "status": "Saved",
        "date_added": datetime.now().strftime("%Y-%m-%d"),
        "date_applied": "",
        "notes": "",
    }
    tracker.append(entry)
    save_tracker(tracker)


def check_backend_status():
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=0.3)
        return response.status_code == 200
    except Exception:
        return False


def stat_card(label, value, colour="#e0e0e0"):
    return (f'<div class="stat-card" style="border-top: 3px solid {colour};">'
            f'<div class="stat-value" style="color:{colour}">{value}</div>'
            f'<div class="stat-label">{label}</div>'
            f'</div>')


def relative_date(date_str):
    """Return a human-readable relative date (e.g. '3d ago')."""
    if not date_str or str(date_str) in ("N/A", ""):
        return "N/A"
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        days = (datetime.now() - d).days
        if days == 0: return "Today"
        if days == 1: return "Yesterday"
        if days < 7: return f"{days}d ago"
        if days < 30: return f"{days // 7}w ago"
        return str(date_str)[:10]
    except Exception:
        return str(date_str)


def _render_tracker_entry(entry, tracker, real_idx, status, status_idx):
    """Render a single tracker entry card with notes and action buttons."""
    entry_id = entry.get("id")
    score = entry.get("fit_score", 0)
    score_col = "#28a745" if score >= 60 else "#ffc107" if score >= 35 else "#6c757d"

    with st.container(border=True):
        meta_parts = []
        if entry.get("salary"):
            meta_parts.append(entry["salary"])
        if entry.get("date_applied"):
            meta_parts.append(f"Applied {relative_date(entry['date_applied'])}")
        elif entry.get("date_added"):
            meta_parts.append(f"Saved {relative_date(entry['date_added'])}")
        meta_str = "  ·  ".join(meta_parts)

        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:2px;">'
            f'<div>'
            f'<div style="font-size:0.88rem;font-weight:600;color:#e0e0e0">{entry.get("title","?")}</div>'
            f'<div style="font-size:0.72rem;color:#666;margin-top:2px">{entry.get("company","")}</div>'
            f'</div>'
            f'<span style="font-size:1.15rem;font-weight:700;color:{score_col};flex-shrink:0;margin-left:10px">{score}</span>'
            f'</div>'
            + (f'<div style="font-size:0.68rem;color:#444;margin-bottom:4px">{meta_str}</div>' if meta_str else ''),
            unsafe_allow_html=True,
        )

        new_notes = st.text_area(
            "Notes", value=entry.get("notes", ""),
            placeholder="Interview date, contact name…",
            key=f"notes_{entry_id}",
            label_visibility="collapsed",
            height=60,
        )
        if new_notes != entry.get("notes", ""):
            tracker[real_idx]["notes"] = new_notes
            save_tracker(tracker)

        btn_cols = st.columns(3)
        with btn_cols[0]:
            if entry.get("url"):
                st.link_button("Open", entry["url"], use_container_width=True)
        with btn_cols[1]:
            if status_idx < len(TRACKER_STATUSES) - 1:
                next_status = TRACKER_STATUSES[status_idx + 1]
                if st.button(f"→ {next_status}", key=f"fwd_{entry_id}", use_container_width=True):
                    tracker[real_idx]["status"] = next_status
                    if next_status == "Applied" and not tracker[real_idx].get("date_applied"):
                        tracker[real_idx]["date_applied"] = datetime.now().strftime("%Y-%m-%d")
                    save_tracker(tracker)
                    st.rerun()
        with btn_cols[2]:
            if status_idx > 0:
                prev_status = TRACKER_STATUSES[status_idx - 1]
                if st.button(f"← {prev_status}", key=f"bck_{entry_id}", use_container_width=True):
                    tracker[real_idx]["status"] = prev_status
                    if prev_status == "Saved":
                        tracker[real_idx]["date_applied"] = ""
                    save_tracker(tracker)
                    st.rerun()

        if st.button("Remove", key=f"rm_{entry_id}", type="tertiary"):
            tracker.pop(real_idx)
            save_tracker(tracker)
            st.rerun()


# ── Navigation ────────────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "Overview"

# Auto-pull from gist on startup (once per session)
if "gist_synced" not in st.session_state:
    st.session_state.gist_synced = True
    try:
        from tools.gist_sync import auto_pull_if_newer
        if auto_pull_if_newer():
            st.rerun()
    except Exception:
        pass

_sidebar_loc = load_config().get("search_params", {}).get("location", "London")
st.sidebar.markdown(
    '<div style="padding:0.5rem 0 0.75rem;">'
    '<div style="font-size:1.2rem;font-weight:700;color:#e0e0e0;letter-spacing:-0.01em">JobRadar</div>'
    f'<div style="font-size:0.65rem;color:#555;letter-spacing:0.08em;text-transform:uppercase;margin-top:3px">{_sidebar_loc} · Job Search</div>'
    '</div>',
    unsafe_allow_html=True,
)

for _p in ["Overview", "Jobs", "Tracker", "Insights", "Sites", "Screenshots", "Settings"]:
    if st.sidebar.button(_p, key=f"nav_{_p}", use_container_width=True,
                         type="primary" if st.session_state.page == _p else "secondary"):
        st.session_state.page = _p
        st.rerun()

_api_ok = check_backend_status()
_dot = "#28a745" if _api_ok else "#dc3545"
_api_label = "Extension API online" if _api_ok else "Extension API offline"
st.sidebar.markdown(
    f'<hr style="border:none;border-top:1px solid #222;margin:8px 0 0;">'
    f'<div style="display:flex;align-items:center;gap:6px;padding:0.5rem 0.75rem 0;'
    f'font-size:0.7rem;color:#555;">'
    f'<span style="width:6px;height:6px;border-radius:50%;background:{_dot};'
    f'flex-shrink:0;display:inline-block"></span>{_api_label}</div>',
    unsafe_allow_html=True,
)

page = st.session_state.page

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

if page == "Overview":
    jobs = load_jobs()
    tracker = load_tracker()

    # ── Top stats (3 cards) ──
    total = len(jobs)
    applied = sum(1 for t in tracker if t.get("status") in ("Applied", "Interview", "Offer", "Rejected"))
    top = max((j.get("fit_score", 0) for j in jobs), default=0)

    c1, c2, c3 = st.columns(3)
    for col, label, val, colour in [
        (c1, "Jobs Found", total, "#e0e0e0"),
        (c2, "Applied", applied, "#4f8ef7"),
        (c3, "Top Score", top, "#28a745" if top >= 60 else "#ffc107" if top >= 35 else "#6c757d"),
    ]:
        col.markdown(stat_card(label, val, colour), unsafe_allow_html=True)

    st.divider()

    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("Top Jobs")
        if not jobs:
            st.caption("No jobs yet — run a search below.")
        else:
            top_jobs = sorted(jobs, key=lambda x: x.get("fit_score", 0), reverse=True)[:5]
            rows = ""
            for job in top_jobs:
                score = job.get("fit_score", 0)
                bc = "#28a745" if score >= 60 else "#ffc107" if score >= 35 else "#6c757d"
                rows += (
                    f'<div style="background:#1e1e2e;border:1px solid #222;border-left:3px solid {bc};'
                    f'border-radius:6px;padding:9px 12px;margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div style="font-size:0.82rem;font-weight:500;color:#d0d0d0;line-height:1.3">{job["title"]}</div>'
                    f'<span class="score-badge" style="background:{bc}22;color:{bc};margin-left:10px;flex-shrink:0">{score}</span>'
                    f'</div>'
                    f'<div style="font-size:0.7rem;color:#555;margin-top:4px">{job["company"]} · {job.get("location","")}</div>'
                    f'</div>'
                )
            st.markdown(rows, unsafe_allow_html=True)

    with right:
        st.subheader("Recent Activity")
        if not tracker:
            st.caption("Nothing tracked yet.")
        else:
            recent = sorted(
                tracker,
                key=lambda x: max(x.get("date_applied") or "", x.get("date_added") or ""),
                reverse=True,
            )[:4]
            rows = ""
            for t in recent:
                colour = STATUS_COLOURS.get(t.get("status", "Saved"), "#888")
                rows += (
                    f'<div style="background:#1e1e2e;border:1px solid #222;border-left:3px solid {colour};'
                    f'border-radius:6px;padding:9px 12px;margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div style="font-size:0.82rem;font-weight:500;color:#d0d0d0">{t.get("title","")}</div>'
                    f'<span style="background:{colour}22;color:{colour};font-size:0.6rem;font-weight:700;'
                    f'padding:2px 7px;border-radius:10px;flex-shrink:0;margin-left:8px">{t.get("status","?")}</span>'
                    f'</div>'
                    f'<div style="font-size:0.7rem;color:#555;margin-top:4px">{t.get("company","")}'
                    f'{(" · " + relative_date(t["date_added"])) if t.get("date_added") else ""}</div>'
                    f'</div>'
                )
            st.markdown(rows, unsafe_allow_html=True)

    st.divider()

    # ── Quick search ──
    _scored_path = TMP_DIR / "scored_jobs.json"
    _last_str = (
        "Last searched: " + datetime.fromtimestamp(_scored_path.stat().st_mtime).strftime("%d %b %Y %H:%M")
        if _scored_path.exists() else "Never searched"
    )
    st.subheader("Search Jobs")
    st.caption(_last_str)
    reed_key = os.getenv("REED_API_KEY", "")
    if not reed_key:
        st.warning(
            "Reed API key not set. "
            "Get a free key at [reed.co.uk/developers/jobseeker](https://www.reed.co.uk/developers/jobseeker) "
            "then add `REED_API_KEY=your-key` to `.env`."
        )
    else:
        _cfg = load_config()
        _api_cfg = _cfg.get("api", {})
        _ov_max = st.slider(
            "Max results", min_value=25, max_value=500, step=25,
            value=int(_api_cfg.get("max_results", 100)),
            key="ov_max_results",
        )
        if st.button("Search Reed.co.uk", type="primary", use_container_width=True):
            if _ov_max != _api_cfg.get("max_results"):
                _cfg["api"] = {**_api_cfg, "max_results": _ov_max}
                save_config(_cfg)
            with st.spinner("Searching Reed for matching jobs…"):
                code, stdout, stderr = run_tool("run_job_scrape.py")
            if code == 0:
                st.success("Done — go to **Jobs** to see results.")
            else:
                st.error("Search failed")
                st.code(stdout + stderr)


# ─────────────────────────────────────────────────────────────────────────────
# JOBS
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Jobs":
    jobs = load_jobs()

    if not jobs:
        st.info("No jobs found yet. Run a search from **Overview** or **Settings**.")
    else:
        # ── Filters: search + score slider ────────────────────────────────
        f1, f2 = st.columns([3, 1])
        with f1:
            search = st.text_input("Search", placeholder="Title or company…", label_visibility="collapsed")
        with f2:
            min_score = st.slider("Min score", 0, 100, 0, step=5)

        _hidden_urls = load_hidden_jobs()
        filtered = [
            j for j in jobs
            if j.get("fit_score", 0) >= min_score
            and (not search or search.lower() in j.get("title", "").lower()
                 or search.lower() in j.get("company", "").lower())
            and j.get("url", "") not in _hidden_urls
        ]
        filtered.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
        _hidden_count = sum(1 for j in jobs if j.get("url", "") in _hidden_urls)
        _hidden_note = f" · {_hidden_count} hidden" if _hidden_count else ""
        st.caption(f"{len(filtered)} of {len(jobs)} jobs{_hidden_note}")

        if filtered:
            _PAGE_SIZE = 50
            if "sel_idx" not in st.session_state:
                st.session_state.sel_idx = 0
            if "jobs_page" not in st.session_state:
                st.session_state.jobs_page = 0

            _max_page = max(0, (len(filtered) - 1) // _PAGE_SIZE)
            if st.session_state.jobs_page > _max_page:
                st.session_state.jobs_page = 0
            _page = st.session_state.jobs_page
            _page_start = _page * _PAGE_SIZE
            _page_end = min(_page_start + _PAGE_SIZE, len(filtered))
            _page_jobs = filtered[_page_start:_page_end]

            tracker = load_tracker()
            _tracked_urls = {t["url"]: t["status"] for t in tracker if t.get("url")}
            _tracked_titles = {(t.get("title", "").lower(), t.get("company", "").lower()): t["status"] for t in tracker}

            list_col, detail_col = st.columns([1, 1.8])

            # ── Job list ──────────────────────────────────────────────────
            with list_col:
                with st.container(height=550):
                    for local_idx, _j in enumerate(_page_jobs):
                        orig_idx = _page_start + local_idx
                        _sc = _j.get("fit_score", 0)
                        is_sel = st.session_state.sel_idx == orig_idx
                        _t = _j["title"]
                        _c = _j.get("company", "")

                        # Build clean two-line label: title [score] / company
                        _t_disp = _t[:40] + ("…" if len(_t) > 40 else "")
                        label = f"{_t_disp}  [{_sc}]"
                        if _c:
                            label += f"\n{_c}"

                        if st.button(label, key=f"j{orig_idx}", use_container_width=True,
                                     type="primary" if is_sel else "secondary"):
                            st.session_state.sel_idx = orig_idx
                            st.rerun()

                # Pagination
                if len(filtered) > _PAGE_SIZE:
                    _pc1, _pc2, _pc3 = st.columns([1, 2, 1])
                    with _pc1:
                        if _page > 0 and st.button("Prev", use_container_width=True):
                            st.session_state.jobs_page -= 1
                            st.session_state.sel_idx = (_page - 1) * _PAGE_SIZE
                            st.rerun()
                    with _pc2:
                        st.caption(f"Page {_page + 1} / {_max_page + 1}")
                    with _pc3:
                        if _page < _max_page and st.button("Next", use_container_width=True):
                            st.session_state.jobs_page += 1
                            st.session_state.sel_idx = (_page + 1) * _PAGE_SIZE
                            st.rerun()

            # ── Detail panel ──────────────────────────────────────────────
            sel_idx = min(st.session_state.sel_idx, len(filtered) - 1)
            job = filtered[sel_idx]

            with detail_col:
                score = job.get("fit_score", 0)
                bc = "#28a745" if score >= 60 else "#ffc107" if score >= 35 else "#6c757d"
                _meta_parts = []
                if job.get("company"):
                    _meta_parts.append(job["company"])
                if job.get("location"):
                    _meta_parts.append(job["location"])
                _rd = relative_date(job.get("date_posted", ""))
                if _rd and _rd != "—":
                    _meta_parts.append(_rd)
                _sal = job.get("salary", "")
                if _sal:
                    _meta_parts.append(_sal)
                if job.get("source"):
                    _meta_parts.append(job["source"])

                st.markdown(
                    f'<div class="detail-header">'
                    f'<div class="dh-title-row">'
                    f'<span class="dh-title">{job["title"]}</span>'
                    f'<span class="score-badge" style="background:{bc}22;color:{bc};font-size:0.85rem">{score}</span>'
                    f'</div>'
                    f'<div class="dh-meta">{" &nbsp;·&nbsp; ".join(_meta_parts)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # ── Action buttons (3 only) ──────────────────────────────
                job_url = job.get("url", "#")
                tracked_entry = next(
                    (t for t in tracker if t.get("url") == job_url or
                     (t.get("title") == job.get("title") and t.get("company") == job.get("company"))),
                    None,
                )
                _entry_status = tracked_entry.get("status") if tracked_entry else None
                already_applied = _entry_status in ("Applied", "Interview", "Offer", "Rejected")

                b1, b2, b3 = st.columns(3)
                with b1:
                    if job_url and job_url != "#":
                        st.link_button("Apply", job_url, type="primary", use_container_width=True)
                with b2:
                    if tracked_entry:
                        if st.button("Untrack", use_container_width=True, key=f"untrack_{sel_idx}"):
                            tracker = [t for t in tracker if t.get("id") != tracked_entry.get("id")]
                            save_tracker(tracker)
                            st.rerun()
                    else:
                        if st.button("Track", use_container_width=True, key=f"track_{sel_idx}"):
                            add_to_tracker(job)
                            st.rerun()
                with b3:
                    if already_applied:
                        if st.button(f"Undo ({_entry_status})", use_container_width=True, key=f"applied_{sel_idx}"):
                            real_idx = next(i for i, t in enumerate(tracker)
                                            if t.get("id") == tracked_entry.get("id"))
                            tracker[real_idx]["status"] = "Saved"
                            tracker[real_idx]["date_applied"] = ""
                            save_tracker(tracker)
                            st.toast("Reverted to Saved.")
                            st.rerun()
                    else:
                        if st.button("Mark Applied", use_container_width=True, key=f"applied_{sel_idx}"):
                            if tracked_entry:
                                real_idx = next(i for i, t in enumerate(tracker)
                                                if t.get("id") == tracked_entry.get("id"))
                                tracker[real_idx]["status"] = "Applied"
                                if not tracker[real_idx].get("date_applied"):
                                    tracker[real_idx]["date_applied"] = datetime.now().strftime("%Y-%m-%d")
                            else:
                                import uuid
                                tracker.append({
                                    "id": str(uuid.uuid4())[:8],
                                    "title": job.get("title", ""),
                                    "company": job.get("company", ""),
                                    "location": job.get("location", ""),
                                    "salary": job.get("salary", ""),
                                    "url": job_url,
                                    "fit_score": job.get("fit_score", 0),
                                    "status": "Applied",
                                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                                    "date_applied": datetime.now().strftime("%Y-%m-%d"),
                                    "notes": "",
                                })
                            save_tracker(tracker)
                            st.toast("Marked as applied!")
                            st.rerun()

                # Hide link (subtle, below actions)
                if st.button("Hide this job", key=f"hide_{sel_idx}", type="tertiary"):
                    _hidden = load_hidden_jobs()
                    _hidden.add(job_url)
                    save_hidden_jobs(_hidden)
                    st.session_state.sel_idx = max(0, sel_idx - 1)
                    st.rerun()

                # ── Detail tabs ───────────────────────────────────────────
                tab_desc, tab_ats, tab_letter, tab_research = st.tabs(
                    ["Description", "ATS Match", "Cover Letter", "Research"]
                )

                with tab_desc:
                    st.write(job.get("description", "No description available."))

                with tab_ats:
                    from tools.ats_matcher import match_job as _ats_match
                    _ats = _ats_match(job.get("description", ""), job.get("title", ""))
                    _mpct = _ats["match_pct"]
                    _mc = "#28a745" if _mpct >= 60 else "#ffc107" if _mpct >= 35 else "#dc3545"
                    st.markdown(
                        f'<span style="font-size:1.6rem;font-weight:700;color:{_mc}">{_mpct}%</span>'
                        f' &nbsp; keyword match ({len(_ats["matched"])} of {_ats["job_skills_count"]} skills)',
                        unsafe_allow_html=True,
                    )
                    if _ats["experience_required"]:
                        st.caption(f"Experience required: {_ats['experience_required']}")
                    _ac, _bc = st.columns(2)
                    with _ac:
                        if _ats["matched"]:
                            st.markdown("**You have:**")
                            st.markdown(" ".join(
                                f'<span style="background:#28a74522;color:#28a745;padding:2px 8px;'
                                f'border-radius:4px;margin:2px;display:inline-block">{s}</span>'
                                for s in _ats["matched"]
                            ), unsafe_allow_html=True)
                    with _bc:
                        if _ats["missing"]:
                            st.markdown("**Missing:**")
                            st.markdown(" ".join(
                                f'<span style="background:#dc354522;color:#dc3545;padding:2px 8px;'
                                f'border-radius:4px;margin:2px;display:inline-block">{s}</span>'
                                for s in _ats["missing"]
                            ), unsafe_allow_html=True)
                    if _ats["missing"]:
                        st.caption("Add any of these missing skills to your profile if you have them.")

                with tab_letter:
                    cl_key = f"cl_{job.get('url', '') or job.get('title', '')}"
                    if st.button("Generate Cover Letter", use_container_width=True, key=f"cl_btn_{sel_idx}"):
                        _databank = load_qa_databank()
                        _reports = load_company_reports()
                        _company_research = _reports.get(job.get("company", ""), "")
                        with st.spinner("Drafting cover letter…"):
                            _cl_result = _generate_cover_letter(
                                {
                                    "title": job.get("title", ""),
                                    "company": job.get("company", ""),
                                    "description": job.get("description", ""),
                                    "location": job.get("location", ""),
                                },
                                _databank,
                                company_research=_company_research,
                            )
                        st.session_state[cl_key] = _cl_result

                    cl_result = st.session_state.get(cl_key)
                    if cl_result:
                        qc = cl_result["quality_checks"]
                        match_pct = int(cl_result["match_quality"] * 100)
                        status_icon = "\u2705" if qc.get("passes") else "\u26a0\ufe0f"
                        st.caption(f"{status_icon} Match: {match_pct}%  \u00b7  Words: {cl_result['word_count']}")
                        if cl_result["unmatched"]:
                            st.warning("No match for: " + ", ".join(cl_result["unmatched"]))
                        if qc.get("ai_phrases"):
                            st.error("AI phrases remain: " + ", ".join(qc["ai_phrases"]))
                        st.text_area(
                            "letter",
                            value=cl_result["cover_letter"],
                            height=340,
                            key=f"cl_text_{sel_idx}",
                            label_visibility="collapsed",
                        )
                        if st.button("Regenerate", key=f"cl_regen_{sel_idx}"):
                            del st.session_state[cl_key]
                            st.rerun()

                with tab_research:
                    company = job.get("company", "")
                    reports = load_company_reports()
                    if company in reports:
                        st.markdown(reports[company])
                    else:
                        st.caption("No research yet for this company.")
                    if st.button("Research Company", use_container_width=True, key=f"research_{sel_idx}"):
                        with st.spinner("Researching…"):
                            report = generate_company_report(company, job.get("title"))
                            save_company_report(company, report)
                        st.rerun()

        else:
            st.info("No jobs match your filters — try lowering the minimum score or clearing the search.")


# ─────────────────────────────────────────────────────────────────────────────
# TRACKER  —  Kanban board
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Tracker":
    tracker = load_tracker()
    counts = {s: sum(1 for t in tracker if t.get("status") == s) for s in TRACKER_STATUSES}

    if not tracker:
        st.info("Nothing tracked yet. Open a job in **Jobs** and click **Track**.")
    else:
        # ── Kanban tabs (one per status) ──
        tab_labels = [f"{s} ({counts[s]})" for s in TRACKER_STATUSES]
        tabs = st.tabs(tab_labels)

        for tab, status in zip(tabs, TRACKER_STATUSES):
            with tab:
                entries = [t for t in tracker if t.get("status") == status]
                entries_sorted = (
                    sorted(entries, key=lambda x: x.get("fit_score", 0), reverse=True)
                    if status == "Saved"
                    else sorted(entries, key=lambda x: (x.get("date_applied") or x.get("date_added") or ""), reverse=True)
                )

                if not entries_sorted:
                    st.markdown(
                        '<div style="text-align:center;padding:32px 0;color:#333;font-size:0.82rem">'
                        'Nothing here yet</div>',
                        unsafe_allow_html=True,
                    )
                    continue

                status_idx = TRACKER_STATUSES.index(status)

                # ── Applied tab: group by date with mass-reject ──
                if status == "Applied":
                    from itertools import groupby
                    keyfn = lambda x: x.get("date_applied") or "Unknown date"
                    for date_label, group_iter in groupby(entries_sorted, key=keyfn):
                        group = list(group_iter)
                        group_ids = [e.get("id") for e in group]

                        hdr_cols = st.columns([3, 1])
                        with hdr_cols[0]:
                            try:
                                d = datetime.strptime(date_label, "%Y-%m-%d")
                                display_date = f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"
                            except (ValueError, AttributeError):
                                display_date = date_label
                            st.markdown(
                                f'<div style="font-size:0.78rem;font-weight:600;color:#888;'
                                f'padding:8px 0 4px 0;letter-spacing:0.04em">'
                                f'{display_date} — {len(group)} application{"s" if len(group) != 1 else ""}</div>',
                                unsafe_allow_html=True,
                            )
                        with hdr_cols[1]:
                            if st.button("Reject All", key=f"mass_reject_{date_label}",
                                         use_container_width=True, type="secondary"):
                                for i, t in enumerate(tracker):
                                    if t.get("id") in group_ids:
                                        tracker[i]["status"] = "Rejected"
                                save_tracker(tracker)
                                st.rerun()

                        for entry in group:
                            entry_id = entry.get("id")
                            real_idx = next(
                                (i for i, t in enumerate(tracker) if t.get("id") == entry_id), None
                            )
                            if real_idx is None:
                                continue
                            _render_tracker_entry(entry, tracker, real_idx, status, status_idx)
                    continue

                # ── All other statuses ──
                for entry in entries_sorted:
                    entry_id = entry.get("id")
                    real_idx = next(
                        (i for i, t in enumerate(tracker) if t.get("id") == entry_id), None
                    )
                    if real_idx is None:
                        continue
                    _render_tracker_entry(entry, tracker, real_idx, status, status_idx)


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHTS  —  Skills Gap + Application Analytics
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Insights":
    st.title("Insights")

    tab_gap, tab_analytics = st.tabs(["Skills Gap", "Analytics"])

    # ── Skills Gap tab ────────────────────────────────────────────────────────
    with tab_gap:
        jobs = load_jobs()
        if not jobs:
            st.info("No jobs scraped yet. Run a search first to see skills gap analysis.")
        else:
            from tools.ats_matcher import skills_gap_analysis, get_user_skills

            gap = skills_gap_analysis(jobs)
            ranked = gap["ranked"]
            coverage = gap["top_20_coverage"]

            # Summary stats
            g1, g2, g3 = st.columns(3)
            _cov_c = "#28a745" if coverage >= 60 else "#ffc107" if coverage >= 35 else "#dc3545"
            g1.markdown(stat_card("Top 20 Coverage", f"{coverage}%", _cov_c), unsafe_allow_html=True)
            g2.markdown(stat_card("Skills Detected", gap["total_skills_found"], "#4f8ef7"), unsafe_allow_html=True)
            g3.markdown(stat_card("Your Skills", gap["user_skills_count"], "#aaa"), unsafe_allow_html=True)

            st.divider()

            if ranked:
                # Top 20 most demanded skills — horizontal bar chart
                st.subheader("Most In-Demand Skills")
                st.caption("Green = you have it. Red = missing from your profile.")

                top = ranked[:20]
                for item in top:
                    pct = item["pct"]
                    col = "#28a745" if item["have"] else "#dc3545"
                    icon = "  " if item["have"] else "  "
                    st.markdown(
                        f'<div style="display:flex;align-items:center;margin:3px 0">'
                        f'<div style="width:160px;font-size:0.85rem">{icon}{item["skill"]}</div>'
                        f'<div style="flex:1;background:#333;border-radius:4px;height:18px;overflow:hidden">'
                        f'<div style="width:{pct}%;background:{col};height:100%;border-radius:4px"></div>'
                        f'</div>'
                        f'<div style="width:50px;text-align:right;font-size:0.8rem;color:#aaa">{pct}%</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.divider()

                # Missing high-demand skills
                missing = [r for r in ranked[:30] if not r["have"]]
                if missing:
                    st.subheader("Skills to Consider Adding")
                    st.caption("These are frequently requested in jobs you're targeting but missing from your profile.")
                    for item in missing[:15]:
                        st.markdown(
                            f'- **{item["skill"]}** — appears in {item["pct"]}% of jobs ({item["count"]} listings)'
                        )
                else:
                    st.success("You cover all top 30 most-demanded skills!")

    # ── Analytics tab ─────────────────────────────────────────────────────────
    with tab_analytics:
        tracker = load_tracker()
        jobs = load_jobs()

        if not tracker:
            st.info("No tracked applications yet. Start tracking jobs to see analytics.")
        else:
            total_tracked = len(tracker)
            counts = {s: sum(1 for t in tracker if t.get("status") == s) for s in TRACKER_STATUSES}

            applied_count = counts.get("Applied", 0) + counts.get("Interview", 0) + counts.get("Offer", 0) + counts.get("Rejected", 0)
            interview_count = counts.get("Interview", 0) + counts.get("Offer", 0)
            offer_count = counts.get("Offer", 0)

            # Conversion funnel
            st.subheader("Application Funnel")
            funnel_data = [
                ("Jobs Found", len(jobs), "#e0e0e0"),
                ("Tracked", total_tracked, "#4f8ef7"),
                ("Applied", applied_count, "#aaa"),
                ("Interview", interview_count, "#ffc107"),
                ("Offer", offer_count, "#28a745"),
            ]

            for label, count, colour in funnel_data:
                max_val = max(len(jobs), 1)
                width = max(int((count / max_val) * 100), 2) if count > 0 else 0
                st.markdown(
                    f'<div style="display:flex;align-items:center;margin:4px 0">'
                    f'<div style="width:100px;font-size:0.85rem">{label}</div>'
                    f'<div style="flex:1;background:#333;border-radius:4px;height:24px;overflow:hidden">'
                    f'<div style="width:{width}%;background:{colour};height:100%;border-radius:4px;'
                    f'display:flex;align-items:center;padding-left:8px;font-size:0.8rem;color:#fff">'
                    f'{count}</div></div></div>',
                    unsafe_allow_html=True,
                )

            st.divider()

            # Key metrics
            st.subheader("Key Metrics")
            m1, m2, m3, m4 = st.columns(4)

            response_rate = round((interview_count / applied_count) * 100) if applied_count > 0 else 0
            rejection_rate = round((counts.get("Rejected", 0) / applied_count) * 100) if applied_count > 0 else 0

            # Avg fit score of interviews vs non-interviews
            interview_scores = [t.get("fit_score", 0) for t in tracker if t.get("status") in ("Interview", "Offer")]
            rejected_scores = [t.get("fit_score", 0) for t in tracker if t.get("status") == "Rejected"]
            avg_int = round(sum(interview_scores) / len(interview_scores)) if interview_scores else "-"
            avg_rej = round(sum(rejected_scores) / len(rejected_scores)) if rejected_scores else "-"

            _rr_c = "#28a745" if response_rate >= 20 else "#ffc107" if response_rate >= 5 else "#dc3545"
            m1.markdown(stat_card("Response Rate", f"{response_rate}%", _rr_c), unsafe_allow_html=True)
            m2.markdown(stat_card("Applied", applied_count, "#aaa"), unsafe_allow_html=True)
            m3.markdown(stat_card("Avg Score (Interview)", avg_int, "#ffc107"), unsafe_allow_html=True)
            m4.markdown(stat_card("Avg Score (Rejected)", avg_rej, "#dc3545"), unsafe_allow_html=True)

            st.divider()

            # Status breakdown
            st.subheader("Status Breakdown")
            for status in TRACKER_STATUSES:
                cnt = counts[status]
                if cnt > 0:
                    pct = round((cnt / total_tracked) * 100)
                    colour = STATUS_COLOURS[status]
                    st.markdown(
                        f'<div style="display:flex;align-items:center;margin:3px 0">'
                        f'<div style="width:100px;font-size:0.85rem">{status}</div>'
                        f'<div style="flex:1;background:#333;border-radius:4px;height:18px;overflow:hidden">'
                        f'<div style="width:{pct}%;background:{colour};height:100%;border-radius:4px"></div>'
                        f'</div>'
                        f'<div style="width:70px;text-align:right;font-size:0.8rem;color:#aaa">{cnt} ({pct}%)</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Fit score insight
            if applied_count > 0:
                st.divider()
                st.subheader("Insight")
                if interview_scores and rejected_scores:
                    if avg_int != "-" and avg_rej != "-" and avg_int > avg_rej:
                        st.markdown(
                            f"Jobs where you got interviews had an average fit score of **{avg_int}** "
                            f"vs **{avg_rej}** for rejections. "
                            f"Focus on jobs scoring **{avg_int - 10}+** for best results."
                        )
                    elif avg_int != "-" and avg_rej != "-":
                        st.markdown(
                            "Fit scores don't seem to predict interview success yet. "
                            "Consider tailoring your CV more closely to job descriptions — "
                            "check the **ATS Keyword Match** on the Jobs page."
                        )
                elif not interview_scores and applied_count >= 5:
                    st.markdown(
                        f"You've applied to **{applied_count}** jobs with no interviews yet. "
                        "Try checking the **ATS Keyword Match** on each job to improve your CV alignment."
                    )


# ─────────────────────────────────────────────────────────────────────────────
# SCREENSHOTS
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Screenshots":
    st.header("Screenshot Job Analyser")
    st.caption("Click the area below, then press **Ctrl+V** to paste a screenshot. Paste multiple to compare.")

    if not check_backend_status():
        st.error("Flask backend not running — start it from **Settings → Extension**.")
    else:
        import streamlit.components.v1 as components
        components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0e1117; color: #e0e0e0; padding: 16px; }
  #paste-zone {
    border: 2px dashed #444; border-radius: 12px; padding: 28px;
    text-align: center; cursor: pointer;
    transition: border-color 0.2s, background 0.2s; margin-bottom: 20px; outline: none;
  }
  #paste-zone:focus, #paste-zone.active { border-color: #4f8ef7; background: #141928; }
  #paste-zone p { color: #888; font-size: 0.95rem; margin-bottom: 6px; }
  #paste-zone kbd {
    background: #2a2d3a; border: 1px solid #555; border-radius: 4px;
    padding: 2px 7px; font-size: 0.85rem; color: #ccc;
  }
  .job-card { background: #1e1e2e; border: 1px solid #333; border-radius: 10px;
               padding: 16px; margin-bottom: 14px; }
  .job-card h3 { font-size: 1rem; margin-bottom: 4px; }
  .badges { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
  .badge { border-radius: 8px; padding: 8px 14px; font-size: 0.8rem; border: 1px solid #333; }
  .badge .label { color: #888; text-transform: uppercase; font-size: 0.65rem;
                  letter-spacing: 0.06em; margin-bottom: 2px; }
  .badge .value { font-weight: 700; font-size: 1.2rem; }
  .score-high { color: #28a745; } .score-med { color: #ffc107; } .score-low { color: #6c757d; }
  details summary { cursor: pointer; font-size: 0.82rem; color: #4f8ef7; margin-top: 6px; user-select: none; }
  details p { font-size: 0.82rem; color: #bbb; margin-top: 8px; white-space: pre-wrap; line-height: 1.5; }
  .spinner { display: none; text-align: center; padding: 16px; font-size: 0.85rem; color: #888; }
  .spinner.visible { display: block; }
  .preview-img { max-width: 100%; max-height: 180px; border-radius: 6px; border: 1px solid #333; margin-bottom: 12px; }
  #clear-btn { background: none; border: 1px solid #555; color: #888; border-radius: 6px;
               padding: 5px 14px; font-size: 0.8rem; cursor: pointer; margin-bottom: 14px; display: none; }
  #clear-btn:hover { border-color: #888; color: #ccc; }
</style>
</head>
<body>
<div id="paste-zone" tabindex="0">
  <p>Click here, then paste a screenshot</p>
  <p><kbd>Ctrl</kbd> + <kbd>V</kbd> &nbsp;·&nbsp; Paste multiple times to compare</p>
</div>
<div class="spinner" id="spinner">Analysing with Claude vision…</div>
<button id="clear-btn" onclick="clearResults()">Clear results</button>
<div id="results"></div>
<script>
const API = 'http://localhost:5000/api/analyze-screenshot';
let jobs = [];
const zone = document.getElementById('paste-zone');
const spinner = document.getElementById('spinner');
const resultsEl = document.getElementById('results');
const clearBtn = document.getElementById('clear-btn');
zone.addEventListener('focus', () => zone.classList.add('active'));
zone.addEventListener('blur', () => zone.classList.remove('active'));
zone.addEventListener('click', () => zone.focus());
document.addEventListener('paste', handlePaste);
function handlePaste(e) {
  const items = [...(e.clipboardData?.items || [])];
  const imageItem = items.find(i => i.type.startsWith('image/'));
  if (!imageItem) return;
  e.preventDefault();
  const blob = imageItem.getAsFile();
  const mediaType = imageItem.type;
  const reader = new FileReader();
  reader.onload = async function(evt) {
    const dataUrl = evt.target.result;
    const base64 = dataUrl.split(',')[1];
    spinner.classList.add('visible');
    zone.style.opacity = '0.5';
    try {
      const resp = await fetch(API, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({image: base64, media_type: mediaType})
      });
      const data = await resp.json();
      if (data.error) { addErrorCard(data.error, dataUrl); }
      else { jobs.unshift({...data.job, preview: dataUrl}); renderResults(); }
    } catch(err) { addErrorCard('Could not reach backend: ' + err.message, dataUrl); }
    finally { spinner.classList.remove('visible'); zone.style.opacity = '1'; }
  };
  reader.readAsDataURL(blob);
}
function scoreClass(s) { return s >= 60 ? 'score-high' : s >= 35 ? 'score-med' : 'score-low'; }
function renderResults() {
  if (!jobs.length) { resultsEl.innerHTML = ''; clearBtn.style.display = 'none'; return; }
  clearBtn.style.display = 'inline-block';
  const sorted = [...jobs].sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0));
  resultsEl.innerHTML = sorted.map(job => {
    const score = job.fit_score ?? 0;
    const req = job.requirements || job.description || '';
    return `<div class="job-card">
      <h3>${esc(job.title || 'Unknown role')} &mdash; ${esc(job.company || 'Unknown company')}</h3>
      <div class="badges">
        <div class="badge"><div class="label">Fit Score</div><div class="value ${scoreClass(score)}">${score}</div></div>
        <div class="badge"><div class="label">Location</div><div class="value" style="font-size:0.95rem">${esc(job.location || '—')}</div></div>
        <div class="badge"><div class="label">Salary</div><div class="value" style="font-size:0.95rem">${esc(job.salary || 'Not listed')}</div></div>
      </div>
      ${req ? `<details><summary>Requirements &amp; description</summary><p>${esc(req)}</p></details>` : ''}
      ${job.preview ? `<details><summary>Screenshot preview</summary><img class="preview-img" src="${job.preview}"></details>` : ''}
    </div>`;
  }).join('');
}
function addErrorCard(msg, preview) {
  jobs.unshift({title: 'Error', company: '', fit_score: 0, error: msg, preview});
  renderResults();
}
function clearResults() { jobs = []; renderResults(); }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
</script>
</body>
</html>
""", height=700, scrolling=True)


# ─────────────────────────────────────────────────────────────────────────────
# SITES
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Sites":
    from datetime import date as _date

    st.title("Watch Sites")
    st.caption("Job boards and company career pages to check manually.")

    config = load_config()
    watch_sites = config.get("watch_sites", [])

    def save_sites(sites):
        config["watch_sites"] = sites
        save_config(config)

    def days_since(date_str):
        if not date_str:
            return None
        try:
            return (_date.today() - _date.fromisoformat(str(date_str))).days
        except ValueError:
            return None

    if not watch_sites:
        st.info("No sites added yet — add one below.")
    else:
        # Sort: never-checked first, then oldest-checked first
        watch_sites.sort(key=lambda s: s.get("last_checked") or "")
        for i, site in enumerate(watch_sites):
            days = days_since(site.get("last_checked"))
            if days is None:
                dot_col, status_text = "#555", "Never checked"
            elif days == 0:
                dot_col, status_text = "#28a745", "Checked today"
            elif days <= 7:
                dot_col, status_text = "#28a745", f"Checked {days}d ago"
            elif days <= 14:
                dot_col, status_text = "#ffc107", f"{days}d ago"
            else:
                dot_col, status_text = "#dc3545", f"{days}d ago — overdue"

            info_col, btn_col = st.columns([4, 1.4])
            with info_col:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:8px 0;border-bottom:1px solid #1a1a28;">'
                    f'<span style="width:7px;height:7px;border-radius:50%;'
                    f'background:{dot_col};flex-shrink:0;display:inline-block"></span>'
                    f'<div><a href="{site.get("url","#")}" target="_blank" '
                    f'style="color:#e0e0e0;font-size:0.85rem;font-weight:500;text-decoration:none;">'
                    f'{site.get("name","Unnamed")}</a>'
                    f'<div style="font-size:0.68rem;color:{dot_col};margin-top:2px">{status_text}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with btn_col:
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✓", key=f"s_chk_{i}", use_container_width=True, help="Mark as checked"):
                        watch_sites[i]["last_checked"] = _date.today().isoformat()
                        save_sites(watch_sites)
                        st.rerun()
                with bc2:
                    if st.button("✕", key=f"s_rm_{i}", use_container_width=True, help="Remove site"):
                        watch_sites.pop(i)
                        save_sites(watch_sites)
                        st.rerun()

    st.divider()
    st.markdown("**Add a site**")
    a1, a2, a3 = st.columns([2, 3, 1])
    with a1:
        new_name = st.text_input("Name", placeholder="CV Library", label_visibility="collapsed", key="site_name")
    with a2:
        new_url = st.text_input("URL", placeholder="https://…", label_visibility="collapsed", key="site_url")
    with a3:
        if st.button("Add", type="primary", use_container_width=True, key="add_site"):
            if new_name and new_url:
                watch_sites.append({
                    "name": new_name.strip(), "url": new_url.strip(),
                    "added": _date.today().isoformat(), "last_checked": None,
                })
                save_sites(watch_sites)
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS  —  tabbed: Profile | Search | Extension
# ─────────────────────────────────────────────────────────────────────────────

elif page == "Settings":
    st.title("Settings")
    st.caption("All changes are saved automatically.")

    tab_profile, tab_search, tab_email, tab_ext, tab_data = st.tabs(
        ["Profile", "Search", "Email Alerts", "Extension", "Data"]
    )

    # ── Profile tab ──────────────────────────────────────────────────────────
    with tab_profile:
        profile = load_profile()
        databank = load_qa_databank()
        user = profile.get("profile", {})
        skills = user.get("skills", {})
        locations = user.get("locations", {})
        salary = user.get("salary", {})
        personal = databank.get("personal_info", {})
        work_auth = databank.get("work_authorization", {})

        # ── About You (Personal Info + Work Authorization) ────────────────
        st.subheader("About You")
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

        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            new_uk = st.selectbox("Eligible to work in UK?", ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("eligible_to_work_uk", "")), key="wa_uk")
        with wc2:
            new_sponsor = st.selectbox("Require sponsorship?", ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("require_sponsorship", "")), key="wa_sp")
        with wc3:
            new_notice = st.text_input("Notice Period", value=work_auth.get("notice_period", ""), key="wa_np")

        new_personal = {
            "full_name": new_name, "email": new_email, "phone": new_phone,
            "city": new_city, "postcode": new_postcode, "country": new_country,
            "linkedin": new_linkedin,
            "github": personal.get("github", ""), "portfolio": personal.get("portfolio", ""),
        }
        if new_personal != personal:
            databank["personal_info"] = new_personal
            save_qa_databank(databank)

        new_work_auth = {
            "eligible_to_work_uk": new_uk, "require_sponsorship": new_sponsor,
            "notice_period": new_notice, "availability": work_auth.get("availability", ""),
        }
        if new_work_auth != work_auth:
            databank["work_authorization"] = new_work_auth
            save_qa_databank(databank)

        st.divider()

        # ── Q&A Bank ─────────────────────────────────────────────────────
        st.subheader("Q&A Bank")
        st.caption("Saved answers used by the Chrome extension")
        questions = databank.get("questions", {})
        updated_questions = {}
        for question, answer in questions.items():
            updated_questions[question] = st.text_area(
                question, value=answer or "", height=70, key=f"qa_{hash(question)}")
        if updated_questions != questions:
            databank["questions"] = updated_questions
            save_qa_databank(databank)

        nc1, nc2, nc3 = st.columns([2, 3, 1])
        with nc1:
            new_q = st.text_input("Question", key="new_q", label_visibility="collapsed", placeholder="Question…")
        with nc2:
            new_a = st.text_input("Answer", key="new_a", label_visibility="collapsed", placeholder="Your answer…")
        with nc3:
            if st.button("Add", key="add_qa", use_container_width=True):
                if new_q:
                    databank["questions"][new_q] = new_a
                    save_qa_databank(databank)
                    st.rerun()

        st.divider()

        # ── Scoring Profile ──────────────────────────────────────────────
        st.subheader("Scoring Profile")
        c1, c2 = st.columns(2)
        with c1:
            new_req = st.text_area("Required Skills (one per line)",
                value="\n".join(skills.get("required", [])), height=100, key="s_req")
            new_locs = st.text_area("Preferred Locations (one per line)",
                value="\n".join(locations.get("preferred", [])), height=80, key="s_locs")
        with c2:
            new_pref = st.text_area("Preferred Skills (one per line)",
                value="\n".join(skills.get("preferred", [])), height=100, key="s_pref")
            sc1, sc2 = st.columns(2)
            with sc1:
                new_min_sal = st.number_input("Min Salary", value=salary.get("minimum", 20000), step=1000, key="s_min")
            with sc2:
                new_pref_sal = st.number_input("Pref Salary", value=salary.get("preferred", 30000), step=1000, key="s_pref_sal")

        new_deal = st.text_area("Dealbreakers (one per line)",
            value="\n".join(user.get("dealbreakers", [])), height=70, key="deal")

        new_profile = {
            "profile": {
                "name": user.get("name", ""),
                "skills": {
                    "required": [s.strip() for s in new_req.split("\n") if s.strip()],
                    "preferred": [s.strip() for s in new_pref.split("\n") if s.strip()],
                },
                "locations": {
                    "preferred": [s.strip() for s in new_locs.split("\n") if s.strip()],
                    "acceptable": locations.get("acceptable", []),
                },
                "salary": {"minimum": int(new_min_sal), "preferred": int(new_pref_sal)},
                "dealbreakers": [s.strip() for s in new_deal.split("\n") if s.strip()],
            },
            "scoring": profile.get("scoring", {}),
        }
        if new_profile != profile:
            save_profile(new_profile)

    # ── Search tab ───────────────────────────────────────────────────────────
    with tab_search:
        config = load_config()
        search_params = config.get("search_params", {})

        c1, c2 = st.columns(2)
        with c1:
            new_titles = st.text_area(
                "Job Titles to Search (one per line)",
                value="\n".join(search_params.get("titles", [])),
                height=180, key="q_titles",
            )
        with c2:
            new_search_loc = st.text_input("Location", value=search_params.get("location", "London"), key="q_loc")
            new_days = st.selectbox(
                "Posted Within",
                options=[1, 3, 7, 14, 30],
                index=[1, 3, 7, 14, 30].index(search_params.get("posted_within_days", 7))
                      if search_params.get("posted_within_days", 7) in [1, 3, 7, 14, 30] else 2,
                format_func=lambda x: f"{x} day{'s' if x > 1 else ''}",
                key="q_days",
            )

        api_cfg = config.get("api", {})
        new_max_results = st.slider(
            "Max results per search title",
            min_value=25, max_value=500, step=25,
            value=int(api_cfg.get("max_results", 100)),
            key="q_max_results",
            help="Reed returns up to 100 per API call; higher values page through multiple requests.",
        )

        new_config = {
            "search_params": {
                "titles": [t.strip() for t in new_titles.split("\n") if t.strip()],
                "keywords": search_params.get("keywords", []),
                "location": new_search_loc,
                "remote": search_params.get("remote", False),
                "experience_level": search_params.get("experience_level", ""),
                "posted_within_days": new_days,
            },
            "api": {**api_cfg, "max_results": new_max_results},
            "salary": config.get("salary", {"minimum": 20000}),
            "sites": config.get("sites", ["reed"]),
            "watch_sites": config.get("watch_sites", []),
        }
        if new_config != config:
            save_config(new_config)

        st.divider()
        reed_key = os.getenv("REED_API_KEY", "")
        if not reed_key:
            st.warning("Reed API key not set. Add `REED_API_KEY=your-key` to `.env`.")
        if st.button("Search Reed.co.uk", type="primary", disabled=not reed_key):
            with st.spinner("Searching…"):
                code, stdout, stderr = run_tool("run_job_scrape.py")
            if code == 0:
                st.success("Done — results in **Jobs**")
            else:
                st.error("Search failed")
            with st.expander("Output", expanded=code != 0):
                st.code(stdout + stderr)

        if st.button("Re-score existing jobs"):
            with st.spinner("Scoring…"):
                code, stdout, stderr = run_tool("score_job_fit.py")
            if code == 0:
                st.success("Done")
            else:
                st.error("Failed")
                st.code(stdout + stderr)

    # ── Email Alerts tab ─────────────────────────────────────────────────────
    with tab_email:
        st.subheader("Email Job Alert Parsing")
        st.caption(
            "Connect your email to automatically parse job listings "
            "from recruiter alert emails (Michael Page, Reed, Indeed, etc.)"
        )

        _email_addr = os.getenv("EMAIL_ADDRESS", "")
        _email_pass = os.getenv("EMAIL_APP_PASSWORD", "")

        if _email_addr and _email_pass:
            st.success(f"Email configured: {_email_addr}")

            if st.button("Test Connection", key="email_test"):
                with st.spinner("Connecting..."):
                    try:
                        sys.path.insert(0, str(TOOLS_DIR))
                        from tools.fetch_email_jobs import connect_imap
                        conn = connect_imap()
                        conn.logout()
                        st.success("Connection successful!")
                    except Exception as _e:
                        st.error(f"Connection failed: {_e}")
        else:
            st.warning("Email not configured.")
            st.markdown("""
**Setup steps for Yahoo Mail:**
1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Enable **2-Step Verification** if not already on
3. Generate an **App Password** (select "Other App")
4. Add to your `.env` file:
```
EMAIL_ADDRESS=your.email@yahoo.co.uk
EMAIL_APP_PASSWORD=your-app-password
EMAIL_IMAP_HOST=imap.mail.yahoo.com
```

**For Gmail:** Use `EMAIL_IMAP_HOST=imap.gmail.com` and a Google App Password.

**For Outlook:** Use `EMAIL_IMAP_HOST=outlook.office365.com`.
""")

        st.divider()

        # Recruiter senders management
        _econfig = load_config()
        _email_cfg = _econfig.get("email_alerts", {})
        _senders = _email_cfg.get("senders", [])

        st.subheader("Recruiter Senders")
        st.caption("Emails from these senders will be parsed for job listings.")

        if _senders:
            for _i, _s in enumerate(_senders):
                _ec1, _ec2, _ec3, _ec4 = st.columns([2, 3, 2, 1])
                with _ec1:
                    st.text(_s.get("name", ""))
                with _ec2:
                    st.text(_s.get("email_from", ""))
                with _ec3:
                    st.text(_s.get("parser", "generic"))
                with _ec4:
                    if st.button("X", key=f"rm_sender_{_i}",
                                 help="Remove this sender"):
                        _senders.pop(_i)
                        _email_cfg["senders"] = _senders
                        _econfig["email_alerts"] = _email_cfg
                        save_config(_econfig)
                        st.rerun()
        else:
            st.info("No senders configured. Load defaults or add manually.")

        # Load defaults button
        if st.button("Load Default Senders", key="load_default_senders"):
            from tools.fetch_email_jobs import DEFAULT_SENDERS
            _email_cfg["senders"] = DEFAULT_SENDERS.copy()
            _email_cfg["enabled"] = True
            _econfig["email_alerts"] = _email_cfg
            if "email" not in _econfig.get("sites", []):
                _econfig.setdefault("sites", []).append("email")
            save_config(_econfig)
            st.rerun()

        st.divider()

        # Add new sender
        st.markdown("**Add a sender**")
        _ac1, _ac2, _ac3 = st.columns([2, 3, 2])
        with _ac1:
            _new_name = st.text_input("Name", placeholder="Michael Page", key="new_sender_name")
        with _ac2:
            _new_from = st.text_input("From address", placeholder="noreply@example.com", key="new_sender_from")
        with _ac3:
            _new_parser = st.selectbox(
                "Parser",
                ["michael_page", "reed", "indeed", "totaljobs", "cv_library", "generic"],
                key="new_sender_parser",
            )
        if st.button("Add Sender", key="add_sender_btn"):
            if _new_name and _new_from:
                _senders.append({"name": _new_name, "email_from": _new_from, "parser": _new_parser})
                _email_cfg["senders"] = _senders
                _email_cfg["enabled"] = True
                _econfig["email_alerts"] = _email_cfg
                if "email" not in _econfig.get("sites", []):
                    _econfig.setdefault("sites", []).append("email")
                save_config(_econfig)
                st.rerun()
            else:
                st.warning("Name and email address are required.")

        st.divider()

        # Manual fetch
        if _email_addr and _email_pass and _senders:
            _days = st.slider("Check emails from last N days", 1, 30, 7, key="email_days_back")
            if st.button("Fetch Email Jobs Now", type="primary", use_container_width=True,
                         key="fetch_email_now"):
                with st.spinner("Connecting to email and parsing job alerts..."):
                    try:
                        sys.path.insert(0, str(TOOLS_DIR))
                        from tools.fetch_email_jobs import scrape as email_scrape
                        _ejobs = email_scrape()
                        if _ejobs:
                            # Score and merge with existing jobs
                            try:
                                from tools.score_job_fit import calculate_fit_score
                                _profile = load_profile()
                                for _j in _ejobs:
                                    _j["fit_score"] = calculate_fit_score(_j, _profile)
                            except Exception:
                                pass

                            # Merge with existing scored jobs
                            _existing = load_jobs()
                            _existing_urls = {j.get("url", "") for j in _existing}
                            _new_count = 0
                            for _j in _ejobs:
                                if _j.get("url", "") not in _existing_urls:
                                    _existing.append(_j)
                                    _new_count += 1

                            if _new_count > 0:
                                TMP_DIR.mkdir(exist_ok=True)
                                with open(TMP_DIR / "scored_jobs.json", "w", encoding="utf-8") as _f:
                                    json.dump(_existing, _f, indent=2, ensure_ascii=False)
                                _gist_auto_push()

                            st.success(f"Found {len(_ejobs)} jobs from email, {_new_count} new.")
                        else:
                            st.info("No jobs found in recent recruiter emails.")
                    except Exception as _e:
                        st.error(f"Email fetch failed: {_e}")

    # ── Extension tab ────────────────────────────────────────────────────────
    with tab_ext:
        backend_running = check_backend_status()

        ec1, ec2 = st.columns([2, 1])
        with ec1:
            if backend_running:
                st.success("Backend running on localhost:5000")
            else:
                st.warning("Backend not running")
        with ec2:
            if not backend_running:
                if st.button("Start Backend", type="primary", use_container_width=True):
                    subprocess.Popen(
                        [sys.executable, str(TOOLS_DIR / "answer_questions_api.py")],
                        cwd=str(TOOLS_DIR),
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
                    )
                    st.info("Starting… refresh in a few seconds")
                    time.sleep(2)
                    st.rerun()

        st.markdown("""
**Setup:** `chrome://extensions` → Developer mode → Load unpacked → select `chrome-extension/`

**Usage:** Open a job application → Click extension → Copy Page → Parse & Get Answers → fill form
        """)

        databank = load_qa_databank()
        questions_count = len([q for q, a in databank.get("questions", {}).items() if a])
        st.caption(f"Q&A Bank: {questions_count} saved answers")

        if backend_running:
            with st.expander("Test API", expanded=False):
                test_text = st.text_area("Paste application text:", height=80, placeholder="Paste text to test…")
                if st.button("Test"):
                    if test_text:
                        try:
                            r = requests.post(
                                "http://localhost:5000/api/parse-and-answer",
                                json={"pageText": test_text, "context": {}}, timeout=30,
                            )
                            if r.ok:
                                data = r.json()
                                st.success(f"Found {data.get('total_questions', 0)} questions")
                                for item in data.get("answers", []):
                                    st.markdown(f"**Q:** {item['question']}")
                                    st.markdown(f"**A:** {item['answer']}")
                                    st.caption(f"Source: {item['source']}")
                                    st.markdown("---")
                        except Exception as e:
                            st.error(str(e))

    # ── Data tab ──────────────────────────────────────────────────────────────
    with tab_data:
        # ── Cloud Sync ──
        st.subheader("Cloud Sync")
        st.caption("Sync your profile, jobs, and settings across machines via a private GitHub Gist.")

        try:
            from tools.gist_sync import get_sync_status, push as gist_push, pull as gist_pull

            _sync = get_sync_status()

            if not _sync["configured"]:
                st.warning(
                    "GitHub token not configured. Add `GITHUB_GIST_TOKEN=ghp_xxx` to your `.env` file.\n\n"
                    "Create a token at [github.com/settings/tokens](https://github.com/settings/tokens) "
                    "with **gist** scope only."
                )
            else:
                if _sync["gist_id"]:
                    _sc1, _sc2 = st.columns(2)
                    with _sc1:
                        st.markdown(f"**Gist:** `{_sync['gist_id'][:12]}...`")
                    with _sc2:
                        if _sync["remote_meta"]:
                            _rm = _sync["remote_meta"]
                            _ts = _rm.get("synced_at", "")[:19].replace("T", " ")
                            _machine = _rm.get("machine", "unknown")
                            st.markdown(f"**Last sync:** {_ts} UTC from *{_machine}*")
                        else:
                            st.markdown("**Last sync:** Unknown")
                    st.caption(f"Syncing {len(_sync['local_files'])} files. Changes auto-push after every save.")
                else:
                    st.info("No gist created yet. Click **Push** to create one.")

                _pc1, _pc2 = st.columns(2)
                with _pc1:
                    if st.button("Push to Gist", type="primary", use_container_width=True,
                                 help="Upload local data to GitHub Gist (overwrites remote)"):
                        with st.spinner("Pushing..."):
                            _pr = gist_push()
                        if _pr["success"]:
                            st.success(f"Pushed {len(_pr['files_pushed'])} files.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Push failed: {_pr['error']}")
                with _pc2:
                    if st.button("Pull from Gist", use_container_width=True,
                                 help="Download data from GitHub Gist (overwrites local)"):
                        with st.spinner("Pulling..."):
                            _pr = gist_pull()
                        if _pr["success"]:
                            st.success(f"Pulled {len(_pr['files_pulled'])} files.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Pull failed: {_pr['error']}")
        except ImportError:
            st.error("gist_sync module not found. Check tools/gist_sync.py exists.")
        except Exception as _e:
            st.error(f"Sync error: {_e}")

        st.divider()

        st.subheader("Export")
        st.caption("Download a backup of all your jobs, profile, and preferences.")

        from tools.backup_restore import export_bytes

        backup_data = export_bytes()
        timestamp = datetime.now().strftime("%Y-%m-%d")
        st.download_button(
            "Download Backup",
            data=backup_data,
            file_name=f"jobradar_backup_{timestamp}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

        st.divider()
        st.subheader("Import")
        st.caption("Restore from a previous backup. This will overwrite current data.")

        uploaded = st.file_uploader(
            "Upload backup file",
            type=["zip"],
            key="backup_upload",
        )
        if uploaded:
            if st.button("Restore Backup", type="primary", use_container_width=True):
                from tools.backup_restore import import_bytes

                ok, result = import_bytes(uploaded.getvalue())
                if ok:
                    st.success(f"Restored {len(result)} files. Refreshing...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Import failed: {result}")
