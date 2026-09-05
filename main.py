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
        --text-secondary: #4B5563;
        --text-muted: #6B7280;
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
    .topnav-left { display: flex; align-items: center; gap: 18px; }

    /* ---- Emblem: deep navy tile, inner bevel, blue rim glow ---- */
    .logo-icon {
        position: relative;
        width: 62px; height: 62px;
        border-radius: 18px;
        background:
            radial-gradient(120% 120% at 28% 18%, #3B82F6 0%, #1D4ED8 42%, #14264F 100%);
        display: flex; align-items: center; justify-content: center;
        box-shadow:
            0 10px 26px rgba(29, 78, 216, 0.38),
            0 2px 5px rgba(11, 18, 32, 0.22),
            inset 0 1px 0 rgba(255, 255, 255, 0.42),
            inset 0 -2px 6px rgba(3, 10, 26, 0.45);
        flex-shrink: 0;
    }
    /* Hairline highlight ring */
    .logo-icon::after {
        content: "";
        position: absolute; inset: 0;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.20);
        pointer-events: none;
    }
    .logo-icon svg { width: 34px; height: 34px; display: block; }

    /* ---- Wordmark ---- */
    .logo-lockup { display: flex; flex-direction: column; }
    .logo-textrow { display: flex; align-items: center; gap: 12px; }
    .logo-text {
        font-weight: 900;
        font-size: 38px;
        letter-spacing: -1.5px;
        line-height: 1.02;
        color: #0B1220;
        white-space: nowrap;
    }
    /* Two-tone: "Audit" in ink, "Intelligence" in a blue gradient */
    .logo-text .lt-accent {
        background: linear-gradient(92deg, #2563EB 0%, #4F46E5 55%, #7C3AED 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #2563EB;
    }

    /* Live status pill */
    .live-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(22, 163, 74, 0.10);
        border: 1px solid rgba(22, 163, 74, 0.35);
        color: #15803D;
        font-size: 10px; font-weight: 800;
        letter-spacing: 1.2px; text-transform: uppercase;
        padding: 4px 10px; border-radius: 999px;
        white-space: nowrap;
    }
    .live-dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: #16A34A;
        box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.65);
        animation: livepulse 2s infinite;
    }
    @keyframes livepulse {
        0%   { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.60); }
        70%  { box-shadow: 0 0 0 7px rgba(22, 163, 74, 0); }
        100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
    }

    /* Strapline with a leading accent rule */
    .logo-sub {
        display: flex; align-items: center; gap: 9px;
        font-size: 11px; font-weight: 700; color: var(--text-muted);
        letter-spacing: 2.1px; text-transform: uppercase; margin-top: 7px;
    }
    .logo-rule {
        width: 30px; height: 3px; border-radius: 2px;
        background: linear-gradient(90deg, #2563EB, #7C3AED);
        flex-shrink: 0;
    }

    /* ---- Top-right principal (Pragati) block ---- */
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
    .topnav-user-name { font-weight: 800; font-size: 20px; color: #0B1220; letter-spacing: -0.3px; }
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

    .action-caption {
        font-size: 11.5px; color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace; padding-top: 10px;
    }

    /* ---------------- Section headings ---------------- */
    .section-heading {
        font-size: 15px;
        font-weight: 700;
        color: #0B1220;
        margin: 4px 0 14px 0;
    }
    .page-title {
        font-size: 26px;
        font-weight: 800;
        color: #0B1220;
        letter-spacing: -0.5px;
        margin-bottom: 2px;
    }
    .page-subtitle {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 20px;
    }

       /* ================= TAB VISIBILITY FIX (BaseWeb-safe) ================= */
    .stTabs, div[data-testid="stTabs"] { margin-top: 4px; margin-bottom: 20px; }

    .stTabs div[data-baseweb="tab-list"],
    div[data-testid="stTabs"] [role="tablist"] {
        gap: 4px !important;
        border-bottom: 1px solid var(--border) !important;
        background: transparent !important;
    }

    /* Base label — force on button AND every inner node (p / div / span),
       including -webkit-text-fill-color which overrides plain `color`. */
    .stTabs button[data-baseweb="tab"],
    .stTabs button[role="tab"],
    div[data-testid="stTabs"] button[role="tab"],
    .stTabs button[data-baseweb="tab"] *,
    .stTabs button[role="tab"] *,
    div[data-testid="stTabs"] button[role="tab"] * {
        color: #0B1220 !important;
        -webkit-text-fill-color: #0B1220 !important;
        opacity: 1 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px !important;
        text-transform: uppercase !important;
    }

    .stTabs button[data-baseweb="tab"],
    .stTabs button[role="tab"],
    div[data-testid="stTabs"] button[role="tab"] {
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        padding: 9px 18px !important;
        height: auto !important;
    }

    /* Hover */
    .stTabs button[data-baseweb="tab"]:hover,
    .stTabs button[data-baseweb="tab"]:hover *,
    .stTabs button[role="tab"]:hover,
    .stTabs button[role="tab"]:hover * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background: transparent !important;
    }

    /* Selected tab */
    .stTabs button[aria-selected="true"],
    .stTabs button[aria-selected="true"] *,
    div[data-testid="stTabs"] button[aria-selected="true"],
    div[data-testid="stTabs"] button[aria-selected="true"] * {
        color: #2563EB !important;
        -webkit-text-fill-color: #2563EB !important;
        font-weight: 800 !important;
    }
    .stTabs button[aria-selected="true"],
    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 3px solid #2563EB !important;
    }

    /* Kill Streamlit/BaseWeb's default red highlight bar + focus ring */
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"],
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        background-color: transparent !important;
        background-image: none !important;
        height: 0 !important;
        display: none !important;
    }
    .stTabs button:focus,
    .stTabs button:focus-visible,
    .stTabs button:active {
        outline: none !important;
        box-shadow: none !important;
        color: #2563EB !important;
        -webkit-text-fill-color: #2563EB !important;
    }
    /* ===================================================================== */

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
        color: #fff !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13.5px;
        padding: 9px 18px;
    }
    .stButton>button * { color: #fff !important; -webkit-text-fill-color: #fff !important; }
    .stButton>button:hover { background: var(--accent-blue-dark); }
    [data-testid="stDownloadButton"]>button {
        background: #fff;
        color: var(--accent-blue) !important;
        border: 1px solid var(--accent-blue);
        border-radius: 8px;
        font-weight: 600;
    }
    [data-testid="stDownloadButton"]>button:hover { background: #EFF6FF; }

    /* ---------------- Legible light theme inside controls ---------------- */
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
        /* Fallback tint if the hero image fails to load */
        background-color: #1E3A8A;
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
    /* Thumbnails are real <img> elements (not CSS backgrounds) so that a
       broken/hotlink-blocked remote image still paints the element's OWN
       background — i.e. the newspaper placeholder shows through automatically. */
    .insight-thumb {
        width: 180px; min-width: 180px; height: 128px;
        border-radius: 10px;
        object-fit: cover;
        background-color: #EEF2F7;
        background-repeat: no-repeat;
        background-position: center;
        background-size: 52px 52px;
        border: 1px solid var(--border);
        display: block;
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
        font-size: 17px; font-weight: 700; color: #0B1220;
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

    /* ---------------- Risk radar ---------------- */
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
        font-size: 12.5px; color: #0B1220; font-weight: 600; line-height: 1.4; margin-top: 3px;
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
    .footer-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-weight: 800; font-size: 14.5px; color: #0B1220; }
    .footer-tagline { font-size: 12px; color: var(--text-muted); max-width: 320px; line-height: 1.5; }
    .footer-links { display: flex; gap: 22px; font-size: 12.5px; color: var(--text-secondary); font-weight: 600; }
    .footer-copyright { font-size: 11.5px; color: var(--text-muted); margin-top: 18px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. BANKING AUDIT CATEGORIES & QUERIES
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

PAGE_SIZE = 100
MAX_PAGES = 2

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
    "bank", "banking", "lender", "rbi", "central bank", "basel", "npa",
    "asset quality", "provisioning", "capital adequacy", "credit risk",
    "liquidity", "penalty", "fined", "probe", "investigation", "whistleblower",
    "disclosure", "restatement", "irregularities", "lapses",
]

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

def placeholder_data_uri(hex_color="#94A3B8"):
    """
    Inline, URL-encoded newspaper SVG used as the thumbnail fallback.
    Returned as a data: URI so it needs no network call and cannot itself fail.
    """
    c = hex_color.replace("#", "%23")
    return (
        "data:image/svg+xml;charset=utf-8,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        f"stroke='{c}' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E"
        "%3Cpath d='M4 5h13a1 1 0 0 1 1 1v12a2 2 0 0 0 2 2H5a1 1 0 0 1-1-1V5z'/%3E"
        "%3Cpath d='M18 8h2a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2'/%3E"
        "%3Cpath d='M7 8h7'/%3E%3Cpath d='M7 11.5h7'/%3E"
        "%3Cpath d='M7 15h4'/%3E%3Cpath d='M13.5 15h.5'/%3E"
        "%3C/svg%3E"
    )


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
                if page > 1 and ("upgrade" in msg.lower() or "developer" in msg.lower()):
                    continue
                errors.append(f"{category} (page {page}): {msg}")

    raw_count = len(all_articles)

    unique = {}
    title_keys = set()

    for article in all_articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip().lower()
        key = url if url else title

        if not key or key in unique or title in title_keys:
            continue

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
# 3c. RISK RADAR + PRIORITY ALERTS
# ---------------------------------------------------------

def render_risk_radar(rows):
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
# 4. TOP NAVIGATION
# ---------------------------------------------------------

if PRAGATI_PHOTO_B64 and not PRAGATI_PHOTO_B64.startswith("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"):
    avatar_html = (
        f'<img src="data:image/jpeg;base64,{PRAGATI_PHOTO_B64}" '
        f'class="avatar-photo" alt="{PRAGATI_NAME}" />'
    )
else:
    avatar_html = f'<div class="avatar-circle-lg">{PRAGATI_NAME[:1].upper()}</div>'

# Emblem: an audit lens (magnifier) whose glass contains a rising analytics
# bar chart, framed by a scanning arc — "examine + measure + monitor".
LOGO_SVG = """
<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- outer scanning arc -->
  <path d="M26.6 8.4a13 13 0 0 1 .9 13.4" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>
  <path d="M5.2 22.6a13 13 0 0 1 .5-13.9" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>

  <!-- lens ring -->
  <circle cx="14.6" cy="14.6" r="8.2" stroke="#FFFFFF" stroke-width="2.4"/>
  <circle cx="14.6" cy="14.6" r="8.2" fill="#FFFFFF" fill-opacity="0.14"/>

  <!-- analytics bars inside the lens -->
  <rect x="10.7" y="15.1" width="2.25" height="4.5" rx="1.12" fill="#FFFFFF"/>
  <rect x="13.9" y="12.2" width="2.25" height="7.4" rx="1.12" fill="#FFFFFF"/>
  <rect x="17.1" y="9.6"  width="2.25" height="10"  rx="1.12" fill="#FFFFFF"/>

  <!-- handle -->
  <path d="M20.9 20.9 L26.4 26.4" stroke="#FFFFFF" stroke-width="3.1"
        stroke-linecap="round"/>
</svg>
"""

st.markdown(f"""
<div class="topnav">
    <div class="topnav-left">
        <div class="logo-icon">{LOGO_SVG}</div>
        <div class="logo-lockup">
            <div class="logo-textrow">
                <div class="logo-text">Audit<span class="lt-accent">&nbsp;Intelligence</span></div>
                <span class="live-pill"><span class="live-dot"></span>Live</span>
            </div>
            <div class="logo-sub"><span class="logo-rule"></span>Global Banking Risk &amp; Controls Briefing</div>
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

with st.expander("🔎 Ingestion Diagnostics", expanded=False):
    if stats:
        st.markdown(
            f"""
            <div style="font-size:12.5px; color:#111827; line-height:1.9;">
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
    f'<div class="page-subtitle">{len(filtered)} items &nbsp;·&nbsp; verified banking internal controls &amp; regulatory surveillance</div>',
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

    # Category-tinted newspaper placeholder, painted as the <img>'s own background.
    # If the remote image is missing, dead, or hotlink-blocked (403), the browser
    # discards the src and this placeholder remains visible — no more blank boxes.
    fallback = placeholder_data_uri(color)
    # An empty src="" makes some browsers re-request the page, so omit it entirely.
    src_attr = f'src="{article["image_url"]}" ' if article["image_url"] else ""

    thumb_html = (
        f'<img class="insight-thumb" {src_attr}alt="" loading="lazy" '
        f'referrerpolicy="no-referrer" '
        f'style="background-image: url(&quot;{fallback}&quot;);" '
        f'onerror="this.onerror=null; this.removeAttribute(\'src\');" />'
    )

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
            <div style="font-size: 13.5px; color: #4B5563; margin-top: 6px;">Try expanding the lookback window or lowering the relevance floor above.</div>
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
# 10. MAIN LAYOUT
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
