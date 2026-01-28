/**
 * Local Q&A matching module for JobRadar Chrome extension.
 * Ported from Python (tools/answer_questions_api.py calculate_similarity and match_to_databank functions).
 *
 * This module matches extracted questions against the user's Q&A databank.
 * Works completely offline without backend dependency.
 */

/**
 * Calculate word overlap similarity between two texts.
 * @param {string} text1 - First text
 * @param {string} text2 - Second text
 * @returns {number} - Similarity score (0.0 to 1.0)
 */
export function calculateSimilarity(text1, text2) {
  /**
   * Normalize text by removing punctuation and converting to lowercase.
   * @param {string} text - Text to normalize
   * @returns {Set<string>} - Set of normalized words
   */
  const normalize = (text) => {
    const cleaned = text.toLowerCase().replace(/[^\w\s]/g, '');
    return new Set(cleaned.split(/\s+/).filter(w => w.length > 0));
  };

  const words1 = normalize(text1);
  const words2 = normalize(text2);

  if (words1.size === 0 || words2.size === 0) {
    return 0.0;
  }

  // Calculate Jaccard similarity (intersection over union)
  const intersection = new Set([...words1].filter(w => words2.has(w)));
  const union = new Set([...words1, ...words2]);

  return intersection.size / union.size;
}

/**
 * Match question against Q&A databank.
 * @param {string} question - Question to match
 * @param {Object} databank - Q&A databank structure
 * @returns {Object} - { answer: string|null, score: number, source: string }
 */
export function matchToDatabank(question, databank) {
  const questions = databank.questions || {};
  const personalInfo = databank.personal_info || {};
  const salaryInfo = databank.salary || {};
  const workAuth = databank.work_authorization || {};

  let bestMatch = null;
  let bestScore = 0;
  const threshold = 0.3; // Lower threshold for broader matching

  // 1. Check against stored questions (fuzzy matching)
  for (const [storedQ, answer] of Object.entries(questions)) {
    if (!answer) {
      continue; // Skip empty answers
    }

    const score = calculateSimilarity(question, storedQ);
    if (score > bestScore && score > threshold) {
      bestScore = score;
      bestMatch = answer;
    }
  }

  const qLower = question.toLowerCase();

  // 2. Check personal info patterns (exact matches)

  // Name patterns
  const fullName = personalInfo.full_name || '';
  if (fullName) {
    const nameParts = fullName.split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';

    // First name only
    if (qLower.includes('first name') && !qLower.includes('last')) {
      return { answer: firstName, score: 1.0, source: 'personal_info' };
    }

    // Last name only
    if (qLower.includes('last name') || qLower.includes('surname') || qLower.includes('family name')) {
      return { answer: lastName, score: 1.0, source: 'personal_info' };
    }

    // Full name
    if (qLower.includes('your name') || qLower.includes('full name') || (qLower === 'name' && qLower.length < 10)) {
      return { answer: fullName, score: 1.0, source: 'personal_info' };
    }
  }

  // Email patterns
  if (qLower.includes('email') || qLower.includes('e-mail')) {
    if (personalInfo.email) {
      return { answer: personalInfo.email, score: 1.0, source: 'personal_info' };
    }
  }

  // Phone patterns
  if (qLower.includes('phone') || qLower.includes('telephone') || qLower.includes('mobile') || qLower.includes('contact number')) {
    if (personalInfo.phone) {
      return { answer: personalInfo.phone, score: 1.0, source: 'personal_info' };
    }
  }

  // Location patterns
  if (qLower.includes('location') || qLower.includes('address') || qLower.includes('city') || qLower.includes('where do you live')) {
    if (personalInfo.location) {
      return { answer: personalInfo.location, score: 1.0, source: 'personal_info' };
    }
  }

  // LinkedIn patterns
  if (qLower.includes('linkedin')) {
    if (personalInfo.linkedin) {
      return { answer: personalInfo.linkedin, score: 1.0, source: 'personal_info' };
    }
  }

  // Salary patterns
  if (qLower.includes('salary') || qLower.includes('compensation') || qLower.includes('pay') || qLower.includes('wage') || qLower.includes('expected')) {
    if (salaryInfo.expected_salary) {
      return { answer: salaryInfo.expected_salary, score: 1.0, source: 'salary' };
    }
  }

  // Work authorization patterns
  if (qLower.includes('work in uk') || qLower.includes('eligible to work') || qLower.includes('right to work') || qLower.includes('authorization')) {
    if (workAuth.eligible_to_work_uk) {
      return { answer: workAuth.eligible_to_work_uk, score: 1.0, source: 'work_auth' };
    }
  }

  // Sponsorship patterns
  if (qLower.includes('sponsor') || qLower.includes('visa')) {
    if (workAuth.require_sponsorship) {
      return { answer: workAuth.require_sponsorship, score: 1.0, source: 'work_auth' };
    }
  }

  // Notice period patterns
  if (qLower.includes('notice period') || qLower.includes('start date') || qLower.includes('when can you start')) {
    if (workAuth.notice_period) {
      return { answer: workAuth.notice_period, score: 1.0, source: 'work_auth' };
    }
  }

  // Return best match from stored questions or null
  if (bestMatch && bestScore > threshold) {
    return { answer: bestMatch, score: bestScore, source: 'databank' };
  }

  return { answer: null, score: 0, source: 'not_found' };
}
