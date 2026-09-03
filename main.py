"""
Audit Intel — Global Banking Audit Intelligence
------------------------------------------------
Streamlit news-intelligence dashboard with an editorial / financial design,
matching the Visily reference UI.

The news pipeline is preserved from the original app:
  - 5 targeted NewsAPI searches run concurrently
  - deduplication by URL and normalized title
  - transparent audit-relevance scoring (internal to ranking/filtering)
  - rule-based keyword classification
  - lookback days, ingestion depth (articles/category), diagnostics, CSV export
"""

import html
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import pandas as pd
import requests
import streamlit as st

from config import API_KEY as CONFIG_API_KEY


# ---------------------------------------------------------------------------
# APP CONFIGURATION
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Audit Intel — Global Banking Audit Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORIES = {
    "Transformation": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance") AND ("digital transformation" OR "modernization" OR "core banking" OR "automation" OR "artificial intelligence" OR "generative AI" OR "cloud")'
    },
    "Regulation": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "internal controls" OR "compliance" OR "risk" OR "governance") AND ("regulation" OR "regulatory" OR "supervision" OR "RBI" OR "Basel" OR "AML" OR "KYC" OR "sanctions" OR "prudential" OR "enforcement")'
    },
    "People": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "risk" OR "governance" OR "controls") AND ("appointed" OR "appointment" OR "CEO" OR "CFO" OR "CRO" OR "CISO" OR "chief audit" OR "internal audit" OR "audit committee" OR "board")'
    },
    "Cyber and Tech": {
        "query": '("bank" OR "banking" OR "financial institution") AND ("audit" OR "IT controls" OR "risk" OR "governance") AND ("cybersecurity" OR "cyber attack" OR "ransomware" OR "data breach" OR "information security" OR "technology risk" OR "IT audit" OR "cloud security" OR "AI governance" OR "model risk")'
    },
    "Global Banks": {
        "query": '("bank" OR "banking group" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance" OR "regulatory") AND ("HSBC" OR "JPMorgan" OR "JPMorgan Chase" OR "Citi" OR "Citigroup" OR "Barclays" OR "Deutsche Bank" OR "UBS" OR "BNP Paribas" OR "Santander" OR "Standard Chartered" OR "Bank of America" OR "Goldman Sachs" OR "Morgan Stanley" OR "Wells Fargo" OR "ING" OR "ICBC" OR "MUFG" OR "Mizuho")'
    },
}

# Extra audit vocabulary is used to remove ordinary banking stories.
AUDIT_TERMS = [
    "internal audit", "external audit", "audit committee", "auditor",
    "audit finding", "audit findings", "internal control", "internal controls",
    "control weakness", "control weaknesses", "control deficiency",
    "control deficiencies", "governance", "risk management", "operational risk",
    "model risk", "compliance", "regulatory", "regulation", "supervision",
    "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
    "sanctions", "cybersecurity", "cyber security", "it audit", "technology risk",
    "data breach", "ransomware", "fraud", "misconduct", "financial crime",
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
    "Cyber and Tech": [
        "cybersecurity", "cyber security", "cyber attack", "ransomware",
        "data breach", "information security", "technology risk", "it audit",
        "cloud security", "ai governance", "model risk", "digital", "technology",
    ],
    "Global Banks": [
        "hsbc", "jpmorgan", "jpmorgan chase", "citi", "citigroup", "barclays",
        "deutsche bank", "ubs", "bnpparibas", "bnp paribas", "santander",
        "standard chartered", "bank of america", "goldman sachs", "morgan stanley",
        "wells fargo", "ing", "icbc", "mufg", "mizuho",
    ],
}

# UI metadata for categories (display labels + subtle finance palette).
CATEGORY_META = {
    "Transformation": {"label": "Transformation", "color": "#2563EB", "tint": "#EAF1FE", "emoji": "🔄"},
    "Regulation":     {"label": "Regulation",     "color": "#C7740A", "tint": "#FDF3E7", "emoji": "🏛️"},
    "People":         {"label": "People",         "color": "#0E9F6E", "tint": "#E9F8F2", "emoji": "👥"},
    "Cyber and Tech": {"label": "Cyber & Tech",   "color": "#6D4BD8", "tint": "#F1EDFC", "emoji": "🛡️"},
    "Global Banks":   {"label": "Global Banking", "color": "#0F766E", "tint": "#E8F6F5", "emoji": "🌐"},
}


# ---------------------------------------------------------------------------
# GLOBAL STYLES (editorial / financial, light theme, subtle blue accents)
# ---------------------------------------------------------------------------

APP_CSS = """
<style>
:root {
    --ink: #0A1B33;
    --body: #3D4D63;
    --muted: #74849B;
    --line: #E4E9F2;
    --panel: #F5F8FC;
    --accent: #1B5DC9;
    --accent-deep: #0F3E91;
    --blue-tint: #EAF1FD;
    --white: #FFFFFF;
    --serif: 'Source Serif 4', Georgia, 'Times New Roman', serif;
    --sans: 'Inter', -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
}

.stApp { background: var(--white); color: var(--body); font-family: var(--sans); }
footer, #MainMenu { visibility: hidden; }
h1, h2, h3, h4 { font-family: var(--serif); color: var(--ink); }

/* --- compact top navigation --- */
.audit-topbar { display:flex; align-items:center; gap:14px; padding:6px 0 10px; }
.brand-mark {
    width:40px; height:40px; border-radius:12px; flex:0 0 auto;
    background: linear-gradient(135deg, #123C74, #2E77D0);
    color:#fff; font-weight:800; font-size:15px; letter-spacing:.6px;
    display:flex; align-items:center; justify-content:center;
    box-shadow: 0 6px 14px -6px rgba(18,60,116,.45);
}
.brand-name { font-weight:800; color:var(--ink); font-size:17px; letter-spacing:-.2px; line-height:1.15; }
.brand-sub { font-size:10.5px; color:var(--muted); text-transform:uppercase; letter-spacing:1.4px; }
.live-line { display:flex; align-items:center; gap:7px; justify-content:flex-end; font-size:11.5px; color:var(--muted); font-weight:600; }
.live-dot { width:8px; height:8px; border-radius:50%; background:#16A34A; box-shadow:0 0 0 3px rgba(22,163,74,.18); display:inline-block; }

/* --- search bar --- */
div[data-testid="stTextInput"] div[data-baseweb="input"] { border-radius:999px !important; border:1px solid #D9E1EC !important; background:#F4F7FB !important; }
div[data-testid="stTextInput"] input { background:transparent !important; color:var(--ink) !important; font-size:14px !important; }
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border-color:var(--accent) !important; box-shadow:0 0 0 3px rgba(27,93,201,.12) !important; background:#fff !important; }

/* --- buttons --- */
.stButton > button, .stDownloadButton > button {
    border:1px solid #D9E1EC !important; background:#fff !important; color:var(--ink) !important;
    border-radius:10px !important; font-weight:600 !important; font-size:13px !important; height:38px !important;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--accent) !important; color:var(--accent) !important; }
.stButton > button[kind="primary"] { background:linear-gradient(135deg,#123C74,#2E77D0) !important; color:#fff !important; border:none !important; }
.stButton > button[kind="primary"]:hover { color:#fff !important; opacity:.94; }

/* --- category pills (navigation) --- */
div[data-testid="stPills"] [data-testid="stHorizontalBlock"] { gap:8px; flex-wrap:wrap; }
div[data-testid="stPills"] button {
    border-radius:999px !important; border:1px solid var(--line) !important; background:#fff !important;
    color:#42546E !important; font-weight:600 !important; font-size:13px !important; padding:2px 16px !important;
}
div[data-testid="stPills"] button[aria-pressed="true"] {
    background:var(--accent) !important; border-color:var(--accent) !important; color:#fff !important;
}

/* --- section headers --- */
.sec { margin: 20px 0 26px; }
.sec-head { display:flex; align-items:baseline; gap:12px; border-bottom:1px solid var(--line); padding-bottom:8px; margin-bottom:16px; }
.sec-eyebrow { text-transform:uppercase; font-size:10.5px; letter-spacing:1.6px; color:var(--accent); font-weight:800; }
.sec-head h2 { margin:0; font-size:21px; }
.sec-sub { margin-left:auto; color:var(--muted); font-size:12px; }

/* --- chips + meters --- */
.chip { display:inline-flex; align-items:center; gap:6px; padding:2px 11px; border-radius:999px; font-size:10.5px; font-weight:800; letter-spacing:.5px; text-transform:uppercase; white-space:nowrap; }
.topic { display:inline-flex; align-items:center; gap:5px; background:#fff; border:1px solid var(--line); border-radius:999px; padding:3px 11px; font-size:12px; font-weight:600; color:var(--ink); }
.topic b { color:var(--accent); font-weight:800; }
mark { background:#DCECFF; color:#0B2E63; padding:0 3px; border-radius:3px; }
.time { color:var(--muted); font-size:12px; white-space:nowrap; }
.meter { height:6px; background:#E6EBF4; border-radius:99px; overflow:hidden; }
.meter > span { display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#123C74,#2E77D0); width:0; }
.rel-badge { font-size:11.5px; font-weight:700; color:var(--accent); background:var(--blue-tint); padding:2px 9px; border-radius:7px; white-space:nowrap; }

/* --- link buttons --- */
.btn, .btn-ghost {
    display:inline-flex; align-items:center; gap:7px; border-radius:9px; font-weight:600;
    font-size:13px; text-decoration:none; padding:8px 15px; transition:all .15s ease;
}
.btn { background:var(--accent); color:#fff; }
.btn:hover { background:var(--accent-deep); color:#fff; text-decoration:none; }
.btn-ghost { border:1px solid #D9E1EC; background:#fff; color:var(--ink); }
.btn-ghost:hover { border-color:var(--accent); color:var(--accent); text-decoration:none; }
.txt-link { color:var(--accent); font-weight:700; text-decoration:none; font-size:13px; }
.txt-link:hover { text-decoration:underline; }

/* --- featured analysis --- */
.featured { display:grid; grid-template-columns: 2.1fr 1fr; gap:18px; margin-bottom:8px; }
.hero-card { background:#fff; border:1px solid var(--line); border-radius:16px; overflow:hidden; }
.hero-img { display:block; height:250px; width:100%; object-fit:cover; background:linear-gradient(135deg,#DCE7F8,#F4F8FF); }
.hero-body { padding:18px 20px 20px; }
.hero-body .eyebrow { text-transform:uppercase; letter-spacing:1.6px; color:var(--accent); font-weight:800; font-size:10.5px; margin-bottom:8px; }
.hero-body h2 { font-size:26px; line-height:1.22; margin:8px 0 8px; }
.hero-body h2 a { color:var(--ink); text-decoration:none; }
.hero-body h2 a:hover { color:var(--accent); }
.hero-body p { color:var(--body); font-size:14.5px; line-height:1.6; margin:0 0 14px; }
.hero-meta { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:14px; }
.hero-actions { display:flex; gap:10px; flex-wrap:wrap; }
.feat-side { display:flex; flex-direction:column; gap:12px; }
.feat-mini { background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px 16px; display:flex; gap:12px; align-items:flex-start; }
.feat-num { font-family:var(--serif); font-size:20px; font-weight:700; color:var(--accent); line-height:1; padding-top:3px; }
.feat-mini h4 { margin:2px 0 6px; font-size:16px; line-height:1.3; }
.feat-mini h4 a { color:var(--ink); text-decoration:none; }
.feat-mini p { margin:0; color:var(--muted); font-size:12.5px; line-height:1.5; }

/* --- insight cards grid --- */
.card-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(258px, 1fr)); gap:18px; }
.card { background:#fff; border:1px solid var(--line); border-radius:15px; overflow:hidden; display:flex; flex-direction:column; transition:transform .15s ease, box-shadow .15s ease; }
.card:hover { transform:translateY(-3px); box-shadow:0 14px 30px -16px rgba(10,27,51,.25); border-color:#C9D6EA; }
.card-img { display:block; height:150px; width:100%; object-fit:cover; background:linear-gradient(135deg,#E3EDFB,#F6F9FE); }
.card-ph { display:flex; align-items:center; justify-content:center; height:150px; font-size:34px; }
.card-body { padding:14px 16px 15px; display:flex; flex-direction:column; gap:8px; flex:1; }
.card-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.card-title { font-size:16.5px; line-height:1.32; margin:0; }
.card-title a { color:var(--ink); text-decoration:none; }
.card-title a:hover { color:var(--accent); }
.card-desc { color:var(--muted); font-size:12.5px; line-height:1.55; margin:0;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card-meta { margin-top:auto; padding-top:6px; border-top:1px dashed var(--line); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.card-src { font-size:12px; font-weight:600; color:var(--body); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* --- intelligence rail (right sidebar) --- */
.rail { display:flex; flex-direction:column; gap:18px; }
.rail-block { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px 18px; }
.rail-title { text-transform:uppercase; font-size:10.5px; letter-spacing:1.6px; color:var(--accent); font-weight:800; margin-bottom:12px; }
.rank-num { font-family:var(--serif); font-size:44px; font-weight:800; color:var(--ink); line-height:.9; letter-spacing:-1px; }
.rail-block h3 { font-size:17px; line-height:1.3; margin:4px 0 8px; }
.rail-block h3 a { color:var(--ink); text-decoration:none; }
.rail-block h3 a:hover { color:var(--accent); }
.rail-meta { color:var(--muted); font-size:12px; margin:0 0 11px; }
.pulse-row { display:flex; align-items:center; gap:10px; margin:9px 0; }
.pulse-label { width:112px; font-size:12px; font-weight:700; color:var(--body); text-transform:capitalize; }
.pulse-meter { flex:1; }
.pulse-count { font-size:12px; font-weight:800; color:var(--ink); width:22px; text-align:right; }
.pulse-footer { margin-top:12px; padding-top:11px; border-top:1px solid var(--line); display:flex; justify-content:space-between; color:var(--muted); font-size:11.5px; }
.filter-chip { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid var(--line); padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; color:var(--ink); margin:0 6px 8px 0; }
.filter-chip b { color:var(--muted); font-weight:600; }
.footer-note { color:var(--muted); font-size:11.5px; margin-top:8px; border-top:1px solid var(--line); padding-top:10px; }

/* --- search results --- */
.res-row { display:flex; gap:16px; padding:16px 2px; border-bottom:1px solid var(--line); }
.res-rank { font-family:var(--serif); font-size:22px; font-weight:800; color:#C3CFE0; min-width:34px; padding-top:2px; }
.res-main { flex:1; min-width:0; }
.res-top { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:7px; }
.res-meta { color:var(--muted); font-size:12px; }
.res-main h3 { font-size:19px; line-height:1.3; margin:0 0 6px; }
.res-main h3 a { color:var(--ink); text-decoration:none; }
.res-main h3 a:hover { color:var(--accent); }
.res-snip { color:var(--body); font-size:13.5px; line-height:1.6; margin:0 0 9px; }
.res-actions { display:flex; gap:16px; align-items:center; }

/* --- article detail --- */
.breadcrumb { color:var(--muted); font-size:12.5px; margin-bottom:14px; }
.breadcrumb a { color:var(--accent); text-decoration:none; font-weight:600; }
.art-chip-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:12px; }
.art-title { font-size:36px; line-height:1.18; margin:0 0 14px; }
.art-standfirst { font-size:17px; line-height:1.65; color:var(--body); font-family:var(--serif); font-style:italic; margin:0 0 16px; }
.art-meta { display:flex; align-items:center; gap:14px; flex-wrap:wrap; color:var(--muted); font-size:13px; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:10px 0; margin-bottom:18px; }
.art-img { width:100%; border-radius:14px; border:1px solid var(--line); margin-bottom:18px; }
.art-body p { font-size:15.5px; line-height:1.75; color:var(--ink); margin:0 0 14px; }
.topics-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
.related-item { padding:11px 0; border-top:1px dashed var(--line); }
.related-item:first-of-type { border-top:0; padding-top:0; }
.related-item h4 { margin:0 0 4px; font-size:14.5px; line-height:1.35; }
.related-item h4 a { color:var(--ink); text-decoration:none; }
.related-item h4 a:hover { color:var(--accent); }
.dl { display:flex; justify-content:space-between; gap:12px; font-size:12.5px; padding:7px 0; border-top:1px dashed var(--line); }
.dl:first-of-type { border-top:0; }
.dl dt { color:var(--muted); font-weight:600; text-transform:uppercase; font-size:10.5px; letter-spacing:.6px; padding-top:2px; }
.dl dd { margin:0; color:var(--ink); font-weight:600; text-align:right; }

/* --- empty state --- */
.empty { background:var(--panel); border:1px dashed #C9D6EA; border-radius:16px; padding:30px 26px; text-align:center; }
.empty h3 { margin:0 0 6px; font-size:19px; }
.empty p { color:var(--muted); margin:0 0 14px; font-size:13.5px; }

/* --- responsive --- */
@media (max-width: 960px) {
    .featured { grid-template-columns: 1fr; }
}
</style>
"""


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def esc(value):
    """HTML-escape arbitrary text before injecting it into HTML layouts."""
    return html.escape(str(value), quote=True)


def rel_time(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return str(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 86400 * 7:
        return f"{seconds // 86400}d ago"
    return dt.strftime("%b %d, %Y")


def fmt_date(iso):
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return str(iso)
    return dt.strftime("%A, %d %B %Y · %H:%M UTC")


def snippet(text, length=150):
    text = (text or "").strip()
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


def highlight_matches(text, tokens):
    """Escape text then wrap query tokens in <mark>.</mark>"""
    safe = esc(text or "")
    terms = [esc(t) for t in tokens if len(t) >= 2]
    if not terms:
        return safe
    pattern = re.compile("(" + "|".join(map(re.escape, terms)) + ")", re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(1)}</mark>", safe)


def cat_chip(key, with_emoji=False):
    meta = CATEGORY_META.get(key, {"label": key, "color": "#1B5DC9", "tint": "#EAF1FE", "emoji": "•"})
    label = meta["label"]
    if with_emoji:
        label = f"{meta['emoji']} {label}"
    return (f'<span class="chip" style="color:{meta["color"]};background:{meta["tint"]}">'
            f'{esc(label)}</span>')


def relevance_meter(score):
    score = max(0, min(100, int(score)))
    return (f'<span class="rel-badge">{score}/100</span>'
            f'<div class="meter" style="margin-top:6px"><span style="width:{score}%"></span></div>')


STOPWORDS = set(
    "a an the and or but if then else when while for with without from by at in on over under of to into "
    "as is are was were be been being has have had do does did not no nor so too very just can could will "
    "would shall should may might must all any both each few more most other some such only own same than "
    "that this these those it its their they them he she we you our your his her there here what which who "
    "whom how why where out about after before against between during through among because since until "
    "unless new news said says say bank banking banks financial finance global audit audits auditor "
    "regulatory regulation risk risks governance".split()
)


def trending_topics(rows, n=8):
    counter = Counter()
    for article in rows:
        text = f"{article.get('title','')} {article.get('description','')}".lower()
        for word in re.findall(r"[a-z][a-z0-9&+.\-]{2,}", text):
            if word in STOPWORDS or word.isdigit():
                continue
            counter[word] += 1
    return counter.most_common(n)


def search_tokens(query):
    return [t.lower() for t in re.findall(r"\w+", query or "")][:6]


def matches_query(article, tokens):
    if not tokens:
        return True
    haystack = " ".join([
        article.get("title", ""),
        article.get("description", ""),
        article.get("source", ""),
        article.get("category", ""),
        article.get("body", ""),
    ]).lower()
    return all(tok in haystack for tok in tokens)


def secure_image(url):
    if not url:
        return ""
    return str(url).replace("http://", "https://")


# ---------------------------------------------------------------------------
# NEWS PIPELINE (unchanged behavior)
# ---------------------------------------------------------------------------

def get_api_key():
    """Use Streamlit secrets/env first; sidebar entry is the local fallback."""
    if CONFIG_API_KEY.strip():
        return CONFIG_API_KEY.strip()

    env_key = os.getenv("NEWSAPI_KEY", "").strip()
    if env_key:
        return env_key

    try:
        secret_key = st.secrets.get("API_KEY", "")
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
    """Simple, fast, transparent audit relevance score: 0-100."""
    score = 0
    for term in AUDIT_TERMS:
        if term in text:
            score += 5

    for term in [
        "internal audit", "audit committee", "internal controls",
        "control deficiency", "regulatory enforcement", "it audit",
        "technology risk", "financial crime",
    ]:
        if term in text:
            score += 10

    return min(score, 100)


def classify_article(article):
    """Classify using transparent keyword scoring; no paid LLM is required."""
    text = normalize_text(article)
    scores = {}

    for category, terms in CATEGORY_TERMS.items():
        score = sum(1 for term in terms if term in text)
        scores[category] = score

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        best_category = "Regulation"

    return best_category, scores[best_category]


def fetch_category(category, query, api_key, from_date, page_size):
    """Fetch one category from NewsAPI."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message", "NewsAPI returned an error."))

    rows = []
    for article in payload.get("articles", []):
        article["_query_category"] = category
        rows.append(article)

    return rows


@st.cache_data(ttl=300, show_spinner=False)
def load_news(api_key, lookback_days, page_size):
    """
    Fetch all five targeted searches in parallel.
    Cached for 5 minutes so Streamlit reruns do not repeatedly call NewsAPI.
    """
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    all_articles = []
    errors = []

    with ThreadPoolExecutor(max_workers=len(CATEGORIES)) as executor:
        futures = {
            executor.submit(
                fetch_category,
                category,
                settings["query"],
                api_key,
                from_date,
                page_size,
            ): category
            for category, settings in CATEGORIES.items()
        }

        for future in as_completed(futures):
            category = futures[future]
            try:
                all_articles.extend(future.result())
            except Exception as exc:
                errors.append(f"{category}: {exc}")

    # Deduplicate by URL first, then by normalized title.
    unique = {}
    title_keys = set()

    for article in all_articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip().lower()
        key = url if url else title

        if not key or key in unique or title in title_keys:
            continue

        unique[key] = article
        title_keys.add(title)

    cleaned = []
    for article in unique.values():
        text = normalize_text(article)
        relevance = audit_relevance(text)

        # Internal floor — only meaningful audit/risk/control signals are kept.
        if relevance < 5:
            continue

        category, category_score = classify_article(article)

        source = article.get("source") or {}
        body = re.sub(r"\s*\[\+\d+ chars\]$", "", article.get("content") or "")

        cleaned.append({
            "category": category,
            "audit_relevance": relevance,
            "category_score": category_score,
            "title": article.get("title") or "Untitled",
            "description": article.get("description") or "",
            "body": body,
            "source": source.get("name") or "Unknown source",
            "publishedAt": article.get("publishedAt") or "",
            "url": article.get("url") or "",
            "image": secure_image(article.get("urlToImage") or ""),
            "author": article.get("author") or "",
        })

    cleaned.sort(key=lambda x: (x["audit_relevance"], x["publishedAt"]), reverse=True)
    return cleaned, errors


# ---------------------------------------------------------------------------
# RENDER BUILDERS
# ---------------------------------------------------------------------------

def article_link(idx):
    return f"?view=article&idx={idx}"


def card_html(article, idx):
    meta = CATEGORY_META.get(article["category"])
    color = meta["color"] if meta else "#1B5DC9"
    tint = meta["tint"] if meta else "#EAF1FE"
    emoji = meta["emoji"] if meta else "📰"

    img = article.get("image") or ""
    if img:
        visual = (f'<a class="card-img-wrap" href="{article_link(idx)}">'
                  f'<img class="card-img" src="{esc(img)}" alt="{esc(article["title"])}" loading="lazy" '
                  f'onerror="this.style.display=\'none\'"></a>')
    else:
        visual = (f'<div class="card-ph" style="background:linear-gradient(135deg,{tint},{color}22)">'
                  f'<span style="font-size:32px">{emoji}</span></div>')

    return (
        f'<article class="card">'
        f'{visual}'
        f'<div class="card-body">'
        f'<div class="card-top">{cat_chip(article["category"])}'
        f'<span class="time">{rel_time(article["publishedAt"])}</span></div>'
        f'<h3 class="card-title"><a href="{article_link(idx)}">{esc(article["title"])}</a></h3>'
        f'<p class="card-desc">{esc(snippet(article["description"], 150))}</p>'
        f'<div class="card-meta"><span class="card-src">● {esc(article["source"])}</span>'
        f'<span class="rel-badge">{article["audit_relevance"]}/100</span></div>'
        f'</div></article>'
    )


def rail_block(title, inner_html, extra_class=""):
    return (f'<div class="rail-block {extra_class}">'
            f'<div class="rail-title">{title}</div>{inner_html}</div>')


def pulse_block(articles):
    counts = Counter(a["category"] for a in articles)
    total = max(1, len(articles))
    rows = ""
    for key, meta in CATEGORY_META.items():
        count = counts.get(key, 0)
        pct = int(round(count / total * 100))
        rows += (
            f'<div class="pulse-row"><span class="pulse-label">{meta["label"]}</span>'
            f'<div class="pulse-meter"><div class="meter"><span style="width:{pct}%;'
            f'background:linear-gradient(90deg,{meta["color"]}cc,{meta["color"]})"></span></div></div>'
            f'<span class="pulse-count">{count}</span></div>'
        )
    updated = datetime.now(timezone.utc).strftime("%H:%M UTC")
    return rail_block(
        "Market Pulse",
        rows + f'<div class="pulse-footer"><span>Total stories</span><b>{len(articles)}</b></div>'
               f'<div class="pulse-footer"><span>Updated</span><b>{updated}</b></div>',
    )


def active_filters_block(cat_label, lookback, depth, query):
    chips = (
        f'<span class="filter-chip">Category <b>{esc(cat_label or "All topics")}</b></span>'
        f'<span class="filter-chip">Lookback <b>{lookback}d</b></span>'
        f'<span class="filter-chip">Depth <b>{depth}/cat</b></span>'
    )
    if query:
        chips += f'<span class="filter-chip">Query <b>“{esc(query)}”</b></span>'
    return rail_block("Active Filters", chips)


def leader_block(articles):
    if not articles:
        return rail_block("Daily Leader", '<p class="rail-meta">Awaiting stories…</p>')
    top = articles[0]
    idx = articles.index(top)
    return rail_block(
        "Daily Leader",
        f'<div class="rank-num">01</div>'
        f'{cat_chip(top["category"], with_emoji=True)}'
        f'<h3 style="margin-top:8px"><a href="{article_link(idx)}">{esc(top["title"])}</a></h3>'
        f'<p class="rail-meta">{esc(top["source"])} · {rel_time(top["publishedAt"])}</p>'
        f'{relevance_meter(top["audit_relevance"])}'
        f'<p style="margin:12px 0 0"><a class="btn" style="width:100%;justify-content:center" '
        f'href="{article_link(idx)}">Open story</a></p>',
    )


def trending_block(articles):
    topics = trending_topics(articles, 8)
    if not topics:
        return rail_block("Trending Topics", '<p class="rail-meta">No signals yet.</p>')
    chips = "".join(
        f'<span class="topic" style="margin:0 6px 8px 0">{esc(t)} <b>{c}</b></span>'
        for t, c in topics
    )
    return rail_block("Trending Topics", chips)


# ---------------------------------------------------------------------------
# SMART STATE ADAPTERS
# ---------------------------------------------------------------------------

def resolve_view(articles):
    """Resolve current UI view from query params / session state."""
    view = (st.query_params.get_all("view") or [None])[0]
    if view == "article":
        try:
            idx = int(st.query_params.get_all("idx")[0])
        except (ValueError, IndexError, TypeError):
            idx = -1
        if 0 <= idx < len(articles):
            return "article", idx
        return "home", None
    query = (st.session_state.get("news_search") or "").strip()
    if query:
        return "search", None
    return "home", None


def current_rows(articles, picked_category, query=""):
    """Apply category + search filtering (audit-relevance threshold stays internal)."""
    if picked_category and picked_category != "All topics":
        keys = [k for k, m in CATEGORY_META.items() if m["label"] == picked_category]
    else:
        keys = list(CATEGORIES.keys())
    tokens = search_tokens(query)
    rows = [a for a in articles if a["category"] in keys and matches_query(a, tokens)]
    return rows, tokens


def csv_bytes(rows):
    df = pd.DataFrame(rows)[[
        "category", "title", "source", "description", "url",
        "author", "publishedAt", "audit_relevance", "category_score",
    ]]
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------------
# STREAMLIT APP
# ---------------------------------------------------------------------------

st.markdown(APP_CSS, unsafe_allow_html=True)

st.session_state.setdefault("news_search", "")
st.session_state.setdefault("cat_pill", "All topics")

# ---------- API key ----------
api_key = get_api_key()

if not api_key:
    with st.sidebar:
        st.markdown('<div class="brand-name" style="font-size:16px">🏦 Audit Intel</div>')
        st.caption("Global Banking Audit Intelligence")
        api_key = st.text_input(
            "NewsAPI key", type="password",
            help="Your key is used only for this Streamlit session.",
        )
    if not api_key:
        st.markdown(
            '<div class="empty"><h3>API key required</h3>'
            '<p>Set <code>NEWSAPI_KEY</code> as an environment variable, add '
            '<code>API_KEY</code> to Streamlit secrets, or enter your key in the sidebar.</p></div>',
            unsafe_allow_html=True,
        )
        st.stop()

# ---------- Sidebar: feed settings + diagnostics ----------
with st.sidebar:
    st.markdown('<div class="brand-name" style="font-size:16px">🏦 Audit Intel</div>')
    st.caption("Global Banking · Audit · Intelligence")

    with st.expander("⚙️ Feed settings", expanded=True):
        lookback_days = st.slider("Look back (days)", min_value=1, max_value=7, value=3)
        page_size = st.slider(
            "Ingestion depth (articles per category)",
            min_value=10, max_value=100, value=50, step=10,
        )
        if st.button("🔄 Fetch latest news", type="primary", use_container_width=True):
            st.session_state["refresh_requested"] = True

    if api_key:
        try:
            articles, errors = None, []
            # populate diagnostics after load below
        except Exception:
            pass

    st.markdown(
        '<div class="footer-note">Powered by NewsAPI · Run with <code>streamlit run main.py</code> '
        '<br/>Audit relevance & classification are transparent keyword rules — no LLM required.</div>',
        unsafe_allow_html=True,
    )

# ---------- Load news (unchanged trigger behavior) ----------
refresh_requested = st.session_state.pop("refresh_requested", False)

if refresh_requested or "news_loaded" not in st.session_state:
    with st.spinner("Fetching targeted global audit news…"):
        articles, errors = load_news(api_key, lookback_days, page_size)
    st.session_state.news = articles
    st.session_state.news_errors = errors
    st.session_state.news_loaded = True
    st.session_state.load_lookback = lookback_days
    st.session_state.load_depth = page_size

articles = st.session_state.get("news", [])
errors = st.session_state.get("news_errors", [])
lookback_days = st.session_state.get("load_lookback", lookback_days)
page_size = st.session_state.get("load_depth", page_size)

# ---------- Top navigation bar ----------
now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")

header_html = f"""
<div class="audit-topbar">
  <div><div class="brand-mark">AI</div></div>
  <div>
    <div class="brand-name">Audit Intel</div>
    <div class="brand-sub">Banking · Audit · Intelligence</div>
  </div>
</div>
"""
brand_col, search_col, action_col = st.columns([1.35, 3.4, 2.05], vertical_alignment="center")

with brand_col:
    st.markdown(header_html, unsafe_allow_html=True)

with search_col:
    st.text_input(
        "Global search",
        key="news_search",
        value=st.session_state.get("news_search", ""),
        placeholder="Search stories, banks, regulators, topics…",
        icon=":material/search:",
        label_visibility="collapsed",
    )

with action_col:
    st.markdown(
        f'<div class="live-line"><span class="live-dot"></span>Live feed&nbsp;·&nbsp;Updated {now_str}</div>',
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns([1.15, 1])
    with b1:
        st.download_button(
            "📥 CSV",
            data=lambda: csv_bytes(current_rows(articles, st.session_state.get("cat_pill", "All topics"))[0]),
            file_name=f"audit-intel-{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
        )
    with b2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state["refresh_requested"] = True

st.markdown('<div style="border-bottom:1px solid var(--line)"></div>', unsafe_allow_html=True)

# ---------- Category navigation (pills) ----------
count_labels = Counter(a["category"] for a in articles)
pill_options = ["All topics"] + [CATEGORY_META[k]["label"] for k in CATEGORIES]

st.pills(
    "Browse topics",
    options=pill_options,
    key="cat_pill",
    default="All topics",
    selection_mode="single",
    label_visibility="collapsed",
)

count_chips = "".join(
    f'<span class="chip" style="color:{m["color"]};background:{m["tint"]};">{m["emoji"]} {m["label"]}&nbsp;·&nbsp;{count_labels.get(k, 0)}</span> '
    for k, m in CATEGORY_META.items()
)
st.markdown(
    f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 4px">{count_chips}'
    f'<span class="chip" style="color:#42546E;background:#EEF2F8;">Σ {len(articles)} stories</span></div>',
    unsafe_allow_html=True,
)

# ---------- Resolve view ----------
view, article_idx = resolve_view(articles)
query = (st.session_state.get("news_search") or "").strip()
picked_category = st.session_state.get("cat_pill", "All topics")
filtered, tokens = current_rows(articles, picked_category, query)


# ===========================================================================
# VIEW: ARTICLE DETAIL  (page 2 of the Visily reference)
# ===========================================================================
if view == "article" and article_idx is not None and 0 <= article_idx < len(articles):
    article = articles[article_idx]
    back_href = f"?view=search&q={quote(query)}" if query else "?view=home"

    mains, rails = st.columns([2.35, 1.15], gap="large")

    with mains:
        st.markdown(
            f'<div class="breadcrumb"><a href="{back_href}">← Back to feed</a>  /  '
            f'{cat_chip(article["category"])}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="art-chip-row">'
            f'{cat_chip(article["category"], with_emoji=True)}'
            f'<span class="rel-badge">{article["audit_relevance"]}/100 audit relevance</span>'
            f'<span class="time">{fmt_date(article["publishedAt"])}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<h1 class="art-title">{esc(article["title"])}</h1>', unsafe_allow_html=True)

        if article.get("description"):
            st.markdown(f'<p class="art-standfirst">{esc(article["description"])}</p>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="art-meta"><span>🏛 {esc(article["source"])}</span>'
            f'<span>✍️ {esc(article["author"] or "NewsAPI wire")}</span>'
            f'<span>⏱ {rel_time(article["publishedAt"])}</span></div>',
            unsafe_allow_html=True,
        )

        if article.get("image"):
            st.markdown(
                f'<img class="art-img" src="{esc(article["image"])}" '
                f'onerror="this.parentElement.remove()" alt="{esc(article["title"])}" loading="lazy">',
                unsafe_allow_html=True,
            )

        body = (article.get("body") or "").strip()
        if body:
            sentences = re.split(r"(?<=[.!?])\s+", body)
            paragraphs = "".join(
                f"<p>{esc(' '.join(sentences[i:i+3]))}</p>"
                for i in range(0, min(len(sentences), 24), 3)
            )
            st.markdown(f'<div class="art-body">{paragraphs}'
                        f'<p style="color:var(--muted);font-size:12.5px">Excerpt provided by NewsAPI; '
                        f'some trailing text may be truncated.</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="art-body"><p>{esc(article.get("description") or "No extended summary is available.")}</p>'
                f'<p style="color:var(--muted);font-size:12.5px">Full text is behind the source-link paywall/article.</p>'
                f'</div>', unsafe_allow_html=True,
            )

        # Key topics detected by the classifier
        detected = [
            term for term in CATEGORY_TERMS.get(article["category"], [])
            if term in f"{article['title']} {article['description']} {body}".lower()
        ][:8]
        if detected:
            st.markdown(
                '<div class="sec-head"><span class="sec-eyebrow">Key Topics</span>'
                '<h2 style="font-size:15px">Signals detected</h2></div>'
                + '<div class="topics-row">'
                + "".join(f'<span class="topic">#{esc(t.replace(" ", "-"))}</span>' for t in detected)
                + "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f'<div class="hero-actions" style="margin-top:18px">'
            f'<a class="btn" href="{esc(article["url"])}" target="_blank" rel="noopener noreferrer">'
            f'Read full article ↗</a>'
            f'<a class="btn-ghost" href="{back_href}">← Back to feed</a></div>',
            unsafe_allow_html=True,
        )

    with rails:
        # Story intelligence panel
        domain = ""
        try:
            domain = urlparse(article["url"]).netloc
        except Exception:
            pass
        story_meta = (
            f'<dl class="dl"><dt>Category</dt><dd>{esc(CATEGORY_META.get(article["category"], {}).get("label", article["category"]))}</dd></dl>'
            f'<dl class="dl"><dt>Source</dt><dd>{esc(article["source"])}</dd></dl>'
            f'<dl class="dl"><dt>Domain</dt><dd>{esc(domain or "—")}</dd></dl>'
            f'<dl class="dl"><dt>Published</dt><dd>{rel_time(article["publishedAt"])}</dd></dl>'
            f'<dl class="dl"><dt>Feed rank</dt><dd>#{article_idx + 1}</dd></dl>'
            f'<dl class="dl"><dt>Audit relevance</dt><dd>{article["audit_relevance"]}/100</dd></dl>'
            f'<dl class="dl"><dt>Topic signals</dt><dd>{article["category_score"]}</dd></dl>'
        )
        st.markdown(rail_block("Story Intelligence", story_meta), unsafe_allow_html=True)

        # Related stories
        related = [a for a in articles if a["category"] == article["category"] and a is not article][:5]
        if not related:
            related = [a for a in articles if a is not article][:5]
        related_html = "".join(
            f'<div class="related-item">{cat_chip(a["category"])}'
            f'<h4><a href="{article_link(articles.index(a))}">{esc(snippet(a["title"], 90))}</a></h4>'
            f'<span class="time">{esc(a["source"])} · {rel_time(a["publishedAt"])}</span></div>'
            for a in related
        )
        st.markdown(rail_block("Related Stories", related_html or '<p class="rail-meta">None yet.</p>'),
                    unsafe_allow_html=True)

        st.markdown(pulse_block(articles), unsafe_allow_html=True)

    st.stop()


# ===========================================================================
# VIEW: SEARCH RESULTS  (page 3 of the Visily reference)
# ===========================================================================
if view == "search":
    st.markdown(
        '<div class="sec-head"><span class="sec-eyebrow">Search</span>'
        f'<h2 style="color:var(--ink)">Results for “{esc(query)}”</h2>'
        f'<span class="sec-sub">{len(filtered)} story{"s" if len(filtered) != 1 else ""} found '
        f'(in {esc(picked_category or "All topics")})</span></div>',
        unsafe_allow_html=True,
    )

    if not filtered:
        st.markdown(
            f'<div class="empty"><h3>No stories matched “{esc(query)}”</h3>'
            f'<p>Try broader terms, remove the category filter, extend the lookback window, '
            f'or increase ingestion depth in Feed settings.</p>'
            f'<a class="btn" href="?view=home">View all news</a></div>',
            unsafe_allow_html=True,
        )
    else:
        # result breakdown chips
        result_counts = Counter(a["category"] for a in filtered)
        breakdown = "".join(
            f'<span class="chip" style="color:{m["color"]};background:{m["tint"]};">'
            f'{m["label"]} · {result_counts.get(k, 0)}</span> '
            for k, m in CATEGORY_META.items() if result_counts.get(k, 0)
        )
        st.markdown(f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">{breakdown}</div>',
                    unsafe_allow_html=True)

        rows_html = ""
        for pos, article in enumerate(filtered, start=1):
            haystack = " ".join([article["title"], article["description"], article["source"]])
            snip = highlight_matches(snippet(article["description"] or article["title"], 220), tokens)
            rows_html += (
                f'<div class="res-row"><div class="res-rank">{pos:02d}</div><div class="res-main">'
                f'<div class="res-top">{cat_chip(article["category"], with_emoji=True)}'
                f'<span class="res-meta">{esc(article["source"])} · {rel_time(article["publishedAt"])} · '
                f'Relevance <b>{article["audit_relevance"]}/100</b></span></div>'
                f'<h3><a href="{article_link(articles.index(article))}">'
                f'{highlight_matches(article["title"], tokens)}</a></h3>'
                f'<p class="res-snip">{snip}</p>'
                f'<div class="res-actions">'
                f'<a class="txt-link" href="{article_link(articles.index(article))}">Read story →</a>'
                f'<a class="txt-link" href="{esc(article["url"])}" target="_blank" rel="noopener noreferrer">Source ↗</a>'
                f'</div></div></div>'
            )
        st.markdown(rows_html, unsafe_allow_html=True)

        if len(filtered) > 60:
            st.caption("Showing the first 60 ranked results — refine your query for more precision.")
    st.stop()


# ===========================================================================
# VIEW: HOME — featured analysis, insights grid, intelligence rail
# ===========================================================================

if not articles:
    st.markdown(
        '<div class="empty"><h3>No stories loaded yet</h3>'
        '<p>Click “🔄 Fetch latest news” in Feed settings to pull the intelligence feed.</p></div>',
        unsafe_allow_html=True,
    )
    st.stop()

featured_pool = filtered if filtered else articles
leader = articles[0] if articles else None
side_picks = featured_pool[1:3]

# ---------- Featured analysis ----------
if featured_pool:
    main_feat = featured_pool[0]
    main_idx = articles.index(main_feat)
    meta = CATEGORY_META.get(main_feat["category"], {})

    hero_img = main_feat.get("image")
    hero_visual = (
        f'<img class="hero-img" src="{esc(hero_img)}" alt="{esc(main_feat["title"])}" loading="lazy" '
        f'onerror="this.style.display=\'none\'">'
        if hero_img
        else f'<div class="hero-img" style="display:flex;align-items:center;justify-content:center;'
             f'background:linear-gradient(120deg,{meta.get("tint","#EAF1FE")},{meta.get("color","#2563EB")}33)">'
             f'<span style="font-size:54px">{meta.get("emoji","📰")}</span></div>'
    )

    side_html = ""
    for pos, item in enumerate(side_picks, start=2):
        meta_s = CATEGORY_META.get(item["category"], {})
        side_html += (
            f'<div class="feat-mini"><div class="feat-num">0{pos}</div><div style="min-width:0">'
            f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">'
            f'{cat_chip(item["category"])}</div>'
            f'<h4><a href="{article_link(articles.index(item))}">{esc(snippet(item["title"], 110))}</a></h4>'
            f'<p>{esc(item["source"])} · {rel_time(item["publishedAt"])}</p></div></div>'
        )

    featured_html = f"""
    <div class="featured">
      <div class="hero-card">
        <a href="{article_link(main_idx)}">{hero_visual}</a>
        <div class="hero-body">
          <div class="eyebrow">⭐ Featured Analysis · {rel_time(main_feat["publishedAt"])}</div>
          {cat_chip(main_feat["category"], with_emoji=True)}
          <h2><a href="{article_link(main_idx)}">{esc(main_feat["title"])}</a></h2>
          <p>{esc(snippet(main_feat["description"] or "Top-ranked story in today's intelligence feed.", 240))}</p>
          <div class="hero-meta">
            <span class="rel-badge">{main_feat["audit_relevance"]}/100 relevance</span>
            <span class="time">🏛 {esc(main_feat["source"])} · {esc(main_feat["author"] or "NewsAPI wire")}</span>
          </div>
          <div class="hero-actions">
            <a class="btn" href="{article_link(main_idx)}">Read analysis</a>
            <a class="btn-ghost" href="{esc(main_feat["url"])}" target="_blank" rel="noopener noreferrer">Open source ↗</a>
          </div>
        </div>
      </div>
      <div class="feat-side">{side_html or '<div class="feat-mini"><div class="feat-num">02</div><div><h4>More stories loading…</h4></div></div>'}</div>
    </div>
    """
    st.markdown(featured_html, unsafe_allow_html=True)

st.markdown(
    '<div class="sec-head" style="margin-top:26px"><span class="sec-eyebrow">Latest Insights</span>'
    f'<h2>Fresh from the desk</h2>'
    f'<span class="sec-sub">{len(filtered)} story{"s" if len(filtered) != 1 else ""} · sorted by audit relevance</span></div>',
    unsafe_allow_html=True,
)

# ---------- Main content + right intelligence rail ----------
main_col, rail_col = st.columns([3, 1.12], gap="large")

with main_col:
    if not filtered:
        st.markdown(
            f'<div class="empty"><h3>No stories in {esc(picked_category)}</h3>'
            f'<p>Select “All topics”, extend the lookback window, or increase ingestion depth '
            f'in Feed settings.</p><a class="btn" href="?view=home">Reset view</a></div>',
            unsafe_allow_html=True,
        )
    else:
        grid_html = "".join(card_html(a, articles.index(a)) for a in filtered[:60])
        st.markdown(f'<div class="card-grid">{grid_html}</div>', unsafe_allow_html=True)
        if len(filtered) > 60:
            st.caption("Showing the first 60 stories — refine the category or search to focus.")

with rail_col:
    st.markdown(
        leader_block(articles)
        + trending_block(articles)
        + active_filters_block(picked_category, lookback_days, page_size, query)
        + pulse_block(articles),
        unsafe_allow_html=True,
    )

# ---------- Diagnostics ----------
if errors:
    with st.expander("⚠️ Source / API diagnostics"):
        for error in errors:
            st.write(error)
        st.caption("Other categories may have loaded normally — partial feed shown.")

st.markdown(
    '<div class="footer-note" style="margin-top:14px">Data source: NewsAPI (indexed sources only). '
    'Deduplicated by URL + normalized title · Audit relevance & classification are rule-based '
    'keyword signals, kept internal to ranking and filtering.</div>',
    unsafe_allow_html=True,
)
