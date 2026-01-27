"""Test question extraction - Regex vs AI comparison."""
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from answer_questions_api import extract_questions_regex, extract_questions_with_ai

# Sample job application page texts
SAMPLE_PAGES = [
    # Sample 1: Workday-style form
    """
    Job Application - Software Engineer

    Personal Information
    First Name *
    Last Name *
    Email Address *
    Phone Number *
    Location (City, Country) *

    Work Authorization
    Are you eligible to work in the UK? *
    Do you require visa sponsorship? *

    Professional Information
    LinkedIn Profile URL
    GitHub Profile URL
    Portfolio Website

    Additional Questions
    Why are you interested in this role?
    What makes you a good fit for our company?
    When can you start?
    What is your expected salary?

    Submit Application
    """,

    # Sample 2: Greenhouse-style form
    """
    Apply for Senior Backend Developer

    Contact Information
    Full Name *
    Email *
    Phone *
    Current Location *

    Resume *
    Drop files here or click to upload

    Cover Letter (Optional)

    Questions
    1. Do you have experience with Python and Django? *
    2. How many years of backend development experience do you have? *
    3. Are you authorized to work in the United States? *
    4. What is your notice period or availability date? *

    Additional Information
    How did you hear about this position?

    Privacy Policy
    By submitting this application, you agree to our terms.
    """,

    # Sample 3: Lever-style form with embedded questions
    """
    Backend Engineer - Apply Now

    Personal Details
    Name *
    Email address *
    Phone *
    Current company
    LinkedIn

    Application Questions
    Why do you want to work at TechCorp? *
    (Please describe your motivation in 2-3 sentences)

    What's your biggest technical achievement? *
    (Share a project you're proud of)

    Do you have experience with:
    - Microservices architecture
    - Docker/Kubernetes
    - AWS or GCP

    Availability
    When can you start? *
    Notice period: *

    Compensation
    Expected salary (annual): *

    Submit Your Application
    """
]

def test_extraction():
    """Test regex extraction on sample pages."""
    print("=" * 80)
    print("REGEX EXTRACTION TEST")
    print("=" * 80)
    print()

    for i, page in enumerate(SAMPLE_PAGES, 1):
        print(f"\n{'=' * 80}")
        print(f"SAMPLE {i}")
        print('=' * 80)
        print(f"Page length: {len(page)} characters")
        print()

        # Extract with regex
        questions = extract_questions_regex(page)

        print(f"Questions found: {len(questions)}")
        print()

        for j, question in enumerate(questions, 1):
            print(f"  {j}. {question}")

        print()

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("""
The regex extractor looks for:
1. Common form field labels (First Name, Email, etc.)
2. Direct questions ending with "?"
3. Patterns like "Why...", "What...", "Do you...", etc.

Pros:
- Fast and free (no API costs)
- Works offline
- No rate limits

Cons:
- May miss unconventional field labels
- Can't understand context
- Fixed patterns only

For most job applications, regex should work well because forms use
standard labels. AI extraction is more flexible but costs money per request.

RECOMMENDATION: Start with regex, add AI extraction as optional upgrade.
""")

if __name__ == "__main__":
    test_extraction()
