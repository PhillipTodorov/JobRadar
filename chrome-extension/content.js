// Job Application Assistant — Field Highlighter
// Injected into every page. Listens for highlight requests from the side panel.
// Uses only DOM reads/writes — no HTTP requests, so no anti-bot triggers.

// Guard: if popup.js injects this file as a fallback, don't register duplicate listeners.
if (!window.__jobRadarContentLoaded) {
  window.__jobRadarContentLoaded = true;

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.action !== 'highlightField') return;
    const found = highlightField(message.fieldLabel);
    sendResponse({ found });
  });
}

function highlightField(label) {
  const needle = label.toLowerCase()
    .replace(/\s*[\*\(].*$/, '')   // strip "(required)" style suffixes
    .replace(/\s+required\s*$/i, '')
    .replace(/:$/, '')
    .trim();

  clearHighlights();

  // Strategy 1: <label> elements
  for (const el of document.querySelectorAll('label')) {
    const text = normalizeLabel(el.textContent);
    if (labelsMatch(text, needle)) {
      const input = getInputForLabel(el);
      if (input) { applyHighlight(el, input); return true; }
    }
  }

  // Strategy 2: Any short text node near a form control
  const candidates = document.querySelectorAll(
    'span, div, p, td, th, legend, h1, h2, h3, h4, h5, li'
  );
  for (const el of candidates) {
    // Only use the element's own direct text (not text from children)
    const ownText = Array.from(el.childNodes)
      .filter(n => n.nodeType === Node.TEXT_NODE)
      .map(n => n.textContent)
      .join('')
      .trim();
    if (!ownText || ownText.length > 80) continue;
    const text = normalizeLabel(ownText);
    if (labelsMatch(text, needle)) {
      const input = getNearbyInput(el);
      if (input) { applyHighlight(el, input); return true; }
    }
  }

  // Strategy 3: Match input attributes (name, id, placeholder, aria-label)
  for (const input of document.querySelectorAll('input, textarea, select')) {
    const attrs = [
      input.name,
      input.id,
      input.placeholder,
      input.getAttribute('aria-label'),
      input.getAttribute('aria-labelledby') && document.getElementById(input.getAttribute('aria-labelledby'))?.textContent,
    ].filter(Boolean);
    if (attrs.some(a => normalizeLabel(a).includes(needle) || needle.includes(normalizeLabel(a)))) {
      applyHighlight(null, input);
      return true;
    }
  }

  return false;
}

function normalizeLabel(text) {
  return text
    .toLowerCase()
    .replace(/\s*[\*\(].*$/, '')
    .replace(/\s+required\s*$/i, '')
    .replace(/:/g, '')
    .replace(/_/g, ' ')
    .trim();
}

function labelsMatch(a, b) {
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}

function getInputForLabel(label) {
  const forAttr = label.getAttribute('for');
  if (forAttr) {
    const el = document.getElementById(forAttr);
    if (el) return el;
  }
  return label.querySelector('input, textarea, select');
}

function getNearbyInput(el) {
  // Next siblings
  let sib = el.nextElementSibling;
  for (let i = 0; i < 5 && sib; i++, sib = sib.nextElementSibling) {
    const inp = sib.matches('input,textarea,select') ? sib : sib.querySelector('input, textarea, select');
    if (inp) return inp;
  }
  // Parent's next sibling
  const parent = el.parentElement;
  if (parent) {
    let psib = parent.nextElementSibling;
    for (let i = 0; i < 3 && psib; i++, psib = psib.nextElementSibling) {
      const inp = psib.matches('input,textarea,select') ? psib : psib.querySelector('input, textarea, select');
      if (inp) return inp;
    }
  }
  return null;
}

function applyHighlight(labelEl, inputEl) {
  const HIGHLIGHT = 'jobradar-highlight';
  if (labelEl) {
    labelEl.dataset[HIGHLIGHT] = '1';
    labelEl.style.cssText += ';outline:3px solid #3b82f6 !important;border-radius:3px;';
  }
  inputEl.dataset[HIGHLIGHT] = '1';
  inputEl.style.cssText += ';outline:3px solid #3b82f6 !important;box-shadow:0 0 0 5px rgba(59,130,246,0.25) !important;';
  inputEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

  setTimeout(clearHighlights, 3000);
}

function clearHighlights() {
  document.querySelectorAll('[data-jobradar-highlight]').forEach(el => {
    el.style.outline = '';
    el.style.boxShadow = '';
    delete el.dataset.jobradarHighlight;
  });
}
