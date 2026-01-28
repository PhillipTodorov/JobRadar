// Job Application Assistant - Side Panel Script

const API_URL = 'http://localhost:5000';
let pageContent = '';
let sourceTabId = null;

// === Q&A Databank Storage Management ===

/**
 * Load Q&A databank from Chrome storage.
 * @returns {Promise<Object>} - Q&A databank structure
 */
async function loadQADatabank() {
  const storage = await chrome.storage.local.get(['qa_databank']);
  return storage.qa_databank || createEmptyDatabank();
}

/**
 * Save Q&A databank to Chrome storage.
 * @param {Object} databank - Q&A databank to save
 */
async function saveQADatabank(databank) {
  databank.last_updated = new Date().toISOString();
  await chrome.storage.local.set({ qa_databank: databank });
}

/**
 * Create empty databank structure.
 * @returns {Object} - Empty Q&A databank
 */
function createEmptyDatabank() {
  return {
    version: '1.0',
    last_updated: new Date().toISOString(),
    personal_info: {},
    questions: {},
    salary: {},
    work_authorization: {}
  };
}

// DOM Elements
const copyPageBtn = document.getElementById('copyPageBtn');
const parseBtn = document.getElementById('parseBtn');
const debugBtn = document.getElementById('debugBtn');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const errorEl = document.getElementById('error');
const errorMessageEl = document.getElementById('errorMessage');
const answersContainer = document.getElementById('answersContainer');
const questionCountEl = document.getElementById('questionCount');
const backendStatusEl = document.getElementById('backendStatus');

// Debug elements
const debugResultsEl = document.getElementById('debugResults');
const debugPageLengthEl = document.getElementById('debugPageLength');
const debugMethodEl = document.getElementById('debugMethod');
const debugAiCountEl = document.getElementById('debugAiCount');
const debugAiQuestionsEl = document.getElementById('debugAiQuestions');
const debugRegexCountEl = document.getElementById('debugRegexCount');
const debugRegexQuestionsEl = document.getElementById('debugRegexQuestions');
const closeDebugBtn = document.getElementById('closeDebugBtn');

// Initialize on load
initialize();

// Event Listeners
copyPageBtn.addEventListener('click', copyPageContent);
parseBtn.addEventListener('click', parseAndAnswer);
debugBtn.addEventListener('click', debugExtraction);
closeDebugBtn.addEventListener('click', () => debugResultsEl.classList.add('hidden'));

async function initialize() {
  // Check backend status
  checkBackendStatus();

  // Get the current active tab
  await updateSourceTab();

  // Load saved data from storage
  const saved = await chrome.storage.local.get(['pageContent', 'answers', 'first_launch']);

  // First launch detection - show welcome message
  if (!saved.first_launch) {
    showWelcomeMessage();
    await chrome.storage.local.set({ first_launch: true });
  }

  // Restore page content and answers
  if (saved.pageContent) {
    pageContent = saved.pageContent;
    setStatus(`Restored ${pageContent.length.toLocaleString()} characters`);
    parseBtn.disabled = false;
    debugBtn.disabled = false;

    if (saved.answers && saved.answers.length > 0) {
      displayAnswers(saved.answers);
    }
  }
}

function showWelcomeMessage() {
  const welcomeEl = document.createElement('div');
  welcomeEl.className = 'welcome-banner';
  welcomeEl.style.cssText = 'background: #e3f2fd; border: 1px solid #2196f3; border-radius: 8px; padding: 16px; margin-bottom: 16px;';
  welcomeEl.innerHTML = `
    <h3 style="margin: 0 0 8px 0; color: #1976d2; font-size: 16px;">Welcome to JobRadar!</h3>
    <p style="margin: 0 0 12px 0; font-size: 14px;">Get started by adding your answers to common questions in <a href="settings.html" style="color: #1976d2;">Settings</a>.</p>
    <p style="margin: 0 0 12px 0; font-size: 14px;">Then use "Copy Page Content" on any job application to auto-fill answers.</p>
    <button id="closeWelcome" class="btn btn-small">Got it!</button>
  `;

  const container = document.querySelector('.container');
  const actions = document.querySelector('.actions');
  container.insertBefore(welcomeEl, actions);

  document.getElementById('closeWelcome').addEventListener('click', () => {
    welcomeEl.remove();
  });
}

// Get the current active tab
async function updateSourceTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      sourceTabId = tab.id;
    }
  } catch (e) {
    console.error('Failed to get active tab:', e);
  }
}

async function checkBackendStatus() {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    if (response.ok) {
      backendStatusEl.textContent = 'Connected';
      backendStatusEl.className = 'connected';
    } else {
      backendStatusEl.textContent = 'Error';
      backendStatusEl.className = 'error';
    }
  } catch (e) {
    backendStatusEl.textContent = 'Not running';
    backendStatusEl.className = 'error';
  }
}

async function copyPageContent() {
  // Always get the current active tab when copying
  await updateSourceTab();

  if (!sourceTabId) {
    showError('No active tab found. Please make sure a webpage is open.');
    return;
  }

  setStatus('Copying page content...');

  try {
    // Execute script in the source tab
    await chrome.scripting.executeScript({
      target: { tabId: sourceTabId },
      func: () => {
        document.execCommand('selectAll');
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
      }
    });

    // Read from clipboard
    pageContent = await navigator.clipboard.readText();

    if (pageContent && pageContent.length > 0) {
      setStatus(`Copied ${pageContent.length.toLocaleString()} characters`);
      parseBtn.disabled = false;
      debugBtn.disabled = false;
      hideError();

      // Save to storage
      await chrome.storage.local.set({ pageContent: pageContent });
    } else {
      setStatus('No content copied');
      showError('Could not copy page content. Try selecting text manually and copying.');
    }
  } catch (e) {
    console.error('Copy error:', e);
    setStatus('Copy failed');
    showError(`Error copying page: ${e.message}`);
  }
}

async function parseAndAnswer() {
  if (!pageContent) {
    showError('No page content. Click "Copy Page Content" first.');
    return;
  }

  setStatus('Parsing questions...');
  parseBtn.disabled = true;
  hideError();

  let answers = [];
  let usedBackend = false;

  try {
    // Try backend first with 3s timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`${API_URL}/api/parse-and-answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pageText: pageContent, context: {} }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      answers = data.answers || [];
      usedBackend = true;
      setStatus(`Done! Found ${answers.length} questions (Backend)`);
    } else {
      throw new Error(`Server error: ${response.status}`);
    }
  } catch (e) {
    // Backend unavailable - use local processing
    console.log('Backend unavailable, using local extraction:', e.message);
    setStatus('Parsing locally...');

    try {
      // Import local modules
      const { extractQuestionsRegex } = await import('./lib/extraction.js');
      const { matchToDatabank } = await import('./lib/matching.js');

      // Load Q&A databank from storage
      const databank = await loadQADatabank();

      // Extract questions locally
      const questions = extractQuestionsRegex(pageContent);

      // Match against databank
      answers = questions.map(question => {
        const { answer, score, source } = matchToDatabank(question, databank);

        if (answer && score > 0.3) {
          return {
            question,
            answer,
            source,
            confidence: score
          };
        } else {
          return {
            question,
            answer: '[No answer in databank - add in Settings]',
            source: 'not_found',
            confidence: 0
          };
        }
      });

      setStatus(`Done! Found ${answers.length} questions (Local mode)`);
    } catch (localError) {
      console.error('Local extraction error:', localError);
      setStatus('Error');
      showError(`Failed to extract questions: ${localError.message}`);
      parseBtn.disabled = false;
      return;
    }
  }

  displayAnswers(answers);
  await chrome.storage.local.set({ answers });
  parseBtn.disabled = false;
}

function displayAnswers(answers) {
  if (!answers || answers.length === 0) {
    answersContainer.innerHTML = '<p class="no-results">No questions found on this page.</p>';
    questionCountEl.textContent = '0';
    resultsEl.classList.remove('hidden');
    return;
  }

  questionCountEl.textContent = answers.length;
  answersContainer.innerHTML = '';

  answers.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'answer-card';

    const isFromDatabank = item.source === 'databank';
    const textareaId = `answer-${index}`;
    const originalAnswer = isFromDatabank ? item.answer : '';

    card.innerHTML = `
      <div class="question">
        <span class="question-num">Q${index + 1}:</span>
        ${escapeHtml(item.question)}
      </div>
      <div class="answer">
        <textarea id="${textareaId}" data-original="${escapeAttr(originalAnswer)}" placeholder="Type your answer here...">${isFromDatabank ? escapeHtml(item.answer) : ''}</textarea>
      </div>
      <div class="meta">
        <span class="source ${item.source}">${isFromDatabank ? 'From Databank' : 'Not in Databank'}</span>
        <button class="btn btn-small copy-btn" data-textarea="${textareaId}" data-question="${escapeAttr(item.question)}" data-source="${item.source}">Copy</button>
      </div>
    `;

    answersContainer.appendChild(card);
  });

  // Add copy button listeners
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const textareaId = e.target.dataset.textarea;
      const textarea = document.getElementById(textareaId);
      const answer = textarea ? textarea.value : '';
      const question = e.target.dataset.question;
      const source = e.target.dataset.source;
      const originalAnswer = textarea ? textarea.dataset.original : '';

      if (!answer.trim()) {
        e.target.textContent = 'Empty!';
        setTimeout(() => {
          e.target.textContent = 'Copy';
        }, 1500);
        return;
      }

      try {
        // Copy to clipboard
        await navigator.clipboard.writeText(answer);
        e.target.textContent = 'Copied!';
        setTimeout(() => {
          e.target.textContent = 'Copy';
        }, 1500);

        // Track answer usage
        trackAnswerUsage(question, answer, source, originalAnswer !== answer);
      } catch (err) {
        console.error('Copy failed:', err);
      }
    });
  });

  resultsEl.classList.remove('hidden');
}

function setStatus(message) {
  statusEl.textContent = message;
}

function showError(message) {
  errorMessageEl.textContent = message;
  errorEl.classList.remove('hidden');
}

function hideError() {
  errorEl.classList.add('hidden');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttr(text) {
  return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

async function trackAnswerUsage(question, answer, source, wasEdited) {
  try {
    // Get current tab info
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const jobUrl = tab ? tab.url : '';
    const jobTitle = tab ? tab.title : '';

    // Try to extract company name from title or URL
    let company = '';
    if (jobTitle) {
      // Common patterns: "Job Title at Company Name" or "Job Title - Company Name"
      const atMatch = jobTitle.match(/\sat\s+([^|\-]+)/i);
      const dashMatch = jobTitle.match(/\s-\s+([^|\-]+)/i);
      if (atMatch) {
        company = atMatch[1].trim();
      } else if (dashMatch) {
        company = dashMatch[1].trim();
      }
    }

    // Send tracking data to backend
    await fetch(`${API_URL}/api/track-answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: question,
        answer: answer,
        source: source,
        was_edited: wasEdited,
        job_url: jobUrl,
        job_title: jobTitle,
        company: company
      })
    });

    // Silently track - don't show errors to user
  } catch (err) {
    console.error('Failed to track answer:', err);
  }
}

async function debugExtraction() {
  if (!pageContent) {
    showError('No page content. Click "Copy Page Content" first.');
    return;
  }

  setStatus('Running debug extraction...');
  debugBtn.disabled = true;

  try {
    const response = await fetch(`${API_URL}/api/debug/extract-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ pageText: pageContent })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    // Update debug display
    debugPageLengthEl.textContent = data.page_text_length.toLocaleString();
    debugMethodEl.textContent = data.method_used;

    // AI questions
    debugAiCountEl.textContent = data.ai_extraction.count;
    debugAiQuestionsEl.innerHTML = '';
    if (data.ai_extraction.error) {
      debugAiQuestionsEl.innerHTML = `<li style="color: red;">Error: ${escapeHtml(data.ai_extraction.error)}</li>`;
    } else {
      data.ai_extraction.questions.forEach(q => {
        const li = document.createElement('li');
        li.textContent = q;
        debugAiQuestionsEl.appendChild(li);
      });
    }

    // Regex questions
    debugRegexCountEl.textContent = data.regex_extraction.count;
    debugRegexQuestionsEl.innerHTML = '';
    data.regex_extraction.questions.forEach(q => {
      const li = document.createElement('li');
      li.textContent = q;
      debugRegexQuestionsEl.appendChild(li);
    });

    debugResultsEl.classList.remove('hidden');
    setStatus('Debug complete');

  } catch (e) {
    console.error('Debug error:', e);
    setStatus('Debug failed');
    showError(`Debug failed: ${e.message}`);
  }

  debugBtn.disabled = false;
}
