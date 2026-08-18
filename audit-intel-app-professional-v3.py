import os
import re
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    import anthropic
except Exception:
    anthropic = None

st.set_page_config(
    page_title="Audit Intel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Professional editorial theme inspired by the supplied brief
# ============================================================
st.markdown("""
<style>
    .stApp { background:#f4f1e7; color:#222936; }
    [data-testid="stHeader"] { background:rgba(244,241,231,.92); }
    [data-testid="stSidebar"] {
        background:#16233a;
        border-right:1px solid #243653;
    }
    [data-testid="stSidebar"] * { color:#f5f7fb !important; }
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] small { color:#b9c4d4 !important; }
    [data-testid="stSidebar"] hr { border-color:#30415e !important; }
    [data-testid="stSidebar"] input { color:#ffffff !important; }
    .block-container { max-width:1160px; padding-top:2rem; padding-bottom:3rem; }

    .hero {
        padding:28px 32px 30px;
        border:1px solid #ddd6c6;
        border-radius:26px;
        background:#f9f6ec;
        box-shadow:0 14px 45px rgba(48,43,31,.07);
        margin-bottom:14px;
    }
    .eyebrow { color:#b47b25; font-size:12px; font-weight:900; letter-spacing:.16em; text-transform:uppercase; }
    .hero h1 { margin:7px 0 8px; color:#182338; font-size:46px; line-height:1.02; letter-spacing:-.04em; }
    .hero p { color:#706c62; margin:0; font-size:16px; }

    .market-banner {
        display:flex; justify-content:space-between; align-items:center; gap:16px;
        padding:13px 16px; border:1px solid #ddd6c6; border-radius:17px;
        background:#eeebdf; margin:10px 0 16px;
    }
    .market-title { color:#817b6d; font-size:11px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
    .market-count { color:#1c2434; font-size:13px; font-weight:850; margin-top:2px; }

    .metric { border:1px solid #ddd6c6; background:#f9f6ec; border-radius:17px; padding:14px 16px; }
    .metric .v { font-size:25px; font-weight:900; color:#182338; }
    .metric .l { color:#817c70; font-size:11px; font-weight:700; }

    .section-title { font-size:19px; font-weight:900; margin:19px 0 10px; color:#1c2434; }

    .chip {
        display:inline-block; padding:5px 10px; border-radius:999px;
        font-size:10px; font-weight:900; margin-right:5px; border:1px solid #ddd6c6;
        letter-spacing:.03em;
    }
    .chip-audit { background:#e5eeeb; color:#4f766b; }
    .chip-transform { background:#f1ead9; color:#96702d; }
    .chip-workflow { background:#e5eee9; color:#52766d; }
    .chip-process { background:#eee7dc; color:#84694c; }
    .chip-india { background:#f4ead6; color:#9a6c28; }
    .chip-global { background:#e6edf0; color:#536b7a; }

    .source { color:#777267; font-size:12px; font-weight:800; margin-top:7px; }
    .card {
        border:1px solid #ddd6c6; border-radius:24px; background:#fbfaf4;
        padding:21px 23px 1px; margin:0 0 15px;
        box-shadow:0 8px 28px rgba(48,43,31,.065); overflow:hidden;
    }
    .card h3 { margin:12px 0 8px; font-size:25px; color:#1c2434; letter-spacing:-.025em; line-height:1.16; }
    .summary { color:#4f4b44; font-size:16px; line-height:1.62; margin-bottom:17px; }
    .ai-badge { display:inline-flex; gap:5px; align-items:center; padding:4px 8px; border-radius:999px; background:#f0ede3; color:#89754e; border:1px solid #e1dac9; font-size:9px; font-weight:900; }
    .footer-note { color:#8b877d; font-size:11px; margin-top:20px; }

    div.stButton > button, .stLinkButton > a {
        border-radius:14px !important; border:1px solid #d9d2c2 !important;
        background:#fbfaf4 !important; color:#343b46 !important; font-weight:800 !important;
    }
    div.stButton > button:hover, .stLinkButton > a:hover { border-color:#aa9d83 !important; color:#172033 !important; }
    div.stButton > button[kind="primary"] { background:#182338 !important; color:#fff !important; border-color:#182338 !important; }

    div[role="radiogroup"] { gap:8px; }
    div[role="radiogroup"] label { background:#fbfaf4; border:1px solid #ddd6c6; border-radius:999px; padding:7px 14px; }
    div[role="radiogroup"] label:hover { border-color:#b7ab92; }

    [data-testid="stSidebar"] .stRadio label {
        background:#22324d !important;
        border:1px solid #3a4b67 !important;
        color:#f5f7fb !important;
        border-radius:999px;
        padding:7px 14px;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background:#2c3e5b !important;
        border-color:#8090aa !important;
    }
    [data-testid="stSidebar"] .stRadio label p {
        color:#f5f7fb !important;
        font-size:13px;
        font-weight:750;
    }
    [data-testid="stSidebar"] .stRadio label span {
        color:#f5f7fb !important;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color:#ffffff !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color:#b9c4d4 !important;
    }
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stSlider div {
        color:#f5f7fb !important;
    }
    [data-testid="stSidebar"] div.stButton > button {
        background:#22324d !important;
        color:#ffffff !important;
        border-color:#405473 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Demo data — deliberately includes Indian + global examples
# ============================================================
DEMO_ARTICLES = [
    {
        "title":"Building in-house instead of buying",
        "source":"HDFC Bank Newsroom",
        "category":"Workflow",
        "market":"Indian Banks",
        "summary":"Indian banks are exploring in-house AI capabilities alongside external platforms. For audit, the opportunity is to connect evidence, approvals and exception handling while retaining traceability and human oversight.",
        "url":"https://www.hdfcbank.com/",
        "published":"3 days ago",
    },
    {
        "title":"Data-led controls reshape Indian banking audit",
        "source":"Indian Banking Intelligence",
        "category":"Audit",
        "market":"Indian Banks",
        "summary":"Data-led control monitoring is creating a path from periodic sampling toward more continuous exception review. Audit teams can use this shift to focus scarce time on material anomalies and judgment-heavy work.",
        "url":"https://www.rbi.org.in/",
        "published":"5 days ago",
    },
    {
        "title":"Internal audit operating models are becoming more digital",
        "source":"Banking Conclave",
        "category":"Process",
        "market":"Indian Banks",
        "summary":"Internal audit functions are redesigning operating models around centralized evidence, data-driven risk assessment and faster issue remediation. The change also increases demand for analytics and technology skills within audit teams.",
        "url":"https://www.rbi.org.in/",
        "published":"1 week ago",
    },
    {
        "title":"Copilot embedded inside ServiceNow instances",
        "source":"ServiceNow Case Studies",
        "category":"Workflow",
        "market":"Global Banks",
        "summary":"Global financial institutions are embedding copilots into workflow platforms so users can query operational information in plain language. For audit, the value is faster evidence retrieval without losing workflow history and accountability.",
        "url":"https://www.servicenow.com/",
        "published":"1 week ago",
    },
    {
        "title":"Agentic AI emerges as a priority for audit transformation",
        "source":"Global Banking Technology",
        "category":"Transformation",
        "market":"Global Banks",
        "summary":"Global banks are testing agentic systems for multi-step tasks such as evidence gathering, policy comparison and exception triage. Governance, human approval and auditability remain the main adoption constraints.",
        "url":"https://www.bis.org/",
        "published":"4 days ago",
    },
    {
        "title":"AI governance increases demand for traceable controls",
        "source":"Risk & Compliance Monitor",
        "category":"Audit",
        "market":"Global Banks",
        "summary":"As AI adoption grows, control functions are putting more emphasis on model decisions, evidence lineage and control ownership. This makes traceable workflows and explainable evidence increasingly important to audit.",
        "url":"https://www.bis.org/",
        "published":"2 weeks ago",
    },
    {
        "title":"Digital evidence collection cuts manual audit effort",
        "source":"Financial Services Tech",
        "category":"Workflow",
        "market":"Indian Banks",
        "summary":"Automated evidence collection can reduce repetitive requests across control owners and create a more consistent evidence trail. Integration with existing workflow systems is the key implementation consideration.",
        "url":"https://www.rbi.org.in/",
        "published":"2 weeks ago",
    },
]

# Google News RSS is intentionally broad for a demo. Replace/expand with approved sources later.
SOURCE_GROUPS = {
    "Indian Banks": [
        ("HDFC Bank", "https://news.google.com/rss/search?q=" + quote_plus("HDFC Bank AI audit transformation") + "&hl=en-IN&gl=IN&ceid=IN:en"),
        ("Indian Banking", "https://news.google.com/rss/search?q=" + quote_plus("Indian banking AI internal audit transformation") + "&hl=en-IN&gl=IN&ceid=IN:en"),
        ("RBI / Banking", "https://news.google.com/rss/search?q=" + quote_plus("RBI banking AI risk controls") + "&hl=en-IN&gl=IN&ceid=IN:en"),
    ],
    "Global Banks": [
        ("Global Banking", "https://news.google.com/rss/search?q=" + quote_plus("global banks AI internal audit transformation") + "&hl=en&gl=US&ceid=US:en"),
        ("Banking Technology", "https://news.google.com/rss/search?q=" + quote_plus("banking technology audit AI workflow") + "&hl=en&gl=US&ceid=US:en"),
        ("Global Risk", "https://news.google.com/rss/search?q=" + quote_plus("global banking AI governance audit controls") + "&hl=en&gl=US&ceid=US:en"),
    ],
}

CATEGORIES = ["All", "Audit", "Transformation", "Workflow", "Process"]
MARKETS = ["All", "Indian Banks", "Global Banks"]

# ============================================================
# Helpers
# ============================================================
def get_secret(name, default=""):
    try:
        value = st.secrets.get(name, "")
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def db_conn():
    conn = sqlite3.connect("audit_intel.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            item_id TEXT PRIMARY KEY,
            reaction TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn


def get_reactions():
    conn = db_conn()
    rows = conn.execute("SELECT item_id, reaction FROM reactions").fetchall()
    conn.close()
    return {k:v for k,v in rows}


def save_reaction(item_id_value, reaction):
    conn = db_conn()
    conn.execute(
        "INSERT INTO reactions(item_id,reaction,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(item_id) DO UPDATE SET reaction=excluded.reaction, updated_at=excluded.updated_at",
        (item_id_value, reaction, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def make_item_id(item):
    return hashlib.sha1((item.get("url","") + item.get("title","")).encode()).hexdigest()[:12]


def clean_text(text):
    text = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def infer_market(source, text):
    blob = (source + " " + text).lower()
    indian_terms = [
        "hdfc", "icici", "sbi", "state bank of india", "axis bank", "kotak",
        "indusind", "idfc first", "bandhan", "rbl bank", "yes bank", "bank of baroda",
        "punjab national bank", "pnb", "canara bank", "union bank of india", "india",
        "indian banking", "rbi", "reserve bank of india", "nabard", "sebi"
    ]
    return "Indian Banks" if any(term in blob for term in indian_terms) else "Global Banks"


def fetch_rss(feed_url, source_name, limit=5):
    response = requests.get(feed_url, timeout=15, headers={"User-Agent":"AuditIntelMVP/1.0"})
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items = []
    for entry in parsed.entries[:limit]:
        title = clean_text(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        published = entry.get("published", "") or entry.get("updated", "")
        if title and link:
            items.append({
                "title":title,
                "source":source_name,
                "url":link,
                "raw_text":summary,
                "published":published,
            })
    return items


def classify_heuristic(text):
    t = text.lower()
    if any(x in t for x in ["workflow", "servicenow", "automation", "evidence collection"]):
        return "Workflow"
    if any(x in t for x in ["internal audit", "audit", "control testing", "assurance"]):
        return "Audit"
    if any(x in t for x in ["process", "operating model", "remediation"]):
        return "Process"
    return "Transformation"


def heuristic_summary(text, title):
    text = clean_text(text)
    if not text:
        return f"{title}. The item is relevant to banking transformation and audit intelligence."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    usable = [s.strip() for s in sentences if len(s.strip()) > 25]
    return " ".join(usable[:3])[:700] if usable else text[:700]


def llm_analyze(title, source, text):
    api_key = get_secret("ANTHROPIC_API_KEY")
    model = get_secret("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    if not api_key or anthropic is None:
        return classify_heuristic(title + " " + text), infer_market(source, title + " " + text), heuristic_summary(text, title), False

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""
You are an audit-intelligence analyst for a large bank.

Classify the item into exactly ONE category: Audit, Transformation, Workflow, Process.
Also classify the market as exactly ONE of: Indian Banks, Global Banks.

Audit is the dominant funnel. Use Audit when the item is materially about internal audit,
controls, assurance, testing, evidence, audit operating model, or audit technology.

For market classification, use explicit bank/source/location signals. Indian Banks means
Indian banking institutions or India-specific banking developments. Global Banks means
banks or banking developments outside India or global cross-border banking technology.

Return ONLY valid JSON:
{{"category":"...","market":"Indian Banks or Global Banks","title":"short improved title","summary":"3 concise sentences for a senior banking leader"}}

SOURCE: {source}
TITLE: {title}
CONTENT:
{text[:8000]}
"""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role":"user", "content":prompt}],
        )
        raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        data = json.loads(raw)
        category = data.get("category", "Transformation")
        if category not in CATEGORIES[1:]:
            category = "Transformation"
        market = data.get("market", "Global Banks")
        if market not in MARKETS[1:]:
            market = infer_market(source, title + " " + text)
        return category, market, data.get("summary", heuristic_summary(text, title)), True
    except Exception:
        return classify_heuristic(title + " " + text), infer_market(source, title + " " + text), heuristic_summary(text, title), False


def live_scan(max_per_source=4):
    raw = []
    for market, sources in SOURCE_GROUPS.items():
        for name, url in sources:
            try:
                fetched = fetch_rss(url, name, max_per_source)
                for x in fetched:
                    x["market"] = market
                raw.extend(fetched)
            except Exception:
                pass

    seen = set()
    unique = []
    for x in raw:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        unique.append(x)

    results = []
    for x in unique[:18]:
        category, market, summary, ai_used = llm_analyze(x["title"], x["source"], x["raw_text"])
        results.append({
            "title":x["title"],
            "source":x["source"],
            "category":category,
            "market":market,
            "summary":summary,
            "url":x["url"],
            "published":x["published"] or "Recent",
            "ai_used":ai_used,
        })
    return results


def load_demo():
    return [dict(x, ai_used=False) for x in DEMO_ARTICLES]


# ============================================================
# Session state
# ============================================================
if "feed_items" not in st.session_state:
    st.session_state["feed_items"] = load_demo()
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

reactions = get_reactions()

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("# 🛡️ Audit Intel")
    st.caption("AI-powered audit transformation feed")
    st.divider()

    st.markdown("**Market lens**")
    market_filter = st.radio("Market", MARKETS, index=0, label_visibility="collapsed")

    st.markdown("**Audit lens**")
    selected = st.radio("Category", CATEGORIES, index=0, label_visibility="collapsed")

    st.divider()
    st.markdown("**Scan controls**")
    max_items = st.slider("Items per source", 2, 6, 4)

    if st.button("↗  Run intelligence scan", use_container_width=True, type="primary"):
        with st.spinner("Scanning sources → classifying → summarizing..."):
            fresh = live_scan(max_items)
        if fresh:
            st.session_state["feed_items"] = fresh + st.session_state["feed_items"]
            st.session_state["feed_items"] = st.session_state["feed_items"][:36]
            st.session_state.last_scan = datetime.now().strftime("%d %b %Y, %H:%M")
            st.success(f"Added {len(fresh)} fresh items.")
        else:
            st.warning("Live sources returned no items. Demo feed is still available.")

    if st.button("↻  Reset demo feed", use_container_width=True):
        st.session_state["feed_items"] = load_demo()
        st.session_state.last_scan = None
        st.rerun()

    st.divider()
    api_ready = bool(get_secret("ANTHROPIC_API_KEY"))
    st.markdown("**System status**")
    st.write("🟢 RSS ingestion")
    st.write("🟢 Deduplication")
    st.write(("🟢" if api_ready else "🟡") + (" Claude AI" if api_ready else " Demo AI fallback"))
    st.write("🟢 Reaction signals")
    st.divider()
    st.caption("MVP • 90-day relevance window • Audit-first funnel")

# ============================================================
# Main header
# ============================================================
st.markdown("""
<div class="hero">
  <div class="eyebrow">AUDIT INTEL</div>
  <h1>This week's briefing</h1>
  <p>7 items · updated continuously · nothing older than 3 months</p>
</div>
""", unsafe_allow_html=True)

items = st.session_state["feed_items"]
for x in items:
    x.setdefault("market", infer_market(x.get("source", ""), x.get("title", "") + " " + x.get("summary", "")))

filtered = [
    x for x in items
    if (selected == "All" or x["category"] == selected)
    and (market_filter == "All" or x.get("market") == market_filter)
]

india_count = sum(1 for x in items if x.get("market") == "Indian Banks")
global_count = sum(1 for x in items if x.get("market") == "Global Banks")

st.markdown(
    f'''<div class="market-banner">
        <div><div class="market-title">Banking coverage</div><div class="market-count">Indian banks vs global banks</div></div>
        <div><span class="chip chip-india">INDIA · {india_count}</span><span class="chip chip-global">GLOBAL · {global_count}</span></div>
    </div>''',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
metrics = [
    (len(filtered), "Items shown"),
    (india_count, "Indian bank signals"),
    (global_count, "Global bank signals"),
    (sum(1 for x in items if x.get("ai_used")), "AI analyzed"),
]
for col, (value, label) in zip([c1,c2,c3,c4], metrics):
    with col:
        st.markdown(f'<div class="metric"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Intel feed</div>', unsafe_allow_html=True)
if st.session_state.last_scan:
    st.caption(f"Last live scan: {st.session_state.last_scan}")

# ============================================================
# Feed cards
# ============================================================
if not filtered:
    st.info("No intelligence in this filter yet. Try another market/category or run a live scan.")
else:
    for item in filtered:
        iid = make_item_id(item)
        reaction = reactions.get(iid)
        cat = item["category"].lower()
        if cat == "audit":
            chip_class = "chip-audit"
        elif cat == "transformation":
            chip_class = "chip-transform"
        elif cat == "workflow":
            chip_class = "chip-workflow"
        else:
            chip_class = "chip-process"

        market_chip = '<span class="chip chip-india">INDIA</span>' if item.get("market") == "Indian Banks" else '<span class="chip chip-global">GLOBAL</span>'
        ai = '<span class="ai-badge">✦ CLAUDE ANALYZED</span>' if item.get("ai_used") else '<span class="ai-badge">◌ DEMO ANALYSIS</span>'

        st.markdown(f"""
        <div class="card">
          <div>
            <span class="chip {chip_class}">{item["category"].upper()}</span>
            {market_chip}
            {ai}
          </div>
          <h3>{item["title"]}</h3>
          <div class="source">◉ {item["source"]} &nbsp;·&nbsp; {item.get("published", "Recent")}</div>
          <p class="summary">{item["summary"]}</p>
        </div>
        """, unsafe_allow_html=True)

        b1, b2, b3, b4 = st.columns([0.10, 0.10, 0.20, 0.60])
        with b1:
            if st.button("♡", key=f"like_{iid}", help="More like this"):
                save_reaction(iid, "like")
                reactions[iid] = "like"
                st.rerun()
        with b2:
            if st.button("×", key=f"dis_{iid}", help="Less like this"):
                save_reaction(iid, "dislike")
                reactions[iid] = "dislike"
                st.rerun()
        with b3:
            st.link_button("Read source ↗", item["url"])
        with b4:
            if reaction:
                st.caption(f"Signal captured: **{reaction}**")

st.markdown("""
<div class="footer-note">
MVP architecture: approved RSS/news sources → deduplication → AI classification → executive summary → editorial feed → reaction signal.
For production, move SQLite to an approved Postgres environment and schedule ingestion. Do not place bank-confidential data or credentials in a public repository.
</div>
""", unsafe_allow_html=True)
