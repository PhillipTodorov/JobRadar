// Background service worker - opens extension in side panel

chrome.action.onClicked.addListener(async (tab) => {
  // Save the source tab ID so the side panel knows which tab to copy from
  await chrome.storage.local.set({ sourceTabId: tab.id });

  // Open the side panel
  await chrome.sidePanel.open({ tabId: tab.id });
});

// Enable side panel to open on action click
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
