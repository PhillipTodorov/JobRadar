/**
 * Local question extraction module for JobRadar Chrome extension.
 * Ported from Python (tools/answer_questions_api.py extract_questions_regex function).
 *
 * This module extracts questions from job application pages using regex patterns.
 * Works completely offline without backend dependency.
 */

/**
 * Extract questions from job application page text using regex patterns.
 * @param {string} pageText - Full page text content
 * @returns {string[]} - Array of extracted questions (max 15)
 */
export function extractQuestionsRegex(pageText) {
  const questions = [];

  // Direct questions to applicant
  // Only match questions that are clearly asking the user for input
  const questionPatterns = [
    /Why (?:are you|do you want)[^.?\n]{10,100}\?/gi,
    /What (?:is your|are your)[^.?\n]{5,80}\?/gi,
    /Do you (?:have|require|need)[^.?\n]{5,60}\?/gi,
    /Are you (?:authorized|eligible|willing)[^.?\n]{5,60}\?/gi,
    /Tell us about (?:yourself|your)[^.?\n]{5,60}/gi,
    /Describe your [^.?\n]{5,60}/gi,
    /Please (?:provide|describe|explain) [^.?\n]{5,60}/gi,
  ];

  // Extract matches from question patterns
  for (const pattern of questionPatterns) {
    const matches = pageText.matchAll(pattern);
    for (const match of matches) {
      const question = match[0].trim();

      // Filter out job description phrases
      if (!isJobDescription(question) && !questions.includes(question)) {
        questions.push(question);
      }
    }
  }

  // Common form field labels - only exact matches
  const formFields = [
    'First Name', 'Last Name', 'Full Name', 'Email', 'Email Address',
    'Phone', 'Phone Number', 'Mobile Number', 'Address', 'City',
    'Postcode', 'Post Code', 'Zip Code', 'Country', 'LinkedIn',
    'Expected Salary', 'Current Salary', 'Notice Period', 'Start Date',
    'Cover Letter', 'Resume', 'CV'
  ];

  const textLower = pageText.toLowerCase();
  for (const field of formFields) {
    if (textLower.includes(field.toLowerCase()) && !questions.includes(field)) {
      questions.push(field);
    }
  }

  // Deduplicate (case-insensitive)
  const seen = new Set();
  const unique = [];
  for (const q of questions) {
    const qLower = q.toLowerCase().trim();
    if (!seen.has(qLower)) {
      seen.add(qLower);
      unique.push(q);
    }
  }

  // Typical form has 5-15 fields
  return unique.slice(0, 15);
}

/**
 * Check if text looks like job description rather than a form field.
 * @param {string} text - Text to check
 * @returns {boolean} - True if likely job description
 */
function isJobDescription(text) {
  const textLower = text.toLowerCase();

  // Phrases that indicate job requirements, not form fields
  const jobDescPhrases = [
    'experience with', 'experience in', 'knowledge of', 'proficiency in',
    'ability to', 'responsible for', 'you will', 'we are looking',
    'the ideal candidate', 'requirements', 'qualifications',
    'must have', 'should have', 'preferred', 'required',
    'years of experience', 'degree in', 'background in',
    'skills in', 'familiarity with', 'understanding of'
  ];

  return jobDescPhrases.some(phrase => textLower.includes(phrase));
}
