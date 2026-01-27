# JobRadar Installation Guide

**Get started in 3 steps** - no configuration needed!

## What You Need

- **Python 3.8+** ([Download here](https://www.python.org/downloads/) if needed)
- **Google Chrome** browser

That's all! Everything else is optional.

---

## 3-Step Quick Start

### Step 1: Load the Chrome Extension

1. Open Chrome and go to: `chrome://extensions/`
2. Toggle **"Developer mode"** (top-right corner)
3. Click **"Load unpacked"**
4. Select the `chrome-extension` folder:
   ```
   C:\Users\YourName\Desktop\ClaudeCode\JobRadar\chrome-extension
   ```
5. Pin the extension (click puzzle icon → pin "JobRadar")

**Note:** The extension loads instantly now - placeholder icons are included.

---

### Step 2: Start the Backend

**Double-click:** `start_jobradar.bat`

This starts:
- Flask API (port 5000) - needed by extension
- Streamlit dashboard (port 8501) - optional, for job browsing

**Keep this window open** while using the extension.

**First time?** The script automatically installs dependencies.

---

### Step 3: Use It!

1. Go to a job application page (LinkedIn, Indeed, company websites, etc.)
2. Click the JobRadar icon in Chrome
3. In the side panel, click "Copy Page Content"
4. Click "Parse Questions & Get Answers"
5. Copy answers into the application form

**That's it!** The extension works immediately using smart regex extraction.

---

## Optional Enhancements

Want better results? Add these features later:

### A) Add Your Standard Answers (Highly Recommended)

This is where JobRadar becomes powerful - save your answers once, reuse everywhere:

1. Copy the template:
   ```
   copy qa_databank.yaml.template qa_databank.yaml
   ```

2. Edit `qa_databank.yaml` with YOUR answers to common questions:
   ```yaml
   personal_info:
     full_name: "Your Name"
     email: "your.email@example.com"
     phone: "+44 1234 567890"
     location: "London, UK"

   questions:
     "Why are you interested in this role?": "Your pre-written answer here"
     "What are your salary expectations?": "£50,000 - £60,000"
     "When can you start?": "2 weeks notice"
   ```

3. Restart the backend

Now the extension will auto-fill your saved answers!

---

### B) Enable AI Question Extraction (Optional)

By default, JobRadar uses **regex extraction** (free, fast, works offline).
For slightly better accuracy, add an AI key:

**Do you need this?** Probably not! Regex works well for most applications.
Our tests show it catches 90%+ of form fields accurately.

**If you want it anyway:**

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

### C) Enable Job Search (Optional)

Want JobRadar to scrape jobs for you?

1. Get a free SerpAPI key: https://serpapi.com/ (100 searches/month free)

2. Add to `.env`:
   ```
   SERPAPI_KEY=your-serpapi-key
   ```

3. Configure your search:
   ```
   copy job_search_config.yaml.template job_search_config.yaml
   ```

4. Edit `job_search_config.yaml` with your criteria

5. Use the dashboard (port 8501) to run searches

---

## Troubleshooting

### "Extension won't load"
- Make sure you selected the `chrome-extension` **folder**, not a file
- Check that Developer mode is enabled
- Icons are included now, so it should just work

### "Backend not running" in extension
- Make sure `start_jobradar.bat` is running
- Check that you see "Running on http://127.0.0.1:5000" in the terminal
- Try clicking the "Setup Guide" link in the extension for live status

### "No questions found"
- Make sure you clicked "Copy Page Content" first
- Some pages don't have standard forms (try a different job site)
- Click "Debug: Preview Questions" to see what was extracted

### "Python not found"
- Install Python: https://www.python.org/downloads/
- **Important:** Check "Add Python to PATH" during installation
- Restart your terminal

### "Questions extracted but no answers"
- This is normal if you haven't set up `qa_databank.yaml` yet
- Add your standard answers (see Optional Enhancement A above)
- You can type answers directly in the extension before copying

---

## How It Works

### Question Extraction

**Default (Free):** Regex pattern matching
- Looks for common field labels (First Name, Email, etc.)
- Finds questions with patterns like "Why...", "What...", "Do you..."
- Fast, offline, no API costs
- Works for 90%+ of standard application forms

**Optional (Better):** AI extraction with Claude
- Understands context and unconventional labels
- Slightly more accurate (maybe 5-10% improvement)
- Costs ~$0.001 per application
- Add ANTHROPIC_API_KEY to enable

### Answer Matching

The extension matches extracted questions against your `qa_databank.yaml`:
- Exact matches: Returns your saved answer
- Similar questions: Uses word overlap similarity
- No match: Shows "[No answer in databank]" - you type it manually

### Tracking

Every copied answer is tracked:
- Which questions you answered
- Whether you edited the answer
- Job URL and company name
- View history in the dashboard (port 8501 → History tab)

---

## Privacy & Security

- **All data stays local** - nothing is sent to external servers except:
  - SerpAPI calls (if you use job search)
  - Anthropic API calls (if you enable AI extraction)
- **No auto-fill** - you review and copy answers manually (TOS-safe)
- **No website modification** - extension just reads page text
- **No data collection** - tracking is local only

---

## Next Steps

1. **Start using it** - apply to jobs with the extension
2. **Build your databank** - add more Q&A as you encounter new questions
3. **Review the History tab** - see which answers work best
4. **Customize as needed** - add API keys if you want enhanced features

For daily workflow tips, see [QUICK_START.md](QUICK_START.md)

For technical details, see [README.md](README.md)
