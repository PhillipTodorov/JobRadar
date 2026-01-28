"""Job Scraper Dashboard - Streamlit UI (Minimalist Design)

Run with: streamlit run app.py
"""

import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import streamlit as st
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
TMP_DIR = PROJECT_ROOT / ".tmp"
PROFILE_PATH = PROJECT_ROOT / "user_profile.yaml"
CONFIG_PATH = PROJECT_ROOT / "job_search_config.yaml"
QA_DATABANK_PATH = PROJECT_ROOT / "qa_databank.yaml"
REPORTS_PATH = TMP_DIR / "company_reports.json"
TOOLS_DIR = PROJECT_ROOT / "tools"

# Page config
st.set_page_config(
    page_title="JobRadar | Smart Job Search Automation",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Google Fonts, Font Awesome, and Material Icons
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=Material+Icons&family=Material+Icons+Outlined&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# JavaScript to fix UI issues - using HTML component for better execution
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    console.log('[JobRadar] UI fixer loaded');
    let lastFixCount = { icons: 0, radios: 0, navIcons: 0 };

    function fixUI() {
        let changesMade = false;

        // Fix collapse button text (faster interval catches Streamlit re-renders)
        const iconSpans = parent.document.querySelectorAll('span[data-testid="stIconMaterial"]');
        iconSpans.forEach((el) => {
            const text = el.textContent.trim();
            if (text === 'keyboard_double_arrow_left' || text === 'keyboard_double_arrow_right') {
                el.textContent = text === 'keyboard_double_arrow_left' ? '‹' : '›';
                el.style.setProperty('font-size', '28px', 'important');
                el.style.setProperty('font-family', 'Arial, sans-serif', 'important');
                changesMade = true;
            }
        });

        // Aggressively hide radio button circles - target ALL possible elements
        const radioSelectors = [
            '[data-testid="stSidebar"] [role="radio"]',
            '[data-testid="stSidebar"] input[type="radio"]',
            '[data-testid="stSidebar"] .st-emotion-cache-1gulkj5',  // Streamlit's radio circle class
            '[data-testid="stSidebar"] label > div:first-child',    // First div in label (usually the circle)
        ];

        let hiddenCount = 0;
        radioSelectors.forEach(selector => {
            parent.document.querySelectorAll(selector).forEach(el => {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('width', '0', 'important');
                el.style.setProperty('height', '0', 'important');
                el.style.setProperty('opacity', '0', 'important');
                el.style.setProperty('position', 'absolute', 'important');
                el.style.setProperty('left', '-9999px', 'important');
                hiddenCount++;
            });
        });

        // Add icons to navigation buttons using Material Icons
        const navButtons = parent.document.querySelectorAll('[data-testid="stSidebar"] .stButton button');
        const iconMap = {
            'Jobs': 'work',
            'Settings': 'settings',
            'CV': 'description',
            'Projects': 'rocket_launch',
            'Actions': 'bolt',
            'History': 'show_chart'
        };

        let iconsAdded = 0;
        navButtons.forEach((button) => {
            const buttonText = button.textContent.trim();
            const iconName = iconMap[buttonText];

            if (iconName && !button.querySelector('.nav-icon')) {
                // Create icon span
                const iconSpan = document.createElement('span');
                iconSpan.className = 'nav-icon material-icons';
                iconSpan.textContent = iconName;
                iconSpan.style.cssText = 'font-size: 20px; margin-right: 10px; vertical-align: middle; font-family: "Material Icons" !important;';

                // Insert at the beginning of button
                button.insertBefore(iconSpan, button.firstChild);
                iconsAdded++;
            }
        });

        // Only log when we make changes (reduces console spam)
        if (changesMade && lastFixCount.icons !== iconSpans.length) {
            console.log('[JobRadar] Fixed collapse button icons');
            lastFixCount.icons = iconSpans.length;
        }
        if (hiddenCount > 0 && lastFixCount.radios !== hiddenCount) {
            console.log('[JobRadar] Hidden', hiddenCount, 'radio elements');
            lastFixCount.radios = hiddenCount;
        }
        if (iconsAdded > 0 && lastFixCount.navIcons !== iconsAdded) {
            console.log('[JobRadar] Added', iconsAdded, 'navigation icons');
            lastFixCount.navIcons = iconsAdded;
        }
    }

    // Run faster (100ms) to catch Streamlit re-renders before they're visible
    fixUI();
    setInterval(fixUI, 100);
})();
</script>
""", height=0)

# Professional dark theme design system - Linear/Vercel inspired
st.markdown("""
<style>
/* CSS Version: v2.7.4 - Fixed element-container spacing in sidebar */
/* ============================================ */
/* DESIGN SYSTEM FOUNDATION */
/* ============================================ */

:root {
    /* Base colors - deeper, more sophisticated */
    --color-bg-primary: #000000;
    --color-bg-secondary: #0a0a0a;
    --color-bg-tertiary: #111111;
    --color-bg-elevated: #1a1a1a;

    /* Borders - subtle and refined */
    --color-border-subtle: rgba(255, 255, 255, 0.06);
    --color-border-medium: rgba(255, 255, 255, 0.1);
    --color-border-strong: rgba(255, 255, 255, 0.15);

    /* Text - proper contrast */
    --color-text-primary: #ffffff;
    --color-text-secondary: rgba(255, 255, 255, 0.7);
    --color-text-muted: rgba(255, 255, 255, 0.5);
    --color-text-disabled: rgba(255, 255, 255, 0.3);

    /* Accent colors - vibrant but tasteful */
    --color-accent-blue: #3b82f6;
    --color-accent-blue-hover: #60a5fa;
    --color-accent-cyan: #06b6d4;
    --color-accent-purple: #8b5cf6;
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-danger: #ef4444;

    /* Glassmorphism */
    --glass-bg: rgba(255, 255, 255, 0.03);
    --glass-border: rgba(255, 255, 255, 0.08);

    /* Shadows - softer and more realistic */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.5);
    --shadow-md: 0 2px 8px 0 rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 4px 16px 0 rgba(0, 0, 0, 0.5);
    --shadow-xl: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
    --shadow-glow-blue: 0 0 24px rgba(59, 130, 246, 0.15);

    /* Spacing scale */
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;
}

/* Fix Material Icons rendering */
.material-icons,
.material-icons-outlined,
[class*="material-icons"] {
    font-family: 'Material Icons', 'Material Icons Outlined' !important;
    font-weight: normal !important;
    font-style: normal !important;
    font-size: 24px !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-block !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
}

/* Global typography */
* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Override font-family for icon elements */
.material-icons *,
.material-icons-outlined *,
[class*="material-icons"] * {
    font-family: inherit !important;
}

/* Main app container with subtle gradient */
.stApp {
    background: radial-gradient(ellipse at top, #0a0a0a 0%, #000000 100%);
}

.main .block-container {
    padding-top: var(--space-xl);
    padding-bottom: var(--space-2xl);
    max-width: 1400px;
}

/* ============================================ */
/* SIDEBAR NAVIGATION - Linear inspired */
/* ============================================ */

[data-testid="stSidebar"] {
    background: var(--color-bg-primary);
    border-right: 1px solid var(--color-border-subtle);
    backdrop-filter: blur(20px);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: var(--space-xl);
}

/* Sidebar title - gradient text */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
    font-size: 1.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--color-accent-blue) 0%, var(--color-accent-cyan) 60%, var(--color-accent-purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: var(--space-xl);
    text-align: center;
    letter-spacing: -0.03em;
    line-height: 1.2;
}

/* Navigation buttons with Material Icons (icons injected via JavaScript) */
[data-testid="stSidebar"] .stButton {
    margin-bottom: 0 !important;
    margin-top: 0 !important;
}

/* Remove spacing from element containers in sidebar */
[data-testid="stSidebar"] .element-container {
    margin-bottom: 0 !important;
    margin-top: 0 !important;
}

[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px !important;
    padding: 0.35rem 0.75rem !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
    display: flex !important;
    align-items: center !important;
}

[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    border-color: transparent !important;
    color: var(--color-text-secondary) !important;
}

[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.03) !important;
    border-color: rgba(255, 255, 255, 0.06) !important;
    color: var(--color-text-primary) !important;
    transform: translateX(2px) !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(59, 130, 246, 0.1) !important;
    border-color: rgba(59, 130, 246, 0.4) !important;
    color: var(--color-text-primary) !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: rgba(59, 130, 246, 0.15) !important;
    border-color: rgba(59, 130, 246, 0.5) !important;
    transform: none !important;
}

/* Hide Material Icons keyboard text to prevent flash on collapse */
span[data-testid="stIconMaterial"] {
    font-family: 'Material Icons', 'Material Icons Outlined' !important;
    font-size: 24px !important;
}

/* Sidebar footer */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] .caption {
    color: var(--color-text-disabled);
    font-size: 0.75rem;
}

/* Fix sidebar collapse button - JavaScript handles the actual text replacement */
button[kind="icon"],
button[data-testid="baseButton-header"],
[data-testid="collapsedControl"] button {
    font-size: 24px !important;
    font-weight: bold !important;
}

/* ============================================ */
/* PAGE HEADERS */
/* ============================================ */

h1 {
    font-size: 2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.04em !important;
    line-height: 1.1 !important;
    margin-bottom: var(--space-sm) !important;
    color: var(--color-text-primary) !important;
}

h2 {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
    margin-top: var(--space-xl) !important;
    margin-bottom: var(--space-md) !important;
    color: var(--color-text-primary) !important;
}

h3 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    margin-bottom: var(--space-sm) !important;
    color: var(--color-text-primary) !important;
}

.caption, [data-testid="stCaptionContainer"] {
    color: var(--color-text-muted) !important;
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
}

/* ============================================ */
/* METRICS & KPI CARDS - Glassmorphism */
/* ============================================ */

[data-testid="stMetric"] {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    padding: var(--space-lg);
    border-radius: 12px;
    border: 1px solid var(--glass-border);
    box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255, 255, 255, 0.03);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
}

[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg), var(--shadow-glow-blue);
    border-color: rgba(59, 130, 246, 0.2);
    background: rgba(59, 130, 246, 0.03);
}

[data-testid="stMetricValue"] {
    font-size: 2.25rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.04em !important;
    background: linear-gradient(135deg, var(--color-accent-blue) 0%, var(--color-accent-cyan) 70%, var(--color-accent-purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1 !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 600 !important;
    color: var(--color-text-muted) !important;
    margin-bottom: var(--space-sm) !important;
}

/* ============================================ */
/* BUTTONS - Refined and subtle */
/* ============================================ */

.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.875rem;
    padding: 0.625rem 1.25rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid var(--color-border-subtle);
    box-shadow: none;
    letter-spacing: -0.01em;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.stButton > button[kind="primary"] {
    background: var(--color-accent-blue);
    border-color: var(--color-accent-blue);
    color: white;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.1);
}

.stButton > button[kind="primary"]:hover {
    background: var(--color-accent-blue-hover);
    border-color: var(--color-accent-blue-hover);
    box-shadow: var(--shadow-glow-blue), var(--shadow-sm);
}

.stButton > button[kind="secondary"] {
    background: var(--glass-bg);
    backdrop-filter: blur(8px);
    border-color: var(--color-border-medium);
    color: var(--color-text-secondary);
}

.stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: var(--color-border-strong);
    color: var(--color-text-primary);
}

/* Link buttons */
.stLinkButton > a {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.875rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    background: var(--glass-bg);
    border: 1px solid var(--color-border-subtle);
}

/* ============================================ */
/* FORM INPUTS - Clean and minimal */
/* ============================================ */

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--glass-bg) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid var(--color-border-subtle) !important;
    border-radius: 8px !important;
    color: var(--color-text-primary) !important;
    font-size: 0.875rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    padding: 0.625rem 0.875rem !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: rgba(59, 130, 246, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08) !important;
    background: rgba(59, 130, 246, 0.02) !important;
}

/* Input labels */
.stTextInput > label,
.stTextArea > label,
.stNumberInput > label,
.stSelectbox > label {
    font-weight: 600 !important;
    font-size: 0.8125rem !important;
    color: var(--color-text-secondary) !important;
    margin-bottom: var(--space-sm) !important;
    letter-spacing: -0.01em !important;
}

/* ============================================ */
/* TABS - Linear style */
/* ============================================ */

.stTabs [data-baseweb="tab-list"] {
    gap: var(--space-sm);
    background: transparent;
    border-bottom: 1px solid var(--color-border-subtle);
    padding-bottom: 0;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 500;
    font-size: 0.875rem;
    color: var(--color-text-muted);
    padding: 0.75rem 1.25rem;
    border-radius: 6px 6px 0 0;
    background: transparent;
    border: none;
    transition: all 0.2s;
    position: relative;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--glass-bg);
    color: var(--color-text-secondary);
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--glass-bg);
    color: var(--color-text-primary);
    font-weight: 600;
}

.stTabs [data-baseweb="tab"][aria-selected="true"]::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--color-accent-blue);
}

/* ============================================ */
/* CONTAINERS & CARDS - Glassmorphism */
/* ============================================ */

.element-container {
    margin-bottom: var(--space-md);
}

/* Dividers - subtle */
hr {
    border: none !important;
    height: 1px !important;
    background: var(--color-border-subtle) !important;
    margin: var(--space-xl) 0 !important;
}

/* Scrollable containers */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    background: var(--glass-bg);
    backdrop-filter: blur(8px);
    border: 1px solid var(--color-border-subtle);
    border-radius: 8px;
    padding: var(--space-md);
}

/* Code blocks */
.stCodeBlock {
    border-radius: 8px;
    border: 1px solid var(--color-border-subtle);
    background: var(--color-bg-secondary);
}

/* ============================================ */
/* SCORE BADGES - More sophisticated */
/* ============================================ */

.score-high {
    color: var(--color-success);
    font-weight: 700;
    font-size: 1.375rem;
    letter-spacing: -0.02em;
}

.score-med {
    color: var(--color-warning);
    font-weight: 700;
    font-size: 1.375rem;
    letter-spacing: -0.02em;
}

.score-low {
    color: var(--color-text-disabled);
    font-weight: 600;
    font-size: 1.125rem;
}

/* ============================================ */
/* DATA DISPLAY */
/* ============================================ */

/* Expanders (if any remain) */
.streamlit-expanderHeader {
    font-size: 0.875rem;
    font-weight: 600;
    background: var(--glass-bg);
    backdrop-filter: blur(8px);
    border-radius: 8px;
    border: 1px solid var(--color-border-subtle);
    transition: all 0.2s;
}

.streamlit-expanderHeader:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: var(--color-border-medium);
}

/* Success/Warning/Error messages - glassmorphic */
.stSuccess {
    background: rgba(16, 185, 129, 0.08);
    backdrop-filter: blur(8px);
    border-left: 2px solid var(--color-success);
    border-radius: 8px;
    padding: var(--space-md);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-left-width: 2px;
}

.stWarning {
    background: rgba(245, 158, 11, 0.08);
    backdrop-filter: blur(8px);
    border-left: 2px solid var(--color-warning);
    border-radius: 8px;
    padding: var(--space-md);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-left-width: 2px;
}

.stError {
    background: rgba(239, 68, 68, 0.08);
    backdrop-filter: blur(8px);
    border-left: 2px solid var(--color-danger);
    border-radius: 8px;
    padding: var(--space-md);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-left-width: 2px;
}

.stInfo {
    background: rgba(59, 130, 246, 0.08);
    backdrop-filter: blur(8px);
    border-left: 2px solid var(--color-accent-blue);
    border-radius: 8px;
    padding: var(--space-md);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-left-width: 2px;
}

/* ============================================ */
/* JOB CARDS - Custom styling for jobs page */
/* ============================================ */

.job-card {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: var(--space-lg);
    margin-bottom: 0.4rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow-sm);
}

.job-card:hover {
    border-color: rgba(59, 130, 246, 0.3);
    box-shadow: var(--shadow-md), var(--shadow-glow-blue);
    transform: translateY(-2px);
}

.job-score-badge {
    display: inline-block;
    padding: 0.375rem 0.875rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.875rem;
    letter-spacing: -0.01em;
}

.job-score-high {
    background: rgba(16, 185, 129, 0.12);
    color: var(--color-success);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.job-score-med {
    background: rgba(245, 158, 11, 0.12);
    color: var(--color-warning);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.job-score-low {
    background: rgba(255, 255, 255, 0.05);
    color: var(--color-text-muted);
    border: 1px solid var(--color-border-subtle);
}

/* ============================================ */
/* UTILITIES */
/* ============================================ */

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Smooth scrolling */
html {
    scroll-behavior: smooth;
}

/* Selection color */
::selection {
    background: rgba(59, 130, 246, 0.2);
    color: var(--color-text-primary);
}

/* Focus visible for accessibility */
*:focus-visible {
    outline: 2px solid var(--color-accent-blue);
    outline-offset: 2px;
}

/* Reduce motion for accessibility */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* ============================================ */
/* RESPONSIVE ADJUSTMENTS */
/* ============================================ */

@media (max-width: 768px) {
    :root {
        --space-xl: 1.5rem;
        --space-2xl: 2rem;
    }

    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.125rem !important; }

    [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
    }

    .main .block-container {
        padding-left: var(--space-md);
        padding-right: var(--space-md);
    }

    [data-testid="stMetric"] {
        padding: var(--space-md);
    }
}
</style>
""", unsafe_allow_html=True)


# === Data Loading Functions ===

def load_jobs():
    """Load jobs from scored_jobs.json."""
    scored_path = TMP_DIR / "scored_jobs.json"
    if scored_path.exists():
        with open(scored_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_profile():
    """Load user profile."""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"profile": {"skills": {"required": [], "preferred": []}, "locations": {"preferred": [], "acceptable": []}, "salary": {"minimum": 20000, "preferred": 30000}, "dealbreakers": []}, "scoring": {"weights": {}}}


def save_profile(profile_data):
    """Save user profile."""
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)


def load_config():
    """Load job search config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"search_params": {"titles": [], "location": "London", "posted_within_days": 7}, "api": {"max_results": 50, "pages": 3}}


def save_config(config_data):
    """Save job search config."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


def load_qa_databank():
    """Load Q&A databank."""
    if QA_DATABANK_PATH.exists():
        with open(QA_DATABANK_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"personal_info": {}, "work_authorization": {}, "salary": {}, "questions": {}, "cover_letter": {}}


def save_qa_databank(databank):
    """Save Q&A databank."""
    with open(QA_DATABANK_PATH, "w", encoding="utf-8") as f:
        yaml.dump(databank, f, default_flow_style=False, allow_unicode=True)


def load_company_reports():
    """Load saved company reports."""
    if REPORTS_PATH.exists():
        with open(REPORTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_company_report(company_name, report):
    """Save a company report."""
    reports = load_company_reports()
    reports[company_name] = report
    TMP_DIR.mkdir(exist_ok=True)
    with open(REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)


def run_tool(script_name):
    """Run a Python script from the tools directory."""
    script_path = TOOLS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(TOOLS_DIR),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def generate_company_report(company_name, job_title=None):
    """Generate a research report on a company using Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return f"""**API Key Required**

Add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

**Research {company_name} manually:**
- [Google](https://www.google.com/search?q={company_name.replace(' ', '+')})
- [LinkedIn](https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')})
- [Glassdoor](https://www.glassdoor.co.uk/Reviews/{company_name.replace(' ', '-')}-Reviews)
"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": f"""Brief company research report (under 200 words) for {company_name}.
Job: {job_title or 'Not specified'}

Include:
1. What the company does
2. Key things to research before applying
3. 2-3 potential interview questions
4. Red flags to watch for

Be concise and actionable."""}]
        )
        return f"## {company_name}\n\n{message.content[0].text}"
    except Exception as e:
        return f"**Error:** {str(e)}\n\n[Google {company_name}](https://www.google.com/search?q={company_name.replace(' ', '+')})"


def check_backend_status():
    """Check if the Flask backend is running."""
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


# === Navigation ===

st.sidebar.markdown("# JobRadar")
st.sidebar.markdown("---")

# Initialize page state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Jobs"

# Custom navigation with Material Icons (already loaded)
nav_items = [
    ("Jobs", "work"),           # briefcase icon
    ("Settings", "settings"),   # settings icon
    ("CV", "description"),      # document icon
    ("Projects", "rocket_launch"),  # rocket icon
    ("Actions", "bolt"),        # lightning icon
    ("History", "show_chart"),  # chart icon
]

# Render navigation buttons
for page_name, icon in nav_items:
    is_active = st.session_state.current_page == page_name

    # Use Material Icons with button text
    if st.sidebar.button(
        f"{page_name}",
        key=f"nav_{page_name}",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.current_page = page_name
        st.rerun()

page = st.session_state.current_page

st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 • Built with Claude Code")


# ============================================================
# PAGE 1: JOBS (Main View)
# ============================================================

if page == "Jobs":
    # Page header
    st.markdown("# Job Dashboard")
    st.caption("Browse and filter scraped jobs by fit score")
    st.markdown("---")

    jobs = load_jobs()

    # Stats row - compact
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(jobs))
    c2.metric("Matching", len([j for j in jobs if j.get("fit_score", 0) > 0]))
    if jobs:
        c3.metric("Top Score", max(j.get("fit_score", 0) for j in jobs))
        c4.metric("Avg Score", f"{sum(j.get('fit_score', 0) for j in jobs) / len(jobs):.0f}")
    else:
        c3.metric("Top Score", "-")
        c4.metric("Avg Score", "-")

    st.divider()

    if not jobs:
        st.info("No jobs found. Go to **Actions** to scrape jobs.")
    else:
        # Filters - single compact row
        f1, f2, f3 = st.columns([1, 2, 1])
        with f1:
            min_score = st.selectbox("Min Score", [0, 20, 40, 60, 80], index=0, label_visibility="collapsed")
        with f2:
            search = st.text_input("Search", placeholder="Search jobs...", label_visibility="collapsed")
        with f3:
            show_zero = st.checkbox("Show 0", value=False, help="Include jobs with score=0")

        # Filter jobs
        filtered = [
            j for j in jobs
            if (j.get("fit_score", 0) >= min_score or (show_zero and j.get("fit_score", 0) == 0))
            and (not search or search.lower() in j.get("title", "").lower() or search.lower() in j.get("company", "").lower())
        ]
        filtered.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

        st.caption(f"Showing {len(filtered)} of {len(jobs)} jobs")

        if filtered:
            # Initialize selection
            if 'sel_idx' not in st.session_state:
                st.session_state.sel_idx = 0

            # Two columns: list + details
            list_col, detail_col = st.columns([1, 1.2])

            with list_col:
                st.markdown("**Job Matches**")
                with st.container(height=450):
                    for idx, job in enumerate(filtered):
                        score = job.get('fit_score', 0)
                        is_sel = st.session_state.sel_idx == idx

                        # Create clean job card
                        score_badge = ""
                        if score >= 70:
                            score_badge = f'<span class="job-score-badge job-score-high">{score}</span>'
                        elif score >= 40:
                            score_badge = f'<span class="job-score-badge job-score-med">{score}</span>'
                        else:
                            score_badge = f'<span class="job-score-badge job-score-low">{score}</span>'

                        # Job title and company
                        title = job['title'][:40] + "..." if len(job['title']) > 40 else job['title']
                        company = job['company'][:25] + "..." if len(job['company']) > 25 else job['company']

                        if st.button(
                            f"{score} · {title}\n{company}",
                            key=f"j{idx}",
                            use_container_width=True,
                            type="primary" if is_sel else "secondary",
                        ):
                            st.session_state.sel_idx = idx
                            st.rerun()

            # Keep selection in bounds
            sel_idx = min(st.session_state.sel_idx, len(filtered) - 1)
            job = filtered[sel_idx]

            with detail_col:
                score = job.get('fit_score', 0)
                score_color = "green" if score >= 70 else "orange" if score >= 40 else "gray"

                st.markdown(f"### {job['title']}")
                st.markdown(f"**{job['company']}** · :{score_color}[Score: {score}]")

                # Clean info line without emojis
                info_parts = []
                if job.get('location'):
                    info_parts.append(job['location'])
                if job.get('date_posted'):
                    info_parts.append(job.get('date_posted'))
                if job.get('salary'):
                    info_parts.append(job.get('salary'))
                else:
                    info_parts.append("Salary not listed")

                st.caption(" · ".join(info_parts))

                # Action buttons
                b1, b2 = st.columns(2)
                job_url = job.get('url', '#')

                with b1:
                    if job_url and job_url != '#':
                        st.link_button("Apply", job_url, type="primary", use_container_width=True)

                with b2:
                    company = job.get('company', '')
                    reports = load_company_reports()

                    if company in reports:
                        if st.button("View Report", use_container_width=True):
                            st.session_state['show_report'] = company
                    else:
                        if st.button("Research", use_container_width=True):
                            with st.spinner("Researching..."):
                                report = generate_company_report(company, job.get('title'))
                                save_company_report(company, report)
                            st.session_state['show_report'] = company
                            st.rerun()

                st.divider()

                # Show report OR description
                if st.session_state.get('show_report') == job.get('company'):
                    reports = load_company_reports()
                    if job.get('company') in reports:
                        st.markdown(reports[job.get('company')])
                        if st.button("Close Report", key="close_rep", use_container_width=True):
                            st.session_state['show_report'] = None
                            st.rerun()
                else:
                    # Show job description inline
                    st.markdown("**Job Description**")
                    with st.container(height=300):
                        st.write(job.get("description", "No description available."))


# ============================================================
# PAGE 2: SETTINGS (All Configuration)
# ============================================================

elif page == "Settings":
    st.markdown("# Settings")
    st.caption("Configure your profile, job preferences, and Q&A databank")
    st.markdown("---")

    # Load all data
    profile = load_profile()
    config = load_config()
    databank = load_qa_databank()

    user = profile.get("profile", {})
    skills = user.get("skills", {})
    locations = user.get("locations", {})
    salary = user.get("salary", {})
    search_params = config.get("search_params", {})
    personal = databank.get("personal_info", {})

    # Use tabs for different setting sections
    tab1, tab2, tab3, tab4 = st.tabs(["Profile", "Job Search", "Q&A Bank", "Advanced"])

    with tab1:
        # Personal Info
        st.subheader("Personal Information")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Name", value=personal.get("full_name", ""), key="p_name")
            new_email = st.text_input("Email", value=personal.get("email", ""), key="p_email")
            new_phone = st.text_input("Phone", value=personal.get("phone", ""), key="p_phone")
        with c2:
            new_city = st.text_input("City", value=personal.get("city", ""), key="p_city")
            new_postcode = st.text_input("Postcode", value=personal.get("postcode", ""), key="p_postcode")
            new_country = st.text_input("Country", value=personal.get("country", ""), key="p_country")

        new_linkedin = st.text_input("LinkedIn", value=personal.get("linkedin", ""), key="p_li")

        # Auto-save personal info
        new_personal = {
            "full_name": new_name, "email": new_email, "phone": new_phone,
            "city": new_city, "postcode": new_postcode, "country": new_country,
            "linkedin": new_linkedin,
            "github": personal.get("github", ""), "portfolio": personal.get("portfolio", "")
        }
        if new_personal != databank.get("personal_info", {}):
            databank["personal_info"] = new_personal
            save_qa_databank(databank)

        st.divider()

        # Job Preferences
        st.subheader("Job Preferences")
        c1, c2 = st.columns(2)

        with c1:
            new_req = st.text_area(
                "Required Skills (one per line)",
                value="\n".join(skills.get("required", [])),
                height=120, key="s_req"
            )
            new_locs = st.text_area(
                "Preferred Locations (one per line)",
                value="\n".join(locations.get("preferred", [])),
                height=80, key="s_locs"
            )

        with c2:
            new_pref = st.text_area(
                "Preferred Skills (one per line)",
                value="\n".join(skills.get("preferred", [])),
                height=120, key="s_pref"
            )
            c2a, c2b = st.columns(2)
            with c2a:
                new_min_sal = st.number_input("Min Salary", value=salary.get("minimum", 20000), step=1000, key="s_min")
            with c2b:
                new_pref_sal = st.number_input("Pref Salary", value=salary.get("preferred", 30000), step=1000, key="s_pref_sal")

        # Auto-save job preferences
        new_profile = {
            "profile": {
                "name": user.get("name", new_name),
                "skills": {
                    "required": [s.strip() for s in new_req.split("\n") if s.strip()],
                    "preferred": [s.strip() for s in new_pref.split("\n") if s.strip()],
                },
                "locations": {
                    "preferred": [s.strip() for s in new_locs.split("\n") if s.strip()],
                    "acceptable": locations.get("acceptable", []),
                },
                "salary": {"minimum": int(new_min_sal), "preferred": int(new_pref_sal)},
                "dealbreakers": user.get("dealbreakers", []),
            },
            "scoring": profile.get("scoring", {}),
        }
        if new_profile != profile:
            save_profile(new_profile)
            profile = new_profile

    with tab2:
        # Search Configuration
        st.subheader("Search Configuration")
        c1, c2 = st.columns(2)

        with c1:
            new_titles = st.text_area(
                "Job Titles to Search (one per line)",
                value="\n".join(search_params.get("titles", [])),
                height=120, key="q_titles"
            )

        with c2:
            new_search_loc = st.text_input("Search Location", value=search_params.get("location", "London"), key="q_loc")
            new_days = st.selectbox(
                "Posted Within",
                options=[1, 3, 7, 14, 30],
                index=[1, 3, 7, 14, 30].index(search_params.get("posted_within_days", 7)) if search_params.get("posted_within_days", 7) in [1, 3, 7, 14, 30] else 2,
                format_func=lambda x: f"{x} day{'s' if x > 1 else ''}",
                key="q_days"
            )

        # Auto-save search config
        new_config = {
            "search_params": {
                "titles": [t.strip() for t in new_titles.split("\n") if t.strip()],
                "keywords": search_params.get("keywords", []),
                "location": new_search_loc,
                "remote": search_params.get("remote", False),
                "experience_level": search_params.get("experience_level", ""),
                "posted_within_days": new_days,
            },
            "api": config.get("api", {"max_results": 50, "pages": 3}),
        }
        if new_config != config:
            save_config(new_config)

        st.divider()

        # Dealbreakers
        st.subheader("Dealbreakers")
        new_deal = st.text_area(
            "Keywords that disqualify a job (one per line)",
            value="\n".join(user.get("dealbreakers", [])),
            height=100, key="deal"
        )

        # Auto-save dealbreakers
        new_dealbreakers = [s.strip() for s in new_deal.split("\n") if s.strip()]
        if new_dealbreakers != user.get("dealbreakers", []):
            profile["profile"]["dealbreakers"] = new_dealbreakers
            save_profile(profile)

    with tab3:
        # Q&A Bank
        st.subheader("Q&A Bank")
        st.caption("Saved answers for the Chrome extension")

        questions = databank.get("questions", {})

        # Show existing Q&A in a cleaner format
        if questions:
            for idx, (question, answer) in enumerate(questions.items()):
                with st.container():
                    st.markdown(f"**Q{idx+1}:** {question}")
                    new_answer = st.text_area(
                        "Answer", value=answer or "", height=60,
                        key=f"qa_{hash(question)}", label_visibility="collapsed"
                    )
                    # Auto-save changes
                    if new_answer != answer:
                        databank["questions"][question] = new_answer
                        save_qa_databank(databank)
                    st.markdown("---")
        else:
            st.info("No questions saved yet. Add your first one below.")

        # Add new question
        st.markdown("**Add New Question**")
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            new_q = st.text_input("Question", key="new_q", label_visibility="collapsed", placeholder="Question...")
        with c2:
            new_a = st.text_input("Answer", key="new_a", label_visibility="collapsed", placeholder="Your answer...")
        with c3:
            if st.button("Add", key="add_qa", type="primary", use_container_width=True):
                if new_q:
                    databank["questions"][new_q] = new_a
                    save_qa_databank(databank)
                    st.rerun()

    with tab4:
        # Work Authorization
        st.subheader("Work Authorization")
        work_auth = databank.get("work_authorization", {})

        c1, c2, c3 = st.columns(3)
        with c1:
            new_uk = st.selectbox(
                "Eligible to work in UK?",
                ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("eligible_to_work_uk", "")),
                key="wa_uk"
            )
        with c2:
            new_sponsor = st.selectbox(
                "Require sponsorship?",
                ["Yes", "No", ""],
                index=["Yes", "No", ""].index(work_auth.get("require_sponsorship", "")),
                key="wa_sp"
            )
        with c3:
            new_notice = st.text_input("Notice Period", value=work_auth.get("notice_period", ""), key="wa_np")

        # Auto-save work auth
        new_work_auth = {
            "eligible_to_work_uk": new_uk,
            "require_sponsorship": new_sponsor,
            "notice_period": new_notice,
            "availability": work_auth.get("availability", "")
        }
        if new_work_auth != work_auth:
            databank["work_authorization"] = new_work_auth
            save_qa_databank(databank)

    st.caption("All changes are saved automatically")


# ============================================================
# PAGE 3: CV (Upload & Parse Resume)
# ============================================================

elif page == "CV":
    st.markdown("# CV Parser")
    st.caption("Upload your CV to automatically extract information")
    st.markdown("---")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your CV/Resume (.docx, .pdf, or .txt)",
        type=["docx", "doc", "pdf", "txt"],
        help="Upload your CV and we'll extract key information to populate your profile"
    )

    if uploaded_file:
        # Save uploaded file
        cv_dir = PROJECT_ROOT / "profile"
        cv_dir.mkdir(exist_ok=True)
        cv_path = cv_dir / uploaded_file.name

        with open(cv_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Uploaded: {uploaded_file.name}")

        # Extract text from CV
        try:
            if uploaded_file.name.endswith(('.docx', '.doc')):
                from docx import Document
                doc = Document(cv_path)
                cv_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            elif uploaded_file.name.endswith('.txt'):
                with open(cv_path, 'r', encoding='utf-8') as f:
                    cv_text = f.read()
            elif uploaded_file.name.endswith('.pdf'):
                # Try multiple extraction methods and compare results
                cv_text = ""
                extraction_methods = []

                # Method 1: pdfplumber (default)
                try:
                    import pdfplumber
                    pdfplumber_text = ""
                    with pdfplumber.open(cv_path) as pdf:
                        num_pages = len(pdf.pages)
                        st.info(f"📄 PDF has {num_pages} page(s)")
                        for i, page in enumerate(pdf.pages, 1):
                            text = page.extract_text()
                            if text:
                                pdfplumber_text += text + "\n\n"
                                st.caption(f"pdfplumber page {i}: {len(text)} chars")
                    pdfplumber_text = pdfplumber_text.strip()
                    extraction_methods.append(("pdfplumber", pdfplumber_text))
                except Exception as e:
                    st.warning(f"pdfplumber extraction failed: {e}")

                # Method 2: pypdf (fallback)
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(cv_path)
                    pypdf_text = ""
                    num_pages = len(reader.pages)
                    for i, page in enumerate(reader.pages, 1):
                        text = page.extract_text()
                        pypdf_text += text + "\n\n"
                        st.caption(f"pypdf page {i}: {len(text)} chars")
                    pypdf_text = pypdf_text.strip()
                    extraction_methods.append(("pypdf", pypdf_text))
                except Exception as e:
                    st.warning(f"pypdf extraction failed: {e}")

                # Compare and show results
                if extraction_methods:
                    if len(extraction_methods) > 1:
                        st.markdown("**Extraction Comparison:**")
                        for method_name, text in extraction_methods:
                            st.write(f"- {method_name}: {len(text)} chars")

                    # Use whichever method extracted the most text
                    method_name, cv_text = max(extraction_methods, key=lambda x: len(x[1]))
                    st.success(f"✅ Using {method_name} (extracted {len(cv_text)} chars)")
            else:
                cv_text = ""

            # Minimal cleanup - just remove excessive blank lines
            if cv_text:
                import re
                # Only remove 4+ consecutive newlines, keep normal spacing
                cv_text = re.sub(r'\n{4,}', '\n\n\n', cv_text)
                cv_text = cv_text.strip()

            if cv_text:
                # Show preview inline
                st.markdown("**CV Preview**")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"Extracted {len(cv_text)} characters from CV")
                with col2:
                    st.download_button(
                        label="Download Full Text",
                        data=cv_text,
                        file_name="cv_extracted.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with st.container(height=400):
                    st.text(cv_text)

                st.divider()

                # AI-powered extraction
                api_key = os.getenv("ANTHROPIC_API_KEY")

                if api_key:
                    st.subheader("Extract Information")
                    st.caption("Use Claude AI to automatically populate your profile from your CV")

                    if st.button("Parse CV with AI", type="primary", use_container_width=True):
                        with st.spinner("Analyzing CV..."):
                            try:
                                import anthropic
                                client = anthropic.Anthropic(api_key=api_key)

                                prompt = f"""Extract structured information from this CV/resume.

CV Text:
{cv_text}

Return a JSON object with these fields:
{{
    "name": "Full name",
    "email": "email@example.com",
    "phone": "+44 1234 567890",
    "location": "City, Country",
    "linkedin": "LinkedIn URL if present",
    "github": "GitHub URL if present",
    "skills": ["skill1", "skill2", "skill3", ...],
    "years_experience": "X years",
    "current_role": "Current or most recent job title",
    "summary": "2-3 sentence professional summary"
}}

Only include fields that are present in the CV. Return valid JSON only."""

                                message = client.messages.create(
                                    model="claude-3-5-haiku-20241022",
                                    max_tokens=1500,
                                    messages=[{"role": "user", "content": prompt}]
                                )

                                response_text = message.content[0].text.strip()

                                # Clean markdown code blocks if present
                                if response_text.startswith("```"):
                                    import re
                                    response_text = re.sub(r'^```\w*\n?', '', response_text)
                                    response_text = re.sub(r'\n?```$', '', response_text)

                                extracted = json.loads(response_text)

                                # Show extracted data
                                st.success("CV parsed successfully!")
                                st.json(extracted)

                                st.divider()

                                # Apply to profile
                                if st.button("Apply to Profile", type="primary"):
                                    # Update qa_databank with personal info
                                    databank = load_qa_databank()
                                    personal = databank.get("personal_info", {})

                                    if extracted.get("name"):
                                        personal["full_name"] = extracted["name"]
                                    if extracted.get("email"):
                                        personal["email"] = extracted["email"]
                                    if extracted.get("phone"):
                                        personal["phone"] = extracted["phone"]
                                    if extracted.get("location"):
                                        city_country = extracted["location"].split(",")
                                        if len(city_country) >= 1:
                                            personal["city"] = city_country[0].strip()
                                        if len(city_country) >= 2:
                                            personal["country"] = city_country[1].strip()
                                    if extracted.get("linkedin"):
                                        personal["linkedin"] = extracted["linkedin"]
                                    if extracted.get("github"):
                                        personal["github"] = extracted["github"]

                                    databank["personal_info"] = personal
                                    save_qa_databank(databank)

                                    # Update profile with skills
                                    profile = load_profile()
                                    if extracted.get("skills"):
                                        profile["profile"]["skills"]["required"] = extracted["skills"][:10]  # Top 10 skills
                                    save_profile(profile)

                                    st.success("Profile updated! Check the Settings page.")
                                    st.balloons()

                            except Exception as e:
                                st.error(f"Failed to parse CV: {e}")
                                st.info("You can manually update your profile in the Settings page.")

                else:
                    st.warning("AI parsing requires ANTHROPIC_API_KEY in .env file")
                    st.info("You can still manually update your profile in the Settings page")

        except Exception as e:
            st.error(f"Failed to read CV: {e}")

    else:
        # No file uploaded - show instructions
        st.info("Upload your CV to get started")

        st.markdown("""
### What gets extracted:
- Personal information (name, email, phone, location)
- Skills and technologies
- Work experience summary
- LinkedIn and GitHub profiles
- Professional summary

### How it works:
1. Upload your CV (.docx or .txt format)
2. Click "Parse CV with AI"
3. Review extracted information
4. Click "Apply to Profile" to update your settings

**Note:** Requires ANTHROPIC_API_KEY in `.env` for AI parsing.
        """)


# ============================================================
# PAGE 4: PROJECTS (GitHub Portfolio)
# ============================================================

elif page == "Projects":
    st.markdown("# GitHub Projects")
    st.caption("Showcase your projects for job applications")
    st.markdown("---")

    # Load or initialize projects
    projects_path = PROJECT_ROOT / "github_projects.yaml"
    if projects_path.exists():
        with open(projects_path, "r", encoding="utf-8") as f:
            projects_data = yaml.safe_load(f) or {"projects": []}
    else:
        projects_data = {"projects": []}

    projects = projects_data.get("projects", [])

    # Add new project button
    if st.button("Add New Project", type="primary"):
        st.session_state['adding_project'] = True

    # Show add form if requested
    if st.session_state.get('adding_project', len(projects) == 0):
        with st.form("add_project"):
            st.subheader("Add Project")
            c1, c2 = st.columns(2)

            with c1:
                proj_name = st.text_input("Project Name *", placeholder="My Awesome Project")
                proj_url = st.text_input("GitHub URL *", placeholder="https://github.com/username/repo")
                proj_demo = st.text_input("Live Demo URL", placeholder="https://myproject.com (optional)")

            with c2:
                proj_tech = st.text_input("Technologies Used *", placeholder="Python, Flask, React, PostgreSQL")
                proj_role = st.text_input("Your Role", placeholder="Full-stack developer, Solo project, etc.")

            proj_desc = st.text_area(
                "Description *",
                placeholder="Brief description of what the project does and your contributions...",
                height=80
            )

            proj_highlights = st.text_area(
                "Key Achievements",
                placeholder="- Implemented real-time notifications\n- Reduced load time by 50%",
                height=60
            )

            c1, c2 = st.columns(2)
            with c1:
                submitted = st.form_submit_button("Add Project", type="primary", use_container_width=True)
            with c2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

            if submitted:
                if proj_name and proj_url and proj_desc and proj_tech:
                    new_project = {
                        "name": proj_name,
                        "url": proj_url,
                        "demo_url": proj_demo,
                        "technologies": proj_tech,
                        "role": proj_role,
                        "description": proj_desc,
                        "highlights": proj_highlights,
                        "added_date": datetime.datetime.now().isoformat()
                    }

                    projects.append(new_project)
                    projects_data["projects"] = projects

                    with open(projects_path, "w", encoding="utf-8") as f:
                        yaml.dump(projects_data, f, default_flow_style=False, allow_unicode=True)

                    st.session_state['adding_project'] = False
                    st.success("Project added!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields (marked with *)")

            if cancelled:
                st.session_state['adding_project'] = False
                st.rerun()

        st.divider()

    # Display projects in clean cards
    if not projects:
        st.info("No projects added yet. Click 'Add New Project' above!")
    else:
        st.subheader(f"Your Projects ({len(projects)})")

        for idx, project in enumerate(projects):
            with st.container():
                # Project card
                c1, c2 = st.columns([4, 1])

                with c1:
                    st.markdown(f"### {project['name']}")
                    caption_parts = [project.get('technologies', 'N/A')]
                    if project.get('role'):
                        caption_parts.append(project['role'])
                    st.caption(" · ".join(caption_parts))

                with c2:
                    # Action buttons
                    if project.get('url'):
                        st.link_button("GitHub", project['url'], use_container_width=True)
                    if project.get('demo_url'):
                        st.link_button("Demo", project['demo_url'], use_container_width=True)

                # Description
                st.markdown(project.get('description', 'No description'))

                # Highlights
                if project.get('highlights'):
                    st.markdown("**Key Achievements:**")
                    st.markdown(project.get('highlights'))

                # Actions
                col1, col2, col3 = st.columns([1, 2, 3])
                with col1:
                    if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
                        projects.pop(idx)
                        projects_data["projects"] = projects
                        with open(projects_path, "w", encoding="utf-8") as f:
                            yaml.dump(projects_data, f, default_flow_style=False, allow_unicode=True)
                        st.rerun()

                with col2:
                    if st.button("Copy Description", key=f"copy_{idx}", use_container_width=True):
                        # Generate a formatted description for job applications
                        formatted = f"""**{project['name']}**
Technologies: {project.get('technologies', 'N/A')}
{project.get('description', '')}

{project.get('highlights', '')}

GitHub: {project.get('url', '')}"""
                        st.code(formatted, language="text")

                st.divider()

        # Export all projects
        if st.button("Export All Projects as JSON", use_container_width=True):
            st.download_button(
                "Download",
                data=json.dumps(projects, indent=2),
                file_name=f"github_projects_{datetime.datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )


# ============================================================
# PAGE 5: ACTIONS (Tools & Extension)
# ============================================================

elif page == "Actions":
    st.markdown("# Actions")
    st.caption("Scrape jobs, manage backend, and test the Chrome extension")
    st.markdown("---")

    # Main action buttons
    st.subheader("Scrape & Score Jobs")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Scrape New Jobs", type="primary", use_container_width=True):
            with st.spinner("Scraping jobs..."):
                code, stdout, stderr = run_tool("run_job_scrape.py")
            if code == 0:
                st.success("Done!")
                st.rerun()
            else:
                st.error("Failed")
                st.code(stdout + stderr, language="text")

    with c2:
        if st.button("Re-score Jobs", use_container_width=True):
            with st.spinner("Scoring..."):
                code, stdout, stderr = run_tool("score_job_fit.py")
            if code == 0:
                st.success("Done!")
                st.rerun()
            else:
                st.error("Failed")
                st.code(stdout + stderr, language="text")

    # Quick stats
    jobs = load_jobs()
    if jobs:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Jobs", len(jobs))
        c2.metric("Matching", len([j for j in jobs if j.get('fit_score', 0) > 0]))
        c3.metric("High Fit (70+)", len([j for j in jobs if j.get('fit_score', 0) >= 70]))

    st.divider()

    # Chrome Extension Status
    st.subheader("Chrome Extension")
    backend_running = check_backend_status()

    c1, c2 = st.columns([2, 1])
    with c1:
        if backend_running:
            st.success("Backend running on localhost:5000")
        else:
            st.warning("Backend not running")

    with c2:
        if not backend_running:
            if st.button("Start Backend", type="primary", use_container_width=True):
                subprocess.Popen(
                    [sys.executable, str(TOOLS_DIR / "answer_questions_api.py")],
                    cwd=str(TOOLS_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                )
                st.info("Starting... refresh in a few seconds")
                time.sleep(2)
                st.rerun()

    # Quick setup instructions
    st.markdown("""
**Setup:** `chrome://extensions` → Enable Developer mode → Load unpacked → Select `chrome-extension/` folder

**Usage:** Open job form → Click extension icon → Copy page content → Get answers
    """)

    # Q&A stats
    databank = load_qa_databank()
    questions_count = len([q for q, a in databank.get("questions", {}).items() if a])
    st.caption(f"Q&A Bank: {questions_count} saved answers")

    # Test API section (only if backend is running)
    if backend_running:
        st.divider()
        st.subheader("Test API")
        test_text = st.text_area("Paste application text to test:", height=100, placeholder="Paste job application text...")

        if st.button("Test Extraction", type="primary"):
            if test_text:
                try:
                    response = requests.post(
                        "http://localhost:5000/api/parse-and-answer",
                        json={"pageText": test_text, "context": {}},
                        timeout=30
                    )
                    if response.ok:
                        data = response.json()
                        st.success(f"Found {data.get('total_questions', 0)} questions")
                        for item in data.get("answers", []):
                            st.markdown(f"**Q:** {item['question']}")
                            st.markdown(f"**A:** {item['answer']}")
                            st.caption(f"Source: {item['source']}")
                            st.divider()
                except Exception as e:
                    st.error(str(e))


# ============================================================
# PAGE 6: HISTORY (Answer Usage Tracking)
# ============================================================

elif page == "History":
    st.markdown("# Answer Usage History")
    st.caption("Track which answers you used for each application")
    st.markdown("---")

    # Load history
    history_path = TMP_DIR / "answer_usage_history.json"
    history = []
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                history.reverse()  # Most recent first
        except Exception as e:
            st.error(f"Failed to load history: {e}")

    if not history:
        st.info("No answer usage tracked yet. Use the Chrome extension to track answers.")
        st.markdown("""
**How tracking works:**
1. Open the Chrome extension on a job application page
2. Parse questions and get answers
3. When you copy an answer, it's automatically tracked
4. See patterns and improve your answers over time
        """)
    else:
        # Stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(history))
        c2.metric("Databank", len([h for h in history if h['source'] == 'databank']))
        c3.metric("Custom", len([h for h in history if h['source'] != 'databank']))
        c4.metric("Edited", len([h for h in history if h.get('was_edited', False)]))

        st.divider()

        # Filters
        st.subheader("Filters")
        c1, c2, c3 = st.columns(3)
        with c1:
            filter_source = st.selectbox("Source", ["All", "Databank", "Custom"], index=0)
        with c2:
            filter_company = st.text_input("Company", placeholder="Filter by company...")
        with c3:
            limit = st.number_input("Show entries", min_value=5, max_value=100, value=20, step=5)

        # Apply filters
        filtered = history
        if filter_source != "All":
            filtered = [h for h in filtered if h['source'].lower() == filter_source.lower()]
        if filter_company:
            filtered = [h for h in filtered if filter_company.lower() in h.get('company', '').lower()]

        filtered = filtered[:int(limit)]

        st.divider()

        # Show history in clean cards
        st.subheader(f"Recent Activity ({len(filtered)} / {len(history)} entries)")

        for idx, entry in enumerate(filtered):
            with st.container():
                # Header row
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{entry.get('company', 'Unknown Company')}**")
                with c2:
                    st.caption(entry['timestamp'][:10])
                with c3:
                    edited_suffix = " (edited)" if entry.get('was_edited') else ""
                    st.caption(f"{entry['source']}{edited_suffix}")

                # Question & Answer
                st.markdown(f"**Q:** {entry['question']}")
                st.text_area("Answer", entry['answer'], height=80, disabled=True, label_visibility="collapsed", key=f"ans_{idx}")

                # Job link if available
                if entry.get('job_url'):
                    st.link_button("View Job", entry['job_url'], use_container_width=False)

                st.divider()

        # Export
        if st.button("Export History as JSON", use_container_width=True):
            st.download_button(
                "Download",
                data=json.dumps(history, indent=2),
                file_name=f"answer_history_{datetime.datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
