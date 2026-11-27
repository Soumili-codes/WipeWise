"""Shared UI/UX styling, typography, cards, and badges for WipeWise."""

from __future__ import annotations

import html
import streamlit as st

FOREST_DARK = "#1B4332"
FOREST_MID = "#2D6A4F"
SAGE_BG = "#EBF2EC"
SAGE_BORDER = "#D5E3D8"
LIME_ACCENT = "#52B788"
OFF_WHITE = "#F7F9F6"
CHARCOAL = "#1F2933"
MUTED_TEXT = "#52606D"

CHART_PALETTE = [
    "#1B4332",
    "#2D6A4F",
    "#52B788",
    "#74C69D",
    "#95D5B2",
    "#40916C",
    "#6B7D75",
]

_BADGE_STYLES: dict[str, tuple[str, str, str]] = {
    "Repair": ("#FFF4E5", "#9A5B13", "#F3D3A6"),
    "Under Repair": ("#FFF4E5", "#9A5B13", "#F3D3A6"),
    "Reuse": ("#E6F4EA", "#1B4332", "#B7DFC5"),
    "Reused": ("#E6F4EA", "#1B4332", "#B7DFC5"),
    "Ready for Reuse": ("#E6F4EA", "#1B4332", "#B7DFC5"),
    "Donate": ("#E8F5F1", "#1F5E4B", "#B5DFD2"),
    "Donated": ("#E8F5F1", "#1F5E4B", "#B5DFD2"),
    "Ready for Donation": ("#E8F5F1", "#1F5E4B", "#B5DFD2"),
    "Resell": ("#EDF7ED", "#24572D", "#C2E0C4"),
    "Resold": ("#EDF7ED", "#24572D", "#C2E0C4"),
    "Ready for Resale": ("#EDF7ED", "#24572D", "#C2E0C4"),
    "Recycle": ("#E9EFF5", "#2B4C65", "#C4D4E2"),
    "Recycled": ("#E9EFF5", "#2B4C65", "#C4D4E2"),
    "Ready for Recycling": ("#E9EFF5", "#2B4C65", "#C4D4E2"),
    "Independently verified": ("#1B4332", "#FFFFFF", "#1B4332"),
    "Documented": ("#E6F4EA", "#1B4332", "#A8D5B9"),
    "User reported": ("#FFF4E5", "#9A5B13", "#F3D3A6"),
    "Not started": ("#F1F5F3", "#52606D", "#D5DDD8"),
    "In Use": ("#EEF3F0", "#2D6A4F", "#C8DBD0"),
    "Assessed": ("#EDF3F7", "#2B4C65", "#CAD8E3"),
}


def inject_global_styles() -> None:
    """Inject consistent WipeWise visual styling across the Streamlit app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #1F2933;
        }

        .stApp {
            background-color: #F7F9F6;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1220px;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #163326;
            border-right: 1px solid #234938;
        }

        section[data-testid="stSidebar"] * {
            color: #EEF5F0;
        }

        section[data-testid="stSidebar"] .stRadio > div {
            gap: 0.28rem;
        }

        section[data-testid="stSidebar"] .stRadio label {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 0.48rem 0.75rem;
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }

        section[data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(82, 183, 136, 0.16);
            border-color: rgba(149, 213, 178, 0.45);
        }

        /* Buttons */
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
            border-radius: 10px;
            font-weight: 600;
            padding: 0.5rem 1.1rem;
            border: 1px solid #1B4332;
            transition: all 0.15s ease;
        }

        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background-color: #1B4332;
            color: #FFFFFF;
        }

        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
            background-color: #2D6A4F;
            border-color: #2D6A4F;
        }

        /* Form containers */
        div[data-testid="stForm"] {
            background-color: #FFFFFF;
            border: 1px solid #D9E2DC;
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            box-shadow: 0 2px 10px rgba(27, 67, 50, 0.04);
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            background-color: #FFFFFF;
            border: 1px solid #D9E2DC;
            border-radius: 12px;
            box-shadow: 0 1px 6px rgba(27, 67, 50, 0.03);
        }

        /* Custom WipeWise components */
        .ww-header-card {
            background-color: #FFFFFF;
            border: 1px solid #D9E2DC;
            border-left: 5px solid #1B4332;
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 2px 10px rgba(27, 67, 50, 0.05);
        }

        .ww-header-kicker {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #2D6A4F;
            margin-bottom: 0.25rem;
        }

        .ww-header-title {
            font-size: 1.65rem;
            font-weight: 700;
            color: #1B4332;
            margin: 0;
            line-height: 1.2;
        }

        .ww-header-sub {
            font-size: 0.96rem;
            color: #52606D;
            margin-top: 0.35rem;
            margin-bottom: 0;
            line-height: 1.5;
        }

        .ww-kpi-card {
            background-color: #FFFFFF;
            border: 1px solid #D9E2DC;
            border-radius: 12px;
            padding: 1rem 1.15rem;
            box-shadow: 0 2px 8px rgba(27, 67, 50, 0.04);
            height: 100%;
            margin-bottom: 0.75rem;
        }

        .ww-kpi-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #52606D;
            margin-bottom: 0.35rem;
        }

        .ww-kpi-value {
            font-size: 1.65rem;
            font-weight: 700;
            color: #1B4332;
            line-height: 1.15;
        }

        .ww-kpi-caption {
            font-size: 0.78rem;
            color: #6B7D75;
            margin-top: 0.35rem;
        }

        .ww-card {
            background-color: #FFFFFF;
            border: 1px solid #D9E2DC;
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 2px 8px rgba(27, 67, 50, 0.04);
            margin-bottom: 0.85rem;
        }

        .ww-empty {
            background-color: #FFFFFF;
            border: 1px dashed #B9CEC0;
            border-radius: 14px;
            padding: 2rem 1.5rem;
            text-align: center;
            margin: 0.75rem 0;
        }

        .ww-empty-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #1B4332;
            margin-bottom: 0.35rem;
        }

        .ww-empty-desc {
            font-size: 0.92rem;
            color: #52606D;
            max-width: 560px;
            margin: 0 auto;
        }

        .ww-badge {
            display: inline-block;
            padding: 0.2rem 0.62rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 600;
            line-height: 1.3;
        }

        .ww-sidebar-brand {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(149, 213, 178, 0.25);
            border-radius: 12px;
            padding: 0.95rem 1rem;
            margin-bottom: 1rem;
        }

        .ww-sidebar-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #FFFFFF;
            margin: 0;
        }

        .ww-sidebar-tagline {
            font-size: 0.78rem;
            color: #B7E4C7;
            margin-top: 0.2rem;
            margin-bottom: 0;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Render the WipeWise identity card at the top of the sidebar."""
    st.sidebar.markdown(
        """
        <div class="ww-sidebar-brand">
            <p class="ww-sidebar-title">♻️ WipeWise</p>
            <p class="ww-sidebar-tagline">Secure Your Data. Save Your Device.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, kicker: str = "WipeWise Platform") -> None:
    """Render a consistent top header card for a page."""
    st.markdown(
        f"""
        <div class="ww-header-card">
            <div class="ww-header-kicker">{html.escape(kicker)}</div>
            <h1 class="ww-header-title">{html.escape(title)}</h1>
            <p class="ww-header-sub">{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str | int,
    caption: str = "",
    accent_color: str = FOREST_DARK,
) -> None:
    """Render a styled metric card."""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_caption = html.escape(str(caption))
    caption_html = (
        f'<div class="ww-kpi-caption">{safe_caption}</div>' if safe_caption else ""
    )
    st.markdown(
        f"""
        <div class="ww-kpi-card" style="border-top: 3px solid {accent_color};">
            <div class="ww-kpi-label">{safe_label}</div>
            <div class="ww-kpi-value">{safe_value}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_html(label: str) -> str:
    """Return an HTML pill badge for a status, recommendation, or verification state."""
    bg, fg, border = _BADGE_STYLES.get(label, ("#EEF3F0", "#1F2933", "#D5DDD8"))
    return (
        f'<span class="ww-badge" style="background:{bg}; color:{fg}; '
        f'border:1px solid {border};">{html.escape(label)}</span>'
    )


def render_empty_state(title: str, description: str) -> None:
    """Render a clean empty-state placeholder card."""
    st.markdown(
        f"""
        <div class="ww-empty">
            <div class="ww-empty-title">{html.escape(title)}</div>
            <div class="ww-empty-desc">{html.escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
