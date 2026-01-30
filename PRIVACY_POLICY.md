# Privacy Policy for JobRadar Assistant

**Last Updated:** January 29, 2026
**Effective Date:** January 29, 2026

## TL;DR
- Your data stays on your device (Chrome local storage)
- No cloud servers, no data collection, no tracking
- Optional backend runs on YOUR computer (localhost)
- You can export/delete all data anytime

---

## 1. Information We Collect

### Data YOU Enter (Stored Locally Only)
- **Personal Information:** Name, email, phone, location, LinkedIn URL
- **Q&A Answers:** Your saved responses to common job questions
- **Page Content:** Text from job pages (only when you click "Copy Page Content")

### Data We DO NOT Collect
- ❌ Browsing history
- ❌ Passwords or payment info
- ❌ Data from other extensions
- ❌ Any data without your explicit action

---

## 2. How We Store Data

**100% Local Storage:**
- All data stored in Chrome's `chrome.storage.local` API on YOUR device
- Data NEVER leaves your computer unless you enable optional features
- No remote servers (ours or third-party)
- No cloud sync (unless you manually enable backend)

**Optional Backend (Your Choice):**
- Requires explicit setup (not enabled by default)
- Runs on YOUR computer (`localhost:5000`)
- Data still stays local, just in Python backend instead of browser
- You control when it runs

---

## 3. How We Use Data

**Auto-Fill Answers:**
- Match questions on job pages to your saved answers
- All matching happens locally in your browser

**Track Usage (Optional):**
- Count questions extracted, answers copied
- Used to show "most used" answers in settings
- You can disable in Settings → Data & Privacy

---

## 4. Data Sharing

**We share ZERO data. Period.**

**Third-Party Services:**
- None by default
- If you manually add API keys:
  - SerpAPI (job scraping) - requires YOUR API key
  - Anthropic Claude (CV parsing) - requires YOUR API key
  - Both are opt-in and require explicit setup

---

## 5. Your Rights (GDPR-Style)

**Access:** View all your data in Settings → Data & Privacy
**Export:** Download all data as JSON
**Delete:** Clear all data in Settings → Reset
**Uninstall:** Removing extension deletes all local data automatically

---

## 6. Data Retention

**We keep data:** Forever (until you delete it)
**You control data:** Export, delete, or clear anytime
**Uninstall:** All data deleted automatically when you remove extension

---

## 7. Children's Privacy

JobRadar is not intended for users under 13. We do not knowingly collect data from children.

---

## 8. Changes to Privacy Policy

We may update this policy. Changes will be posted with a new "Last Updated" date.

---

## 9. Contact Us

**Questions or concerns?**
Open an issue: https://github.com/yourusername/JobRadar/issues
Email: contact@jobradar.example.com

---

**By using JobRadar, you agree to this Privacy Policy.**
