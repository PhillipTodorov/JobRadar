# Job Scraper Dashboard

A job search automation tool that scrapes job listings, scores them against your profile, and provides a Streamlit dashboard for browsing and researching opportunities.

## Features

- **Job Scraping**: Automatically scrape jobs from LinkedIn via SerpAPI
- **Fit Scoring**: Score jobs 0-100 based on how well they match your skills and preferences
- **Streamlit Dashboard**: Browse jobs, filter by score, and research companies
- **Company Research**: AI-powered company research reports using Claude API
- **Google Sheets Export**: Push results to Google Sheets for tracking
- **Q&A Databank**: Store answers to common application questions
- **CV Parsing**: Extract text from your CV for context

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
SERPAPI_KEY=your-serpapi-key
ANTHROPIC_API_KEY=your-anthropic-key
```

- Get SerpAPI key at: https://serpapi.com/
- Get Anthropic key at: https://console.anthropic.com/

### 3. Set Up Your Profile

Edit `user_profile.yaml` with your skills and preferences:

```yaml
profile:
  name: "Your Name"
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
  dealbreakers:
    - "senior"
    - "10+ years"
```

### 4. Run the Scraper

```bash
cd tools
python run_job_scrape.py
```

### 5. Launch the Dashboard

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
.
├── app.py                    # Streamlit dashboard
├── .env                      # API keys (create this)
├── requirements.txt          # Python dependencies
├── user_profile.yaml         # Your skills and preferences
├── qa_databank.yaml          # Stored Q&A for applications
├── job_search_config.yaml    # Search parameters
├── credentials.json          # Google OAuth (optional)
├── profile/
│   └── *.docx                # Your CV
├── tools/
│   ├── run_job_scrape.py     # Main scraping pipeline
│   ├── scrape_serpapi.py     # SerpAPI LinkedIn scraper
│   ├── score_job_fit.py      # Job fit scoring
│   ├── push_to_sheets.py     # Google Sheets integration
│   ├── parse_cv.py           # CV text extraction
│   └── scraper_utils.py      # Shared utilities
├── .tmp/
│   ├── scored_jobs.json      # Scraped jobs with scores
│   └── company_reports.json  # Cached company research
└── workflows/                # Documentation (optional)
```

## Dashboard Pages

### Dashboard
- Overview statistics (total jobs, matching jobs, average score)
- Top 10 jobs by fit score
- Your profile summary

### View Jobs
- Browse all scraped jobs in a scrollable list
- Filter by minimum fit score
- Search by title or company
- View job details and descriptions
- Generate AI company research reports

### Edit Profile
- Update your skills (required/preferred)
- Set location preferences
- Configure dealbreaker keywords
- Adjust scoring weights

### Q&A Databank
- Store answers to common application questions
- Personal info for quick reference
- Work authorization details
- Cover letter templates

### Search Settings
- Configure job titles to search
- Set location and other filters
- Adjust API parameters

### Run Tools
- Execute scraper directly from dashboard
- Run individual tools
- View tool output

## Scoring System

Jobs are scored 0-100 based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Required Skills | 40% | Must-have skills from your profile |
| Preferred Skills | 25% | Nice-to-have skills |
| Location | 20% | Preferred (100), Acceptable (50), Other (0) |
| Title Relevance | 15% | Contains developer/engineer keywords |

**Dealbreakers**: Jobs containing dealbreaker keywords (e.g., "senior", "10+ years") get a score of 0.

## Google Sheets Integration

To export to Google Sheets:

1. Create a project at https://console.cloud.google.com/
2. Enable Google Sheets API
3. Create OAuth credentials and download as `credentials.json`
4. Place `credentials.json` in project root
5. Run the scraper - it will prompt for authorization

## Configuration Files

### job_search_config.yaml

```yaml
search_params:
  titles:
    - "Junior Software Engineer"
    - "Junior Developer"
  location: "London, United Kingdom"
  posted_within_days: 30

sites:
  - linkedin

output:
  spreadsheet_name: "Job Scraping Results"
  worksheet_name: "Jobs"

api:
  max_results: 50
  pages: 3
```

### user_profile.yaml

```yaml
profile:
  name: "Your Name"
  skills:
    required: [Python, Git]
    preferred: [JavaScript, SQL, React]
  locations:
    preferred: [London, Remote]
    acceptable: [Manchester]
  salary:
    minimum: 25000
    preferred: 35000
  dealbreakers:
    - "senior"
    - "lead"
    - "5+ years"

scoring:
  weights:
    required_skills: 0.40
    preferred_skills: 0.25
    location: 0.20
    title_relevance: 0.15
```

## Chrome Extension - Application Assistant

A Chrome extension that helps you fill out job applications by extracting questions from the page and providing AI-powered answers.

### How It Works

1. Open a job application page
2. Click the extension icon
3. Click "Copy Page Content" - copies all text from the page
4. Click "Parse Questions & Get Answers" - AI extracts questions and generates answers
5. Click "Copy" on any answer to paste into the application form

### Setup

1. **Install Flask dependencies:**
   ```bash
   pip install flask flask-cors
   ```

2. **Start the backend API:**
   ```bash
   cd tools
   python answer_questions_api.py
   ```

3. **Load the extension in Chrome:**
   - Open `chrome://extensions`
   - Enable "Developer mode" (toggle in top right)
   - Click "Load unpacked"
   - Select the `chrome-extension` folder

4. **Add an icon** (optional):
   - Add `icon48.png` and `icon128.png` to `chrome-extension/icons/`
   - You can use any 48x48 and 128x128 PNG images

### Extension Files

```
chrome-extension/
├── manifest.json       # Extension configuration
├── popup/
│   ├── popup.html      # Extension popup UI
│   ├── popup.js        # Popup logic
│   └── popup.css       # Styling
└── icons/
    └── (add your icons here)
```

### TOS-Safe Approach

The extension uses minimal website interaction to avoid TOS violations:
- Only uses standard browser Select All + Copy
- No DOM manipulation or injection
- No automated form filling
- User manually pastes answers
- All processing happens locally

## Dependencies

- `streamlit` - Dashboard UI
- `google-search-results` - SerpAPI client
- `gspread` + `google-auth-oauthlib` - Google Sheets
- `anthropic` - Claude API for company research
- `pyyaml` - Configuration files
- `python-dotenv` - Environment variables
- `pandas` - Data manipulation
- `python-docx` - CV parsing
- `flask` + `flask-cors` - Extension backend API

## License

MIT
