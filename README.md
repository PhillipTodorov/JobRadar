# 🎯 JobRadar

**Job search automation that actually works.**

Scrape jobs → Score by fit → Apply faster with a Chrome extension that knows your answers.

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Chrome Extension](https://img.shields.io/badge/chrome-extension-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What It Does

| Feature | Description |
|---------|-------------|
| 🔍 **Job Scraping** | Pull listings from Google Jobs (via SerpAPI) automatically |
| 📊 **Smart Scoring** | Score jobs 0-100 based on your skills, location, preferences |
| 📋 **Dashboard** | Browse, filter, and research jobs in one place |
| 🧩 **Chrome Extension** | Extract application questions, get suggested answers from your databank |

---

## Demo

> 🚧 **Screenshots coming soon** — project is in active development

<!-- 
TODO: Add screenshots
![Dashboard](screenshots/dashboard.png)
![Extension Popup](screenshots/extension.png)
-->

---

## Tech Stack

**Backend**
- Python 3.8+
- Flask (API for extension)
- Streamlit (dashboard)
- Pandas (data processing)

**Chrome Extension**
- Manifest V3
- JavaScript
- HTML/CSS

**Integrations**
- SerpAPI (job scraping)
- Claude API (question parsing, company research)
- Google Sheets (optional export)

---

## How the Chrome Extension Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Job App Page   │────▶│    Extension    │────▶│  Flask Backend  │
│  (any website)  │     │  (copy content) │     │  (local only)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Parse Questions │
                                               │  Match to Q&A DB │
                                               │  Return Answers  │
                                               └─────────────────┘
                                                        │
                                                        ▼
                              ┌──────────────────────────────────────┐
                              │  You review & manually paste answers │
                              │  (no auto-fill, no DOM manipulation) │
                              └──────────────────────────────────────┘
```

**Privacy-first design:**
- Extension only reads when you click
- All processing happens locally
- No data sent to external servers (except APIs you configure)
- You control every action

---

## Quick Start

```bash
# Clone
git clone https://github.com/PhillipTodorov/JobRadar.git
cd JobRadar

# Setup
cp .env.template .env          # Add your API keys
cp *.yaml.template *.yaml      # Configure your profile

# Install
pip install -r requirements.txt

# Run
python app.py                  # Dashboard at localhost:8501
python tools/answer_questions_api.py  # Extension backend
```

**Chrome Extension:**
1. Go to `chrome://extensions`
2. Enable Developer Mode
3. Load unpacked → select `chrome-extension/` folder

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed setup.

---

## Job Scoring Algorithm

Jobs are scored 0-100 based on weighted factors:

| Factor | Weight | What It Checks |
|--------|--------|----------------|
| Required Skills | 40% | Your must-have skills in job description |
| Preferred Skills | 25% | Your nice-to-have skills |
| Location | 20% | Preferred (100), acceptable (50), other (0) |
| Title Match | 15% | Contains relevant keywords |

**Dealbreakers** (e.g., "senior", "10+ years") → automatic score = 0

---

## Project Structure

```
JobRadar/
├── app.py                    # Streamlit dashboard
├── chrome-extension/         # Browser extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js
│   └── popup/
├── tools/                    # Backend scripts
│   ├── answer_questions_api.py  # Flask API
│   ├── score_job_fit.py         # Scoring algorithm
│   └── scrape_serpapi.py        # Job scraper
├── user_profile.yaml         # Your skills & preferences
├── qa_databank.yaml          # Pre-written answers
└── job_search_config.yaml    # Search parameters
```

---

## Roadmap

- [x] Job scraping from Google Jobs
- [x] Fit scoring algorithm
- [x] Streamlit dashboard
- [x] Chrome extension for application assist
- [ ] Package as Windows .exe
- [ ] More job sources (Indeed, LinkedIn)
- [ ] Application tracking
- [ ] Interview prep tools

---

## Documentation

- **[QUICK_START.md](QUICK_START.md)** — Daily workflow cheat sheet
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** — First-time setup guide
- **[CLAUDE.md](CLAUDE.md)** — Technical architecture

---

## License

MIT — use it, modify it, build on it.

---

<p align="center">
  <i>Built because applying to jobs shouldn't feel like a second job.</i>
</p>
