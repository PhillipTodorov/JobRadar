# JobRadar Quick Start

## Daily Workflow (3 Steps)

### 1. Start Backend
```
Double-click: start_jobradar.bat
```
Keep this window open while job hunting.

### 2. Find Jobs (Optional)
- Dashboard opens automatically → **"Actions"** tab → **"Run Job Search"**
- View results in **"Jobs"** tab

### 3. Apply with Extension
1. Go to job application page
2. Click JobRadar icon in Chrome toolbar
3. Click **"Copy Page Content"**
4. Click **"Parse Questions & Get Answers"**
5. Review answers (edit if needed)
6. Click **"Copy"** for each answer
7. Paste into actual application form

---

## First Time Setup

**Minimum to get started:**
1. **Install Python** (if needed): https://www.python.org/downloads/
2. **Install Chrome Extension**:
   - Go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select `chrome-extension` folder

That's it! The extension works immediately with regex extraction.

**Optional upgrades (add later):**
3. **Configure Your Answers** (highly recommended):
   - Copy `qa_databank.yaml.template` → `qa_databank.yaml`
   - Add your standard answers to common questions
4. **Add API Keys** (optional, for AI extraction):
   - Copy `.env.template` → `.env`
   - Add Anthropic key for better question extraction (regex works well though!)
   - Add SerpAPI key if you want automated job search

---

## Quick Answers to Common Questions

**Q: Do I need API keys?**
A: No! Extension works great without them using regex extraction. AI extraction is only ~5-10% more accurate.

**Q: Does it auto-fill forms?**
A: No. You review and copy answers manually (TOS-safe).

**Q: Where is my data stored?**
A: Everything stays local on your machine. No cloud services.

**Q: How do I add new answers?**
A: Edit `qa_databank.yaml` with new questions and answers. They'll be matched automatically.

**Q: What's better - regex or AI extraction?**
A: Regex works for 90%+ of applications (free, fast). AI is slightly better but costs money. Start with regex.

**Q: Extension says "Backend not running"?**
A: Make sure `start_jobradar.bat` is running. Click "Setup Guide" in the extension for help.

---

## File Cheat Sheet

| File | Purpose | When to Edit |
|------|---------|--------------|
| `user_profile.yaml` | Your personal info, skills, experience | Update as you gain skills |
| `qa_databank.yaml` | Your standard answers to common questions | Add questions as you encounter them |
| `job_search_config.yaml` | Job search criteria (titles, locations, etc.) | When changing job search focus |
| `.env` | API keys (SerpAPI, Anthropic) | Only once during setup |

---

## Dashboard Pages

- **Jobs** - Browse scraped jobs with fit scores
- **Settings** - View/edit your profile and configs
- **Actions** - Run job search, company research
- **History** - See which answers you've used

---

## Keyboard Shortcuts

- `Ctrl+C` - Copy (in extension, use "Copy" buttons)
- `Ctrl+V` - Paste into application form
- `Ctrl+Shift+Y` - Open JobRadar extension (if you set a Chrome shortcut)

---

## Tips

1. **Update your Q&A databank regularly** - Add new questions as you see them
2. **Check the History tab** - See which answers work best
3. **Edit answers before copying** - Customize for each job
4. **Keep backend running** - Don't close `start_jobradar.bat` while applying
5. **Use the Debug button** - If questions aren't extracted correctly

---

Full documentation: `INSTALLATION_GUIDE.md`
