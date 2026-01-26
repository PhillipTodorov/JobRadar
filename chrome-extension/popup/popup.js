// Job Application Assistant - Side Panel Script

const API_URL = 'http://localhost:5000';
let pageContent = '';
let sourceTabId = null;

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
  const saved = await chrome.storage.local.get(['pageContent', 'answers']);

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

  try {
    const response = await fetch(`${API_URL}/api/parse-and-answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pageText: pageContent,
        context: {}
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    displayAnswers(data.answers);
    setStatus('Done!');

    // Save answers to storage
    await chrome.storage.local.set({ answers: data.answers });

  } catch (e) {
    console.error('Parse error:', e);
    setStatus('Error');
    showError(`Failed to connect to backend: ${e.message}`);
  }

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

    card.innerHTML = `
      <div class="question">
        <span class="question-num">Q${index + 1}:</span>
        ${escapeHtml(item.question)}
      </div>
      <div class="answer">
        <textarea id="${textareaId}" placeholder="Type your answer here...">${isFromDatabank ? escapeHtml(item.answer) : ''}</textarea>
      </div>
      <div class="meta">
        <span class="source ${item.source}">${isFromDatabank ? 'From Databank' : 'Not in Databank'}</span>
        <button class="btn btn-small copy-btn" data-textarea="${textareaId}">Copy</button>
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

      if (!answer.trim()) {
        e.target.textContent = 'Empty!';
        setTimeout(() => {
          e.target.textContent = 'Copy';
        }, 1500);
        return;
      }

      try {
        await navigator.clipboard.writeText(answer);
        e.target.textContent = 'Copied!';
        setTimeout(() => {
          e.target.textContent = 'Copy';
        }, 1500);
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
