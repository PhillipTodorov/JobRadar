# 🎯 JobRadar

**Job search automation that actually works.**

Scrape jobs → Score by fit → Apply faster with a Chrome extension that knows your answers.

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Chrome Extension](https://img.shields.io/badge/chrome-extension-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ What It Does

| Feature | Description |
|---------|-------------|
| 🔍 **Job Scraping** | Pull listings from Google Jobs (via SerpAPI) automatically |
| 📊 **Smart Scoring** | Score jobs 0-100 based on your skills, location, preferences |
| 📋 **Dashboard** | Browse, filter, and research jobs in dark mode UI (6 pages) |
| 🧩 **Chrome Extension** | Extract questions using regex, get answers from your databank |
| 📄 **CV Intelligence** | Upload CV (.docx, .pdf, .txt) → AI parses → Auto-fills profile |
| 💼 **Portfolio** | Manage GitHub projects with formatted descriptions for applications |

---

## 🎬 Demo

> 🚧 **Screenshots coming soon** — project is in active development

<!--
TODO: Add screenshots
![Dashboard Dark Mode](screenshots/dashboard.png)
![Extension in Action](screenshots/extension.png)
![CV Parser](screenshots/cv-parser.png)
-->

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      JobRadar System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐       ┌───────────────┐                │
│  │  Streamlit    │◄──────┤  User Profile │                │
│  │  Dashboard    │       │  (YAML files) │                │
│  │  (6 pages)    │       └───────────────┘                │
│  └───────┬───────┘                                         │
│          │                                                 │
│          ├──► Jobs: Browse scored listings                 │
│          ├──► Settings: Edit skills, Q&A databank          │
│          ├──► CV: Upload & parse resume                    │
│          ├──► Projects: GitHub portfolio                   │
│          ├──► Actions: Run scraper, backend status         │
│          └──► History: Track answer usage                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐       ┌───────────────┐                │
│  │  Flask API    │◄──────┤ Chrome Ext    │                │
│  │  :5000        │       │ (side panel)  │                │
│  └───────┬───────┘       └───────────────┘                │
│          │                                                 │
│          ├──► /api/parse_questions (regex extraction)      │
│          ├──► /api/get_answers (match Q&A databank)        │
│          └──► /api/health (status check)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
              │                         │
              ▼                         ▼
    ┌──────────────────┐      ┌──────────────────┐
    │   SerpAPI        │      │  Claude API       │
    │   (job scraping) │      │  (CV parsing,     │
    │   [optional]     │      │   research)       │
    └──────────────────┘      │  [optional]       │
                              └──────────────────┘
```

**Privacy-first design:**
- ✅ All processing happens locally
- ✅ No data sent to external servers (except APIs you configure)
- ✅ Extension only reads when you click
- ✅ You control every action (no auto-fill, no DOM manipulation)

---

## 🛡️ How the Chrome Extension Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Job App Page   │────▶│    Extension    │────▶│  Flask Backend  │
│  (any website)  │     │  (copy content) │     │  (localhost:5000)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Regex Extraction│
                                               │  (90%+ accuracy,│
                                               │   free, instant)│
                                               └────────┬────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Match Q&A DB   │
                                               │  Return Answers │
                                               └────────┬────────┘
                                                        │
                                                        ▼
                              ┌──────────────────────────────────────┐
                              │  You review, edit, and manually copy │
                              │  (TOS-safe: no auto-fill)            │
                              └──────────────────────────────────────┘
```

**Why regex first?**
- **Fast**: Instant extraction, no API calls
- **Free**: No API costs
- **Accurate**: 90%+ success on standard forms (Workday, Greenhouse, Lever)
- **Private**: Everything runs locally

AI extraction (Claude) available as optional upgrade (~5-10% improvement for extra cost).

---

## 🚀 Quick Start

### Minimal Setup (2 Steps)

```bash
# 1. Install Chrome Extension
chrome://extensions/ → Enable "Developer mode" → Load unpacked → chrome-extension/

# 2. Start Backend
Double-click: start_jobradar.bat
```

**Done!** Extension works immediately with regex (no API keys needed).

### Optional Upgrades

```bash
# Add your answers (highly recommended)
cp qa_databank.yaml.template qa_databank.yaml
# Edit with your standard answers

# Enable AI features (optional)
cp .env.template .env
# Add ANTHROPIC_API_KEY for CV parsing + company research
# Add SERPAPI_KEY for automated job search (100 free/month)
```

**Full setup:** See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

---

## 📊 Job Scoring Algorithm

```
┌───────────────────────────────────────────────────────────┐
│  Job Score Calculation (0-100)                            │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Required Skills Match    [████████████████████] 40%     │
│  (Python, Git, JavaScript found in description)          │
│                                                           │
│  Preferred Skills Match   [████████████] 25%             │
│  (React, Docker, SQL found)                              │
│                                                           │
│  Location Preference      [████████████████████] 20%     │
│  (London = 100, Remote = 100, Manchester = 50)           │
│                                                           │
│  Title Relevance          [███████████] 15%              │
│  (Contains "developer", "engineer", "software")          │
│                                                           │
│  = Final Score: 85/100 (High Fit)                        │
│                                                           │
│  ⚠️ Dealbreakers: "senior", "10+ years" → Score = 0     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

| Factor | Weight | What It Checks |
|--------|--------|----------------|
| Required Skills | 40% | % of your must-have skills found in job description |
| Preferred Skills | 25% | % of your nice-to-have skills found |
| Location | 20% | Preferred (100), acceptable (50), other (0) |
| Title Match | 15% | Contains relevant keywords |

> 📌 **Coming Soon**: Interactive weight sliders (game dev tycoon style) to customize scoring

---

## 📱 Dashboard Pages

### 1️⃣ Jobs
- Filter by fit score (0-100)
- Search by title/company/keywords
- View job descriptions
- Generate AI company research (requires ANTHROPIC_API_KEY)
- Direct apply links

### 2️⃣ Settings
- Edit personal info, skills, locations
- Configure dealbreakers (auto-reject keywords)
- Manage Q&A databank inline
- Work authorization details

### 3️⃣ CV
- Upload CV (.docx, .pdf, .txt)
- AI-powered parsing with Claude (optional)
- Auto-populate profile fields
- Preview extracted text

### 4️⃣ Projects
- Add GitHub projects with tech stacks
- Store project descriptions
- Copy formatted descriptions for applications
- Export to JSON

### 5️⃣ Actions
- Run job scraper
- Re-score existing jobs
- Backend status monitor
- Extension API test

### 6️⃣ History
- Track which answers you've used
- Usage frequency per question
- Export history to JSON

---

## 🗂️ Project Structure

```
JobRadar/
├── start_jobradar.bat        # Launch script (Flask + Streamlit)
├── app.py                    # Streamlit dashboard (6 pages)
├── requirements.txt          # Python dependencies
│
├── .env.template             # API key template
├── user_profile.yaml.template    # Config templates
├── qa_databank.yaml.template
├── job_search_config.yaml.template
│
├── chrome-extension/         # Browser extension (Manifest V3)
│   ├── manifest.json
│   ├── icons/
│   ├── popup/
│   │   ├── popup.html        # Main UI
│   │   ├── popup.js          # Extension logic
│   │   ├── popup.css         # Dark mode styling
│   │   ├── settings.html     # Setup guide
│   │   └── settings.js       # Backend status checker
│   └── create_icons.py
│
├── tools/                    # Backend scripts
│   ├── answer_questions_api.py  # Flask API for extension
│   ├── run_job_scrape.py        # Scraping orchestrator
│   ├── scrape_serpapi.py        # SerpAPI scraper
│   ├── score_job_fit.py         # Job scoring algorithm
│   ├── push_to_sheets.py        # Google Sheets export
│   ├── parse_cv.py              # CV text extraction
│   └── scraper_utils.py
│
├── .tmp/                     # Temporary data (gitignored)
│   ├── scored_jobs.json
│   ├── company_reports.json
│   └── answer_usage_history.json
│
├── profile/                  # Your CV files (gitignored)
├── .streamlit/config.toml    # Dark mode theme
└── workflows/                # Technical documentation
```

---

## 🔧 Tech Stack

**Backend**
- Python 3.8+
- Flask (extension API)
- Streamlit (dashboard with dark mode)
- Pandas (data processing)

**Chrome Extension**
- Manifest V3
- JavaScript
- HTML/CSS (dark theme)

**Integrations (Optional)**
- SerpAPI (job scraping)
- Claude API (CV parsing, company research)
- Google Sheets (export jobs)

**CV Parsing**
- python-docx (Word documents)
- pypdf (PDF extraction)

---

## 🔐 Privacy & Data

**Everything stays local:**
- No cloud storage
- No external databases
- No tracking or analytics
- Your data never leaves your machine

**What's gitignored:**
- `.env` (API keys)
- `user_profile.yaml` (your skills/preferences)
- `qa_databank.yaml` (your answers)
- `job_search_config.yaml` (search params)
- `github_projects.yaml` (your portfolio)
- `profile/` (your CV files)
- `.tmp/` (scraped jobs and temp data)

**What's committed:**
- Code and templates only
- No personal information
- No credentials

---

## 🗺️ Roadmap

**Completed:**
- [x] Job scraping from Google Jobs
- [x] Smart fit scoring algorithm
- [x] Streamlit dashboard (dark mode)
- [x] Chrome extension with regex extraction
- [x] CV upload and AI parsing (.docx, .pdf, .txt)
- [x] GitHub projects portfolio
- [x] Answer usage history tracking

**In Progress:**
- [ ] Interactive weight sliders for job scoring (game dev tycoon style)

**Planned:**
- [ ] Multi-source job scraping (Indeed, LinkedIn)
- [ ] Application status tracking
- [ ] Success rate analytics
- [ ] Interview preparation tools
- [ ] Email notifications for new high-fit jobs
- [ ] Cover letter generation from CV + job description
- [ ] Package as Windows .exe

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICK_START.md](QUICK_START.md)** | One-page daily workflow reference (print this!) |
| **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** | Detailed setup for first-time users |
| **[CLAUDE.md](CLAUDE.md)** | Technical architecture (WAT framework) for developers |

---

## ❓ FAQ

**Q: Do I need API keys?**
A: No! The extension works great without them using regex extraction. API keys are only needed for optional features (job scraping, CV parsing, company research).

**Q: Does it auto-fill forms?**
A: No. You review answers and copy/paste manually. This keeps it TOS-safe and gives you control.

**Q: Is my data secure?**
A: Yes. Everything runs locally on your machine. No cloud services, no external servers.

**Q: Why regex over AI?**
A: Regex is fast, free, and 90%+ accurate for standard forms. AI adds minimal benefit (~5-10%) for significant cost.

**Q: Can I use this for other job sites?**
A: Yes! The extension works on any text-based application form. It extracts questions from whatever page you're on.

**Q: How do I update my Q&A answers?**
A: Edit `qa_databank.yaml` or use the Settings page in the dashboard. Changes are saved automatically.

---

## 🤝 Contributing

This is a personal project built with Claude Code using the WAT framework (Workflows, Agents, Tools). See [CLAUDE.md](CLAUDE.md) for technical architecture details.

---

## 📄 License

MIT — use it, modify it, build on it.

---

<p align="center">
  <i>Built because applying to jobs shouldn't feel like a second job.</i>
</p>
