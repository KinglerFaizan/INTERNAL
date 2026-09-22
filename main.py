import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

try:
    from config import API_KEY as CONFIG_API_KEY
except ImportError:
    CONFIG_API_KEY = ""

# NewsAPI credentials are resolved from config.py, environment variables, or
# Streamlit secrets. No credential is rendered in the UI or committed here.
NEWSAPI_KEY = ""


# ---------------------------------------------------------
# 1. APP CONFIGURATION & LIGHT EDITORIAL PALETTE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Audit Intelligence | Global Banking Briefing",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .topnav-left { display: flex; align-items: center; gap: 14px; }
    .topnav-right { display:flex; align-items:center; gap:20px; }

    /* ---- Emblem: deep navy tile, inner bevel, blue rim glow ---- */
    .logo-icon {
        position: relative;
        width: 54px; height: 54px;
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
        font-size: 30px;
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

    /* Avatar: object-position keeps the face centred inside the circle
       instead of cropping to the shoulders. */
    .avatar-photo {
        width: 52px; height: 52px; border-radius: 50%;
        object-fit: cover;
        object-position: center 22%;
        flex-shrink: 0;
        border: 3px solid #fff;
        box-shadow: 0 0 0 2px var(--accent-blue);
        display: block;
    }
    .avatar-circle-lg {
        width: 68px; height: 68px; border-radius: 50%;
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 21px; color: #fff; flex-shrink: 0;
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

    .stTabs button[data-baseweb="tab"]:hover,
    .stTabs button[data-baseweb="tab"]:hover *,
    .stTabs button[role="tab"]:hover,
    .stTabs button[role="tab"]:hover * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background: transparent !important;
    }

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
    .featured-carousel { position:relative; height:390px; margin:8px 0 30px; border-radius:18px; overflow:hidden; background:#0F172A; box-shadow:0 12px 34px rgba(15,23,42,.12); }
    .featured-slide { position:absolute; inset:0; opacity:0; transform:scale(1.015); animation:featuredCycle 24s infinite; animation-fill-mode:both; }
    .featured-slide:nth-child(2) { animation-delay:0s; }
    .featured-slide:nth-child(3) { animation-delay:6s; }
    .featured-slide:nth-child(4) { animation-delay:12s; }
    .featured-slide:nth-child(5) { animation-delay:18s; }
    .featured-slide-bg { position:absolute; inset:0; background-size:cover; background-position:center; background-color:#172554; }
    .featured-slide-bg::after { content:""; position:absolute; inset:0; background:linear-gradient(90deg,rgba(2,6,23,.88) 0%,rgba(2,6,23,.62) 48%,rgba(2,6,23,.20) 100%),linear-gradient(0deg,rgba(2,6,23,.72) 0%,rgba(2,6,23,0) 58%); }
    .featured-slide-content { position:absolute; left:34px; right:34px; bottom:30px; z-index:2; max-width:780px; }
    .featured-slide-kicker { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
    .featured-slide-rank { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#2563EB; color:#fff; font-size:11px; font-weight:900; box-shadow:0 5px 14px rgba(37,99,235,.35); }
    .featured-slide-tag { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; color:#fff; font-size:10px; font-weight:800; letter-spacing:.5px; text-transform:uppercase; background:rgba(37,99,235,.88); border:1px solid rgba(255,255,255,.22); }
    .featured-slide-title { color:#fff; font-size:29px; font-weight:850; line-height:1.22; letter-spacing:-.5px; text-decoration:none; text-shadow:0 2px 18px rgba(0,0,0,.32); display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
    .featured-slide-title:hover { color:#DBEAFE; }
    .featured-slide-meta { color:rgba(255,255,255,.78); font-size:12px; margin-top:12px; font-weight:600; }
    .featured-progress { position:absolute; left:34px; right:34px; top:20px; z-index:4; display:flex; gap:6px; }
    .featured-progress span { flex:1; height:3px; border-radius:99px; background:rgba(255,255,255,.25); overflow:hidden; position:relative; }
    .featured-progress span::after { content:""; position:absolute; inset:0; background:#fff; transform:scaleX(0); transform-origin:left; animation:featuredProgress 24s linear infinite; }
    .featured-progress span:nth-child(1)::after { animation-delay:0s; }
    .featured-progress span:nth-child(2)::after { animation-delay:6s; }
    .featured-progress span:nth-child(3)::after { animation-delay:12s; }
    .featured-progress span:nth-child(4)::after { animation-delay:18s; }
    @keyframes featuredCycle {
        0%, 24% { opacity:1; transform:scale(1); }
        25%, 100% { opacity:0; transform:scale(1.015); }
    }
    @keyframes featuredProgress {
        0%, 24% { transform:scaleX(1); }
        25%, 100% { transform:scaleX(0); }
    }
    .featured-reduced-motion { animation:none !important; }
    @media (prefers-reduced-motion: reduce) {
        .featured-slide { animation:none !important; opacity:0; transform:none; }
        .featured-slide:first-child { opacity:1; }
        .featured-progress span::after { animation:none !important; }
        .featured-progress span:first-child::after { transform:scaleX(1); }
    }

    /* ---------------- Application shell / sidebar ---------------- */
    [data-testid="stSidebar"] { background:#FFFFFF !important; border-right:1px solid #E5E7EB; }
    [data-testid="stSidebar"] > div:first-child { padding-top:14px; }
    [data-testid="stSidebar"] .block-container { padding:10px 14px 24px !important; }
    .sidebar-shell-brand { display:flex; align-items:center; gap:10px; padding:2px 4px 18px; }
    .sidebar-shell-icon { width:38px; height:38px; border-radius:11px; background:linear-gradient(145deg,#6D5DF5,#315BEA); color:#fff; display:flex; align-items:center; justify-content:center; font-size:19px; box-shadow:0 5px 14px rgba(49,91,234,.25); }
    .sidebar-shell-title { font-size:16px; font-weight:900; color:#111827; letter-spacing:-.3px; }
    .sidebar-shell-title span { color:#2563EB; }
    .sidebar-nav { display:flex; flex-direction:column; gap:5px; padding-bottom:16px; border-bottom:1px solid #E5E7EB; }
    .sidebar-nav-item { display:flex; align-items:center; gap:12px; min-height:40px; padding:0 10px; border-radius:10px; color:#5B6678; font-size:12.5px; font-weight:650; }
    .sidebar-nav-item.active { background:#EAF1FF; color:#2563EB; font-weight:800; }
    .sidebar-nav-icon { width:18px; text-align:center; font-size:16px; color:#64748B; }
    .sidebar-nav-item.active .sidebar-nav-icon { color:#2563EB; }
    .sidebar-status { padding:18px 4px 16px; border-bottom:1px solid #E5E7EB; }
    .sidebar-kicker { font-size:9.5px; color:#94A3B8; font-weight:800; letter-spacing:1.3px; text-transform:uppercase; }
    .sidebar-live-row { display:flex; align-items:center; justify-content:space-between; margin-top:9px; }
    .sidebar-live-left { display:flex; align-items:center; gap:7px; font-size:12.5px; font-weight:800; color:#111827; }
    .sidebar-live-dot { width:8px; height:8px; border-radius:50%; background:#16A34A; }
    .sidebar-active-pill { background:#DCFCE7; color:#16A34A; border-radius:999px; padding:4px 10px; font-size:10px; font-weight:800; }
    .sidebar-updated { margin-top:8px; font-size:10.5px; color:#64748B; line-height:1.5; }
    .sidebar-quick-title { padding:17px 4px 8px; font-size:9.5px; color:#94A3B8; font-weight:800; letter-spacing:1.3px; text-transform:uppercase; }
    .sidebar-note { font-size:10px; color:#94A3B8; margin:5px 4px 0; line-height:1.45; }
    .sidebar-filter-label { font-size:10px; color:#64748B; font-weight:700; margin:8px 2px 4px; }

    [data-testid="stSidebar"] .stButton > button { min-height:39px; border-radius:9px; border:1px solid #DCE5F7; background:#F8FAFF; color:#475569 !important; box-shadow:none; font-weight:700; text-align:left; }
    [data-testid="stSidebar"] .stButton > button:hover { border-color:#BFD1FF; background:#EFF5FF; color:#2563EB !important; }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] { background:#1769F5 !important; border-color:#1769F5 !important; color:#fff !important; box-shadow:0 5px 14px rgba(23,105,245,.22); }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover { background:#1258D5 !important; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { border:0 !important; background:transparent !important; margin:3px 0 0; }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary { padding:9px 4px !important; background:transparent !important; border:0 !important; font-size:12px !important; font-weight:700 !important; color:#475569 !important; }
    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] { padding:6px 2px 10px !important; }
    [data-testid="stSidebar"] .stSlider, [data-testid="stSidebar"] .stMultiSelect { margin-top:4px; }
    [data-testid="stSidebar"] .stCaption { color:#94A3B8 !important; font-size:9.5px !important; }
    .top-search { width:320px; height:38px; border:1px solid #E5E7EB; background:#fff; border-radius:999px; display:flex; align-items:center; gap:9px; padding:0 14px; color:#94A3B8; font-size:11px; box-shadow:0 2px 8px rgba(15,23,42,.03); }
    .top-search-icon { font-size:16px; color:#64748B; }
    .top-bell { position:relative; font-size:21px; color:#111827; margin-left:2px; }
    .top-bell-dot { position:absolute; width:7px; height:7px; border-radius:50%; background:#EF4444; right:-2px; top:0; border:1px solid #fff; }
    .news-section-title { display:flex; align-items:center; justify-content:space-between; margin:4px 0 12px; }
    .news-section-title-main { font-size:18px; font-weight:800; color:#0B1220; }
    .news-section-title-sub { font-size:11px; color:var(--text-muted); font-family:'JetBrains Mono',monospace; }
    .sidebar-brand, .sidebar-brand-title, .sidebar-brand-sub { display:none; }
    @media (max-width:900px) {
        .featured-carousel { height:420px; }
        .featured-slide-title { font-size:24px; }
        .featured-slide-content { left:24px; right:24px; bottom:24px; }
        .featured-progress { left:24px; right:24px; }
    }
    @media (max-width:600px) {
        .featured-carousel { height:440px; }
        .featured-slide-title { font-size:21px; }
        .featured-slide-content { left:20px; right:20px; bottom:20px; }
        .featured-progress { left:20px; right:20px; }
    }

    /* ---------------- Insight cards ---------------- */
    .insight-card {
        display:flex;
        flex-direction:column;
        gap:0;
        height:100%;
        background:var(--card);
        border:1px solid var(--border);
        border-radius:15px;
        padding:12px;
        margin-bottom:0;
        transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
        box-shadow:0 4px 16px rgba(15,23,42,.045);
    }
    .insight-card:hover { transform:translateY(-2px); border-color:#CBD5E1; box-shadow:0 10px 26px rgba(15,23,42,.09); }
    .insight-thumb {
        width:100%; min-width:0; height:170px;
        border-radius:11px;
        object-fit:cover;
        background-color:#EEF2F7;
        background-repeat:no-repeat;
        background-position:center;
        background-size:52px 52px;
        border:1px solid #E5E7EB;
        display:block;
        margin-bottom:12px;
    }
    .insight-content { display:flex; flex-direction:column; min-width:0; flex:1; padding:1px 3px 2px; }
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
    "Cyber & Tech": {
        "queries": [
            '("bank" OR "banking") AND (cybersecurity OR "cyber attack" OR ransomware OR "data breach" OR malware OR phishing)',
            '("bank" OR "banking") AND ("artificial intelligence" OR "machine learning" OR cloud OR automation) AND (risk OR controls OR governance OR fraud)',
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
    "Cyber & Tech": "Cyber & Technology",
}
CATEGORY_COLORS = {
    "Transformation": "#2563EB",
    "Regulation": "#16A34A",
    "People": "#6B7280",
    "Global Banks": "#7C3AED",
    "Cyber & Tech": "#0891B2",
}

PAGE_SIZE = 100
MAX_PAGES = 1

PRAGATI_NAME = "Pragati"
PRAGATI_TITLE = "Head of Internal Audit"

# ---------------------------------------------------------
# Pragati's portrait, embedded as a base64 JPEG so it renders
# inside the custom HTML top-nav (a local file path would not
# resolve there). Centre-cropped to a square, 240x240, ~9 KB.
# ---------------------------------------------------------
PRAGATI_PHOTO_B64 = (
    "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"
)

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
    "Cyber & Tech": [
        "cybersecurity", "cyber security", "cyber attack", "ransomware", "data breach",
        "malware", "phishing", "technology", "artificial intelligence", "generative ai",
        "machine learning", "cloud", "automation", "digital fraud",
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

    for name in ("NEWSAPI_KEY", "NEWS_API_KEY", "API_KEY"):
        env_key = os.getenv(name, "").strip()
        if env_key:
            return env_key

    try:
        secret_key = (
            st.secrets.get("NEWSAPI_KEY", "")
            or st.secrets.get("NEWS_API_KEY", "")
            or st.secrets.get("API_KEY", "")
        )
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

    params.pop("apiKey", None)
    response = requests.get(
        url,
        params=params,
        headers={"X-Api-Key": api_key},
        timeout=25,
    )
    try:
        payload = response.json()
    except Exception:
        payload = {}

    if payload.get("status") != "ok":
        code = payload.get("code", "")
        message = payload.get("message", "NewsAPI returned an error.")
        raise RuntimeError(f"{code}: {message}" if code else message)

    articles = payload.get("articles", [])
    for article in articles:
        article["_query_category"] = category

    return articles, payload.get("totalResults", 0)


def fetch_google_rss(category, query, lookback_days):
    """Public fallback used only when NewsAPI returns no usable stories."""
    rss_query = f"{query} when:{max(1, min(30, int(lookback_days)))}d"
    response = requests.get(
        "https://news.google.com/rss/search",
        params={"q": rss_query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers={"User-Agent": "Mozilla/5.0 Audit-Intelligence/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    rows = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link or title.lower().startswith("[removed]"):
            continue
        description = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        description = re.sub(r"\\s+", " ", description).strip()
        source_node = item.find("source")
        source = (source_node.text or "").strip() if source_node is not None else ""
        rows.append({
            "title": title,
            "description": description,
            "content": "",
            "url": link,
            "urlToImage": "",
            "source": {"name": source or "Google News"},
            "publishedAt": (item.findtext("pubDate") or "").strip(),
            "author": "",
            "_query_category": category,
        })
    return rows


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
    fallback_used = False
    fallback_errors = []

    if raw_count == 0:
        fallback_used = True
        rss_jobs = [(category, query) for category, settings in CATEGORIES.items() for query in settings["queries"]]
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(fetch_google_rss, category, query, lookback_days): (category, query)
                for category, query in rss_jobs
            }
            for future in as_completed(futures):
                category, query = futures[future]
                try:
                    all_articles.extend(future.result())
                except Exception as exc:
                    fallback_errors.append(f"{category}: {exc}")
        errors.extend([f"Google News RSS fallback: {msg}" for msg in fallback_errors[:5]])
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
        "provider": "Google News RSS (fallback)" if fallback_used else "NewsAPI",
        "fallback_used": fallback_used,
        "fallback_errors": len(fallback_errors),
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

# Renders the embedded portrait; falls back to the initial-letter circle only
# if the base64 constant above is somehow empty.
avatar_html = '<div class="avatar-circle-lg">P</div>'

# Emblem: an audit lens (magnifier) whose glass contains a rising analytics
# bar chart, framed by a scanning arc — "examine + measure + monitor".
LOGO_SVG = """
<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M26.6 8.4a13 13 0 0 1 .9 13.4" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>
  <path d="M5.2 22.6a13 13 0 0 1 .5-13.9" stroke="#FFFFFF" stroke-opacity="0.42"
        stroke-width="2" stroke-linecap="round"/>

  <circle cx="14.6" cy="14.6" r="8.2" stroke="#FFFFFF" stroke-width="2.4"/>
  <circle cx="14.6" cy="14.6" r="8.2" fill="#FFFFFF" fill-opacity="0.14"/>

  <rect x="10.7" y="15.1" width="2.25" height="4.5" rx="1.12" fill="#FFFFFF"/>
  <rect x="13.9" y="12.2" width="2.25" height="7.4" rx="1.12" fill="#FFFFFF"/>
  <rect x="17.1" y="9.6"  width="2.25" height="10"  rx="1.12" fill="#FFFFFF"/>

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
    <div class="topnav-right">
        <div class="top-search"><span class="top-search-icon">⌕</span><span>Search news, banks, regulation, audit...</span></div>
        <div class="top-bell">♧<span class="top-bell-dot"></span></div>
        <div class="topnav-user">
            <div class="topnav-user-meta">
                <div class="topnav-user-label">Prepared for</div>
                <div class="topnav-user-name">{PRAGATI_NAME}</div>
                <div class="topnav-user-title">{PRAGATI_TITLE}</div>
            </div>
            {avatar_html}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 5. ACTION BAR + SIDEBAR CONTROLS
# ---------------------------------------------------------

api_key = (NEWSAPI_KEY.strip() or get_api_key().strip())
hard_refresh = False

with st.sidebar:
    st.markdown("""
    <div class="sidebar-shell-brand">
        <div class="sidebar-shell-icon">⌁</div>
        <div class="sidebar-shell-title">Audit <span>Intelligence</span></div>
    </div>

    <div class="sidebar-nav">
        <div class="sidebar-nav-item active"><span class="sidebar-nav-icon">⌂</span>News Feed</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">▦</span>Categories</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">♜</span>Global Banks</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">♡</span>Watchlist</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">▱</span>Saved</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">⇩</span>Export</div>
        <div class="sidebar-nav-item"><span class="sidebar-nav-icon">◉</span>Diagnostics</div>
    </div>

    <div class="sidebar-status">
        <div class="sidebar-kicker"><span class="sidebar-live-dot" style="display:inline-block;margin-right:6px;"></span>Live Data</div>
        <div class="sidebar-live-row">
            <div class="sidebar-live-left">NewsAPI</div>
            <div class="sidebar-active-pill">Active</div>
        </div>
        <div class="sidebar-updated">Last updated<br>{st.session_state.get("last_refresh", "waiting for first load")}</div>
    </div>

    <div class="sidebar-quick-title">Quick Controls</div>
    """, unsafe_allow_html=True)

    hard_refresh = st.button("⟳  Refresh All Data", use_container_width=True, type="primary", key="refresh_all")
    if hard_refresh:
        load_news.clear()
        load_market_snapshot.clear()
        st.session_state.pop("news_loaded", None)

    with st.expander("⚙  Filters & Settings", expanded=False):
        lookback_days = st.slider("Lookback Window (Days)", 1, 30, 7)
        min_relevance = st.slider("Minimum Audit Relevance", 0, 40, 5, step=5)
        selected_categories = st.multiselect(
            "Active Categories", options=list(CATEGORIES.keys()),
            default=list(CATEGORIES.keys()),
            format_func=lambda c: CATEGORY_DISPLAY.get(c, c),
        )

    st.markdown('<div class="sidebar-note">NewsAPI is configured server-side. Credentials are never displayed here.</div>', unsafe_allow_html=True)

if not api_key:
    with st.sidebar:
        st.error("NewsAPI is not configured.")
        st.caption("Configure NEWSAPI_KEY in Streamlit secrets, an environment variable, or config.py.")
    st.stop()


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

with st.sidebar:
    with st.expander("🔎 Diagnostics", expanded=False):
        if stats:
            st.markdown(
                f'<div style="font-size:11.5px;color:#374151;line-height:1.9;"><b>Provider:</b> {stats.get("provider","NewsAPI")}<br><b>Requests:</b> {stats.get("queries_run",0)}<br><b>Raw:</b> {stats.get("raw",0)}<br><b>Deduped:</b> {stats.get("deduped",0)}<br><b>Retained:</b> {stats.get("kept",0)}<br><b>Low relevance:</b> {stats.get("dropped_low_relevance",0)}</div>',
                unsafe_allow_html=True,
            )
        for err in errors[:8]:
            st.markdown(f"<div style='font-size:11px;color:#B45309;margin-top:4px;'>• {err}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 8. TOP NEWS AREA
# ---------------------------------------------------------

st.markdown(
    f'<div class="news-section-title"><div><div class="news-section-title-main" style="font-size:24px;">⚡ Today’s Top Banking News</div><div style="font-size:12px;color:#64748B;margin-top:3px;">Key developments in banking, regulation, risk and technology</div></div><div class="news-section-title-sub">{ist_now_str()}</div></div>',
    unsafe_allow_html=True,
)

# 9. RENDER HELPERS
# ---------------------------------------------------------

def render_insight_card(article):
    color = CATEGORY_COLORS.get(article["category"], "#374151")
    label = CATEGORY_DISPLAY.get(article["category"], article["category"])
    rel_time = format_relative_time(article["publishedAt"])
    description_text = article["description"] or "Independent institutional briefing coverage. Select below to review the full verified source documentation."

    fallback = placeholder_data_uri(color)
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


def priority_score(article):
    text = f'{article["title"]} {article["description"]}'.lower()
    alert_hits = sum(1 for term in ALERT_TERMS if term in text)
    cyber_hits = sum(1 for term in CATEGORY_TERMS.get("Cyber & Tech", []) if term in text)
    return article.get("audit_relevance", 0) + (alert_hits * 8) + (cyber_hits * 2)


def render_featured_strip(rows, limit=4):
    if not rows:
        return

    today_rows = [a for a in rows if format_relative_time(a["publishedAt"]) == "Today"]
    source_rows = today_rows if len(today_rows) >= 4 else rows
    ranked = sorted(
        source_rows,
        key=lambda a: (priority_score(a), a["publishedAt"]),
        reverse=True,
    )[:limit]

    slides = []
    for idx, article in enumerate(ranked, 1):
        color = CATEGORY_COLORS.get(article["category"], "#2563EB")
        label = CATEGORY_DISPLAY.get(article["category"], article["category"])
        title = (article["title"] or "Untitled").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        source = (article["source"] or "Source").replace("&", "&amp;")
        image = article.get("image_url") or ""
        bg = f"url('{image}')" if image else "linear-gradient(135deg,#0F172A,#2563EB)"
        slides.append(
            f'<div class="featured-slide">'
            f'<div class="featured-slide-bg" style="background-image:{bg};"></div>'
            f'<div class="featured-slide-content">'
            f'<div class="featured-slide-kicker">'
            f'<span class="featured-slide-rank">{idx}</span>'
            f'<span class="featured-slide-tag" style="background:{color};">{label}</span>'
            f'</div>'
            f'<a class="featured-slide-title" href="{article["url"]}" target="_blank">{title}</a>'
            f'<div class="featured-slide-meta">{source} · {format_relative_time(article["publishedAt"])} · Featured intelligence</div>'
            f'</div></div>'
        )

    # The carousel intentionally uses four stories and rotates client-side.
    # This avoids repeated NewsAPI calls/reruns just to change the visible story.
    progress = ''.join('<span></span>' for _ in range(len(slides)))
    st.markdown(
        '<div class="featured-carousel">'
        f'<div class="featured-progress">{progress}</div>'
        + ''.join(slides)
        + '</div>',
        unsafe_allow_html=True,
    )


def render_feed(rows, show_featured=False):
    if not rows:
        st.markdown("""
        <div class="empty-state-panel">
            <div style="font-size:18px;font-weight:700;color:#111827;">No briefing stories found</div>
            <div style="font-size:13.5px;color:#4B5563;margin-top:6px;">Try expanding the lookback window or lowering the relevance floor in the sidebar.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    if show_featured:
        st.markdown(
            '<div class="news-section-title">'
            '<div><div class="news-section-title-main">Featured Intelligence</div>'
            '<div style="font-size:12px;color:#64748B;margin-top:3px;">Four priority stories · rotating every 6 seconds</div></div>'
            '<div class="news-section-title-sub">01—04</div></div>',
            unsafe_allow_html=True,
        )
        render_featured_strip(rows, 4)

    st.markdown(
        f'<div class="news-section-title"><div><div class="news-section-title-main">Latest Insights</div><div style="font-size:12px;color:#64748B;margin-top:3px;">Two stories per row · newest intelligence first</div></div><div class="news-section-title-sub">{len(rows)} STORIES</div></div>',
        unsafe_allow_html=True,
    )

    # Two editorial cards per row keeps the main feed compact and scannable.
    for start in range(0, len(rows), 2):
        row = rows[start:start + 2]
        cols = st.columns(2, gap="medium")
        for col, art in zip(cols, row):
            with col:
                render_insight_card(art)


# 10. MAIN LAYOUT
# ---------------------------------------------------------

# News is deliberately the first major content block so the opening viewport
# feels like a news product rather than a configuration dashboard.
render_feed(filtered, show_featured=True)

with st.sidebar:
    st.markdown('<div class="sidebar-filter-label">Live Monitoring</div>', unsafe_allow_html=True)
    render_market_panel()
    render_priority_alerts(filtered)
    render_risk_radar(filtered)
    render_source_panel(filtered)

    with st.expander("🎛️ Active Filters", expanded=False):
        active_categories = ", ".join(CATEGORY_DISPLAY.get(c, c) for c in selected_categories) or "None selected"
        st.markdown(
            f'<div style="font-size:11.5px;line-height:1.9;color:#374151;">'
            f'<b>Categories:</b> {active_categories}<br>'
            f'<b>Lookback:</b> Last {lookback_days}d<br>'
            f'<b>Relevance floor:</b> {min_relevance}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("📊 Feed Pulse", expanded=False):
        today_count = sum(1 for a in filtered if format_relative_time(a["publishedAt"]) == "Today")
        unique_sources = len(set(a["source"] for a in filtered))
        st.metric("Stories", len(filtered))
        st.metric("Published Today", today_count)
        st.metric("Unique Sources", unique_sources)

    with st.expander("📥 Export", expanded=False):
        if filtered:
            df_export = pd.DataFrame(filtered)
            csv = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Briefing CSV",
                data=csv,
                file_name=f"audit_intel_briefing_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv_sidebar",
            )

    st.caption("Audit Intelligence · Internal banking risk & controls briefing")


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

