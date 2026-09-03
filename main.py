import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExector, as_completed
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

try:
    from config inport API_KEY as CONFIG_API_KEY
except ImportError:
    CONFIG_API_KEY = ""


# ---------------------------------------------------------
# 1. APP CONFIGURATION & LIGHT EDIORIAL PALETE
# ----------------

st.set_page_config(
    page_title="Audit Intel | Global Banking Briefing",
    page_icon="Aisl",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Fixed ingestion depth — the "Stories Per Category" slider is removed
# from the UI; the feed depth stays constant while all logic is unchanged.
FEED_DEPTH = 50

st.markdown("""
<style>
    @import url('htt ps://fonts.googleapis.com/css2?family=Inter:wg...

    :root {
        --bg: #F7F8FA;
        --card: #FFFFF;
        --border: #E5E7EB;
        --text-primary: #111827;
        --text-secondary: #4B5563;
        --text-muted: #6B7280;
        --accent-blue: #2563EB;
        --accent-blue-dark: #1D4ED8;
    }

    .stApp {
        background: var(--bg);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
    }

    #MainMenu, header[data-testid="stHeader"] { background: transparent; }

    /* ---------------- Top navigation ---------------- */
    .topnav {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 2px 16px 2px; border-bottom: 1px solid var(--border);
        margin-bottom: 18px;
    }
    .topnav-left { display: flex; align-items: center; gap: 10px; }
    .logo-icon {
        width: 32px; height: 32px; border-radius: 8px;
        background: var(--accent-blue);
        display: flex; align-items: center; justify-content: center;
        color: #fff; font-size: 15px;
    }
    .logo-text { font-weight: 800; font-size: 17.5px; color: var(--text-primary); }

    .topnav-right { display: flex; align-items: center; gap: 18px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
    .nav-link { cursor: pointer; transition: color .12s ease; }
    .nav-link:hover { color: var(--accent-blue); }

    /* --- SENSEX ticker chip (top-right corner) --- */
    .sensex-chip {
        display: flex; align-items: center; gap: 7px;
        background: var(--card); border: 1px solid var(--border);
        border-radius: 999px; padding: 5px 12px;
        font-size: 12px; font-weight: 700; color: var(--text-primary);
        box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }
    .sensex-label { color: var(--text-muted); font-weight: 700; letter-spacing: .3px; font-size: 10.5px; text-transform: uppercase; }
    .sensex-up { color: #059669; }
    .sensex-down { color: #DC2626; }
    .sensex-off { color: var(--text-muted); font-weight: 600; }

    /* --- user chip (top-right corner) --- */
    .user-chip { display: flex; align-items: center; gap: 8px; cursor: default; }
    .avatar-circle, .avatar-circle-sm {
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-weight: 700; color: #fff; flex-shrink: 0;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
    }
    .avatar-circle { width: 44px; height: 44px; font-size: 16px; }
    .avatar-circle-sm { width: 30px; height: 30px; font-size: 12.5px; }
    .user-chip-name { line-height: 1.15; text-align: left; }
    .user-chip-name b { display: block; font-size: 12.5px; color: var(--text-primary); font-weight: 800; }
    .user-chip-name span { display: block; font-size: 10.5px; color: var(--text-muted); font-weight: 600; }

    /* ---------------- Section headings ---------------- */
    .section-heading {
        font-size: 15px; font-weight: 800; color: var(--text-primary);
        margin: 4px 0 14px 0;
        display: flex; align-items: baseline; gap: 8px;
    }
    .section-count { font-size: 12px; font-weight: 600; color: var(--text-muted); }
    .page-title { font-size: 26px; font-weight: 800; color: var(--text-primary); letter-spacing: -0.5px; margin-botton: 2px; }
    .page-subtitle { font-size: 13px; color: var(--text-secondar;); margin-bot: 20px; }

    /* ---------------- Pills / tabs ---------------- */
    div[data-testid="stTabs"] { margin-top: 4px; margin-bottom: 20px; }
    div[ata-testid="stAbs"] [role="tablist"] { gap: 4px; border-bottom: 1px solid var(--border); }
    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 0 !improtant; padding: 8px 16px !improtant;
        font-size: 12.5px !improtant; font-weight: 700 !improtant;
        letter-spacing: .3px; text-transform: uppercase; background: transparent !improtant;
        border: none !improtant; border-bottom: 2px solid transparent !improtant;
        color: var(--text-secondar) !improtant;
    }
    div[data-testid="stTabs"] button[role="tab"]:hover { color: var(--text-primary) !improtant; }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--accent-blue) !improtant; border-bottom: 2px solid var(--accent-blue) !improtant;
    }

    /* ---------------- Search input ---------------- */
    .stTextInput>div>div>input {
        background-color: #fff !improtant; border: 1px solid var(--border) !improtant;
        color: var(--text-primary) !improtant; border-radius: 10px !improtant;
        padding: 11px 16px !improtant; font-size: 14px !improtant;
    }
    .stTextInput>div>div>input:focus { border-color: var(--accent-blue) !improtant; box-shadow: 0 0 0 3px rgba(37,99,235,.12) !improtant; }
    .stTextInput div input::placeholder { color: var(--text-muted) !improtant; opacity: 1; }

    /* ---------------- Buttons ---------------- */
    .stButton>button { background: var(--accent-blue); color: #fff; border: none; border-radius: 8px; font-weight: 600; font-size: 13.5px; padding: 9px 18px; }
    .stButton>button:hover { background: var(--accent-blue-dark); }
    [data-testid="stDownloadButton"]>button { background: #fff; color: var(--accent-blue); border: 1px solid var(--accent-blue); border-radius: 8px; font-weight: 600; }
    [data-testid="stDownloadButton"]>button:hover { background: #EFF6FF; }

    /* ---------------- Featured Analysis hero ---------------- */
    .featured-hero {
        position: relative; height: 360px; border-radius: 16px;
        background-size: cover; background-position: center; overflow: hidden;
        margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
    }
    .featured-badge {
        position: absolute; top: 20px; left: 20px; color: #fff; font-size: 11px; font-weight: 700;
        padding: 5px 12px; border-radius: 6px; text-transform: uppercase; letter-spacing: .5px; z-index: 2;
    }
    .featured-text { position: absolute; bottom: 24px; left: 28px; right: 28px; z-index: 2; }
    .featured-title { font-size: 27px; font-weight: 800; color: #fff; line-height: 1.28; margin-bottom: 8px; text-shadow: 0 2px 10px rgba(0,0,0,.35); }
    .featured-meta { font-size: 13px; color: rgba(255,255,255,.92); font-weight: 500; }
    .featured-link-overlay { position: absolute; inset: 0; z-index: 3; }

    /* ---------------- Insight cards ---------------- */
    .insight-card {
        display: flex; gap: 20px; background: var(--card); border: 1px solid var(--border);
        border-radius: 14px; padding: 16px; margin-bottom: 16px;
        transition: box-shadow .15s ease, border-color .15s ease;
    }
    .insight-card:hover { border-color: #D1D5DB; box-shadow: 0 4px 14px rgba(0,0,0,.05); }
    .insight-thumb { width: 180px; min-width: 180px; height: 128px; background-size: cover; background-position: center; background-color: #F3F4F6; border-radius: 10px; }
    .insight-thumb-empty { display: flex; align-items: center; justify-content: center; font-size: 28px; color: #C7CBD3; }
    .insight-content { display: flex; flex-direction: column; min-width: 0; }
    .insight-meta-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .badge { display: inline-block; color: #fff; font-size: 10.5px; font-weight: 700; padding: 3px 10px; border-radius: 5px; text-transform: uppercase; letter-spacing: .4px; }
    .insight-date { font-size: 12px; color: var(--text-muted); font-weight: 500; }
    .insight-title-link { text-decoration: none; }
    .insight-title { font-size: 17px; font-weight: 700; color: #0F172A; line-height: 1.35; margin-bottom: 6px; }
    .insight-title-link:hover .insight-title { color: var(--accent-blue); }
    .insight-desc { font-size: 13.5px; color: var(--text-secondary); line-height: 1.55; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .insight-footer { display: flex; justify-content: space-between; align-items: center; margin-top: auto; }
    .score-chip { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600; color: #B45309; background: #FEF3C7; padding: 3px 10px; border-radius: 20px; }
    .read-link { font-size: 12.5px; font-weight: 700; color: var(--accent-blue); text-decoration: none; }
    .read-link:hover { text-decoration: underline; }

    /* ---------------- Right sidebar panels ---------------- */
    .side-panel { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; margin-bottom: 16px; }
    .side-panel-title { font-size: 11px; font-weight: 800; color: var(--text-primary); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
    .trend-row, .filter-row, .pulse-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px; color: #334155; }
    .trend-row:last-child, .filter-row:last-child, .pulse-row:last-child { border-bottom: none; }
    .trend-count { background: #F3F4F6; color: #4B5563; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 10px; }
    .filter-value { font-weight: 700; color: var(--text-primary); }
    .pulse-value { font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }

    /* --- user profile panel (top of the right rail) --- */
    .profile-row { display: flex; align-items: center; gap: 12px; }
    .profile-meta b { font-size: 15px; color: var(--text-primary); display: block; }
    .profile-meta span { font-size: 12.5px; color: var(--text-muted); font-weight: 600; }
    .internal-tag {
        display: inline-block; margin-top: 12px; font-size: 10.5px; font-weight: 800;
        text-transform: uppercase; letter-spacing: .6px; color: var(--accent-blue);
        background: #EFF6FF; border: 1px solid #BFDBFE; padding: 4px 10px; border-radius: 6px;
    }
    .profile-note { font-size: 12px; color: var(--text-muted); margin-top: 12px; line-height: 1.5; border-top: 1px dashed var(--border); padding-top: 10px; }

    .cta-panel { background: linear-gradient(135deg, #2563EB, #1D4ED8); border-radius: 14px; padding: 20px 22px 6px 22px; color: #fff; margin-bottom: 0; }
    .cta-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
    .cta-desc { font-size: 12.5px; color: rgba(255,255,255,.92); line-height: 1.5; margin-bottom: 14px; }

    .empty-state-panel { text-align: center; padding: 48px; background: var(--card); border-radius: 16px; border: 1px dashed var(--border); margin-top: 14px; }

    /* ---------------- Footer ---------------- */
    .app-footer { display: flex; justify-content: space-between; align-items: flex-start; padding-top: 22px; margin-top: 8px; border-top: 1px solid var(--border); }
    .footer-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-weight: 800; font-size: 14.5px; color: var(--text-primary); }
    .footer-tagline { font-size: 12px; color: var(--text-muted); max-width: 320px; line-height: 1.5; }
    .footer-links { display: flex; gap: 22px; font-size: 12.5px; color: var(--text-secondary); font-weight: 600; cursor: default; }
    .footer-links span:hover { color: var(--accent-blue); }
    .footer-copyright { font-size: 11.5px; color: var(--text-muted); margin-top: 18px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 2. BANKING AUDIT CATEGORIES & QUERIES (4 categories)
# ---------------------------------------------------------

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
    "Global Banks": {
        "query": '("bank" OR "banking group" OR "financial institution") AND ("audit" OR "internal controls" OR "risk" OR "governance" OR "regulatory") AND ("HSBC" OR "JPMorgan" OR "JPMorgan Chase" OR "Citi" OR "Citigroup" OR "Barclays" OR "Deutsche Bank" OR "UBS" OR "BNP Paribas" OR "Santander" OR "Standard Chartered" OR "Bank of America" OR "Goldman Sachs" OR "Morgan Stanley" OR "Wells Fargo" OR "ING" OR "ICBC" OR "MUFG" OR "Mizuho")'
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

AUDIT_TERMS = [
    "internal audit", "external audit", "audit committee", "auditor",
    "audit finding", "audit findings", "internal control", "internal controls",
    "control weakness", "control weaknesses", "control deficiency",
    "control deficiencies", "governance", "risk management", "operational risk",
    "model risk", "compliance", "regulatory", "regulation", "supervision",
    "supervisory", "enforcement", "aml", "anti-money laundering", "kyc",
    "sanctions", "fraud", "misconduct", "financial crime",
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

_ACRONYMS = {"rbi", "aml", "kyc", "ceo", "cfo", "cro", "ciso"}


# ---------------------------------------------------------
# 3. EXTRACTION LOGIC & SCORING (unchanged)
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
        score = sum(1 for term in terms if term in text)
        scores[category] = score

    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        best_category = "Regulation"

    return best_category, scores[best_category]


def fetch_category(category, query, api_key, from_date, page_size):
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
    from_date = (
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")

    all_articles = []
    errors = []

    with ThreadPoolExecutor(max_workers=len(CATEGORIES)) as executor:
        futures = {
            executor.submit(
                fetch_category, category, settings["query"],
                api_key, from_date, page_size,
            ): category
            for category, settings in CATEGORIES.items()
        }

        for future in as_completed(futures):
            category = futures[future]
            try:
                all_articles.extend(future.result())
            except Exception as exc:
                errors.append(f"{category}: {exc}")

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

        if relevance < 5:
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
    return cleaned, errors


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


def format_topic_label(term):
    words = term.split()
    out = []
    for w in words:
        out.append(w.upper() if w in _ACRONYMS else w.capitalize())
    return " ".join(out)


def compute_trending_topics(rows, top_n=4):
    all_terms = set()
    for terms in CATEGORY_TERMS.values():
        all_terms.update(terms)

    counter = Counter()
    for row in rows:
        text = f'{row["title"]} {row["description"]}'.lower()
        for term in all_terms:
            if term in text:
                counter[term] += 1

    return [(format_topic_label(term), count) for term, count in counter.most_common(top_n) if count > 0]


# ---------------------------------------------------------
# 4. LIVE SENSEX (top-right corner) — graceful fallback
# ---------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def get_sensex():
    """
    Real-time SENSEX quote via Yahoo Finance's chart API.
    Returns None (and the chip shows an honest "unavailable" state)
    if the endpoint is blocked or unreachable.
    """
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1d"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        payload = response.json()
        meta = payload["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        previous = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None or previous is None:
            return None
        change = price - previous
        pct = (change / previous) * 100
        return {
            "price": price,
            "change": change,
            "pct": pct,
            "as_of": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        }
    except Exception:
        return None


def render_sensex_chip():
    quote = get_sensex()
    if quote is None:
        return (
            '<span class="sensex-chip" title="Live feed unavailable — check network access">'
            '<span class="sensex-label">SENSEX</span>'
            '<span class="sensex-off">unavailable</span></span>'
        )
    arrow = "▲" if quote["change"] >= 0 else "▼"
    cls = "sensex-up" if quote["change"] >= 0 else "sensex-down"
    sign = "+" if quote["change"] >= 0 else ""
    return (
        f'<span class="sensex-chip" title="Near-live · Yahoo Finance · as of {esc_html(quote["as_of"])}">'
        f'<span class="sensex-label">SENSEX</span>'
        f'<span class="sensex-up" style="color:{"#059669" if quote["change"] >= 0 else "#DC2626"}">{arrow}</span>'
        f'<span>{quote["price"]:,.2f}</span>'
        f'<span class="{cls}">{sign}{quote["pct"]:.2f}%</span></span>'
    )


def esc_html(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------
# 5. TOP NAVIGATION
# ---------------------------------------------------------

st.markdown(f"""
<div class="topnav">
    <div class="topnav-left">
        <div class="logo-icon">🛡</div>
        <div class="logo-text">Audit Intel</div>
    </div>
    <div class="topnav-right">
        {render_sensex_chip()}
        <span class="nav-link">Dashboard</span>
        <span class="nav-link">Saved</span>
        <span class="nav-link">Explore ▾</span>
        <span class="nav-link">🔔</span>
        <div class="user-chip" title="Pragati · Head of Internal Audit">
            <div class="avatar-circle-sm">P</div>
            <div class="user-chip-name" style="display:none">Pragati</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 6. DATA CONTROLS (no "Stories Per Category" slider)
# ---------------------------------------------------------

api_key = get_api_key()

with st.expander("⚙️  Advanced Filters & Data Controls", expanded=(not api_key)):
    if not api_key:
        api_key = st.text_input(
            "NewsAPI Key",
            type="password",
            placeholder="Enter API key...",
            help="Configurable via secrets.toml or config.py for a persistent setup.",
        )

    lookback_days = st.slider("Lookback Window (Days)", min_value=1, max_value=7, value=3)

    selected_categories = st.multiselect(
        "Active Categories",
        options=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        format_func=lambda c: CATEGORY_DISPLAY.get(c, c),
    )

    refresh = st.button("⟲  Update Briefing", type="primary")

if not api_key:
    st.info("💡 Please enter your NewsAPI key above (or configure API_KEY in Streamlit secrets) to load the briefing.")
    st.stop()


# ---------------------------------------------------------
# 7. DATA INGESTION & FILTERING
# ---------------------------------------------------------

if refresh or "news_loaded" not in st.session_state:
    with st.spinner("Compiling this week's audit intelligence briefing..."):
        articles, errors = load_news(api_key, lookback_days, FEED_DEPTH)

    st.session_state.news = articles
    st.session_state.news_errors = errors
    st.session_state.news_loaded = True

articles = st.session_state.get("news", [])
errors = st.session_state.get("news_errors", [])

if selected_categories:
    filtered = [a for a in articles if a["category"] in selected_categories]
else:
    filtered = []

if errors:
    with st.expander("Feed Diagnostic Notices", expanded=False):
        for err in errors:
            st.markdown(f"<div style='font-size: 12px; color: #B45309;'>• {err}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 8. SEARCH BAR
# ---------------------------------------------------------

st.markdown('<div class="page-title">This week\'s briefing</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-subtitle">{len(filtered)} items &nbsp;·&nbsp; verified banking internal controls & regulatory surveillance</div>',
    unsafe_allow_html=True,
)

search_query = st.text_input(
    "Search",
    placeholder="🔍  Search news, regulations, and insights...",
    label_visibility="collapsed",
)

if search_query:
    sq = search_query.lower()
    filtered = [
        a for a in filtered
        if sq in a["title"].lower() or sq in a["description"].lower() or sq in a["source"].lower()
    ]


# ---------------------------------------------------------
# 9. RENDER HELPERS — hero card + insight cards
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
                <span class="score-chip">AUDIT SCORE {article['audit_relevance']}/100</span>
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
            <div style="font-size: 13.5px; color: #6B7280; margin-top: 6px;">Try expanding the lookback window or broadening the search above.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if show_featured:
        st.markdown(
            f'<div class="section-heading">Featured Analysis <span class="section-count">· {len(rows)} story{"s" if len(rows) != 1 else ""}</span></div>',
            unsafe_allow_html=True,
        )
        render_featured(rows[0])
        rest = rows[1:]
    else:
        rest = rows

    if rest:
        st.markdown(
            f'<div class="section-heading">Latest Insights <span class="section-count">· {len(rest)} story{"s" if len(rest) != 1 else ""}</span></div>',
            unsafe_allow_html=True,
        )
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
    # --- User corner section: Pragati · Head of Internal Audit ---
    st.markdown("""
    <div class="side-panel">
        <div class="side-panel-title">👤 Operator</div>
        <div class="profile-row">
            <div class="avatar-circle">P</div>
            <div class="profile-meta">
                <b>Pragati</b>
                <span>Head of Internal Audit</span>
            </div>
        </div>
        <div class="internal-tag">Internal tool</div>
        <div class="profile-note">Personalized briefing for the Internal Audit department. Not for external distribution.</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Top Source (real data) ---
    if filtered:
        source_counts = Counter(a["source"] for a in filtered)
        top_source, top_count = source_counts.most_common(1)[0]
        initial = top_source[:1].upper() if top_source else "?"
        st.markdown(f"""
        <div class="side-panel">
            <div class="side-panel-title">👤 Top Source</div>
            <div style="display:flex; align-items:center; gap:12px;">
                <div class="avatar-circle" style="background:linear-gradient(135deg,#1E3A8A,#2563EB)">{initial}</div>
                <div>
                    <div style="font-weight:700; font-size:14.5px; color:#111827;">{top_source}</div>
                    <div style="font-size:12.5px; color:#6B7280;">{top_count} stories in this briefing</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Trending Topics (real keyword frequency) ---
    trending = compute_trending_topics(filtered)
    if trending:
        rows_html = "".join(
            f'<div class="trend-row"><span>{label}</span><span class="trend-count">{count}</span></div>'
            for label, count in trending
        )
        st.markdown(f"""
        <div class="side-panel">
            <div class="side-panel-title">📈 Trending Topics</div>
            {rows_html}
        </div>
        """, unsafe_allow_html=True)

    # --- Active Filters ---
    active_categories = ", ".join(CATEGORY_DISPLAY.get(c, c) for c in selected_categories) or "None selected"
    search_row = f'<div class="filter-row"><span>Search</span><span class="filter-value">"{search_query}"</span></div>' if search_query else ""
    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">⚙️ Active Filters</div>
        <div class="filter-row"><span>Categories</span><span class="filter-value">{active_categories}</span></div>
        <div class="filter-row"><span>Lookback</span><span class="filter-value">Last {lookback_days}d</span></div>
        {search_row}
    </div>
    """, unsafe_allow_html=True)

    # --- Feed Pulse (real pipeline metrics) ---
    if filtered:
        avg_score = round(sum(a["audit_relevance"] for a in filtered) / len(filtered))
        today_count = sum(1 for a in filtered if format_relative_time(a["publishedAt"]) == "Today")
        unique_sources = len(set(a["source"] for a in filtered))
    else:
        avg_score, today_count, unique_sources = 0, 0, 0

    st.markdown(f"""
    <div class="side-panel">
        <div class="side-panel-title">📊 Feed Pulse</div>
        <div class="pulse-row"><span>Avg Audit Score</span><span class="pulse-value">{avg_score}/100</span></div>
        <div class="pulse-row"><span>Published Today</span><span class="pulse-value">{today_count}</span></div>
        <div class="pulse-row"><span>Unique Sources</span><span class="pulse-value">{unique_sources}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # --- Download CTA (functional CSV export) ---
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
        <div class="footer-brand"><span>🛡</span> Audit Intel</div>
        <div class="footer-tagline">Curated intelligence feed for Audit Committees and Chief Risk Officers across banking and financial services.</div>
    </div>
    <div class="footer-links">
        <span>About Us</span>
        <span>Contact</span>
        <span>Privacy Policy</span>
        <span>Terms of Service</span>
    </div>
</div>
<div class="footer-copyright">© 2026 Audit Intel &middot; Internal tool &middot; Not for external distribution</div>
""", unsafe_allow_html=True)
