# Job Fit Scoring Workflow

## Objective
Score scraped jobs against your profile (skills, location preferences) to prioritize the best matches. Jobs are ranked 0-100 and sorted in Google Sheets.

## Prerequisites
- Job scraping workflow already set up and working
- `user_profile.yaml` configured with your skills

## Inputs
- `user_profile.yaml` — Your skills, location preferences, dealbreakers
- `.tmp/serpapi_raw.json` or `.tmp/linkedin_raw.json` — Scraped job data

## How It Works

The scoring algorithm checks each job against your profile:

| Factor | Weight | How It's Scored |
|--------|--------|-----------------|
| Required skills | 40% | % of your must-have skills found in job description |
| Preferred skills | 25% | % of nice-to-have skills found |
| Location | 20% | 100 if preferred, 50 if acceptable, 0 otherwise |
| Title relevance | 15% | 100 if contains developer/engineer/software |

**Dealbreakers:** If any dealbreaker keyword (e.g., "senior", "10+ years") is found, the job gets a score of 0.

## Steps

### 1. Configure Your Profile

Edit `user_profile.yaml` in the project root:

```yaml
profile:
  skills:
    required:      # Must-haves (40% weight)
      - Python
      - JavaScript
    preferred:     # Nice-to-haves (25% weight)
      - React
      - Docker
      - AWS

  locations:
    preferred:     # Full points
      - London
      - Remote
    acceptable:    # Half points
      - Manchester

  dealbreakers:    # Jobs with these get score = 0
    - "senior"
    - "10+ years"
```

### 2. Run the Full Pipeline

```bash
cd tools
python run_job_scrape.py
```

This will:
1. Scrape jobs via SerpAPI
2. Score each job against your profile
3. Save scored results to `.tmp/scored_jobs.json`
4. Push to Google Sheets sorted by fit_score

### 3. Score Existing Jobs (Without Re-scraping)

```bash
cd tools
python score_job_fit.py
```

This reads from `.tmp/` and outputs scored jobs.

## Tools Used

| Tool | Purpose |
|------|---------|
| `tools/score_job_fit.py` | Calculates fit scores (0-100) |
| `user_profile.yaml` | Your skills and preferences |
| `tools/run_job_scrape.py` | Orchestrates scraping + scoring |

## Expected Output

**Google Sheets columns:**
```
title | company | location | url | date_posted | salary | description | source | scraped_at | fit_score
```

Jobs are sorted by `fit_score` descending, so best matches appear first.

**Console output:**
```
Scored 82 jobs:
  Jobs with score > 0: 65
  Jobs filtered (dealbreakers): 17
  Average score: 42.3
  Top score: 78 - Junior Developer at TechCorp
```

## Tuning Tips

1. **Too many jobs filtered?** Remove dealbreakers or be more specific (e.g., "8+ years" instead of just "years")

2. **Wrong jobs ranking high?** Add more required skills to be more selective

3. **Good jobs ranking low?** Check if you're missing skill synonyms (e.g., add both "JS" and "JavaScript")

4. **Adjust weights** in `user_profile.yaml` under `scoring.weights` to prioritize what matters most

## Edge Cases

- **No profile file:** Pipeline runs without scoring, warns user
- **Empty skills:** Neutral score (50) for that category
- **Missing location:** Gets 0 for location score
- **Job without description:** Only title is matched (lower accuracy)
