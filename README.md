# JobRadar - Job Application Assistant

An all-in-one job search automation tool that helps you find jobs, score them by fit, and assist with applications through a Chrome extension.

## What It Does

1. **Scrapes job listings** from multiple sources (Google Jobs via SerpAPI)
2. **Scores jobs 0-100** based on your skills, location, and preferences
3. **Dashboard** to browse, filter, and research jobs
4. **Chrome Extension** to assist with job applications (extract questions, provide answers from your databank)

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - One-page daily workflow reference (print this!)
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Detailed setup instructions for first-time users
- **[CLAUDE.md](CLAUDE.md)** - Technical architecture (WAT framework) for developers

## Quick Start

**First Time Setup:** See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed instructions.

**Daily Use:** See [QUICK_START.md](QUICK_START.md) for the workflow cheat sheet.

### TL;DR (If you already have Python)

1. **Setup:** Copy `.env.template` → `.env` and add API keys (optional)
2. **Configure:** Copy `.yaml.template` files → `.yaml` and edit with your info
3. **Install Extension:** Load `chrome-extension/` folder in Chrome (`chrome://extensions/`)
4. **Run:** Double-click `start_jobradar.bat`
5. **Use:** Click JobRadar extension icon on job application pages

That's it!

Then in another terminal:
```bash
python tools/answer_questions_api.py
```

The dashboard will open at http://localhost:8501

### 5. Install Chrome Extension

1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. Pin the extension to your toolbar

## How to Use

### Finding Jobs

1. Open the dashboard (http://localhost:8501)
2. Go to "Actions" tab
3. Click "Scrape New Jobs"
4. Jobs will be scored and saved to `.tmp/scored_jobs.json`

### Applying to Jobs

1. Open a job application page
2. Click the JobRadar extension icon
3. Click "Copy Page Content" to capture the application form
4. Click "Parse Questions & Get Answers"
5. Review the answers provided from your databank
6. Copy answers and paste into the application manually

**Privacy Note**: The extension only reads page text when you click the button. It never auto-fills or modifies the website. All processing happens locally on your machine.

## Project Structure

```
JobRadar/
├── start_jobradar.bat        # Launch script (runs both services)
├── app.py                    # Streamlit dashboard
├── .env                      # API keys (create this)
├── requirements.txt          # Python dependencies
│
├── user_profile.yaml         # Your skills/preferences (gitignored)
├── qa_databank.yaml          # Answers to common questions (gitignored)
├── job_search_config.yaml    # Search parameters (gitignored)
│
├── chrome-extension/         # Browser extension
│   ├── manifest.json
│   ├── background.js
│   └── popup/
│       ├── popup.html
│       ├── popup.js
│       └── popup.css
│
├── tools/                    # Backend scripts
│   ├── answer_questions_api.py  # Flask API for extension
│   ├── run_job_scrape.py        # Scraping orchestrator
│   ├── scrape_serpapi.py        # SerpAPI scraper
│   ├── score_job_fit.py         # Job scoring algorithm
│   ├── push_to_sheets.py        # Google Sheets export
│   ├── parse_cv.py              # CV text extraction
│   └── scraper_utils.py         # Shared utilities
│
├── .tmp/                     # Temporary data (gitignored)
│   ├── scored_jobs.json      # Scraped jobs with scores
│   └── company_reports.json  # Cached company research
│
└── workflows/                # Documentation
    ├── job_scrape.md
    └── job_fit_scoring.md
```

## Dashboard Pages

### Jobs (Browse)
- Filter by fit score
- Search by title/company
- View job details and descriptions
- Generate AI company research
- Apply link

### Settings
- Personal info
- Skills (required/preferred)
- Location preferences
- Dealbreakers (auto-reject keywords)
- Q&A databank
- Work authorization details

### Actions
- Run job scraper
- Re-score existing jobs
- Start/stop extension backend
- Test API connection

## How Job Scoring Works

Jobs are scored 0-100 based on weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Required Skills | 40% | % of your required skills found in job description |
| Preferred Skills | 25% | % of your preferred skills found |
| Location | 20% | 100 if preferred, 50 if acceptable, 0 otherwise |
| Title Relevance | 15% | Contains "developer", "engineer", or "software" |

**Dealbreakers**: Jobs with dealbreaker keywords (e.g., "senior", "10+ years") automatically get score = 0.

## Chrome Extension - How It Works

The extension helps you fill out applications faster:

1. **You open** a job application page
2. **You click** "Copy Page Content" (uses standard browser copy)
3. **Extension sends** the text to your local Flask backend
4. **Backend extracts** questions using regex (fast, free) or Claude API (if regex fails)
5. **Backend matches** questions against your Q&A databank
6. **Extension shows** answers in the popup
7. **You review** and manually copy/paste into the form

**TOS-Safe Design**:
- No DOM manipulation
- No auto-filling
- No automated submission
- You control every action
- All processing is local (no cloud services)

## Optional: Google Sheets Export

To export jobs to Google Sheets:

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable Google Sheets API
4. Create OAuth credentials (Desktop app)
5. Download as `credentials.json` and place in project root
6. Run scraper - it will prompt for authorization once
7. Token saves to `token.json` for future use

## Configuration Files

### user_profile.yaml
```yaml
profile:
  name: "Your Name"
  email: "you@example.com"
  skills:
    required:
      - Python
      - Git
    preferred:
      - JavaScript
      - SQL
  locations:
    preferred:
      - London
      - Remote
    acceptable:
      - Manchester
  salary:
    minimum: 25000
    preferred: 35000
  dealbreakers:
    - "senior"
    - "5+ years"
```

### qa_databank.yaml
```yaml
personal:
  name: "Your Name"
  email: "you@example.com"
  phone: "+44 1234 567890"

work_auth:
  uk_eligible: "Yes"
  sponsorship_needed: "No"

questions:
  - question: "Why do you want to work here?"
    answer: "Your answer..."
  - question: "What are your salary expectations?"
    answer: "£30,000 - £35,000"
```

### job_search_config.yaml
```yaml
search_params:
  titles:
    - "Junior Software Engineer"
    - "Junior Developer"
  location: "London, United Kingdom"
  posted_within_days: 30

sites:
  - google_jobs

output:
  spreadsheet_name: "Job Applications"
  worksheet_name: "Jobs"

api:
  max_results: 50
  pages: 3
```

## Dependencies

All dependencies install via `pip install -r requirements.txt`:

- `streamlit` - Dashboard UI
- `flask` + `flask-cors` - Extension backend API
- `google-search-results` - SerpAPI client for job scraping
- `anthropic` - Claude API for company research
- `gspread` + `google-auth-oauthlib` - Google Sheets (optional)
- `pyyaml` - Configuration files
- `python-dotenv` - Environment variables
- `pandas` - Data processing
- `python-docx` - CV parsing

## Roadmap

- [ ] Package as Windows .exe (single-click install)
- [ ] Add more job sources (Indeed, LinkedIn direct)
- [ ] Track application status and history
- [ ] Success rate analytics
- [ ] Interview preparation tools

## License

MIT
