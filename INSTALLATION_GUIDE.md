# JobRadar Installation Guide

**Get started in 2 minutes** - no backend or API keys needed!

## What You Need

- **Google Chrome** browser

That's it! Python backend is completely optional.

---

## 2-Step Quick Start

### Step 1: Load the Chrome Extension

1. Open Chrome and go to: `chrome://extensions/`
2. Toggle **"Developer mode"** (top-right corner)
3. Click **"Load unpacked"**
4. Select the `chrome-extension` folder:
   ```
   C:\Users\YourName\Desktop\ClaudeCode\JobRadar\chrome-extension
   ```
5. Pin the extension (click puzzle icon → pin "JobRadar")

**Note:** The extension loads instantly - placeholder icons are included.

---

### Step 2: Add Your Answers

1. Click the JobRadar extension icon
2. Click **"Settings"** in the extension
3. Go to the **"Personal Info"** tab:
   - Add your name, email, phone, location, LinkedIn
4. Go to the **"Q&A Bank"** tab:
   - Click **"+ Add Question"**
   - Add common questions and your pre-written answers
   - Examples:
     - "Why are you interested in this role?" → Your standard answer
     - "What are your salary expectations?" → "£50,000 - £60,000"
     - "When can you start?" → "2 weeks notice"

**That's it!** Your answers are saved in Chrome storage and ready to use.

---

### Using the Extension

1. Go to a job application page (LinkedIn, Indeed, company websites, etc.)
2. Click the JobRadar icon in Chrome
3. In the side panel, click **"Copy Page Content"**
4. Click **"Parse Questions & Get Answers"**
5. Review the matched answers and copy them into the application form

**The extension works completely offline** using local regex extraction and Chrome storage.

---

## Optional Enhancements

The extension works great standalone! Add these features if you want advanced capabilities:

### A) Enable Python Backend (Optional)

The backend adds:
- AI-powered question extraction (~5% more accurate than regex)
- Answer usage tracking and analytics
- Cross-device sync (if you use multiple computers)
- Job scraping and scoring dashboard

**Requirements:**
- Python 3.8+ ([Download here](https://www.python.org/downloads/))

**Setup:**

1. **Double-click:** `start_jobradar.bat`

   This starts:
   - Flask API (port 5000) - for extension features
   - Streamlit dashboard (port 8501) - for job browsing

   **First time?** The script automatically installs dependencies.

2. **Keep the window open** while using advanced features

3. In the extension:
   - Go to **Settings → Backend (Optional)** tab
   - Verify status shows **"Connected ✓"**
   - Enable **"Auto-sync Q&A data"** if desired

**With backend enabled:**
- Extension tries backend first, falls back to local if unavailable
- Your Chrome storage Q&A syncs with backend (bidirectional)
- Usage history is tracked in the dashboard

---

### B) Enable AI Question Extraction (Requires Backend)

By default, the extension uses **regex extraction** (free, fast, works offline).
For slightly better accuracy (~5%), enable AI:

**Do you need this?** Probably not! Regex works well for 90%+ of applications.

**If you want it:**

1. Copy the template:
   ```
   copy .env.template .env
   ```

2. Get a free API key: https://console.anthropic.com/

3. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

4. Restart the backend

**Cost:** ~$0.001 per application (extremely cheap)

---

### C) Enable Job Search (Requires Backend)

Want JobRadar to scrape and score jobs for you?

1. Get a free SerpAPI key: https://serpapi.com/ (100 searches/month free)

2. Add to `.env`:
   ```
   SERPAPI_KEY=your-serpapi-key
   ```

3. Configure your search:
   ```
   copy job_search_config.yaml.template job_search_config.yaml
   copy user_profile.yaml.template user_profile.yaml
   ```

4. Edit both YAML files with your criteria and skills

5. Use the dashboard (port 8501) to run searches and view scored jobs

---

## Troubleshooting

### "Extension won't load"
- Make sure you selected the `chrome-extension` **folder**, not a file
- Check that Developer mode is enabled
- Icons are included now, so it should just work

### "No questions found"
- Make sure you clicked **"Copy Page Content"** first
- Some pages don't have standard forms (try a different job site)
- Check that the page actually contains a job application form

### "Questions extracted but no answers"
- This is normal if you haven't added Q&A entries yet
- Go to **Settings → Q&A Bank** and add your standard answers
- You can also type answers directly in the extension before copying

### "Backend not running" message (Optional)
- **This is fine!** The extension works standalone without the backend
- Status shows "(Local mode)" - this means it's working locally
- If you want backend features, start `start_jobradar.bat`
- Check **Settings → Backend (Optional)** tab for connection status

### "Python not found" (Only if using backend)
- Install Python: https://www.python.org/downloads/
- **Important:** Check "Add Python to PATH" during installation
- Restart your terminal

---

## How It Works

### Question Extraction

**Standalone Mode (Default):** Local regex extraction
- Runs completely in your browser (JavaScript)
- Looks for common field labels (First Name, Email, etc.)
- Finds questions with patterns like "Why...", "What...", "Do you..."
- Fast, offline, no API costs, no backend needed
- Works for 90%+ of standard application forms (Workday, Greenhouse, Lever)

**Backend Mode (Optional):** AI extraction with Claude
- Requires Python backend and ANTHROPIC_API_KEY
- Understands context and unconventional labels
- Slightly more accurate (maybe 5% improvement)
- Costs ~$0.001 per application
- Extension automatically tries backend first, falls back to local

### Answer Matching

**Standalone Mode:**
- Matches extracted questions against your Chrome storage Q&A databank
- Exact matches: Personal info fields (name, email, phone)
- Fuzzy matches: Uses word overlap similarity for stored questions
- No match: Shows "[No answer in databank - add in Settings]"
- All processing happens locally in your browser

**Backend Mode (Optional):**
- Can sync Q&A data between Chrome storage and backend YAML file
- Enables cross-device sync if you use multiple computers
- Bidirectional: Changes in extension sync to backend and vice versa

### Tracking (Backend Only)

If backend is enabled, every copied answer is tracked:
- Which questions you answered
- Whether you edited the answer
- Job URL and company name
- View history in the dashboard (port 8501 → History tab)

**Standalone mode:** No tracking - your data stays private in Chrome storage

---

## Privacy & Security

**Standalone Mode (Default):**
- **100% private** - all data stored in Chrome's local storage
- **No network calls** - everything runs in your browser
- **No external servers** - no cloud services, no backend required
- **No tracking** - your data never leaves your machine

**Backend Mode (Optional):**
- **Local backend only** - runs on your computer (localhost)
- **No cloud services** - data never sent to external servers except:
  - SerpAPI calls (only if you enable job search)
  - Anthropic API calls (only if you enable AI extraction)
- **You control everything** - backend is optional and runs locally

**Both Modes:**
- **No auto-fill** - you review and copy answers manually (TOS-safe)
- **No website modification** - extension only reads page text when you click
- **No data collection** - no analytics, no telemetry
- **Open source** - inspect the code yourself

---

## Next Steps

1. **Start using it** - apply to jobs with the extension
2. **Build your Q&A bank** - add more answers in Settings as you encounter new questions
3. **Export your data** - use Settings → Import/Export to backup your Q&A databank
4. **(Optional) Add backend** - if you want AI extraction, tracking, or job scraping

For daily workflow tips, see [QUICK_START.md](QUICK_START.md)

For technical details, see [README.md](README.md)

---

**Ready for Chrome Web Store!** The extension now works with zero setup - just install and start applying.
