from __future__ import annotations

import base64
import html
import re
from datetime import timedelta
from io import StringIO
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="The P-S-A Dashboard",
    page_icon="NI",
    layout="wide",
    initial_sidebar_state="expanded",
)


CATEGORIES = [
    "Laws and Regs",
    "Industry Insights",
    "Litigation/Enforcement",
    "Data Breach",
]

CATEGORY_DETAILS = {
    "Laws and Regs": {
        "abbr": "LR",
        "label": "Regulatory signal",
        "description": "Privacy, cybersecurity, AI, and data protection laws, regulations, guidance, and legislative updates.",
    },
    "Industry Insights": {
        "abbr": "II",
        "label": "Market intelligence",
        "description": "Business, technology, policy, and market developments affecting governance and risk strategy.",
    },
    "Litigation/Enforcement": {
        "abbr": "LE",
        "label": "Dispute and agency action",
        "description": "Lawsuits, enforcement actions, settlements, investigations, and court decisions.",
    },
    "Data Breach": {
        "abbr": "DB",
        "label": "Incident tracking",
        "description": "Cyber incidents, data breaches, ransomware events, unauthorized access, and disclosure trends.",
    },
}

WORKSPACE_OPTIONS = {
    "news_center": {
        "title": "News Center",
        "icon": "news",
        "description": "Stay current with the latest developments across privacy, cybersecurity, AI, and data protection.",
        "button": "Open",
    },
    "legislation": {
        "title": "Legislation",
        "icon": "building",
        "description": "Track proposed and enacted laws, bills, regulations, and government guidance.",
        "button": "Open",
    },
    "litigation": {
        "title": "Litigation/Enforcement Actions",
        "icon": "scales",
        "description": "Monitor lawsuits, enforcement actions, investigations, and regulatory decisions.",
        "button": "Open",
    },
    "education": {
        "title": "Educational Resources",
        "icon": "graduation",
        "description": "Access whitepapers, reports, webinars, and tools to support your knowledge and strategy.",
        "button": "Open",
    },
}

LINKEDIN_UPDATES = [
    {
        "account": "Federal Trade Commission",
        "date": "Jun 7, 2026",
        "preview": "Promoting competition and protecting consumers",
        "avatar": "FTC",
        "avatar_image": "assets/ftc-logo.jpeg",
        "url": "https://www.linkedin.com/company/federal-trade-commission/",
    },
    {
        "account": "California Privacy Protection Agency",
        "date": "Jun 7, 2026",
        "preview": "Committed to promoting the education and awareness of consumers' privacy rights and businesses' responsibilities under the CCPA/CPRA, Delete Act, and Opt-Me Out Act.",
        "avatar": "CPPA",
        "url": "https://www.linkedin.com/company/calprivacy/posts/?feedView=all",
    },
    {
        "account": "Cybersecurity and Infrastructure Security Agency",
        "date": "Jun 7, 2026",
        "preview": "Defend Today, Secure Tomorrow",
        "avatar": "CISA",
        "url": "https://www.linkedin.com/company/cisagov/",
    },
]

NEWS_CENTER_ARTICLES = [
    {
        "date": "Jun 04, 2026",
        "title": "Louisiana: Data Privacy Act signed by Governor",
        "summary": "Louisiana Governor has signed into Data Privacy Act. The linked source provides the full details and context. Review the original article for jurisdiction-specific facts, dates, and implications.",
        "source": "State of Louisiana Official Website",
    },
    {
        "date": "Jun 04, 2026",
        "title": "USA: President signs Executive Order on promoting AI and security",
        "summary": "By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered: Section 1. The United States continues to lead the world in Artificial Intelligence (AI)...",
        "source": "The White House",
    },
    {
        "date": "May 27, 2026",
        "title": "Connecticut: Governor signs Online Safety Bill",
        "summary": "The law establishes a regulatory framework for social media and artificial intelligence. It was authored in Hartford and signed into law with bipartisan support.",
        "source": "Hartford Courant",
    },
]

NEWS_DATE_RANGE_OPTIONS = [
    "Past Week",
    "Past Month",
    "Past Three Months",
    "Past Year",
    "All",
]

NEWS_TOPIC_OPTIONS = [
    "Data Breach",
    "Industry Insights",
    "Litigation/Enforcement",
    "Laws and Regs",
]

NEWS_SORT_OPTIONS = [
    "Most Recent Stories",
    "Oldest Stories",
]

NEWS_SAVED_VIEWS = {
    "All Stories": {
        "date_range": "All",
        "topics": NEWS_TOPIC_OPTIONS,
        "sort_filter": "Most Recent Stories",
        "keyword": "",
    },
    "Policy Watch": {
        "date_range": "Past Month",
        "topics": ["Laws and Regs", "Industry Insights"],
        "sort_filter": "Most Recent Stories",
        "keyword": "",
    },
    "Enforcement Watch": {
        "date_range": "Past Month",
        "topics": ["Litigation/Enforcement"],
        "sort_filter": "Most Recent Stories",
        "keyword": "",
    },
    "Breach Watch": {
        "date_range": "Past Month",
        "topics": ["Data Breach"],
        "sort_filter": "Most Recent Stories",
        "keyword": "",
    },
}

NEWS_FILTER_DEFAULTS = {
    "date_range": "All",
    "topics": NEWS_TOPIC_OPTIONS,
    "sort_filter": "Most Recent Stories",
    "keyword": "",
    "saved_view": "All Stories",
    "display_mode": "List",
    "auto_scroll": False,
}


DEMO_SHEET_DATA = [
    {
        "Date": "2026-06-06",
        "Laws and Regs": "State privacy law update https://example.com/state-privacy-law-update",
        "Industry Insights": "AI governance programs mature across privacy teams https://example.com/ai-governance-programs",
        "Litigation/Enforcement": "Regulator announces privacy enforcement settlement https://example.com/privacy-enforcement-settlement",
        "Data Breach": "Company discloses unauthorized access incident https://example.com/unauthorized-access-incident",
    },
    {
        "Date": "2026-06-01",
        "Laws and Regs": "New cybersecurity guidance released https://example.com/cybersecurity-guidance",
        "Industry Insights": "Privacy operations teams increase automation budgets https://example.com/privacy-automation-budgets",
        "Litigation/Enforcement": "Court narrows claims in data privacy dispute https://example.com/privacy-dispute-claims",
        "Data Breach": "Ransomware incident response lessons published https://example.com/ransomware-response-lessons",
    },
]


def escape(value) -> str:
    return html.escape(str(value), quote=True)


def story_source(url: str) -> str:
    parsed = urlparse(str(url))
    return parsed.netloc.replace("www.", "") or "Source"


def workspace_icon(icon_name: str) -> str:
    icons = {
        "news": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5h12.5v13H4z"></path><path d="M16.5 8H20v9.5a1 1 0 0 1-1 1h-2.5z"></path><path d="M7 9h6.5"></path><path d="M7 12.5h2.5"></path><path d="M11.5 12.5h2"></path><path d="M7 15.5h6.5"></path></svg>',
        "building": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h16"></path><path d="M5.5 19h13"></path><path d="M7 9v10"></path><path d="M11 9v10"></path><path d="M15 9v10"></path><path d="M19 9v10"></path><path d="M3.5 7.5 12 3.5l8.5 4"></path></svg>',
        "scales": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v16"></path><path d="M7 20h10"></path><path d="M5 7h14"></path><path d="M8 7 5 14h6z"></path><path d="M16 7l-3 7h6z"></path></svg>',
        "graduation": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 8.5 12 4.5l8.5 4-8.5 4z"></path><path d="M7 11v4.5c1.4 1.1 3.1 1.7 5 1.7s3.6-.6 5-1.7V11"></path><path d="M20.5 9v5"></path></svg>',
    }
    return icons.get(icon_name, "")


def asset_data_url(path: str) -> str:
    asset_path = Path(__file__).parent / path
    mime_type = "image/jpeg"
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #f4f7fc;
                --card: #ffffff;
                --ink: #112d62;
                --ink-soft: #1c3568;
                --muted: #5b6e8f;
                --line: #dbe6f3;
                --blue: #1d5fd0;
                --blue-soft: #eef5ff;
                --sidebar: #f8fbff;
            }

            .stApp {
                background: var(--bg);
                color: var(--ink);
            }

            .block-container {
                max-width: 1520px;
                padding-top: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }

            section[data-testid="stSidebar"] {
                background: var(--sidebar);
                border-right: 1px solid var(--line);
            }

            button[data-testid="stBaseButton-headerNoPadding"] {
                background: white !important;
                border: 1px solid var(--line) !important;
                border-radius: 999px !important;
                box-shadow: 0 8px 18px rgba(14, 42, 94, 0.12) !important;
                color: var(--ink-soft) !important;
                height: 32px !important;
                width: 32px !important;
            }

            section[data-testid="stSidebar"] > div {
                padding-top: 1rem;
            }

            .sidebar-shell {
                min-height: calc(100vh - 3rem);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .sidebar-shell-news {
                min-height: auto;
                margin-bottom: 0.6rem;
            }

            .sidebar-brand {
                padding: 1rem 0.55rem 1.5rem;
            }

            .sidebar-logo {
                color: var(--ink);
                font-family: Georgia, "Times New Roman", serif;
                font-size: 3rem;
                line-height: 0.95;
                margin: 0;
            }

            .sidebar-wordmark {
                color: #456089;
                font-size: 0.82rem;
                font-weight: 500;
                letter-spacing: 0.12em;
                line-height: 1.45;
                margin-top: 0.35rem;
                text-transform: uppercase;
            }

            .sidebar-nav {
                display: flex;
                flex-direction: column;
                gap: 0.45rem;
                margin-top: 0.5rem;
            }

            .sidebar-item,
            .sidebar-item-active {
                border-radius: 10px;
                color: #3d547c;
                display: block;
                font-size: 0.92rem;
                padding: 0.85rem 1rem;
                text-decoration: none;
            }

            .sidebar-item-active {
                background: linear-gradient(180deg, #f2f7ff 0%, #edf4ff 100%);
                border-left: 3px solid var(--blue);
                color: var(--blue);
                font-weight: 700;
                padding-left: 0.85rem;
            }

            .sidebar-user {
                align-items: center;
                display: flex;
                gap: 0.8rem;
                padding: 1rem 0.55rem 0.35rem;
            }

            .sidebar-avatar {
                align-items: center;
                background: #788db1;
                border-radius: 999px;
                color: white;
                display: inline-flex;
                font-size: 1rem;
                font-weight: 800;
                height: 42px;
                justify-content: center;
                width: 42px;
            }

            .sidebar-user-name {
                color: var(--ink-soft);
                font-size: 0.95rem;
                font-weight: 700;
            }

            .sidebar-user-role {
                color: var(--muted);
                font-size: 0.83rem;
            }

            .hero,
            .story,
            .contact-card,
            .linkedin-panel {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: 16px;
                box-shadow: 0 12px 32px rgba(14, 42, 94, 0.08);
            }

            .hero {
                background:
                    radial-gradient(circle at 78% 18%, rgba(209, 227, 252, 0.95) 0%, rgba(209, 227, 252, 0.42) 18%, rgba(255,255,255,0) 40%),
                    linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
                overflow: hidden;
                padding: 2.2rem 2.3rem;
                margin-bottom: 1.35rem;
                position: relative;
            }

            .hero::after {
                background:
                    radial-gradient(1100px 200px at 88% 8%, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.35) 35%, rgba(255,255,255,0) 70%),
                    linear-gradient(135deg, rgba(199,217,246,0) 0%, rgba(206,223,248,0.65) 50%, rgba(255,255,255,0) 100%);
                border-radius: 50%;
                content: "";
                height: 260px;
                position: absolute;
                right: -120px;
                top: -40px;
                width: 900px;
                opacity: 0.85;
            }

            .hero-title {
                color: var(--ink);
                font-family: Georgia, "Times New Roman", serif;
                font-size: 3.2rem;
                font-weight: 700;
                line-height: 1.08;
                margin: 0;
                max-width: 760px;
                position: relative;
                z-index: 1;
            }

            .hero-subtitle {
                color: #4a6287;
                font-size: 1.02rem;
                line-height: 1.7;
                margin-top: 1rem;
                max-width: 760px;
                position: relative;
                z-index: 1;
            }

            .muted,
            .story-summary {
                color: var(--muted);
            }

            .section-heading {
                color: var(--ink);
                font-size: 1.1rem;
                font-weight: 800;
                margin: 1.15rem 0 0.7rem;
            }

            .workspace-card {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: 14px;
                box-shadow: 0 12px 32px rgba(14, 42, 94, 0.08);
                min-height: 430px;
                padding: 2.2rem 1.6rem 1.9rem;
                text-align: center;
            }

            .workspace-title {
                color: var(--ink-soft);
                font-size: 1.45rem;
                font-weight: 800;
                line-height: 1.18;
                margin: 1.35rem 0 1.1rem;
                min-height: 3.45rem;
            }

            .workspace-copy {
                color: var(--muted);
                font-size: 1.05rem;
                line-height: 1.6;
                margin: 0 auto 2.4rem;
                max-width: 285px;
                min-height: 116px;
            }

            .chip-icon {
                align-items: center;
                background: linear-gradient(180deg, #fbfdff 0%, #f2f7ff 100%);
                border: 1px solid #d6e4f7;
                border-radius: 999px;
                color: #6a88b6;
                display: inline-flex;
                height: 112px;
                justify-content: center;
                margin: 0 auto;
                min-width: 112px;
                width: 112px;
            }

            .chip-icon svg {
                fill: none;
                height: 58px;
                stroke: #58739f;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 1.55;
                width: 58px;
            }

            .workspace-open-button {
                align-items: center;
                background: white;
                border: 1px solid #c8daf4;
                border-radius: 8px;
                color: var(--blue) !important;
                display: inline-flex;
                font-size: 1.1rem;
                font-weight: 800;
                gap: 1rem;
                justify-content: center;
                min-width: 154px;
                padding: 0.8rem 1.2rem;
                text-decoration: none;
            }

            .workspace-open-button span {
                font-size: 1.7rem;
                line-height: 1;
                transform: translateY(-1px);
            }

            .workspace-section {
                margin-bottom: 2.1rem;
            }

            .story {
                margin-bottom: 0.75rem;
                padding: 0.95rem 1rem;
            }

            .story-kicker {
                align-items: center;
                display: flex;
                justify-content: space-between;
                gap: 0.75rem;
            }

            .tag {
                background: #eef5ff;
                border-radius: 999px;
                color: var(--blue);
                font-size: 0.72rem;
                font-weight: 800;
                padding: 0.2rem 0.55rem;
            }

            .story-title {
                color: var(--ink);
                font-size: 1rem;
                font-weight: 820;
                line-height: 1.35;
                margin: 0.7rem 0 0.35rem;
            }

            .story-summary {
                font-size: 0.88rem;
                line-height: 1.5;
            }

            .contact-card {
                padding: 1.1rem 1.15rem;
            }

            .linkedin-panel {
                padding: 1.35rem 1.4rem 1.5rem;
            }

            .linkedin-post {
                border: 1px solid #dfe8f4;
                border-radius: 16px;
                padding: 1.1rem 1.2rem 1rem;
                min-height: 270px;
            }

            .linkedin-grid {
                display: grid;
                gap: 1rem;
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .linkedin-topline {
                display: flex;
                gap: 0.85rem;
                margin-bottom: 1rem;
            }

            .linkedin-avatar {
                align-items: center;
                background: linear-gradient(180deg, #183968 0%, #0f2e59 100%);
                border-radius: 12px;
                color: white;
                display: inline-flex;
                font-size: 1.8rem;
                font-family: Georgia, "Times New Roman", serif;
                font-weight: 700;
                height: 52px;
                justify-content: center;
                min-width: 52px;
                width: 52px;
            }

            .linkedin-avatar img {
                border-radius: 12px;
                display: block;
                height: 52px;
                object-fit: cover;
                width: 52px;
            }

            .linkedin-badge {
                background: #0a66c2;
                border-radius: 4px;
                color: #ffffff;
                display: inline-block;
                font-size: 0.72rem;
                font-weight: 800;
                line-height: 1;
                margin-left: 0.35rem;
                padding: 0.18rem 0.22rem;
            }

            .linkedin-name {
                color: var(--ink-soft);
                font-size: 0.98rem;
                font-weight: 800;
            }

            .linkedin-date {
                color: var(--muted);
                font-size: 0.82rem;
                margin-top: 0.2rem;
            }

            .linkedin-copy {
                color: var(--ink-soft);
                font-size: 0.88rem;
                line-height: 1.6;
                margin: 0.35rem 0 1.5rem;
                min-height: 92px;
            }

            .linkedin-link {
                color: var(--blue) !important;
                font-size: 0.86rem;
                font-weight: 800;
                text-decoration: none;
            }

            .linkedin-footer {
                border-top: 1px solid #e7eef8;
                padding-top: 0.9rem;
            }

            .linkedin-header {
                align-items: center;
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1rem;
            }

            .linkedin-heading {
                color: var(--ink-soft);
                font-size: 1rem;
                font-weight: 800;
            }

            .linkedin-heading .linkedin-badge {
                transform: translateY(-1px);
            }

            .contact-title {
                color: var(--ink-soft);
                font-size: 1.15rem;
                font-weight: 800;
                margin: 0.35rem 0;
            }

            .contact-action {
                background: white;
                border: 1px solid #c8daf4;
                border-radius: 10px;
                color: var(--blue) !important;
                display: inline-flex;
                font-weight: 700;
                gap: 0.65rem;
                justify-content: center;
                margin-top: 0.5rem;
                min-width: 124px;
                padding: 0.72rem 1.1rem;
                text-decoration: none;
            }

            div.stButton > button,
            div.stLinkButton > a {
                border-radius: 10px;
                font-weight: 700;
            }

            .news-shell {
                padding: 0.25rem 0 2rem;
            }

            .news-topbar {
                align-items: center;
                display: flex;
                justify-content: flex-end;
                gap: 0.75rem;
                margin-bottom: 1.2rem;
            }

            .news-header-icon,
            .news-user-avatar,
            .article-action,
            .gemini-mark {
                align-items: center;
                display: inline-flex;
                justify-content: center;
            }

            .news-header-icon {
                background: white;
                border: 1px solid var(--line);
                border-radius: 999px;
                color: var(--ink-soft);
                height: 38px;
                text-decoration: none;
                width: 38px;
            }

            .news-header-icon svg {
                fill: none;
                height: 18px;
                stroke: currentColor;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 1.8;
                width: 18px;
            }

            .filter-home-wrap {
                align-items: center;
                display: flex;
                gap: 0.6rem;
                height: 100%;
            }

            .filter-home-wrap div[data-testid="stButton"] {
                margin: 0;
            }

            .filter-home-wrap div[data-testid="stButton"] > button {
                align-items: center;
                background: white;
                border: 1px solid var(--line);
                border-radius: 999px;
                color: var(--ink-soft);
                display: inline-flex;
                height: 38px;
                justify-content: center;
                min-width: 38px;
                padding: 0;
                width: 38px;
            }

            .news-user-avatar {
                background: var(--ink-soft);
                border-radius: 999px;
                color: white;
                font-size: 0.86rem;
                font-weight: 800;
                height: 40px;
                width: 40px;
            }

            .news-page-heading {
                margin: 0 auto 1.4rem;
                max-width: 860px;
                text-align: center;
            }

            .news-page-heading h1 {
                color: var(--ink);
                font-family: Georgia, "Times New Roman", serif;
                font-size: 2.75rem;
                line-height: 1.1;
                margin: 0 0 0.7rem;
            }

            .news-page-heading p {
                color: var(--muted);
                font-size: 1.02rem;
                line-height: 1.65;
                margin: 0;
            }

            .filter-card,
            .article-card,
            .gemini-panel {
                background: white;
                border: 1px solid var(--line);
                border-radius: 14px;
                box-shadow: 0 10px 28px rgba(14, 42, 94, 0.07);
            }

            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .sidebar-filter-anchor) {
                background: white;
                border: 1px solid var(--line);
                border-radius: 14px;
                box-shadow: 0 12px 28px rgba(14, 42, 94, 0.09);
                margin: 1rem 0.25rem 1.25rem;
                padding: 0.8rem;
            }

            .sidebar-filter-title {
                color: var(--ink);
                font-size: 0.92rem;
                font-weight: 850;
                margin-bottom: 0.55rem;
            }

            .filter-result-pill {
                align-items: center;
                background: #eef5ff;
                border: 1px solid #d6e4f7;
                border-radius: 999px;
                color: var(--ink-soft);
                display: inline-flex;
                font-size: 0.85rem;
                font-weight: 850;
                justify-content: center;
                min-height: 38px;
                padding: 0.25rem 0.8rem;
                white-space: nowrap;
                width: 100%;
            }

            .filter-panel-heading {
                color: var(--ink-soft);
                font-size: 0.9rem;
                font-weight: 850;
                margin-bottom: 0.6rem;
            }

            .filter-grid,
            .filter-grid-secondary {
                display: grid;
                gap: 0.75rem;
            }

            .filter-grid {
                grid-template-columns: 1.35fr repeat(3, 1fr);
                margin-bottom: 0.75rem;
            }

            .filter-grid-secondary {
                align-items: center;
                grid-template-columns: 1.25fr 1.35fr 1.25fr 0.7fr 0.8fr;
            }

            .filter-field {
                background: #f9fbff;
                border: 1px solid #dce6f4;
                border-radius: 10px;
                color: var(--ink-soft);
                min-height: 58px;
                padding: 0.55rem 0.7rem;
            }

            .filter-label {
                color: var(--muted);
                font-size: 0.72rem;
                font-weight: 800;
                margin-bottom: 0.25rem;
                text-transform: uppercase;
            }

            .filter-value {
                color: var(--ink-soft);
                font-size: 0.92rem;
                font-weight: 760;
            }

            .toggle-row {
                align-items: center;
                display: flex;
                gap: 0.65rem;
            }

            .toggle-pill {
                background: var(--blue);
                border-radius: 999px;
                height: 24px;
                position: relative;
                width: 44px;
            }

            .toggle-pill::after {
                background: white;
                border-radius: 999px;
                content: "";
                height: 18px;
                position: absolute;
                right: 3px;
                top: 3px;
                width: 18px;
            }

            .clear-button,
            .apply-button {
                align-items: center;
                border-radius: 10px;
                display: flex;
                font-size: 0.9rem;
                font-weight: 800;
                justify-content: center;
                min-height: 58px;
                text-decoration: none;
            }

            .clear-button {
                background: white;
                border: 1px solid #dce6f4;
                color: var(--ink-soft) !important;
            }

            .apply-button {
                background: var(--blue);
                border: 1px solid var(--blue);
                color: white !important;
            }

            .results-toolbar {
                align-items: center;
                color: var(--muted);
                display: flex;
                justify-content: space-between;
                margin: 1rem 0 0.8rem;
            }

            .results-toolbar strong {
                color: var(--ink-soft);
            }

            .view-icons {
                align-items: center;
                display: inline-flex;
                gap: 0.4rem;
                margin-left: 0.9rem;
            }

            .view-icons span {
                align-items: center;
                border: 1px solid #dce6f4;
                border-radius: 8px;
                color: var(--ink-soft);
                display: inline-flex;
                height: 32px;
                justify-content: center;
                width: 32px;
            }

            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .news-rail-anchor) {
                align-items: center;
                display: flex;
                flex-direction: column;
                gap: 0.7rem;
                margin: 3.5rem 0.2rem 1rem;
                padding: 0;
            }

            section[data-testid="stSidebar"]:has(.focus-rail-anchor) {
                width: 92px !important;
                min-width: 92px !important;
                background: rgba(248, 251, 255, 0.92);
                box-shadow: 8px 0 28px rgba(14, 42, 94, 0.04);
            }

            section[data-testid="stSidebar"]:has(.focus-rail-anchor) > div {
                padding-left: 0.72rem;
                padding-right: 0.72rem;
            }

            section[data-testid="stSidebar"]:has(.focus-rail-anchor) [data-testid="stButton"] > button,
            section[data-testid="stSidebar"]:has(.focus-rail-anchor) [data-testid="stPopoverButton"] {
                align-items: center;
                background: white;
                border: 1px solid var(--line);
                border-radius: 999px;
                box-shadow: 0 8px 18px rgba(14, 42, 94, 0.08);
                color: var(--ink-soft);
                display: inline-flex;
                height: 48px;
                justify-content: center;
                min-height: 48px;
                min-width: 48px;
                padding: 0;
                width: 48px;
            }

            .focus-rail-anchor {
                width: 100%;
            }

            .focus-rail-count {
                align-items: center;
                background: #eef5ff;
                border: 1px solid #d6e4f7;
                border-radius: 999px;
                color: var(--ink-soft);
                display: inline-flex;
                font-size: 0.76rem;
                font-weight: 900;
                justify-content: center;
                min-height: 42px;
                width: 58px;
            }

            .focus-rail-caption {
                color: var(--muted);
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0;
                text-align: center;
            }

            section[data-testid="stMain"] div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .news-toolbar-anchor) {
                background: rgba(244, 247, 252, 0.94);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(219, 230, 243, 0.7);
                box-shadow: 0 12px 24px rgba(14, 42, 94, 0.04);
                margin-bottom: 0.9rem;
                padding: 0.8rem 0 0.65rem;
                position: sticky;
                top: 0.25rem;
                z-index: 26;
            }

            .feed-count-pill,
            .filter-result-pill {
                align-items: center;
                background: #eef5ff;
                border: 1px solid #d6e4f7;
                border-radius: 999px;
                color: var(--ink-soft);
                display: inline-flex;
                font-size: 0.84rem;
                font-weight: 850;
                justify-content: center;
                min-height: 40px;
                padding: 0.25rem 0.85rem;
                white-space: nowrap;
                width: 100%;
            }

            .story-card {
                background: white;
                border: 1px solid var(--line);
                border-radius: 16px;
                box-shadow: 0 10px 28px rgba(14, 42, 94, 0.07);
                color: inherit;
                display: grid;
                gap: 0.95rem;
                grid-template-columns: 44px minmax(0, 1fr);
                margin-bottom: 0.7rem;
                padding: 0.82rem 0.95rem;
                text-decoration: none !important;
                text-decoration-color: transparent !important;
                transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
            }

            .story-card:hover {
                border-color: #c8daf4;
                box-shadow: 0 14px 30px rgba(14, 42, 94, 0.1);
                color: inherit;
                text-decoration: none !important;
                text-decoration-color: transparent !important;
                transform: translateY(-1px);
            }

            .story-card-featured {
                padding: 1.05rem 1.1rem;
            }

            .story-card-compact {
                padding-top: 0.72rem;
                padding-bottom: 0.72rem;
            }

            .story-card-comfort {
                padding-top: 0.92rem;
                padding-bottom: 0.92rem;
            }

            .story-card-body {
                min-width: 0;
            }

            .story-card-icon {
                align-self: start;
            }

            .story-card-title {
                color: var(--ink-soft);
                font-size: 1.03rem;
                font-weight: 860;
                line-height: 1.32;
                margin: 0.1rem 0 0.32rem;
            }

            .story-card-featured .story-card-title {
                font-size: 1.22rem;
                line-height: 1.28;
            }

            .story-card-preview {
                color: var(--muted);
                font-size: 0.92rem;
                line-height: 1.58;
                margin-bottom: 0.55rem;
                max-width: 70ch;
            }

            .story-card-featured .story-card-preview {
                margin-bottom: 0.7rem;
            }

            .story-card-meta {
                margin-bottom: 0.28rem;
            }

            .story-card-footer {
                margin-top: 0.15rem;
            }

            .story-card .article-footer {
                min-width: 0;
            }

            .story-card .article-source {
                white-space: nowrap;
            }

            .story-card .article-actions {
                gap: 0.35rem;
            }

            .story-card .article-action,
            .story-card .gemini-mark {
                height: 32px;
                width: 32px;
            }

            .story-card-compact .story-card-preview {
                display: none;
            }

            .story-card-compact .article-meta {
                margin-bottom: 0.2rem;
            }

            .story-card-compact .story-card-title {
                font-size: 0.98rem;
                line-height: 1.28;
            }

            .news-card-grid {
                display: grid;
                gap: 0.9rem;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            }

            .story-card-grid {
                grid-template-columns: minmax(0, 1fr);
                margin-bottom: 0;
                min-height: 238px;
                padding: 1rem;
            }

            .story-card-grid .story-card-icon {
                display: none;
            }

            .story-card-grid .story-card-body {
                display: flex;
                flex-direction: column;
                min-height: 100%;
            }

            .story-card-grid .story-card-title {
                font-size: 1.04rem;
                line-height: 1.32;
                margin: 0.18rem 0 0.55rem;
            }

            .story-card-grid .story-card-preview {
                display: -webkit-box;
                -webkit-box-orient: vertical;
                -webkit-line-clamp: 3;
                line-clamp: 3;
                overflow: hidden;
            }

            .story-card-grid .story-card-footer {
                margin-top: auto;
                padding-top: 0.65rem;
            }

            .story-card-grid .article-meta {
                align-items: flex-start;
                gap: 0.38rem;
            }

            .story-card-grid .article-badge {
                white-space: normal;
            }

            .story-card-grid .article-date,
            .story-card-grid .article-jurisdiction {
                white-space: nowrap;
            }

            .news-feed-shell {
                display: grid;
                gap: 0.55rem;
                margin: 0 auto;
                max-width: 1160px;
            }

            .news-feed-shell.feed-display-cards {
                max-width: 1280px;
            }

            .news-feed-intro {
                color: var(--muted);
                font-size: 0.95rem;
                margin: 0 0 0.35rem;
            }

            .news-content-grid {
                align-items: start;
                display: grid;
                gap: 1.2rem;
                grid-template-columns: minmax(0, 1fr) 360px;
            }

            .article-card {
                color: inherit;
                display: grid;
                gap: 0.85rem;
                grid-template-columns: 46px minmax(0, 1fr);
                margin-bottom: 0.65rem;
                padding: 0.85rem 0.95rem;
                text-decoration: none !important;
                text-decoration-color: transparent !important;
                transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
            }

            .article-card:hover {
                color: inherit;
                border-color: #c8daf4;
                box-shadow: 0 14px 30px rgba(14, 42, 94, 0.1);
                text-decoration: none !important;
                text-decoration-color: transparent !important;
                transform: translateY(-1px);
            }

            .article-card:link,
            .article-card:visited,
            .article-card:active,
            .article-card:focus,
            .article-card *,
            .article-card:focus {
                text-decoration: none !important;
                text-decoration-color: transparent !important;
            }

            .article-icon {
                align-items: center;
                background: #eef5ff;
                border: 1px solid #d3e4fb;
                border-radius: 12px;
                color: var(--blue);
                display: flex;
                height: 42px;
                justify-content: center;
                width: 42px;
            }

            .article-icon svg {
                fill: none;
                height: 22px;
                stroke: currentColor;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 1.8;
                width: 22px;
            }

            .article-meta {
                align-items: center;
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-bottom: 0.35rem;
            }

            .article-badge {
                background: #eef5ff;
                border-radius: 999px;
                color: var(--blue);
                font-size: 0.68rem;
                font-weight: 850;
                line-height: 1.2;
                padding: 0.18rem 0.5rem;
            }

            .article-date,
            .article-source,
            .article-jurisdiction {
                color: var(--muted);
                font-size: 0.78rem;
            }

            .article-source {
                color: var(--blue);
                font-weight: 760;
                text-decoration: none;
            }

            .article-title {
                color: var(--ink-soft);
                font-size: 1rem;
                font-weight: 850;
                line-height: 1.3;
                margin-bottom: 0.35rem;
            }

            .article-footer {
                align-items: center;
                display: flex;
                justify-content: space-between;
                gap: 1rem;
            }

            .article-source svg,
            .article-action svg {
                fill: none;
                stroke: currentColor;
                stroke-linecap: round;
                stroke-linejoin: round;
                stroke-width: 1.8;
            }

            .article-source svg {
                height: 14px;
                margin-left: 0.25rem;
                transform: translateY(2px);
                width: 14px;
            }

            .article-actions {
                align-items: center;
                display: flex;
                gap: 0.4rem;
            }

            .article-action,
            .gemini-mark {
                border-radius: 999px;
                height: 34px;
                width: 34px;
            }

            .article-action {
                border: 1px solid #dce6f4;
                color: var(--ink-soft);
            }

            .article-action svg {
                height: 16px;
                width: 16px;
            }

            .gemini-mark {
                background: #edf4ff;
                border: 1px solid #cde0fb;
                color: var(--blue);
                font-weight: 900;
            }

            .gemini-panel {
                padding: 1.15rem;
                position: sticky;
                top: 1rem;
            }

            .gemini-title {
                color: var(--ink-soft);
                font-size: 1.18rem;
                font-weight: 850;
                margin-bottom: 0.25rem;
            }

            .gemini-subtitle,
            .gemini-disclaimer,
            .gemini-meta {
                color: var(--muted);
                font-size: 0.84rem;
                line-height: 1.45;
            }

            .gemini-section-title {
                color: var(--ink-soft);
                font-size: 0.95rem;
                font-weight: 850;
                margin: 1.05rem 0 0.45rem;
            }

            .gemini-summary {
                color: var(--ink-soft);
                font-size: 0.9rem;
                line-height: 1.55;
            }

            .gemini-panel ul {
                color: var(--muted);
                font-size: 0.88rem;
                line-height: 1.55;
                margin: 0.7rem 0;
                padding-left: 1.1rem;
            }

            .prompt-chip {
                background: #f7faff;
                border: 1px solid #dce6f4;
                border-radius: 999px;
                color: var(--ink-soft);
                display: inline-block;
                font-size: 0.82rem;
                font-weight: 760;
                margin: 0 0.35rem 0.45rem 0;
                padding: 0.42rem 0.65rem;
            }

            .gemini-input {
                background: #f9fbff;
                border: 1px solid #dce6f4;
                border-radius: 12px;
                color: var(--muted);
                font-size: 0.86rem;
                margin: 0.8rem 0 0.55rem;
                padding: 0.75rem 0.85rem;
            }

            @media (max-width: 1200px) {
                .linkedin-grid {
                    grid-template-columns: 1fr;
                }
                .news-content-grid {
                    grid-template-columns: 1fr;
                }
                .gemini-panel {
                    position: static;
                }
                .filter-grid,
                .filter-grid-secondary {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }

            @media (max-width: 900px) {
                .hero-title {
                    font-size: 2.3rem;
                }
                .workspace-card {
                    min-height: auto;
                }
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
                .filter-grid,
                .filter-grid-secondary,
                .article-card {
                    grid-template-columns: 1fr;
                }
                .news-page-heading h1 {
                    font-size: 2.1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_access_tab() -> None:
    components.html(
        """
        <script>
        (() => {
            const parentDocument = window.parent.document;
            const existing = parentDocument.getElementById("psa-sidebar-access-tab");
            if (existing) {
                existing.remove();
            }

            const tab = parentDocument.createElement("button");
            tab.id = "psa-sidebar-access-tab";
            tab.type = "button";
            tab.innerHTML = "<span aria-hidden='true'>☰</span><span>Side Panel</span>";
            tab.setAttribute("aria-label", "Open side panel");
            Object.assign(tab.style, {
                alignItems: "center",
                background: "#ffffff",
                border: "1px solid #dbe6f3",
                borderRadius: "999px",
                boxShadow: "0 10px 24px rgba(14, 42, 94, 0.16)",
                color: "#1c3568",
                cursor: "pointer",
                display: "inline-flex",
                font: "800 13px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                gap: "7px",
                minHeight: "36px",
                padding: "0 13px",
                position: "fixed",
                top: "18px",
                zIndex: "2147483647",
            });

            const findSidebarToggle = () => {
                const candidates = [...parentDocument.querySelectorAll('button[data-testid="stBaseButton-headerNoPadding"]')];
                return candidates.find((button) => button.offsetParent !== null) || candidates[0];
            };

            const positionTab = () => {
                const sidebar = parentDocument.querySelector('section[data-testid="stSidebar"]');
                const rect = sidebar ? sidebar.getBoundingClientRect() : null;
                const sidebarOpen = rect && rect.width > 90 && rect.right > 0;
                tab.style.left = `${sidebarOpen ? Math.round(rect.right + 14) : 14}px`;
            };

            tab.addEventListener("click", () => {
                const toggle = findSidebarToggle();
                if (toggle) {
                    toggle.click();
                    window.parent.setTimeout(positionTab, 280);
                }
            });

            parentDocument.body.appendChild(tab);
            positionTab();
            window.parent.addEventListener("resize", positionTab);
        })();
        </script>
        """,
        height=0,
    )


def remove_sidebar_access_tab() -> None:
    components.html(
        """
        <script>
        (() => {
            window.parent.document.getElementById("psa-sidebar-access-tab")?.remove();
        })();
        </script>
        """,
        height=0,
    )


def load_demo_sheet() -> pd.DataFrame:
    st.warning("Using demo news data because the live Google Sheet is not accessible yet.")
    df = pd.DataFrame(DEMO_SHEET_DATA)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_public_google_sheet() -> pd.DataFrame:
    sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        return load_demo_sheet()

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0"
    try:
        response = requests.get(csv_url, timeout=12)
        response.raise_for_status()
        if "text/html" in response.headers.get("content-type", ""):
            return load_demo_sheet()

        df = pd.read_csv(StringIO(response.text))
        df.columns = [str(column).strip() for column in df.columns]
        if "Date" not in df.columns:
            return load_demo_sheet()

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df
    except Exception:
        return load_demo_sheet()


def extract_stories_from_cell(cell_text: str, row_date, category: str) -> list[dict]:
    if pd.isna(cell_text) or not str(cell_text).strip():
        return []

    text = str(cell_text).strip()
    url_pattern = r"https?://[^\s\"<>]+"
    urls = re.findall(url_pattern, text)
    if not urls:
        return []

    segments = re.split(url_pattern, text)
    stories = []
    for index, url in enumerate(urls):
        title_source = segments[index]
        title_source = re.sub(r"Link\s*-?\s*$", "", title_source, flags=re.IGNORECASE).strip()
        title_parts = re.split(r"\n\s*\n", title_source)
        title = title_parts[-1].strip() if title_parts else title_source
        title = re.sub(r"\s+", " ", title.replace('"', "")).strip()
        if not title or title.lower() == "untitled story":
            title = f"Update from {story_source(url)}"
        stories.append({"date": row_date, "category": category, "title": title, "url": url.strip()})

    return stories


def transform_sheet_to_stories(df: pd.DataFrame) -> pd.DataFrame:
    stories = []
    for _, row in df.iterrows():
        for category in CATEGORIES:
            if category in row:
                stories.extend(extract_stories_from_cell(row[category], row.get("Date"), category))

    stories_df = pd.DataFrame(stories)
    if stories_df.empty:
        return pd.DataFrame(columns=["date", "category", "title", "url", "source"])

    stories_df["date"] = pd.to_datetime(stories_df["date"], errors="coerce")
    stories_df = stories_df.dropna(subset=["date"]).drop_duplicates(subset=["url"])
    stories_df["source"] = stories_df["url"].apply(story_source)
    return stories_df.sort_values("date", ascending=False)


def filter_stories(stories_df: pd.DataFrame, search_term: str, date_filter: str) -> pd.DataFrame:
    filtered = stories_df
    today = pd.Timestamp.today().normalize()
    if date_filter == "Today":
        filtered = filtered[filtered["date"] >= today]
    elif date_filter == "Last 7 Days":
        filtered = filtered[filtered["date"] >= today - timedelta(days=7)]
    elif date_filter == "Last 30 Days":
        filtered = filtered[filtered["date"] >= today - timedelta(days=30)]

    if search_term:
        filtered = filtered[filtered["title"].str.contains(search_term, case=False, na=False, regex=False)]
    return filtered


def summarize_story(story: pd.Series) -> str:
    title = str(story["title"]).strip().rstrip(".")
    if not title:
        return "This article covers the development listed in the headline. It focuses on the facts described in the article. It should be reviewed for the article's specific details."

    if ":" in title:
        lead, detail = [part.strip() for part in title.split(":", 1)]
        if lead and detail:
            return (
                f"This article covers {detail}. "
                f"It frames the development around {lead}. "
                "The story focuses on the facts described in the article."
            )

    return (
        f"This article covers {title}. "
        "It focuses on the development described in the headline. "
        "The story discusses the facts and implications presented in the article."
    )


def render_sidebar(workspace_view: str | None = None) -> None:
    with st.sidebar:
        if workspace_view == "news_center":
            st.markdown('<div class="focus-rail-caption">Focus</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                """
                <div class="sidebar-shell">
                    <div>
                        <div class="sidebar-brand">
                            <div class="sidebar-logo">PSA</div>
                            <div class="sidebar-wordmark">Intelligent<br>Dashboard</div>
                        </div>
                        <div class="sidebar-nav">
                            <span class="sidebar-item-active">Home</span>
                            <span class="sidebar-item">Bookmarks</span>
                            <span class="sidebar-item">Saved Searches</span>
                            <span class="sidebar-item">Alerts</span>
                            <span class="sidebar-item">Settings</span>
                            <span class="sidebar-item">Help</span>
                            <span class="sidebar-item">Contact</span>
                        </div>
                    </div>
                    <div class="sidebar-user">
                        <span class="sidebar-avatar">CS</span>
                        <div>
                            <div class="sidebar-user-name">Chris Smith</div>
                            <div class="sidebar-user-role">Account Admin</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">The P-S-A Dashboard</div>
            <div class="hero-subtitle">Your centralized workspace for monitoring privacy, cybersecurity, AI governance, regulatory developments, and litigation trends.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_cards(stories_df: pd.DataFrame) -> None:
    st.markdown('<div class="workspace-section">', unsafe_allow_html=True)
    cols = st.columns(4)
    keys = ["news_center", "legislation", "litigation", "education"]
    for col, key in zip(cols, keys):
        option = WORKSPACE_OPTIONS[key]
        with col:
            st.markdown(
                f"""
                <div class="workspace-card">
                    <span class="chip-icon">{workspace_icon(option['icon'])}</span>
                    <div class="workspace-title">{escape(option['title'])}</div>
                    <div class="workspace-copy">{escape(option['description'])}</div>
                    <a class="workspace-open-button" href="?workspace={escape(key)}">Open <span>›</span></a>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_story_card(story: pd.Series, compact: bool = False) -> None:
    date = story["date"].strftime("%b %d, %Y")
    st.markdown(
        f"""
        <div class="story">
            <div class="story-kicker">
                <span class="tag">{escape(story['category'])}</span>
                <span class="muted">{date} · {escape(story['source'])}</span>
            </div>
            <div class="story-title">{escape(story['title'])}</div>
            <div class="story-summary">{escape(summarize_story(story))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 1, 5])
    with cols[0]:
        st.link_button("Read Source", story["url"], use_container_width=True)
    with cols[1]:
        share_link = f"mailto:?subject={quote_plus(story['title'])}&body={quote_plus(story['url'])}"
        st.link_button("Share", share_link, use_container_width=True)


def render_questions_card() -> None:
    subject = quote_plus("Question about a dashboard news story")
    body = quote_plus("Story/title:\nCategory:\nQuestion:\n\n")
    st.markdown(
        f"""
        <div class="contact-card">
            <div class="eyebrow">Conversation Support</div>
            <div class="contact-title">Any Questions?</div>
            <a class="contact-action" href="mailto:?subject={subject}&body={body}">Start a Conversation</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_linkedin_updates() -> None:
    posts_html = []
    for post in LINKEDIN_UPDATES:
        avatar_html = (
            f'<span class="linkedin-avatar"><img src="{asset_data_url(post["avatar_image"])}" alt="{escape(post["account"])} logo"></span>'
            if post.get("avatar_image")
            else f'<span class="linkedin-avatar">{escape(post["avatar"])}</span>'
        )
        posts_html.append(
            (
                '<div class="linkedin-post">'
                '<div class="linkedin-topline">'
                f"{avatar_html}"
                "<div>"
                f'<div class="linkedin-name">{escape(post["account"])} <span class="linkedin-badge">in</span></div>'
                f'<div class="linkedin-date">{escape(post["date"])}</div>'
                "</div>"
                "</div>"
                f'<div class="linkedin-copy">{escape(post["preview"])}</div>'
                '<div class="linkedin-footer">'
                f'<a class="linkedin-link" href="{escape(post["url"])}" target="_blank">View on LinkedIn ↗</a>'
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        (
            '<div class="linkedin-panel">'
            '<div class="linkedin-header">'
            '<div class="linkedin-heading">LinkedIn Updates <span class="linkedin-badge">in</span></div>'
            '<a class="linkedin-link" href="https://www.linkedin.com/" target="_blank">View all on LinkedIn ↗</a>'
            "</div>"
            f'<div class="linkedin-grid">{"".join(posts_html)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_dashboard(stories_df: pd.DataFrame) -> None:
    render_header()
    render_workspace_cards(stories_df)
    render_linkedin_updates()


def render_news_center_header() -> None:
    st.markdown(
        """
        <div class="news-topbar">
            <span class="news-header-icon" aria-label="Notifications">
                <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"></path><path d="M10 20h4"></path></svg>
            </span>
            <span class="news-header-icon" aria-label="Help">
                <svg viewBox="0 0 24 24"><path d="M9.2 9a3 3 0 1 1 5.1 2.1c-.9.7-1.4 1.2-1.4 2.4"></path><path d="M12 17.5h.01"></path><path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z"></path></svg>
            </span>
            <span class="news-user-avatar">EK</span>
        </div>
        <div class="news-page-heading">
            <h1>Your News Center</h1>
            <p>Track privacy, AI, cybersecurity, data protection laws, regulations, guidance, and legislative updates.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def infer_jurisdiction(title: str) -> str:
    prefix = str(title).split(":", 1)[0].strip()
    if ":" in str(title) and 2 <= len(prefix) <= 60:
        return prefix
    return "Unspecified"


def ensure_news_filter_state() -> None:
    for key, value in NEWS_FILTER_DEFAULTS.items():
        st.session_state.setdefault(f"news_{key}", value if not isinstance(value, list) else value.copy())


def apply_news_saved_view(view_name: str) -> None:
    preset = NEWS_SAVED_VIEWS.get(view_name, NEWS_SAVED_VIEWS["All Stories"])
    st.session_state.news_date_range = preset["date_range"]
    st.session_state.news_topics = preset["topics"].copy()
    st.session_state.news_sort_filter = preset["sort_filter"]
    st.session_state.news_keyword = preset["keyword"]
    st.session_state.news_saved_view = view_name
    st.session_state["_news_saved_view_applied"] = view_name


def reset_news_filters() -> None:
    apply_news_saved_view("All Stories")
    st.session_state.news_display_mode = NEWS_FILTER_DEFAULTS["display_mode"]
    st.session_state.news_auto_scroll = NEWS_FILTER_DEFAULTS["auto_scroll"]


def initialize_news_filter_state() -> None:
    ensure_news_filter_state()
    if "news_display_mode" not in st.session_state:
        st.session_state.news_display_mode = NEWS_FILTER_DEFAULTS["display_mode"]
    if st.session_state.get("_focus_mode_initialized") is not True:
        st.session_state.news_auto_scroll = NEWS_FILTER_DEFAULTS["auto_scroll"]
        st.session_state.news_display_mode = NEWS_FILTER_DEFAULTS["display_mode"]
        st.session_state["_focus_mode_initialized"] = True
    if st.session_state.get("news_saved_view") not in NEWS_SAVED_VIEWS:
        apply_news_saved_view("All Stories")


def filter_news_center_stories(
    stories_df: pd.DataFrame,
    date_range_option: str,
    topics: list[str],
    keyword: str,
    sort_filter: str,
) -> pd.DataFrame:
    filtered = stories_df.copy()

    date_windows = {
        "Past Week": 7,
        "Past Month": 30,
        "Past Three Months": 90,
        "Past Year": 365,
    }
    if date_range_option in date_windows and not filtered.empty:
        latest_story_date = filtered["date"].max()
        cutoff_date = latest_story_date - timedelta(days=date_windows[date_range_option])
        filtered = filtered[filtered["date"] >= cutoff_date]

    if topics:
        filtered = filtered[filtered["category"].isin(topics)]
    if keyword:
        search_space = (
            filtered["title"].fillna("")
            + " "
            + filtered["category"].fillna("")
            + " "
            + filtered["source"].fillna("")
        )
        filtered = filtered[search_space.str.contains(keyword, case=False, na=False, regex=False)]

    return filtered.sort_values("date", ascending=(sort_filter == "Oldest Stories"))


def render_news_rail(stories_df: pd.DataFrame) -> tuple[object, bool]:
    initialize_news_filter_state()
    with st.sidebar:
        st.markdown('<div class="news-rail-anchor focus-rail-anchor"></div>', unsafe_allow_html=True)
        result_count_slot = st.empty()
        if st.button(
            "",
            key="news_home_button",
            help="Return to Homepage",
            icon=":material/home:",
            use_container_width=True,
        ):
            st.session_state.workspace_view = None
            st.query_params.clear()
            st.rerun()

        with st.popover(
            "",
            icon=":material/tune:",
            use_container_width=True,
        ):
            st.markdown('<div class="filter-panel-heading">Focus controls</div>', unsafe_allow_html=True)
            saved_view_options = list(NEWS_SAVED_VIEWS.keys())
            saved_view = st.selectbox(
                "Saved Views",
                saved_view_options,
                index=saved_view_options.index(st.session_state.news_saved_view),
            )
            if saved_view != st.session_state.get("_news_saved_view_applied"):
                apply_news_saved_view(saved_view)
                st.rerun()

            st.toggle(
                "Auto-Scroll News Feed",
                key="news_auto_scroll",
            )
            if st.button("Reset Filters", use_container_width=True):
                reset_news_filters()
                st.rerun()

        if st.button(
            "",
            key="focus_search_button",
            help="Jump to search",
            icon=":material/search:",
            use_container_width=True,
        ):
            st.session_state["_focus_search_requested"] = True
        st.markdown('<div class="focus-rail-caption">Search</div>', unsafe_allow_html=True)

    return result_count_slot, st.session_state.news_auto_scroll


def render_news_toolbar() -> tuple[str, list[str], str, str, str, object]:
    toolbar_shell = st.container()
    topics = st.session_state.news_topics.copy()
    with toolbar_shell:
        st.markdown('<div class="news-toolbar-anchor"></div>', unsafe_allow_html=True)
        toolbar_cols = st.columns([2.0, 0.66, 0.76, 0.66, 0.58, 0.62])
        with toolbar_cols[0]:
            keyword = st.text_input(
                "Search stories",
                placeholder="Search stories, sources, or topics...",
                key="news_keyword",
            )
        with toolbar_cols[1]:
            sort_filter = st.selectbox("Sort", NEWS_SORT_OPTIONS, key="news_sort_filter")
        with toolbar_cols[2]:
            date_range_option = st.selectbox("Date range", NEWS_DATE_RANGE_OPTIONS, key="news_date_range")
        with toolbar_cols[3]:
            with st.popover("Topics", icon=":material/tune:", use_container_width=True):
                topics = st.multiselect(
                    "Choose a Topic",
                    NEWS_TOPIC_OPTIONS,
                    key="news_topics",
                )
        with toolbar_cols[4]:
            display_mode = st.selectbox("Display", ["List", "Cards"], key="news_display_mode")
        with toolbar_cols[5]:
            result_count_slot = st.empty()
    if st.session_state.pop("_focus_search_requested", False):
        render_focus_search_controller()
    return (
        keyword,
        topics if "topics" in locals() else st.session_state.news_topics,
        date_range_option,
        sort_filter,
        display_mode,
        result_count_slot,
    )


def render_auto_scroll_controller(enabled: bool) -> None:
    enabled_js = "true" if enabled else "false"
    components.html(
        f"""
        <script>
        (() => {{
            const parentWindow = window.parent;
            if (parentWindow.__psaNewsAutoScrollTimer) {{
                parentWindow.clearInterval(parentWindow.__psaNewsAutoScrollTimer);
                parentWindow.__psaNewsAutoScrollTimer = null;
            }}
            if (parentWindow.__psaNewsAutoScrollDelay) {{
                parentWindow.clearTimeout(parentWindow.__psaNewsAutoScrollDelay);
                parentWindow.__psaNewsAutoScrollDelay = null;
            }}

            if (!{enabled_js}) {{
                return;
            }}

            const scrollStep = 1;
            const scrollDelay = 42;
            const startDelay = 3500;
            parentWindow.__psaNewsAutoScrollDelay = parentWindow.setTimeout(() => {{
                parentWindow.__psaNewsAutoScrollDelay = null;
                parentWindow.__psaNewsAutoScrollTimer = parentWindow.setInterval(() => {{
                const scrollTarget = parentWindow.document.querySelector('[data-testid="stMain"]');
                const doc = parentWindow.document.documentElement;
                const scrollTop = scrollTarget ? scrollTarget.scrollTop : (parentWindow.scrollY || doc.scrollTop);
                const viewportHeight = scrollTarget ? scrollTarget.clientHeight : parentWindow.innerHeight;
                const scrollHeight = scrollTarget ? scrollTarget.scrollHeight : doc.scrollHeight;
                const atBottom = scrollTop + viewportHeight >= scrollHeight - 8;

                if (atBottom) {{
                    parentWindow.clearInterval(parentWindow.__psaNewsAutoScrollTimer);
                    parentWindow.__psaNewsAutoScrollTimer = null;
                    return;
                }}

                if (scrollTarget) {{
                    scrollTarget.scrollTop += scrollStep;
                }} else {{
                    parentWindow.scrollBy({{ top: scrollStep, left: 0, behavior: "auto" }});
                }}
                }}, scrollDelay);
            }}, startDelay);

            const stopAutoScroll = () => {{
                if (parentWindow.__psaNewsAutoScrollDelay) {{
                    parentWindow.clearTimeout(parentWindow.__psaNewsAutoScrollDelay);
                    parentWindow.__psaNewsAutoScrollDelay = null;
                }}
                if (parentWindow.__psaNewsAutoScrollTimer) {{
                    parentWindow.clearInterval(parentWindow.__psaNewsAutoScrollTimer);
                    parentWindow.__psaNewsAutoScrollTimer = null;
                }}
            }};
            parentWindow.addEventListener("wheel", stopAutoScroll, {{ once: true, passive: true }});
            parentWindow.addEventListener("touchstart", stopAutoScroll, {{ once: true, passive: true }});
            parentWindow.addEventListener("keydown", stopAutoScroll, {{ once: true }});
        }})();
        </script>
        """,
        height=0,
    )


def render_feed_progress_bar(story_count: int) -> None:
    components.html(
        f"""
        <script>
        (() => {{
            const parentDocument = window.parent.document;
            parentDocument.getElementById("psa-sidebar-access-tab")?.remove();
            const existing = parentDocument.getElementById("psa-feed-progress");
            if (existing) {{
                existing.remove();
            }}

            const progress = parentDocument.createElement("div");
            progress.id = "psa-feed-progress";
            progress.innerHTML = `
                <div class="psa-feed-progress-track">
                    <span class="psa-feed-progress-fill"></span>
                </div>
                <span class="psa-feed-progress-label">{story_count:,} stories</span>
            `;
            Object.assign(progress.style, {{
                alignItems: "center",
                background: "rgba(255, 255, 255, 0.94)",
                border: "1px solid #dbe6f3",
                borderRadius: "999px",
                bottom: "18px",
                boxShadow: "0 12px 28px rgba(14, 42, 94, 0.12)",
                color: "#1c3568",
                display: "flex",
                font: "800 12px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                gap: "10px",
                left: "50%",
                minWidth: "260px",
                padding: "8px 12px",
                position: "fixed",
                transform: "translateX(-50%)",
                zIndex: "2147483646",
            }});

            const style = parentDocument.createElement("style");
            style.id = "psa-feed-progress-style";
            style.textContent = `
                #psa-feed-progress .psa-feed-progress-track {{
                    background: #eef5ff;
                    border-radius: 999px;
                    height: 8px;
                    overflow: hidden;
                    width: 150px;
                }}
                #psa-feed-progress .psa-feed-progress-fill {{
                    background: #1d5fd0;
                    border-radius: 999px;
                    display: block;
                    height: 100%;
                    width: 0%;
                }}
                #psa-feed-progress .psa-feed-progress-label {{
                    white-space: nowrap;
                }}
            `;
            parentDocument.getElementById("psa-feed-progress-style")?.remove();
            parentDocument.head.appendChild(style);
            parentDocument.body.appendChild(progress);

            const update = () => {{
                const scrollTarget = parentDocument.querySelector('[data-testid="stMain"]');
                const top = scrollTarget ? scrollTarget.scrollTop : parentDocument.documentElement.scrollTop;
                const height = scrollTarget
                    ? scrollTarget.scrollHeight - scrollTarget.clientHeight
                    : parentDocument.documentElement.scrollHeight - parentDocument.documentElement.clientHeight;
                const pct = height > 0 ? Math.min(100, Math.max(0, (top / height) * 100)) : 0;
                progress.querySelector(".psa-feed-progress-fill").style.width = `${{pct}}%`;
            }};

            const scrollTarget = parentDocument.querySelector('[data-testid="stMain"]');
            if (scrollTarget) {{
                scrollTarget.addEventListener("scroll", update, {{ passive: true }});
            }} else {{
                window.parent.addEventListener("scroll", update, {{ passive: true }});
            }}
            update();
        }})();
        </script>
        """,
        height=0,
    )


def render_focus_search_controller() -> None:
    components.html(
        """
        <script>
        (() => {
            const parentDocument = window.parent.document;
            const searchInput = parentDocument.querySelector('input[aria-label="Search stories"]');
            if (searchInput) {
                searchInput.scrollIntoView({ block: "center", behavior: "smooth" });
                searchInput.focus();
            }
        })();
        </script>
        """,
        height=0,
    )


def story_to_news_center_article(story: pd.Series) -> dict:
    return {
        "category": story["category"],
        "date": story["date"].strftime("%b %d, %Y"),
        "jurisdiction": infer_jurisdiction(story["title"]),
        "brief": summarize_story(story),
        "title": story["title"],
        "source": story["source"],
        "url": story["url"],
    }


def news_center_articles(stories_df: pd.DataFrame) -> list[dict]:
    if stories_df.empty:
        return NEWS_CENTER_ARTICLES

    return [story_to_news_center_article(story) for _, story in stories_df.iterrows()]


def article_preview(article: dict) -> str:
    preview = article.get("brief") or article.get("summary") or ""
    if preview:
        return str(preview)
    title = str(article.get("title", "")).strip()
    if not title:
        return "Open the source for the full story."
    return f"{title}. Open the source for the full context."


def render_featured_article_card(article: dict) -> None:
    article_url = article.get("url", "#")
    category = article.get("category", "Laws and Regs")
    jurisdiction = article.get("jurisdiction", "Unspecified")
    source = article.get("source", "Source")
    source_context = source if jurisdiction == "Unspecified" else f"{jurisdiction} / {source}"
    preview = article_preview(article)
    source_link = (
        f'<a class="article-source" href="{escape(article_url)}" target="_blank" rel="noopener noreferrer">'
        'Open source <svg viewBox="0 0 24 24"><path d="M7 17 17 7"></path><path d="M8 7h9v9"></path></svg></a>'
    )
    actions = (
        '<div class="article-actions">'
        '<span class="article-action"><svg viewBox="0 0 24 24"><path d="M6 4h12v17l-6-4-6 4z"></path></svg></span>'
        '<span class="article-action"><svg viewBox="0 0 24 24"><path d="M18 8a3 3 0 1 0-2.8-4"></path><path d="M6 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path><path d="M18 16a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path><path d="m8.6 15.5 6.8-4"></path><path d="m8.6 18.5 6.8 2.8"></path></svg></span>'
        '<span class="gemini-mark">✦</span></div>'
    )
    card_html = (
        f'<div class="story-card story-card-featured" aria-label="Story: {escape(article["title"])}">'
        f'<div class="article-icon story-card-icon">{workspace_icon("news")}</div>'
        '<div class="story-card-body">'
        '<div class="article-meta story-card-meta">'
        '<span class="article-badge">Featured</span>'
        f'<span class="article-badge">{escape(category)}</span>'
        f'<span class="article-date">{escape(article["date"])}</span>'
        f'<span class="article-jurisdiction">{escape(source_context)}</span>'
        '</div>'
        f'<div class="story-card-title">{escape(article["title"])}</div>'
        f'<div class="story-card-preview">{escape(preview)}</div>'
        f'<div class="article-footer story-card-footer">{source_link}{actions}</div>'
        '</div></div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def article_card_html(article: dict, display_mode: str = "List") -> str:
    article_url = article.get("url", "#")
    category = article.get("category", "Laws and Regs")
    jurisdiction = article.get("jurisdiction", "Unspecified")
    source = article.get("source", "Source")
    source_context = source if jurisdiction == "Unspecified" else f"{jurisdiction} / {source}"
    is_card_view = display_mode == "Cards"
    card_class = "story-card story-card-grid" if is_card_view else "story-card story-card-compact"
    preview_markup = (
        f'<div class="story-card-preview">{escape(article_preview(article))}</div>'
        if is_card_view
        else ""
    )
    source_link = (
        f'<a class="article-source" href="{escape(article_url)}" target="_blank" rel="noopener noreferrer">'
        'Open source <svg viewBox="0 0 24 24"><path d="M7 17 17 7"></path><path d="M8 7h9v9"></path></svg></a>'
    )
    actions = (
        '<div class="article-actions">'
        '<span class="article-action"><svg viewBox="0 0 24 24"><path d="M6 4h12v17l-6-4-6 4z"></path></svg></span>'
        '<span class="article-action"><svg viewBox="0 0 24 24"><path d="M18 8a3 3 0 1 0-2.8-4"></path><path d="M6 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path><path d="M18 16a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"></path><path d="m8.6 15.5 6.8-4"></path><path d="m8.6 18.5 6.8 2.8"></path></svg></span>'
        '<span class="gemini-mark">✦</span></div>'
    )
    return (
        f'<div class="{card_class}" aria-label="Story: {escape(article["title"])}">'
        f'<div class="article-icon story-card-icon">{workspace_icon("news")}</div>'
        '<div class="story-card-body">'
        '<div class="article-meta">'
        f'<span class="article-badge">{escape(category)}</span>'
        f'<span class="article-date">{escape(article["date"])}</span>'
        f'<span class="article-jurisdiction">{escape(source_context)}</span>'
        '</div>'
        f'<div class="story-card-title">{escape(article["title"])}</div>'
        f'{preview_markup}'
        f'<div class="article-footer story-card-footer">{source_link}{actions}</div>'
        '</div></div>'
    )


def render_article_card(article: dict, display_mode: str = "List") -> None:
    st.markdown(article_card_html(article, display_mode), unsafe_allow_html=True)


def render_gemini_panel() -> None:
    st.markdown(
        """
        <div class="gemini-panel">
            <div class="gemini-title">Ask Gemini</div>
            <div class="gemini-subtitle">AI assistant for quick insights and answers.</div>
            <div class="gemini-section-title">Article Summary</div>
            <div class="gemini-summary">Louisiana's Data Privacy Act establishes comprehensive data protection requirements for businesses that collect or process personal data of Louisiana residents.</div>
            <ul>
                <li>Grants residents rights to access, correct, and delete personal data.</li>
                <li>Requires businesses to implement reasonable security measures.</li>
                <li>Enforced by the Attorney General with civil penalties for violations.</li>
                <li>Takes effect on January 1, 2027.</li>
            </ul>
            <div class="gemini-meta">Source: State of Louisiana Official Website</div>
            <div class="gemini-meta">Generated by Gemini &middot; May 26, 2026</div>
            <div class="gemini-section-title">Suggested Prompts</div>
            <span class="prompt-chip">Summarize this article</span>
            <span class="prompt-chip">What are the legal implications?</span>
            <span class="prompt-chip">Compare with similar regulations</span>
            <div class="gemini-input">Ask a question about this article...</div>
            <div class="gemini-disclaimer">Gemini can make mistakes. Check important info.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_news_center_page(filtered_stories_df: pd.DataFrame, auto_scroll: bool, display_mode: str) -> None:
    is_card_view = display_mode == "Cards"
    st.markdown('<div class="news-shell feed-layout">', unsafe_allow_html=True)
    render_news_center_header()
    render_auto_scroll_controller(auto_scroll)
    render_feed_progress_bar(len(filtered_stories_df))
    articles = news_center_articles(filtered_stories_df)
    feed_class = "news-feed-shell feed-display-cards" if is_card_view else "news-feed-shell"
    st.markdown(f'<div class="{feed_class}">', unsafe_allow_html=True)
    if articles:
        st.markdown('<div class="featured-label">Featured story</div>', unsafe_allow_html=True)
        render_featured_article_card(articles[0])
        if len(articles) > 1:
            st.markdown('<div class="featured-label">More from your feed</div>', unsafe_allow_html=True)
            if is_card_view:
                card_articles = articles[1:]
                for row_start in range(0, len(card_articles), 3):
                    columns = st.columns(3, gap="medium")
                    for column, article in zip(columns, card_articles[row_start : row_start + 3]):
                        with column:
                            render_article_card(article, display_mode="Cards")
            else:
                for article in articles[1:]:
                    render_article_card(article, display_mode=display_mode)
    else:
        st.markdown(
            f"""
            <div class="story-card story-card-compact">
                <div class="article-icon story-card-icon">{workspace_icon("news")}</div>
                <div class="story-card-body">
                    <div class="story-card-title">No stories matched the current filters.</div>
                    <div class="story-card-preview">Try broadening the date range, selecting more topics, or clearing the keyword search.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_category_page(stories_df: pd.DataFrame, category: str) -> None:
    if st.button("Back to Workspace"):
        st.session_state.selected_category = None
        st.session_state.workspace_view = None
        st.rerun()

    st.markdown(f'<div class="section-heading">{escape(category)}</div>', unsafe_allow_html=True)
    st.caption(CATEGORY_DETAILS[category]["description"])
    search_term = st.text_input("Search this category", placeholder="Search within this category...")
    category_df = stories_df[stories_df["category"] == category]
    if search_term:
        category_df = category_df[category_df["title"].str.contains(search_term, case=False, na=False, regex=False)]

    st.caption(f"{len(category_df):,} stories")
    for _, story in category_df.head(100).iterrows():
        render_story_card(story)


def render_news_center(filtered_stories_df: pd.DataFrame, auto_scroll: bool, display_mode: str) -> None:
    render_news_center_page(filtered_stories_df, auto_scroll, display_mode)


def render_blank_workspace(title: str) -> None:
    if st.button("Back to Workspace"):
        st.session_state.workspace_view = None
        st.query_params.clear()
        st.rerun()

    st.markdown(f'<div class="section-heading">{escape(title)}</div>', unsafe_allow_html=True)


def render_placeholder(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">V2 Workspace</div>
            <div class="hero-title">{escape(title)}</div>
            <div class="hero-subtitle">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_styles()
    raw_df = load_public_google_sheet()
    stories_df = transform_sheet_to_stories(raw_df)
    if stories_df.empty:
        st.warning("No stories were found.")
        return

    workspace_param = st.query_params.get("workspace")
    if workspace_param == "home":
        st.session_state.workspace_view = None
        st.query_params.clear()
        workspace_view = None
    elif workspace_param:
        workspace_view = workspace_param
        st.session_state.workspace_view = workspace_view
    else:
        workspace_view = st.session_state.get("workspace_view")
    if workspace_view is None or workspace_view == "news_center":
        remove_sidebar_access_tab()
    else:
        render_sidebar_access_tab()
    if workspace_view == "news_center":
        rail_count_slot, auto_scroll = render_news_rail(stories_df)
        render_sidebar(workspace_view)
        keyword, topics, date_range_option, sort_filter, display_mode, toolbar_count_slot = render_news_toolbar()
        filtered_stories_df = filter_news_center_stories(
            stories_df,
            date_range_option,
            topics,
            keyword,
            sort_filter,
        )
        rail_count_slot.markdown(
            f'<div class="focus-rail-count">{len(filtered_stories_df):,}</div>',
            unsafe_allow_html=True,
        )
        toolbar_count_slot.markdown(
            f'<div class="feed-count-pill">{len(filtered_stories_df):,} results</div>',
            unsafe_allow_html=True,
        )
        render_news_center(filtered_stories_df, auto_scroll, display_mode)
    elif workspace_view == "legislation":
        render_sidebar(workspace_view)
        render_blank_workspace("Legislation")
    elif workspace_view == "litigation":
        render_sidebar(workspace_view)
        render_blank_workspace("Litigation/Enforcement Actions")
    elif workspace_view == "education":
        render_sidebar(workspace_view)
        render_blank_workspace("Educational Resources")
    else:
        render_sidebar(workspace_view)
        render_dashboard(stories_df)


if __name__ == "__main__":
    main()
