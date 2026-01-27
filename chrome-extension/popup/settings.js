// Settings page script
const API_URL = 'http://localhost:5000';

const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const refreshBtn = document.getElementById('refreshBtn');
const backBtn = document.getElementById('backBtn');

// Check backend status
async function checkBackendStatus() {
  statusIndicator.className = 'status-indicator checking';
  statusText.textContent = 'Checking...';

  try {
    const response = await fetch(`${API_URL}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000) // 3 second timeout
    });

    if (response.ok) {
      const data = await response.json();
      statusIndicator.className = 'status-indicator connected';
      statusText.textContent = '✓ Connected - Backend is running!';
      statusText.style.color = '#10b981';
    } else {
      throw new Error('Backend returned error');
    }
  } catch (e) {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = '✗ Not connected - Please start the backend';
    statusText.style.color = '#ef4444';
  }
}

// Event listeners
refreshBtn.addEventListener('click', checkBackendStatus);
backBtn.addEventListener('click', () => {
  window.location.href = 'popup.html';
});

// Check status on load
checkBackendStatus();

// Auto-refresh every 5 seconds
setInterval(checkBackendStatus, 5000);
