# JobRadar — Session Handoff

> Last updated: 2026-03-15

---

## What Was Built (Complete)

- **Chrome extension gist sync** — Push/pull of `qa_databank` + settings to GitHub Gist. Auto-syncs on every save. Code is in `chrome-extension/popup/settings.js` (functions: `loadGistSettings`, `saveGistSettings`, `gistPush`, `gistPull`, `gistAutoSyncPush`).

- **Phone Inbox feature** — Share job URLs from iPhone → GitHub Gist → Streamlit processes them. Components:
  - `tools/gist_sync.py` — added `read_gist_file()` and `update_gist_file()`
  - `tools/process_pending_jobs.py` — NEW. Reads `pending_job.txt` from gist, scrapes each URL, scores, dedupes, merges into `scored_jobs.json`
  - `app.py` — Phone Inbox section on Overview page (lists pending URLs, Process button)
  - `app.py` — Apple Shortcut setup instructions in Settings page

---

## In Progress (iPhone Shortcut)

User is building an Apple Shortcut to share job URLs from iPhone to JobRadar. They got a 422 error because the nested JSON body wasn't built correctly.

**The shortcut sends a PATCH to GitHub Gist API:**
```
URL: https://api.github.com/gists/{GIST_ID}
Method: PATCH
Headers:
  Authorization: Bearer {GITHUB_GIST_TOKEN}
  Content-Type: application/json
Body (JSON, nested):
  files (Dictionary)
    pending_job.txt (Dictionary)
      content (Text) = Shortcut Input
```

**Key point:** `files` and `pending_job.txt` must be Dictionary type, `content` must be Text type. This is the most common mistake when building in iOS Shortcuts.

**After shortcut works**, user needs to:
1. Put their Gist ID in `.env` as `GITHUB_GIST_ID=...`
2. Open Streamlit app → Settings → push to cloud (creates gist if not exists)
3. Test: share a real job URL from iPhone → check Phone Inbox on Overview page → click "Process All Jobs"

---

## Known Issues / Bugs

- `.env` has `GITHUB_GIST_ID=` empty — needs to be filled after first gist push from Streamlit
- `process_pending_jobs.py` reads one URL at a time (single-file overwrite approach). If user shares two jobs quickly, first may be overwritten. Not a priority to fix.
- `scrape_adzuna.py`, `scrape_careerjet.py`, `scrape_jooble.py` are untracked new files — not yet integrated anywhere

---

## Pending Tasks (Priority Order)

1. **Test iPhone → Gist → Streamlit flow end-to-end** (user is unblocked on shortcut steps)
2. **Integrate new scrapers** — `scrape_adzuna.py`, `scrape_careerjet.py`, `scrape_jooble.py` exist but aren't wired into `run_job_scrape.py`
3. **Validate jobs cron** — `tools/validate_jobs.py` exists but needs to be run manually or scheduled
4. **JS migration** — CLAUDE.md mandates all new features in JavaScript. Streamlit app is tech debt. Long-term: port to Node.js/Express + React frontend

---

## Architecture Reminder

- **Tech direction: JavaScript first.** All new features must be Node.js/JS. Existing Python is frozen (maintain only, no new features). See `CLAUDE.md`.
- Flask backend runs on port 5000. Streamlit is the current UI.
- GitHub Gist is the sync layer between Chrome extension, Streamlit app, and iPhone.
- `.env` holds all credentials — never commit secrets.
- `tools/` = deterministic Python scripts. `workflows/` = SOP markdown files.
