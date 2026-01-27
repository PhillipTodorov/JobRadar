"""Flask API for Job Application Assistant Chrome Extension.

Receives raw page text, extracts questions using AI, matches against
qa_databank.yaml, and generates answers for unmatched questions.

Run with: python answer_questions_api.py
"""

import json
import os
import re
import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.parse_cv import find_cv, parse_docx

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)
CORS(app)  # Allow requests from Chrome extension

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
QA_DATABANK_PATH = PROJECT_ROOT / "qa_databank.yaml"
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
ANSWER_HISTORY_PATH = PROJECT_ROOT / ".tmp" / "answer_usage_history.json"


def load_yaml(path):
    """Load YAML file safely."""
    import yaml
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_qa_databank():
    """Load Q&A databank."""
    return load_yaml(QA_DATABANK_PATH)


def load_profile():
    """Load user profile."""
    return load_yaml(PROFILE_PATH)


def load_cv_text():
    """Load CV text if available."""
    cv_path = find_cv()
    if cv_path:
        return parse_docx(cv_path)
    return ""


def load_answer_history():
    """Load answer usage history."""
    if ANSWER_HISTORY_PATH.exists():
        try:
            with open(ANSWER_HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    return []


def save_answer_history(history):
    """Save answer usage history."""
    try:
        # Ensure .tmp directory exists
        ANSWER_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANSWER_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving history: {e}")
        return False


def calculate_similarity(text1, text2):
    """Calculate simple word overlap similarity."""
    def normalize(text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return set(text.split())

    words1 = normalize(text1)
    words2 = normalize(text2)

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def match_to_databank(question, databank):
    """Try to match question against Q&A databank.

    Returns:
        tuple: (answer, similarity_score) or (None, 0) if no match
    """
    questions = databank.get("questions", {})
    personal_info = databank.get("personal_info", {})
    salary_info = databank.get("salary", {})
    work_auth = databank.get("work_authorization", {})

    best_match = None
    best_score = 0
    threshold = 0.3  # Lower threshold for broader matching

    # Check against stored questions
    for stored_q, answer in questions.items():
        if not answer:  # Skip empty answers
            continue
        score = calculate_similarity(question, stored_q)
        if score > best_score and score > threshold:
            best_score = score
            best_match = answer

    # Check for common patterns
    q_lower = question.lower()

    # Name patterns
    full_name = personal_info.get("full_name", "")
    if full_name:
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        # First name only
        if any(x in q_lower for x in ["first name"]) and "last" not in q_lower:
            return first_name, 1.0

        # Last name only
        if any(x in q_lower for x in ["last name", "surname", "family name"]):
            return last_name, 1.0

        # Full name
        if any(x in q_lower for x in ["your name", "full name", "name"]):
            return full_name, 1.0

    # Email patterns
    if any(x in q_lower for x in ["email", "e-mail"]):
        if personal_info.get("email"):
            return personal_info["email"], 1.0

    # Phone patterns
    if any(x in q_lower for x in ["phone", "telephone", "mobile", "contact number"]):
        if personal_info.get("phone"):
            return personal_info["phone"], 1.0

    # Location patterns
    if any(x in q_lower for x in ["location", "address", "city", "where do you live"]):
        if personal_info.get("location"):
            return personal_info["location"], 1.0

    # LinkedIn patterns
    if "linkedin" in q_lower:
        if personal_info.get("linkedin"):
            return personal_info["linkedin"], 1.0

    # Salary patterns
    if any(x in q_lower for x in ["salary", "compensation", "pay", "wage", "expected"]):
        if salary_info.get("expected_salary"):
            return salary_info["expected_salary"], 1.0

    # Work authorization patterns
    if any(x in q_lower for x in ["work in uk", "eligible to work", "right to work", "authorization"]):
        if work_auth.get("eligible_to_work_uk"):
            return work_auth["eligible_to_work_uk"], 1.0

    # Sponsorship patterns
    if any(x in q_lower for x in ["sponsor", "visa"]):
        if work_auth.get("require_sponsorship"):
            return work_auth["require_sponsorship"], 1.0

    # Notice period patterns
    if any(x in q_lower for x in ["notice period", "start date", "when can you start"]):
        if work_auth.get("notice_period"):
            return work_auth["notice_period"], 1.0

    return best_match, best_score


def _build_extraction_prompt(page_text):
    """Build the Claude prompt for question extraction."""
    return f"""Extract form field labels from this job application page.

CRITICAL RULES:
1. ONLY extract text that is EXPLICITLY WRITTEN in the page text below
2. DO NOT infer, guess, or add common fields that are not present
3. If a field label is not literally in the text, DO NOT include it

Look for form field labels like:
- Input labels (e.g., "First Name", "Email", "Phone")
- Questions asking the applicant for input (e.g., "Why are you interested?")
- Required field indicators with labels

DO NOT include:
- Job requirements, qualifications, or skills
- Job descriptions or responsibilities
- Company information
- Navigation or button text
- Any text that describes the job rather than asks for applicant input

If you only see 3-4 form fields in the text, return only those 3-4 fields. Do not pad the list with expected fields.

Return ONLY a JSON array of the exact field labels found. No explanations.

Page text:
{page_text[:8000]}"""


def extract_questions_with_ai(page_text):
    """Use Claude to extract questions from raw page text."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        # Fallback: simple regex extraction
        return extract_questions_regex(page_text)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = _build_extraction_prompt(page_text)

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Parse JSON response - handle markdown code blocks
        if response_text.startswith("```"):
            response_text = re.sub(r'^```\w*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        questions = json.loads(response_text)
        return questions if isinstance(questions, list) else []

    except Exception as e:
        print(f"AI extraction failed: {e}")
        return extract_questions_regex(page_text)


def extract_questions_regex(page_text):
    """Fallback: extract questions using regex patterns. Very conservative."""
    questions = []

    # Only match questions that are clearly asking the user for input
    # Avoid matching job requirements or descriptions
    question_patterns = [
        # Direct questions to applicant
        r'(Why (?:are you|do you want)[^.?\n]{10,100}\?)',
        r'(What (?:is your|are your)[^.?\n]{5,80}\?)',
        r'(Do you (?:have|require|need)[^.?\n]{5,60}\?)',
        r'(Are you (?:authorized|eligible|willing)[^.?\n]{5,60}\?)',
        r'(Tell us about (?:yourself|your)[^.?\n]{5,60})',
        r'(Describe your [^.?\n]{5,60})',
        r'(Please (?:provide|describe|explain) [^.?\n]{5,60})',
    ]

    for pattern in question_patterns:
        matches = re.findall(pattern, page_text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            match = match.strip()
            # Filter out job description phrases
            if not is_job_description(match):
                if match and match not in questions:
                    questions.append(match)

    # Common form field labels - only exact matches
    form_fields = [
        'First Name', 'Last Name', 'Full Name', 'Email', 'Email Address',
        'Phone', 'Phone Number', 'Mobile Number', 'Address', 'City',
        'Postcode', 'Post Code', 'Zip Code', 'Country', 'LinkedIn',
        'Expected Salary', 'Current Salary', 'Notice Period', 'Start Date',
        'Cover Letter', 'Resume', 'CV'
    ]

    text_lower = page_text.lower()
    for field in form_fields:
        if field.lower() in text_lower and field not in questions:
            questions.append(field)

    # Deduplicate
    seen = set()
    unique = []
    for q in questions:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique[:15]  # Typical form has 5-15 fields


def is_job_description(text):
    """Check if text looks like job description rather than a form field."""
    text_lower = text.lower()
    # Phrases that indicate job requirements, not form fields
    job_desc_phrases = [
        'experience with', 'experience in', 'knowledge of', 'proficiency in',
        'ability to', 'responsible for', 'you will', 'we are looking',
        'the ideal candidate', 'requirements', 'qualifications',
        'must have', 'should have', 'preferred', 'required',
        'years of experience', 'degree in', 'background in',
        'skills in', 'familiarity with', 'understanding of'
    ]
    return any(phrase in text_lower for phrase in job_desc_phrases)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Backend is running"})


@app.route('/api/track-answer', methods=['POST'])
def track_answer():
    """Save answer usage tracking data."""
    data = request.json

    # Required fields
    required = ['question', 'answer', 'source']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    # Load existing history
    history = load_answer_history()

    # Create tracking entry
    from datetime import datetime
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question": data['question'],
        "answer": data['answer'],
        "source": data['source'],  # 'databank' or 'custom'
        "was_edited": data.get('was_edited', False),
        "job_url": data.get('job_url', ''),
        "job_title": data.get('job_title', ''),
        "company": data.get('company', ''),
        "outcome": None  # Can be updated later
    }

    # Add to history
    history.append(entry)

    # Keep only last 1000 entries to prevent file bloat
    if len(history) > 1000:
        history = history[-1000:]

    # Save
    if save_answer_history(history):
        return jsonify({"status": "success", "message": "Answer tracked"})
    else:
        return jsonify({"error": "Failed to save history"}), 500


@app.route('/api/answer-history', methods=['GET'])
def get_answer_history():
    """Get answer usage history."""
    history = load_answer_history()

    # Return most recent first
    history.reverse()

    # Optional filtering by query params
    limit = request.args.get('limit', type=int, default=100)

    return jsonify({
        "history": history[:limit],
        "total": len(history)
    })


@app.route('/api/debug/extract-questions', methods=['POST'])
def debug_extract_questions():
    """Debug endpoint: show raw extraction results without generating answers."""
    data = request.json
    page_text = data.get('pageText', '')

    if not page_text:
        return jsonify({"error": "No page text provided"}), 400

    # Extract using AI
    ai_questions = []
    ai_error = None
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            prompt = _build_extraction_prompt(page_text)

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            if response_text.startswith("```"):
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            ai_questions = json.loads(response_text)
    except Exception as e:
        ai_error = str(e)

    # Extract using regex (always run for comparison)
    regex_questions = extract_questions_regex(page_text)

    return jsonify({
        "page_text_length": len(page_text),
        "page_text_preview": page_text[:500] + "..." if len(page_text) > 500 else page_text,
        "ai_extraction": {
            "questions": ai_questions,
            "count": len(ai_questions),
            "error": ai_error
        },
        "regex_extraction": {
            "questions": regex_questions,
            "count": len(regex_questions)
        },
        "method_used": "ai" if ai_questions and not ai_error else "regex"
    })


@app.route('/api/parse-and-answer', methods=['POST'])
def parse_and_answer():
    """Main endpoint: extract questions and generate answers."""
    data = request.json
    page_text = data.get('pageText', '')
    context = data.get('context', {})

    if not page_text:
        return jsonify({"error": "No page text provided", "answers": []}), 400

    # Load data sources
    databank = load_qa_databank()
    profile = load_profile()
    cv_text = load_cv_text()

    # Build context for AI generation
    ai_context = {
        "profile": profile,
        "cv_text": cv_text,
        **context
    }

    # Extract questions from page
    questions = extract_questions_with_ai(page_text)

    # Filter out anything that looks like job description content
    questions = [q for q in questions if not is_job_description(q)]

    # Sanity check: if we have way too many "questions", something is wrong
    # A typical application form has 5-15 fields
    if len(questions) > 20:
        print(f"Warning: Found {len(questions)} questions, likely extracting job description. Limiting to 15.")
        questions = questions[:15]

    if not questions:
        return jsonify({
            "answers": [],
            "message": "No questions found on page"
        })

    # Process each question
    # Strategy: ONLY match against databank (no AI generation for cost savings)
    # User can edit answers in the extension before copying
    answers = []
    for question in questions:
        match, score = match_to_databank(question, databank)

        if match and score > 0.3:
            # Found a good match in databank
            answers.append({
                "question": question,
                "answer": match,
                "source": "databank",
                "confidence": score
            })
        else:
            # No match - user can type answer in extension
            answers.append({
                "question": question,
                "answer": "[No answer in databank - add this question to Q&A Databank]",
                "source": "not_found",
                "confidence": 0
            })

    return jsonify({
        "answers": answers,
        "total_questions": len(questions),
        "from_databank": len([a for a in answers if a["source"] == "databank"]),
        "not_found": len([a for a in answers if a["source"] == "not_found"])
    })


if __name__ == '__main__':
    print("=" * 50)
    print("Job Application Assistant API")
    print("=" * 50)
    print(f"Q&A Databank: {QA_DATABANK_PATH}")
    print(f"User Profile: {PROFILE_PATH}")
    print()
    print("Starting server on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    app.run(host='127.0.0.1', port=5000, debug=True)
