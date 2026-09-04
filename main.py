import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st

try:
    from config import API_KEY as CONFIG_API_KEY
except ImportError:
    CONFIG_API_KEY = ""


# ---------------------------------------------------------
# 1. APP CONFIGURATION & LIGHT EDITORIAL PALETTE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Audit Intelligence | Global Banking Briefing",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #F7F8FA;
        --card: #FFFFFF;
        --border: #E5E7EB;
        --text-primary: #111827;
        --text-secondary: #6B7280;
        --text-muted: #9CA3AF;
        --accent-blue: #2563EB;
        --accent-blue-dark: #1D4ED8;
        --up: #16A34A;
        --down: #DC2626;
        --amber: #B45309;
    }

    .stApp {
        background: var(--bg);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    #MainMenu, header[data-testid="stHeader"] { background: transparent; }

    /* ---------------- Top navigation ---------------- */
    .topnav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 2px 18px 2px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 8px;
    }
    .topnav-left { display: flex; align-items: center; gap: 14px; }

    /* Gradient tile holding an inline radar/analytics mark (replaces the shield) */
    .logo-icon {
        width: 52px; height: 52px; border-radius: 14px;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 55%, #4F46E5 100%);
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.30);
    }
    .logo-icon svg { width: 30px; height: 30px; display: block; }

    .logo-text {
        font-weight: 900;
        font-size: 34px;
        color: var(--text-primary);
        letter-spacing: -1.1px;
        line-height: 1.05;
    }
    .logo-sub {
        font-size: 11.5px; font-weight: 600; color: var(--text-muted);
        letter-spacing: 1.4px; text-transform: uppercase; margin-top: 3px;
    }

    /* ---- Top-right principal (Pragati) block — enlarged ---- */
    .topnav-user {
        display: flex; align-items: center; gap: 16px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 12px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .topnav-user-meta { text-align: right; line-height: 1.3; }
    .topnav-user-label {
        font-size: 10px; font-weight: 700; color: var(--accent-blue);
        letter-spacing: 1px; text-transform: uppercase; margin-bottom: 3px;
    }
    .topnav-user-name { font-weight: 800; font-size: 20px; color: var(--text-primary); letter-spacing: -0.3px; }
    .topnav-user-title { font-size: 13.5px; color: var(--text-secondary); font-weight: 500; }
    .topnav-user-stamp { font-size: 11px; color: var(--text-muted); margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
    .avatar-photo {
        width: 68px; height: 68px; border-radius: 50%;
        object-fit: cover; flex-shrink: 0;
        border: 3px solid #fff;
        box-shadow: 0 0 0 2px var(--accent-blue);
    }
    .avatar-circle-lg {
        width: 68px; height: 68px; border-radius: 50%;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 26px; color: #fff; flex-shrink: 0;
        box-shadow: 0 0 0 2px var(--accent-blue);
    }

    /* ---------------- Action bar (refresh) ---------------- */
    .action-caption {
        font-size: 11.5px; color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace; padding-top: 10px;
    }

    /* ---------------- Section headings ---------------- */
    .section-heading {
        font-size: 15px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 4px 0 14px 0;
    }
    .page-title {
        font-size: 26px;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: -0.5px;
        margin-bottom: 2px;
    }
    .page-subtitle {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 20px;
    }

    /* ---------------- Pill tabs ---------------- */
    div[data-testid="stTabs"] { margin-top: 4px; margin-bottom: 20px; }
    div[data-testid="stTabs"] [role="tablist"] { gap: 4px; border-bottom: 1px solid var(--border); }
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 0 !important;
        padding: 8px 16px !important;
        font-size: 12.5px !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        color: var(--text-muted) !important;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover { color: var(--text-primary) !important; }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--accent-blue) !important;
        border-bottom: 2px solid var(--accent-blue) !important;
    }

    /* ---------------- Inputs ---------------- */
    .stTextInput>div>div>input {
        background-color: #fff !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 10px !important;
        padding: 11px 16px !important;
        font-size: 14px !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }

    /* ---------------- Buttons ---------------- */
    .stButton>button {
        background: var(--accent-blue);
        color: #fff;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13.5px;
        padding: 9px 18px;
    }
    .stButton>button:hover { background: var(--accent-blue-dark); }
    [data-testid="stDownloadButton"]>button {
        background: #fff;
        color: var(--accent-blue);
        border: 1px solid var(--accent-blue);
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stDownloadButton"]>button:hover { background: #EFF6FF; }

    /* ---------------- Force a legible light theme inside controls ---------------- */
    [data-testid="stExpander"] {
        background: #fff !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }
    [data-testid="stExpander"] summary {
        background: #fff !important;
        color: var(--text-primary) !important;
    }
    [data-testid="stExpander"] summary:hover { color: var(--accent-blue) !important; }
    [data-testid="stExpanderDetails"] { background: #fff !important; }
    [data-testid="stExpander"] label,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] div { color: var(--text-primary) !important; }
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] { color: var(--text-secondary) !important; }
    [data-testid="stSlider"] div[data-baseweb="slider"] > div { background: #E5E7EB !important; }
    [data-testid="stSlider"] div[role="slider"] {
        background-color: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
    }
    div[data-baseweb="tag"] {
        background-color: rgba(37, 99, 235, 0.10) !important;
        border: 1px solid rgba(37, 99, 235, 0.35) !important;
        color: var(--accent-blue) !important;
    }
    div[data-baseweb="tag"] span { color: var(--accent-blue) !important; }
    div[data-baseweb="tag"] svg { fill: var(--accent-blue) !important; }

    /* ---------------- Featured Analysis hero ---------------- */
    .featured-hero {
        position: relative;
        height: 360px;
        border-radius: 16px;
        background-size: cover;
        background-position: center;
        overflow: hidden;
        margin-bottom: 30px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .featured-badge {
        position: absolute; top: 20px; left: 20px;
        color: #fff; font-size: 11px; font-weight: 700;
        padding: 5px 12px; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 0.5px;
        z-index: 2;
    }
    .featured-text { position: absolute; bottom: 24px; left: 28px; right: 28px; z-index: 2; }
    .featured-title {
        font-size: 27px; font-weight: 800; color: #fff; line-height: 1.28;
        margin-bottom: 8px; text-shadow: 0 2px 10px rgba(0,0,0,0.35);
    }
    .featured-meta { font-size: 13px; color: rgba(255,255,255,0.85); font-weight: 500; }
    .featured-link-overlay { position: absolute; inset: 0; z-index: 3; }

    /* ---------------- Insight cards ---------------- */
    .insight-card {
        display: flex;
        gap: 20px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        transition: box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .insight-card:hover { border-color: #D1D5DB; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
    .insight-thumb {
        width: 180px; min-width: 180px; height: 128px;
        background-size: cover; background-position: center;
        background-color: #F3F4F6;
        border-radius: 10px;
    }
    .insight-thumb-empty {
        display: flex; align-items: center; justify-content: center;
        font-size: 28px; color: #C7CBD3;
    }
    .insight-content { display: flex; flex-direction: column; min-width: 0; }
    .insight-meta-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .badge {
        display: inline-block; color: #fff; font-size: 10.5px; font-weight: 700;
        padding: 3px 10px; border-radius: 5px; text-transform: uppercase; letter-spacing: 0.4px;
    }
    .insight-date { font-size: 12px; color: var(--text-muted); font-weight: 500; }
    .insight-title-link { text-decoration: none; }
    .insight-title {
        font-size: 17px; font-weight: 700; color: var(--text-primary);
        line-height: 1.35; margin-bottom: 6px;
    }
    .insight-title-link:hover .insight-title { color: var(--accent-blue); }
    .insight-desc {
        font-size: 13.5px; color: var(--text-secondary); line-height: 1.55;
        margin-bottom: 12px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .insight-footer { display: flex; justify-content: flex-end; align-items: center; margin-top: auto; }
    .read-link {
        font-size: 12.5px; font-weight: 700; color: var(--accent-blue); text-decoration: none;
    }
    .read-link:hover { text-decoration: underline; }

    /* ---------------- Right sidebar panels ---------------- */
    .side-panel {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    .side-panel-title {
        font-size: 11px; font-weight: 700; color: var(--text-secondary);
        text-transform: uppercase; letter-spacing: 0.8px;
        margin-bottom: 14px; display: flex; align-items: center; gap: 6px;
    }
    .filter-row, .pulse-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px; color: #374151;
    }
    .filter-row:last-child, .pulse-row:last-child { border-bottom: none; }
    .filter-value { font-weight: 600; color: var(--text-primary); }
    .pulse-value { font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }

    /* ---------------- Market panel ---------------- */
    .mkt-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 9px 0; border-bottom: 1px solid #F3F4F6;
    }
    .mkt-row:last-child { border-bottom: none; }
    .mkt-name { font-size: 13px; font-weight: 600; color: #374151; }
    .mkt-sub { font-size: 10.5px; color: var(--text-muted); font-weight: 500; }
    .mkt-right { text-align: right; }
    .mkt-price { font-size: 13.5px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
    .mkt-chg { font-size: 11.5px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .mkt-up { color: var(--up); }
    .mkt-down { color: var(--down); }
    .mkt-stamp { font-size: 10.5px; color: var(--text-muted); margin-top: 12px; }

    /* ---------------- Risk radar / exposure bars ---------------- */
    .risk-row { padding: 8px 0; border-bottom: 1px solid #F3F4F6; }
    .risk-row:last-child { border-bottom: none; }
    .risk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .risk-name { font-size: 12.5px; font-weight: 600; color: #374151; }
    .risk-count { font-size: 11px; font-weight: 700; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }
    .risk-track { height: 6px; background: #F3F4F6; border-radius: 3px; overflow: hidden; }
    .risk-fill { height: 100%; border-radius: 3px; }

    .alert-item {
        display: block; text-decoration: none;
        padding: 9px 0; border-bottom: 1px solid #F3F4F6;
    }
    .alert-item:last-child { border-bottom: none; }
    .alert-tag {
        font-size: 9.5px; font-weight: 800; color: var(--amber);
        letter-spacing: 0.6px; text-transform: uppercase;
    }
    .alert-text {
        font-size: 12.5px; color: var(--text-primary); font-weight: 600; line-height: 1.4; margin-top: 3px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .alert-item:hover .alert-text { color: var(--accent-blue); }

    .cta-panel {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        border-radius: 14px;
        padding: 20px 22px 6px 22px;
        color: #fff;
        margin-bottom: -4px;
    }
    .cta-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
    .cta-desc { font-size: 12.5px; color: rgba(255,255,255,0.85); line-height: 1.5; margin-bottom: 14px; }

    /* ---------------- Empty state ---------------- */
    .empty-state-panel {
        text-align: center; padding: 48px;
        background: var(--card); border-radius: 16px; border: 1px dashed var(--border);
        margin-top: 14px;
    }

    /* ---------------- Footer ---------------- */
    .app-footer {
        display: flex; justify-content: space-between; align-items: flex-start;
        padding-top: 22px; margin-top: 8px;
    }
    .footer-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-weight: 800; font-size: 14.5px; color: var(--text-primary); }
    .footer-tagline { font-size: 12px; color: var(--text-muted); max-width: 320px; line-height: 1.5; }
    .footer-links { display: flex; gap: 22px; font-size: 12.5px; color: var(--text-secondary); font-weight: 600; }
    .footer-copyright { font-size: 11.5px; color: var(--text-muted); margin-top: 18px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. BANKING AUDIT CATEGORIES & QUERIES
#    Each category now runs MULTIPLE query variants so the feed
#    pulls far more distinct articles from NewsAPI.
# ---------------------------------------------------------

CATEGORIES = {
    "Transformation": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance") AND ("digital transformation" OR "modernization" OR "core banking" OR "automation" OR "artificial intelligence" OR "generative AI" OR "cloud")',
            '("bank" OR "banking") AND ("core banking" OR "digital banking" OR "cloud migration" OR "legacy modernisation" OR "operating model")',
            '("bank" OR "lender" OR "financial services") AND ("artificial intelligence" OR "generative AI" OR "machine learning" OR "automation") AND ("risk" OR "controls" OR "governance" OR "deployment")',
        ]
    },
    "Regulation": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "compliance" OR "risk" OR "governance") AND ("regulation" OR "regulatory" OR "supervision" OR "RBI" OR "Basel" OR "AML" OR "KYC" OR "sanctions" OR "prudential" OR "enforcement")',
            '("Reserve Bank of India" OR "RBI" OR "central bank") AND ("circular" OR "guidelines" OR "penalty" OR "supervisory action" OR "master direction" OR "compliance")',
            '("bank" OR "banking") AND ("anti-money laundering" OR "AML" OR "KYC" OR "sanctions" OR "financial crime" OR "fraud" OR "enforcement action" OR "fined" OR "penalised")',
            '("bank" OR "financial institution") AND ("Basel" OR "prudential" OR "capital adequacy" OR "regulatory capital" OR "stress test" OR "supervisory review")',
        ]
    },
    "People": {
        "queries": [
            '("bank" OR "banking" OR "financial institution") AND ("audit" OR "risk" OR "governance" OR "controls") AND ("appointed" OR "appointment" OR "CEO" OR "CFO" OR "CRO" OR "CISO" OR "chief audit" OR "internal audit" OR "audit committee" OR "board")',
            '("bank" OR "banking group") AND ("chief audit executive" OR "head of internal audit" OR "chief risk officer" OR "chief compliance officer" OR "audit committee chair")',
            '("bank" OR "lender") AND ("resigns" OR "steps down" OR "elevated" OR "promoted" OR "succession" OR "board appointment" OR "reshuffle")',
        ]
    },
    "Global Banks": {
        "queries": [
            '("bank" OR "banking group" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance" OR "regulatory") AND ("HSBC" OR "JPMorgan" OR "JPMorgan Chase" OR "Citi" OR "Citigroup" OR "Barclays" OR "Deutsche Bank" OR "UBS" OR "BNP Paribas" OR "Santander" OR "Standard Chartered")',
            '("Bank of America" OR "Goldman Sachs" OR "Morgan Stanley" OR "Wells Fargo" OR "ING" OR "ICBC" OR "MUFG" OR "Mizuho") AND ("audit" OR "risk" OR "compliance" OR "regulator" OR "governance" OR "controls" OR "fine")',
            '("HSBC" OR "Standard Chartered" OR "Citi" OR "Barclays" OR "Deutsche Bank" OR "UBS") AND ("investigation" OR "probe" OR "penalty" OR "settlement" OR "remediation" OR "internal review")',
        ]
    },
}

CATEGORY_DISPLAY = {
    "Transformation": "Transformation",
    "Regulation": "Regulation",
    "People": "People",
    "Global Banks": "Global Banking",
}
CATEGORY_COLORS = {
    "Transformation": "#2563EB",
    "Regulation": "#16A34A",
    "People": "#6B7280",
    "Global Banks": "#7C3AED",
}

# NewsAPI allows pageSize up to 100 on /v2/everything.
PAGE_SIZE = 100
# Free/Developer plans cap results at the first 100 per query; paid plans paginate further.
# Extra pages fail gracefully and are reported in diagnostics.
MAX_PAGES = 2

# Head of Internal Audit Department — shown top-right
PRAGATI_NAME = "Pragati"
PRAGATI_TITLE = "Head of Internal Audit"
# NOTE: paste your existing base64 string back here.
PRAGATI_PHOTO_B64 = "PASTE_YOUR_EXISTING_BASE64_STRING_HERE"

AUDIT_TERMS = [
    "internal audit", "external audit", "audit committee", "auditor",
    "audit finding", "audit findings", "internal control", "internal controls",
    "control weakness", "control weaknesses", "control deficiency",
    "control deficiencies", "governance", "risk management", "operational risk",
    "model risk", "compliance", "regulatory", "regulation", "supervision",
    "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
    "sanctions", "fraud", "misconduct", "financial crime",
    # Broader banking-risk vocabulary so genuinely relevant stories are not dropped
    "bank", "banking", "lender", "rbi", "central bank", "basel", "npa",
    "asset quality", "provisioning", "capital adequacy", "credit risk",
    "liquidity", "penalty", "fined", "probe", "investigation", "whistleblower",
    "disclosure", "restatement", "irregularities", "lapses",
]

# Terms that should always escalate a story into the priority alert panel
ALERT_TERMS = [
    "enforcement", "penalty", "fined", "fine", "fraud", "misconduct",
    "investigation", "probe", "money laundering", "aml", "sanctions",
    "irregularities", "lapses", "control deficiency", "restatement",
    "whistleblower", "settlement",
]

CATEGORY_TERMS = {
    "Transformation": [
        "digital transformation", "modernization", "modernisation", "core banking",
        "automation", "artificial intelligence", "generative ai", "genai",
        "machine learning", "cloud", "digital banking", "technology transformation",
        "operating model",
    ],
    "Regulation": [
        "regulation", "regulatory", "rbi", "basel", "prudential", "supervision",
        "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
        "sanctions", "capital requirements", "regulatory capital", "compliance",
    ],
    "People": [
        "appointed", "appointment", "ceo", "cfo", "cro", "ciso", "chief audit",
        "internal audit", "audit committee", "board", "director", "chairman",
        "chairwoman", "leadership", "executive",
    ],
    "Global Banks": [
        "hsbc", "jpmorgan", "jpmorgan chase", "citi", "citigroup", "barclays",
        "deutsche bank", "ubs", "bnpparibas", "bnp paribas", "santander",
        "standard chartered", "bank of america", "goldman sachs", "morgan stanley",
        "wells fargo", "ing", "icbc", "mufg", "mizuho",
    ],
}

# Risk themes tracked in the "Risk Radar" panel (counts computed from the live feed)
RISK_THEMES = {
    "Financial crime / AML": (["aml", "anti-money laundering", "money laundering", "kyc", "financial crime", "sanctions"], "#DC2626"),
    "Enforcement / penalties": (["enforcement", "penalty", "fined", "fine", "settlement", "supervisory action"], "#EA580C"),
    "Fraud & misconduct": (["fraud", "misconduct", "irregularities", "lapses", "whistleblower"], "#B45309"),
    "Credit & asset quality": (["npa", "asset quality", "provisioning", "credit risk", "bad loan", "slippage"], "#7C3AED"),
    "Technology & AI risk": (["artificial intelligence", "generative ai", "cloud", "automation", "core banking", "outage"], "#2563EB"),
}


# ---------------------------------------------------------
# 3. EXTRACTION LOGIC & SCORING FUNCTIONS
# ---------------------------------------------------------

def get_api_key():
    """Use Streamlit secrets/env first; the in-page form is the fallback."""
    if CONFIG_API_KEY.strip():
        return CONFIG_API_KEY.strip()

    env_key = os.getenv("NEWSAPI_KEY", "").strip()
    if env_key:
        return env_key

    try:
        secret_key = st.secrets.get("API_KEY", "") or st.secrets.get("NEWSAPI_KEY", "")
        if secret_key:
            return str(secret_key).strip()
    except Exception:
        pass

    return ""


def normalize_text(article):
    fields = [
        article.get("title") or "",
        article.get("description") or "",
        article.get("content") or "",
    ]
    return " ".join(fields).lower()


def audit_relevance(text):
    """Simple, transparent audit relevance score."""
    score = 0
    for term in AUDIT_TERMS:
        if term in text:
            score += 5

    for term in [
        "internal audit", "audit committee", "internal controls",
        "control deficiency", "regulatory enforcement",
        "model risk", "financial crime",
    ]:
        if term in text:
            score += 10

    return min(score, 100)


def classify_article(article):
    """Classify using transparent keyword scoring."""
    text = normalize_text(article)
    scores = {}

    for category, terms in CATEGORY_TERMS.items():
        score = 0
        for term in terms:
            if term in text:
                score += 1
        scores[category] = score

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        best_category = "Regulation"

    return best_category, scores[best_category]


def fetch_query(category, query, api_key, from_date, page_size, page):
    """Fetch a single page of one query variant from NewsAPI."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "page": page,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=25)
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "NewsAPI returned an error."))

    articles = payload.get("articles", [])
    for article in articles:
        article["_query_category"] = category

    return articles, payload.get("totalResults", 0)


@st.cache_data(ttl=300, show_spinner=False)
def load_news(api_key, lookback_days, page_size, min_relevance):
    """
    Fan out every category's query variants (and pages) in parallel,
    then dedupe and score. Cached for 5 minutes; the Refresh button clears it.
    """
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    jobs = []
    for category, settings in CATEGORIES.items():
        for query in settings["queries"]:
            for page in range(1, MAX_PAGES + 1):
                jobs.append((category, query, page))

    all_articles = []
    errors = []
    api_total = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_query, category, query, api_key, from_date, page_size, page):
                (category, page)
            for category, query, page in jobs
        }

        for future in as_completed(futures):
            category, page = futures[future]
            try:
                rows, total = future.result()
                all_articles.extend(rows)
                api_total = max(api_total, total)
            except Exception as exc:
                msg = str(exc)
                # Page-2+ failures on the free tier are expected, not real errors
                if page > 1 and ("upgrade" in msg.lower() or "developer" in msg.lower()):
                    continue
                errors.append(f"{category} (page {page}): {msg}")

    raw_count = len(all_articles)

    # Deduplicate by URL first, then by normalized title
    unique = {}
    title_keys = set()

    for article in all_articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip().lower()
        key = url if url else title

        if not key or key in unique or title in title_keys:
            continue

        # NewsAPI marks pulled/blocked items as "[Removed]"
        if title.startswith("[removed]"):
            continue

        unique[key] = article
        title_keys.add(title)

    deduped_count = len(unique)

    cleaned = []
    dropped_low_relevance = 0

    for article in unique.values():
        text = normalize_text(article)
        relevance = audit_relevance(text)

        if relevance < min_relevance:
            dropped_low_relevance += 1
            continue

        category, category_score = classify_article(article)

        source = article.get("source") or {}
        published = article.get("publishedAt") or ""

        cleaned.append({
            "category": category,
            "audit_relevance": relevance,
            "category_score": category_score,
            "title": article.get("title") or "Untitled",
            "description": article.get("description") or "",
            "source": source.get("name") or "Institutional Source",
            "publishedAt": published,
            "url": article.get("url") or "",
            "author": article.get("author") or "",
            "image_url": article.get("urlToImage") or "",
        })

    cleaned.sort(key=lambda x: (x["audit_relevance"], x["publishedAt"]), reverse=True)

    stats = {
        "queries_run": len(jobs),
        "raw": raw_count,
        "deduped": deduped_count,
        "dropped_low_relevance": dropped_low_relevance,
        "kept": len(cleaned),
        "api_total_reported": api_total,
    }
    return cleaned, errors, stats


def format_relative_time(pub_date_str):
    """Formats relative date nicely (e.g. '3 days ago', '1 week ago')."""
    if not pub_date_str:
        return "Recent"
    try:
        clean_str = pub_date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        now = datetime.now(timezone.utc)
        diff = now - dt
        days = diff.days
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        elif days < 7:
            return f"{days} days ago"
        elif days < 14:
            return "1 week ago"
        else:
            return f"{days // 7} weeks ago"
    except Exception:
        return pub_date_str[:10] if len(pub_date_str) >= 10 else "Recent"


def ist_now_str():
    stamp = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return stamp.strftime("%d %b %Y, %H:%M IST")


# ---------------------------------------------------------
# 3b. LIVE MARKET SNAPSHOT
# ---------------------------------------------------------

MARKET_TICKERS = [
    ("^BSESN",   "SENSEX",      "BSE 30"),
    ("^NSEI",    "NIFTY 50",    "NSE"),
    ("^NSEBANK", "BANK NIFTY",  "NSE Banks"),
    ("USDINR=X", "USD / INR",   "Spot FX"),
    ("BZ=F",     "Brent Crude", "USD/bbl"),
    ("GC=F",     "Gold",        "USD/oz"),
]

YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YF_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AuditIntel/1.0)"}


def fetch_quote(symbol):
    """Fetch last price + change for one symbol from the public Yahoo chart endpoint."""
    resp = requests.get(
        YF_CHART_URL.format(symbol=symbol),
        params={"range": "1d", "interval": "5m"},
        headers=YF_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    meta = resp.json()["chart"]["result"][0]["meta"]

    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")

    if price is None or not prev:
        raise ValueError("No price data returned")

    change = price - prev
    pct = (change / prev) * 100
    return {"price": float(price), "change": float(change), "pct": float(pct)}


@st.cache_data(ttl=180, show_spinner=False)
def load_market_snapshot():
    """Pull all market quotes in parallel. Cached 3 min; Refresh button clears it."""
    results = {}

    with ThreadPoolExecutor(max_workers=len(MARKET_TICKERS)) as executor:
        futures = {
            executor.submit(fetch_quote, symbol): symbol
            for symbol, _, _ in MARKET_TICKERS
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception:
                results[symbol] = None

    return results, ist_now_str()


def render_market_panel():
    quotes, stamp = load_market_snapshot()

    rows_html = ""
    for symbol, name, sub in MARKET_TICKERS:
        q = quotes.get(symbol)

        if not q:
            rows_html += (
                f'<div class="mkt-row">'
                f'<div><div class="mkt-name">{name}</div><div class="mkt-sub">{sub}</div></div>'
                f'<div class="mkt-right"><div class="mkt-price" style="color:#9CA3AF;">—</div>'
                f'<div class="mkt-chg" style="color:#9CA3AF;">unavailable</div></div>'
                f'</div>'
            )
            continue

        cls = "mkt-up" if q["pct"] >= 0 else "mkt-down"
        arrow = "▲" if q["pct"] >= 0 else "▼"
        rows_html += (
            f'<div class="mkt-row">'
            f'<div><div class="mkt-name">{name}</div><div class="mkt-sub">{sub}</div></div>'
            f'<div class="mkt-right"><div class="mkt-price">{q["price"]:,.2f}</div>'
            f'<div class="mkt-chg {cls}">{arrow} {abs(q["change"]):,.2f} ({abs(q["pct"]):.2f}%)</div></div>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📈 Live Market Snapshot</div>
        {rows_html}
        <div class="mkt-stamp">Last refreshed {stamp} · delayed data, indicative only</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# 3c. RISK RADAR + PRIORITY ALERTS (computed from the live feed)
# ---------------------------------------------------------

def render_risk_radar(rows):
    """Theme exposure across the current feed — real counts, no invented data."""
    if not rows:
        return

    counts = {}
    for theme, (terms, color) in RISK_THEMES.items():
        n = 0
        for row in rows:
            text = f'{row["title"]} {row["description"]}'.lower()
            if any(t in text for t in terms):
                n += 1
        counts[theme] = (n, color)

    peak = max((n for n, _ in counts.values()), default=0)
    if peak == 0:
        return

    rows_html = ""
    for theme, (n, color) in sorted(counts.items(), key=lambda x: x[1][0], reverse=True):
        width = int((n / peak) * 100) if peak else 0
        rows_html += (
            f'<div class="risk-row">'
            f'<div class="risk-head"><span class="risk-name">{theme}</span>'
            f'<span class="risk-count">{n}</span></div>'
            f'<div class="risk-track"><div class="risk-fill" style="width:{width}%; background:{color};"></div></div>'
            f'</div>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">🎯 Risk Radar · Theme Exposure</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


def render_priority_alerts(rows, limit=5):
    """Stories carrying enforcement / fraud / AML signals — the ones a CAE reads first."""
    flagged = []
    for row in rows:
        text = f'{row["title"]} {row["description"]}'.lower()
        hits = [t for t in ALERT_TERMS if t in text]
        if hits:
            flagged.append((len(hits), row, hits[0]))

    if not flagged:
        return

    flagged.sort(key=lambda x: (x[0], x[1]["audit_relevance"]), reverse=True)

    items_html = ""
    for _, row, tag in flagged[:limit]:
        items_html += (
            f'<a class="alert-item" href="{row["url"]}" target="_blank">'
            f'<div class="alert-tag">⚠ {tag.upper()} · {row["source"]}</div>'
            f'<div class="alert-text">{row["title"]}</div>'
            f'</a>'
        )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">🚨 Priority Alerts ({len(flagged)})</div>
        {items_html}
    </div>
    """, unsafe_allow_html=True)


def render_source_panel(rows, limit=5):
    """Which outlets are driving the briefing — useful for source-reliance judgement."""
    if not rows:
        return

    counter = Counter(r["source"] for r in rows)
    rows_html = "".join(
        f'<div class="pulse-row"><span>{name}</span><span class="pulse-value">{n}</span></div>'
        for name, n in counter.most_common(limit)
    )

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📰 Top Sources</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# 4. TOP NAVIGATION — bigger wordmark, radar logo, larger principal block
# ---------------------------------------------------------

if PRAGATI_PHOTO_B64 and not PRAGATI_PHOTO_B64.startswith("PASTE_"):
    avatar_html = (
        f'<img src="data:image/jpeg;base64,{PRAGATI_PHOTO_B64}" '
        f'class="avatar-photo" alt="{PRAGATI_NAME}" />'
    )
else:
    avatar_html = f'<div class="avatar-circle-lg">{PRAGATI_NAME[:1].upper()}</div>'

# Inline SVG: concentric radar sweep with a rising signal bar — reads as
# "surveillance + analytics" rather than the generic security shield.
LOGO_SVG = """
<svg viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.9"
     stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="9" opacity="0.35"/>
  <circle cx="12" cy="12" r="5.5" opacity="0.6"/>
  <circle cx="12" cy="12" r="1.6" fill="#FFFFFF" stroke="none"/>
  <path d="M12 12 L18.4 5.6" opacity="0.95"/>
  <path d="M6.5 16.5 L9.5 13.2 L12.2 15 L16.4 9.8" opacity="0.95"/>
</svg>
"""

st.markdown(f"""
<div class="topnav">
    <div class="topnav-left">
        <div class="logo-icon">{LOGO_SVG}</div>
        <div>
            <div class="logo-text">Audit Intelligence</div>
            <div class="logo-sub">Global Banking Risk & Controls Briefing</div>
        </div>
    </div>
    <div class="topnav-user">
        <div class="topnav-user-meta">
            <div class="topnav-user-label">Prepared for</div>
            <div class="topnav-user-name">{PRAGATI_NAME}</div>
            <div class="topnav-user-title">{PRAGATI_TITLE}</div>
            <div class="topnav-user-stamp">{ist_now_str()}</div>
        </div>
        {avatar_html}
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 5. ACTION BAR — one button refreshes BOTH news and markets
# ---------------------------------------------------------

api_key = get_api_key()

act_l, act_r = st.columns([1, 4])

with act_l:
    hard_refresh = st.button("⟲  Refresh All Data", use_container_width=True, key="refresh_all")

with act_r:
    last_run = st.session_state.get("last_refresh", "not yet loaded this session")
    st.markdown(
        f'<div class="action-caption">News + market data · last pulled: {last_run}</div>',
        unsafe_allow_html=True,
    )

if hard_refresh:
    # Clear both caches so the next call genuinely re-hits NewsAPI and Yahoo
    load_news.clear()
    load_market_snapshot.clear()
    st.session_state.pop("news_loaded", None)


# ---------------------------------------------------------
# 6. DATA CONTROLS
# ---------------------------------------------------------

with st.expander("⚙️  Advanced Filters & Data Controls", expanded=(not api_key)):
    if not api_key:
        api_key = st.text_input(
            "NewsAPI Key",
            type="password",
            placeholder="Enter API key...",
            help="Configurable via secrets.toml or config.py for a persistent setup.",
        )

    ctrl_a, ctrl_b = st.columns(2)

    with ctrl_a:
        lookback_days = st.slider("Lookback Window (Days)", min_value=1, max_value=30, value=7)

    with ctrl_b:
        min_relevance = st.slider(
            "Minimum Audit Relevance",
            min_value=0, max_value=40, value=5, step=5,
            help="Lower this to widen the feed; raise it to keep only high-signal stories.",
        )

    selected_categories = st.multiselect(
        "Active Categories",
        options=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        format_func=lambda c: CATEGORY_DISPLAY.get(c, c),
    )

if not api_key:
    st.info("💡 Please enter your NewsAPI key above (or configure API_KEY in Streamlit secrets) to load the briefing.")
    st.stop()


# ---------------------------------------------------------
# 7. DATA INGESTION & FILTERING
# ---------------------------------------------------------

params_key = (lookback_days, min_relevance)

if ("news_loaded" not in st.session_state) or (st.session_state.get("params_key") != params_key):
    with st.spinner("Compiling the audit intelligence briefing..."):
        articles, errors, stats = load_news(api_key, lookback_days, PAGE_SIZE, min_relevance)

    st.session_state.news = articles
    st.session_state.news_errors = errors
    st.session_state.news_stats = stats
    st.session_state.news_loaded = True
    st.session_state.params_key = params_key
    st.session_state.last_refresh = ist_now_str()

articles = st.session_state.get("news", [])
errors = st.session_state.get("news_errors", [])
stats = st.session_state.get("news_stats", {})

filtered = [a for a in articles if a["category"] in selected_categories] if selected_categories else []

# Ingestion diagnostics — shows exactly where articles are being lost
with st.expander("🔎 Ingestion Diagnostics", expanded=False):
    if stats:
        st.markdown(
            f"""
            <div style="font-size:12.5px; color:#374151; line-height:1.9;">
            <b>{stats['queries_run']}</b> query/page requests sent ·
            <b>{stats['raw']}</b> articles returned by NewsAPI ·
            <b>{stats['deduped']}</b> after de-duplication ·
            <b>{stats['dropped_low_relevance']}</b> dropped below the relevance floor ·
            <b>{stats['kept']}</b> retained in the briefing
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "If 'retained' is low, lower the Minimum Audit Relevance slider or widen the "
            "lookback window. NewsAPI's free tier also caps each query at 100 results and "
            "roughly one month of history."
        )
    for err in errors:
        st.markdown(f"<div style='font-size:12px; color:#B45309;'>• {err}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 8. PAGE TITLE
# ---------------------------------------------------------

st.markdown('<div class="page-title">This week\'s briefing</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-subtitle">{len(filtered)} items &nbsp;·&nbsp; verified banking internal controls & regulatory surveillance</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 9. RENDER HELPERS
# ---------------------------------------------------------

def render_featured(article):
    color = CATEGORY_COLORS.get(article["category"], "#374151")
    label = CATEGORY_DISPLAY.get(article["category"], article["category"])
    rel_time = format_relative_time(article["publishedAt"])

    if article["image_url"]:
        bg = f'linear-gradient(180deg, rgba(17,24,39,0) 35%, rgba(17,24,39,0.88) 100%), url(\'{article["image_url"]}\')'
    else:
        bg = 'linear-gradient(135deg, #1E3A8A, #2563EB)'

    st.markdown(f"""
    <div class="featured-hero" style="background-image: {bg};">
        <div class="featured-badge" style="background: {color};">{label}</div>
        <div class="featured-text">
            <div class="featured-title">{article['title']}</div>
            <div class="featured-meta">By {article['source']} &nbsp;·&nbsp; {rel_time}</div>
        </div>
        <a href="{article['url']}" target="_blank" class="featured-link-overlay"></a>
    </div>
    """, unsafe_allow_html=True)


def render_insight_card(article):
    color = CATEGORY_COLORS.get(article["category"], "#374151")
    label = CATEGORY_DISPLAY.get(article["category"], article["category"])
    rel_time = format_relative_time(article["publishedAt"])
    description_text = article["description"] or "Independent institutional briefing coverage. Select below to review the full verified source documentation."

    if article["image_url"]:
        thumb_html = f'<div class="insight-thumb" style="background-image: url(\'{article["image_url"]}\');"></div>'
    else:
        thumb_html = '<div class="insight-thumb insight-thumb-empty">📰</div>'

    st.markdown(f"""
    <div class="insight-card">
        {thumb_html}
        <div class="insight-content">
            <div class="insight-meta-row">
                <span class="badge" style="background: {color};">{label}</span>
                <span class="insight-date">{rel_time}</span>
            </div>
            <a href="{article['url']}" target="_blank" class="insight-title-link">
                <div class="insight-title">{article['title']}</div>
            </a>
            <div class="insight-desc">{description_text}</div>
            <div class="insight-footer">
                <a href="{article['url']}" target="_blank" class="read-link">Read source ↗</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_feed(rows, show_featured=True):
    if not rows:
        st.markdown("""
        <div class="empty-state-panel">
            <div style="font-size: 18px; font-weight: 700; color: #111827;">No briefing stories found</div>
            <div style="font-size: 13.5px; color: #6B7280; margin-top: 6px;">Try expanding the lookback window or lowering the relevance floor above.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if show_featured:
        st.markdown('<div class="section-heading">Featured Analysis</div>', unsafe_allow_html=True)
        render_featured(rows[0])
        rest = rows[1:]
    else:
        rest = rows

    if rest:
        st.markdown('<div class="section-heading">Latest Insights</div>', unsafe_allow_html=True)
        for art in rest:
            render_insight_card(art)


# ---------------------------------------------------------
# 10. MAIN LAYOUT — feed (left) + intelligence sidebar (right)
# ---------------------------------------------------------

col_main, col_side = st.columns([2.3, 1], gap="large")

with col_main:
    if not filtered:
        render_feed(filtered)
    else:
        tab_labels = ["All Insights"] + [CATEGORY_DISPLAY.get(c, c) for c in selected_categories]
        tabs = st.tabs(tab_labels)

        with tabs[0]:
            render_feed(filtered, show_featured=True)

        for tab, category in zip(tabs[1:], selected_categories):
            with tab:
                cat_rows = [a for a in filtered if a["category"] == category]
                render_feed(cat_rows, show_featured=False)

with col_side:
    render_market_panel()
    render_priority_alerts(filtered)
    render_risk_radar(filtered)
    render_source_panel(filtered)

    active_categories = ", ".join(CATEGORY_DISPLAY.get(c, c) for c in selected_categories) or "None selected"
    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">⚙️ Active Filters</div>
        <div class="filter-row"><span>Categories</span><span class="filter-value">{active_categories}</span></div>
        <div class="filter-row"><span>Lookback</span><span class="filter-value">Last {lookback_days}d</span></div>
        <div class="filter-row"><span>Relevance floor</span><span class="filter-value">{min_relevance}</span></div>
    </div>
    """, unsafe_allow_html=True)

    if filtered:
        today_count = sum(1 for a in filtered if format_relative_time(a["publishedAt"]) == "Today")
        unique_sources = len(set(a["source"] for a in filtered))
    else:
        today_count, unique_sources = 0, 0

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📊 Feed Pulse</div>
        <div class="pulse-row"><span>Total Stories</span><span class="pulse-value">{len(filtered)}</span></div>
        <div class="pulse-row"><span>Published Today</span><span class="pulse-value">{today_count}</span></div>
        <div class="pulse-row"><span>Unique Sources</span><span class="pulse-value">{unique_sources}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="cta-panel">
        <div class="cta-title">Audit Intelligence Brief</div>
        <div class="cta-desc">Export this briefing as a CSV for Audit Committee and Chief Risk Officer distribution.</div>
    </div>
    """, unsafe_allow_html=True)
    if filtered:
        df_export = pd.DataFrame(filtered)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Briefing CSV",
            data=csv,
            file_name=f"audit_intel_briefing_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_csv_sidebar",
        )


# ---------------------------------------------------------
# 11. FOOTER
# ---------------------------------------------------------

st.markdown("""
<div class="app-footer">
    <div>
        <div class="footer-brand"><span>📡</span> Audit Intelligence</div>
        <div class="footer-tagline">Curated intelligence feed for Audit Committees and Chief Risk Officers across banking and financial services.</div>
    </div>
    <div class="footer-links">
        <span>About Us</span>
        <span>Contact</span>
        <span>Privacy Policy</span>
        <span>Terms of Service</span>
    </div>
</div>
<div class="footer-copyright">© 2026 Audit Intelligence &middot; Internal tool &middot; Not for external distribution</div>
""", unsafe_allow_html=True)
