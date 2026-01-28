/**
 * JobRadar Settings - Q&A Management
 * Complete rewrite for standalone-first architecture
 */

const API_URL = 'http://localhost:5000';

// Global state
let currentDatabank = null;
let currentEditingQuestion = null;
let allQuestions = [];

// DOM Elements
const backBtn = document.getElementById('backBtn');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Personal Info form
const personalInfoForm = document.getElementById('personalInfoForm');

// Q&A Bank elements
const qaSearch = document.getElementById('qaSearch');
const addQABtn = document.getElementById('addQABtn');
const qaList = document.getElementById('qaList');
const qaModal = document.getElementById('qaModal');
const modalTitle = document.getElementById('modalTitle');
const qaForm = document.getElementById('qaForm');
const cancelModal = document.getElementById('cancelModal');

// Import/Export elements
const exportBtn = document.getElementById('exportBtn');
const importBtn = document.getElementById('importBtn');
const importFile = document.getElementById('importFile');
const syncFromBackendBtn = document.getElementById('syncFromBackendBtn');

// Backend status elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const refreshBtn = document.getElementById('refreshBtn');
const backendSettingsForm = document.getElementById('backendSettingsForm');

// =====================
// Initialization
// =====================

initialize();

async function initialize() {
  // Load databank
  await loadDatabank();

  // Check backend status
  checkBackendStatus();

  // Set up event listeners
  setupEventListeners();

  // Populate UI
  populatePersonalInfoForm();
  populateQAList(allQuestions);
  loadBackendSettings();
}

function setupEventListeners() {
  // Back button
  backBtn.addEventListener('click', () => {
    window.location.href = 'popup.html';
  });

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      switchTab(targetTab);
    });
  });

  // Personal Info form
  personalInfoForm.addEventListener('submit', handlePersonalInfoSubmit);

  // Q&A Bank
  qaSearch.addEventListener('input', handleSearch);
  addQABtn.addEventListener('click', openAddModal);
  cancelModal.addEventListener('click', closeModal);
  qaForm.addEventListener('submit', handleQAFormSubmit);

  // Import/Export
  exportBtn.addEventListener('click', exportDatabank);
  importBtn.addEventListener('click', () => importFile.click());
  importFile.addEventListener('change', handleImportFile);
  syncFromBackendBtn.addEventListener('click', syncFromBackend);

  // Backend settings
  refreshBtn.addEventListener('click', checkBackendStatus);
  backendSettingsForm.addEventListener('submit', handleBackendSettingsSubmit);
}

// =====================
// Tab Management
// =====================

function switchTab(tabName) {
  // Update tab buttons
  tabBtns.forEach(btn => {
    if (btn.dataset.tab === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update tab contents
  tabContents.forEach(content => {
    if (content.id === `tab-${tabName}`) {
      content.classList.add('active');
    } else {
      content.classList.remove('active');
    }
  });
}

// =====================
// Databank Management
// =====================

async function loadDatabank() {
  const storage = await chrome.storage.local.get(['qa_databank']);
  currentDatabank = storage.qa_databank || createEmptyDatabank();
  allQuestions = Object.entries(currentDatabank.questions || {});
  return currentDatabank;
}

async function saveDatabank() {
  currentDatabank.last_updated = new Date().toISOString();
  await chrome.storage.local.set({ qa_databank: currentDatabank });

  // Sync to backend if enabled
  const settings = await loadSettings();
  if (settings.backend_enabled && settings.auto_sync) {
    syncToBackend();
  }
}

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

// =====================
// Personal Info
// =====================

function populatePersonalInfoForm() {
  const personalInfo = currentDatabank.personal_info || {};

  const form = personalInfoForm;
  form.elements['full_name'].value = personalInfo.full_name || '';
  form.elements['email'].value = personalInfo.email || '';
  form.elements['phone'].value = personalInfo.phone || '';
  form.elements['location'].value = personalInfo.location || '';
  form.elements['linkedin'].value = personalInfo.linkedin || '';
}

async function handlePersonalInfoSubmit(e) {
  e.preventDefault();

  const formData = new FormData(personalInfoForm);

  currentDatabank.personal_info = {
    full_name: formData.get('full_name'),
    email: formData.get('email'),
    phone: formData.get('phone'),
    location: formData.get('location'),
    linkedin: formData.get('linkedin')
  };

  await saveDatabank();

  alert('Personal information saved!');
}

// =====================
// Q&A Bank Management
// =====================

function populateQAList(questions) {
  if (!questions || questions.length === 0) {
    qaList.innerHTML = '<p class="no-results">No questions added yet. Click "+ Add Question" to get started.</p>';
    return;
  }

  qaList.innerHTML = '';

  questions.forEach(([question, answer]) => {
    const qaItem = createQAItem(question, answer);
    qaList.appendChild(qaItem);
  });
}

function createQAItem(question, answer) {
  const item = document.createElement('div');
  item.className = 'qa-item';

  const content = document.createElement('div');
  content.className = 'qa-item-content';

  const questionEl = document.createElement('div');
  questionEl.className = 'qa-item-question';
  questionEl.textContent = question;

  const answerEl = document.createElement('div');
  answerEl.className = 'qa-item-answer';
  answerEl.textContent = answer || '[No answer]';

  content.appendChild(questionEl);
  content.appendChild(answerEl);

  const actions = document.createElement('div');
  actions.className = 'qa-item-actions';

  const editBtn = document.createElement('button');
  editBtn.className = 'btn btn-small';
  editBtn.textContent = 'Edit';
  editBtn.onclick = () => openEditModal(question, answer);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'btn btn-small';
  deleteBtn.textContent = 'Delete';
  deleteBtn.onclick = () => deleteQAEntry(question);

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);

  item.appendChild(content);
  item.appendChild(actions);

  return item;
}

function handleSearch(e) {
  const searchTerm = e.target.value.toLowerCase().trim();

  if (!searchTerm) {
    populateQAList(allQuestions);
    return;
  }

  const filtered = allQuestions.filter(([question, answer]) => {
    return question.toLowerCase().includes(searchTerm) ||
           (answer && answer.toLowerCase().includes(searchTerm));
  });

  populateQAList(filtered);
}

function openAddModal() {
  currentEditingQuestion = null;
  modalTitle.textContent = 'Add Question';
  qaForm.elements['question'].value = '';
  qaForm.elements['answer'].value = '';
  qaModal.classList.remove('hidden');
  qaForm.elements['question'].focus();
}

function openEditModal(question, answer) {
  currentEditingQuestion = question;
  modalTitle.textContent = 'Edit Question';
  qaForm.elements['question'].value = question;
  qaForm.elements['answer'].value = answer || '';
  qaModal.classList.remove('hidden');
  qaForm.elements['question'].focus();
}

function closeModal() {
  qaModal.classList.add('hidden');
  currentEditingQuestion = null;
}

async function handleQAFormSubmit(e) {
  e.preventDefault();

  const formData = new FormData(qaForm);
  const question = formData.get('question').trim();
  const answer = formData.get('answer').trim();

  if (!question || !answer) {
    alert('Both question and answer are required.');
    return;
  }

  // If editing, delete old question first (if question text changed)
  if (currentEditingQuestion && currentEditingQuestion !== question) {
    delete currentDatabank.questions[currentEditingQuestion];
  }

  // Add/update question
  currentDatabank.questions[question] = answer;

  await saveDatabank();

  // Reload list
  await loadDatabank();
  populateQAList(allQuestions);

  // Reset search
  qaSearch.value = '';

  closeModal();
}

async function deleteQAEntry(question) {
  if (!confirm(`Delete this question?\n\n"${question}"`)) {
    return;
  }

  delete currentDatabank.questions[question];
  await saveDatabank();

  // Reload list
  await loadDatabank();
  populateQAList(allQuestions);
}

// =====================
// Import/Export
// =====================

async function exportDatabank() {
  const json = JSON.stringify(currentDatabank, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `jobradar-qa-${new Date().toISOString().split('T')[0]}.json`;
  a.click();

  URL.revokeObjectURL(url);

  alert('Q&A databank exported successfully!');
}

async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const databank = JSON.parse(text);

    // Validate structure
    if (!databank.questions || typeof databank.questions !== 'object') {
      throw new Error('Invalid databank format: missing "questions" object');
    }

    // Confirm overwrite
    if (!confirm('This will replace your current Q&A data. Continue?')) {
      importFile.value = ''; // Reset file input
      return;
    }

    // Set version and timestamp
    databank.version = '1.0';
    databank.last_updated = new Date().toISOString();

    // Save
    currentDatabank = databank;
    await saveDatabank();

    // Reload UI
    await loadDatabank();
    populatePersonalInfoForm();
    populateQAList(allQuestions);

    alert('Q&A data imported successfully!');
  } catch (e) {
    alert(`Import failed: ${e.message}`);
  }

  importFile.value = ''; // Reset file input
}

async function syncFromBackend() {
  try {
    const response = await fetch(`${API_URL}/api/qa-databank`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const backendData = await response.json();

    // Confirm import
    const questionCount = Object.keys(backendData.questions || {}).length;
    if (!confirm(`Found ${questionCount} Q&A entries on backend. Import them?`)) {
      return;
    }

    // Save to storage
    currentDatabank = backendData;
    await saveDatabank();

    // Reload UI
    await loadDatabank();
    populatePersonalInfoForm();
    populateQAList(allQuestions);

    alert('Q&A data synced from backend successfully!');
  } catch (e) {
    alert(`Sync failed: ${e.message}\n\nMake sure the backend is running.`);
  }
}

async function syncToBackend() {
  const settings = await loadSettings();

  try {
    const response = await fetch(`${settings.backend_url}/api/qa-databank`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentDatabank),
      signal: AbortSignal.timeout(3000)
    });

    if (response.ok) {
      console.log('Synced to backend successfully');
      currentDatabank.last_synced_with_backend = new Date().toISOString();
      await chrome.storage.local.set({ qa_databank: currentDatabank });
    }
  } catch (e) {
    console.log('Backend sync failed (will retry later):', e.message);
  }
}

// =====================
// Backend Settings
// =====================

async function checkBackendStatus() {
  statusIndicator.className = 'status-indicator checking';
  statusText.textContent = 'Checking...';

  try {
    const response = await fetch(`${API_URL}/api/health`, {
      signal: AbortSignal.timeout(3000)
    });

    if (response.ok) {
      statusIndicator.className = 'status-indicator connected';
      statusText.textContent = 'Connected ✓';
    } else {
      throw new Error('Backend error');
    }
  } catch (e) {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = 'Not running (extension works standalone)';
  }
}

async function loadSettings() {
  const storage = await chrome.storage.local.get(['settings']);
  return storage.settings || {
    backend_url: 'http://localhost:5000',
    backend_enabled: true,
    auto_sync: true
  };
}

async function loadBackendSettings() {
  const settings = await loadSettings();

  const form = backendSettingsForm;
  form.elements['backend_url'].value = settings.backend_url;
  form.elements['backend_enabled'].checked = settings.backend_enabled;
  form.elements['auto_sync'].checked = settings.auto_sync;
}

async function handleBackendSettingsSubmit(e) {
  e.preventDefault();

  const formData = new FormData(backendSettingsForm);

  const settings = {
    backend_url: formData.get('backend_url'),
    backend_enabled: formData.get('backend_enabled') === 'on',
    auto_sync: formData.get('auto_sync') === 'on'
  };

  await chrome.storage.local.set({ settings });

  alert('Backend settings saved!');

  // Refresh status
  checkBackendStatus();
}
