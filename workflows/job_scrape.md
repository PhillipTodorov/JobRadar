# Job Scraping Workflow

## Objective
Fetch job listings via SerpAPI (Google Jobs) and deliver results to Google Sheets (or CSV fallback).

## Prerequisites
- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`
- SerpAPI key (free tier: 100 searches/month) — add to `.env` as `SERPAPI_KEY`
- (Optional) Google OAuth credentials for Sheets output — see Google Sheets Setup below

## Inputs
- `job_search_config.yaml` — search parameters, site list, output settings, API config
- `.env` — contains `SERPAPI_KEY`

## Steps

### Full Pipeline
Run everything with one command:
```
cd tools
python run_job_scrape.py
```

### Individual Steps (for debugging)
1. Fetch jobs via SerpAPI only: `python tools/scrape_serpapi.py`
2. Push existing data to Sheets: `python tools/push_to_sheets.py`

## Tools Used
| Tool | Purpose |
|------|---------|
| `tools/scraper_utils.py` | Config loading, data normalization, CSV export |
| `tools/scrape_serpapi.py` | Google Jobs fetcher via SerpAPI |
| `tools/push_to_sheets.py` | Google Sheets OAuth + data push |
| `tools/run_job_scrape.py` | Pipeline orchestrator |

## Expected Output
- `.tmp/linkedin_raw.json` — raw scraped data (named by site in config)
- `.tmp/jobs_export.csv` — combined CSV of all jobs
- Google Sheet with columns: title, company, location, url, date_posted, salary, description, source, scraped_at

## SerpAPI Setup
1. Go to https://serpapi.com/ and create a free account
2. Copy your API key from the dashboard
3. Add to `.env`: `SERPAPI_KEY=your_key_here`
4. Free tier provides 100 searches/month — sufficient for daily job searching

## Google Sheets Setup (One-Time)
1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: **Desktop application**
6. Download the JSON and save as `credentials.json` in project root
7. Run `python tools/push_to_sheets.py` — a browser window opens for Google login
8. After login, `token.json` is created automatically (gitignored)

## Edge Cases & Lessons Learned
- **API key missing**: Script exits with instructions if `SERPAPI_KEY` not found in `.env`
- **Rate limiting**: Free tier is 100 searches/month. Each title in config is a separate search. 3 titles × 3 pages = 9 API calls per run.
- **Deduplication**: Jobs are deduplicated by title+company across multiple title queries to avoid repeats.
- **Token expiry**: If Google auth fails, delete `token.json` and re-run to re-authenticate.
- **No results**: Try broader search terms or increase `posted_within_days` in config.

## Adding a New Job Site Scraper
1. Create `tools/scrape_<sitename>.py`
2. Import shared utilities from `scraper_utils`
3. Implement a `scrape()` function that returns a list of normalized job dicts
4. Save raw results to `.tmp/<sitename>_raw.json`
5. Add the scraper module name to `SCRAPERS` dict in `run_job_scrape.py`
6. Add the site name to `sites` list in `job_search_config.yaml`
