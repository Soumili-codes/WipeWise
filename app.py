"""WipeWise — Smart Device Lifecycle & Data Safety Platform."""

from __future__ import annotations

import streamlit as st

from database.db import initialize_db
from ui.pages import (
    assessment,
    dashboard,
    impact,
    passport,
    safety_shield,
    sanitization,
    timeline,
)
from ui.styles import inject_global_styles, render_sidebar_brand

PAGES = {
    "Dashboard": dashboard.render,
    "Device Assessment": assessment.render,
    "Data Safety Shield": safety_shield.render,
    "Lifecycle Passport": passport.render,
    "Sanitization Records": sanitization.render,
    "Impact Tracker": impact.render,
    "Lifecycle Timeline": timeline.render,
}


def main() -> None:
    """Configure page, initialize SQLite, and render the active WipeWise view."""
    st.set_page_config(
        page_title="WipeWise — Secure Your Data. Save Your Device.",
        page_icon="♻️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_db()
    inject_global_styles()
    render_sidebar_brand()

    # Apply programmatic navigation requests before instantiating the radio widget
    if "pending_nav" in st.session_state:
        target = st.session_state.pop("pending_nav")
        if target in PAGES:
            st.session_state["main_navigation"] = target

    selected_page = st.sidebar.radio(
        "Navigate",
        options=list(PAGES.keys()),
        key="main_navigation",
    )

    st.sidebar.divider()
    st.sidebar.caption(
        "WipeWise stores your Device Passports, assessments, sanitization records, "
        "and timelines locally in SQLite (`wipewise.db`)."
    )

    PAGES[selected_page]()


if __name__ == "__main__":
    main()
