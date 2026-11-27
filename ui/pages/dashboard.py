"""Dashboard page for WipeWise."""

from __future__ import annotations

import html
import pandas as pd
import plotly.express as px
import streamlit as st

from database.db import (
    format_device_label,
    list_assessments,
    list_devices,
    list_impact_records,
    list_lifecycle_events,
    list_sanitization_records,
)
from ui.styles import (
    CHART_PALETTE,
    FOREST_DARK,
    FOREST_MID,
    LIME_ACCENT,
    badge_html,
    render_empty_state,
    render_kpi_card,
    render_page_header,
)


def _navigate_to(page_name: str) -> None:
    st.session_state["pending_nav"] = page_name
    st.rerun()


def render() -> None:
    """Render the executive sustainability & data-safety dashboard."""
    render_page_header(
        title="WipeWise — Device Lifecycle Command Center",
        subtitle=(
            "Assess device viability, safeguard personal data before transfer or disposal, "
            "maintain persistent Device Passports, and track estimated e-waste outcomes."
        ),
        kicker="Secure Your Data. Save Your Device.",
    )

    devices = list_devices()
    assessments = list_assessments()
    sanitizations = list_sanitization_records()
    impacts = list_impact_records()
    recent_events = list_lifecycle_events(ascending=False)[:6]

    total_devices = len(devices)
    assessed_device_ids = {a["device_id"] for a in assessments}
    devices_assessed = len(assessed_device_ids)

    repair_count = sum(
        1
        for d in devices
        if d.get("current_recommendation") == "Repair" or d.get("status") == "Under Repair"
    )
    reuse_donate_resell_count = sum(
        1
        for d in devices
        if d.get("current_recommendation") in {"Reuse", "Donate", "Resell"}
        or d.get("status") in {
            "Reused",
            "Donated",
            "Resold",
            "Ready for Reuse",
            "Ready for Donation",
            "Ready for Resale",
        }
    )
    recycle_count = sum(
        1
        for d in devices
        if d.get("current_recommendation") == "Recycle"
        or d.get("status") in {"Recycled", "Ready for Recycling"}
    )

    verified_or_doc_sanitizations = sum(
        1
        for s in sanitizations
        if s.get("verification") in {"Documented", "Independently verified"}
    )

    diverted_kg = sum(
        float(i.get("estimated_ewaste_diverted_kg") or 0.0)
        if i.get("action") != "Recycled"
        else 0.0
        for i in impacts
    )
    # Fallback for legacy rows migrated without precomputed diverted column
    if impacts and diverted_kg == 0.0:
        diverted_kg = sum(
            float(i.get("weight") or 0.0)
            for i in impacts
            if i.get("action") in {"Repaired", "Reused", "Donated", "Resold"}
        )

    recycled_kg = sum(
        float(i.get("weight") or 0.0)
        for i in impacts
        if i.get("action") == "Recycled"
    )
    co2_est_kg = sum(float(i.get("estimated_co2_saved_kg") or 0.0) for i in impacts)

    # First-time onboarding experience when no devices are registered yet
    if total_devices == 0:
        st.markdown(
            """
            <div class="ww-card" style="border-left: 4px solid #52B788;">
                <h3 style="margin-top:0; color:#1B4332;">Welcome to WipeWise — Start in 3 Simple Steps</h3>
                <p style="color:#52606D; margin-bottom:0.65rem;">
                    Avoid premature e-waste and protect sensitive files before selling, donating, or recycling old electronics.
                </p>
                <ol style="color:#1F2933; margin-bottom:0.25rem; padding-left:1.25rem;">
                    <li><strong>Assess Your Device:</strong> Evaluate condition, battery health, and repairability to get a transparent rule-based recommendation.</li>
                    <li><strong>Protect Your Data:</strong> Walk through the Data Safety Shield checklist and record sanitization details.</li>
                    <li><strong>Maintain Your Passport:</strong> Keep a persistent lifecycle timeline and estimate environmental impact.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cta1, cta2, cta3, cta4 = st.columns(4)
    with cta1:
        if st.button("🔍 Assess a Device", key="dash_cta_assess", use_container_width=True, type="primary"):
            _navigate_to("Device Assessment")
    with cta2:
        if st.button("🔐 Data Safety Shield", key="dash_cta_shield", use_container_width=True):
            _navigate_to("Data Safety Shield")
    with cta3:
        if st.button("📋 Device Passports", key="dash_cta_passport", use_container_width=True):
            _navigate_to("Lifecycle Passport")
    with cta4:
        if st.button("🧹 Log Sanitization", key="dash_cta_sanitize", use_container_width=True):
            _navigate_to("Sanitization Records")

    st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

    # Primary KPI Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            "Registered Devices",
            total_devices,
            "Active Device Passports in SQLite",
            FOREST_DARK,
        )
    with k2:
        render_kpi_card(
            "Devices Assessed",
            devices_assessed,
            f"{len(assessments)} saved assessment(s)",
            FOREST_MID,
        )
    with k3:
        render_kpi_card(
            "Sanitization Records",
            len(sanitizations),
            f"{verified_or_doc_sanitizations} documented or verified",
            LIME_ACCENT,
        )
    with k4:
        render_kpi_card(
            "Est. E-Waste Diverted",
            f"{diverted_kg:.1f} kg",
            f"~{co2_est_kg:.1f} kg est. CO2e avoided",
            FOREST_DARK,
        )

    # Recommendation & Action Summary Row
    r1, r2, r3 = st.columns(3)
    with r1:
        render_kpi_card(
            "Recommended for Repair",
            repair_count,
            "Devices flagged for repair or refurbishment",
            "#D97706",
        )
    with r2:
        render_kpi_card(
            "Reuse / Donate / Resell",
            reuse_donate_resell_count,
            "Devices suited for lifespan extension",
            FOREST_MID,
        )
    with r3:
        render_kpi_card(
            "Recommended / Sent to Recycle",
            recycle_count,
            f"{recycled_kg:.1f} kg reported for authorized recycling",
            "#2B4C65",
        )

    st.markdown("<div style='height: 0.4rem'></div>", unsafe_allow_html=True)

    # Charts Section
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Device Portfolio by Recommendation / Status")
        if devices:
            labels = [
                d.get("current_recommendation") or d.get("status") or "Unassessed"
                for d in devices
            ]
            df_devices = pd.DataFrame({"Outcome": labels}).value_counts().reset_index(name="Count")
            fig_devices = px.pie(
                df_devices,
                names="Outcome",
                values="Count",
                hole=0.52,
                color_discrete_sequence=CHART_PALETTE,
            )
            fig_devices.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.18),
                height=310,
            )
            st.plotly_chart(fig_devices, use_container_width=True)
        else:
            render_empty_state(
                "No Devices Registered Yet",
                "Register or assess your first device to see lifecycle recommendations across your portfolio.",
            )

    with c2:
        st.subheader("Reported Weight by Lifecycle Action")
        if impacts:
            df_imp = pd.DataFrame(impacts)
            grouped = (
                df_imp.groupby("action", as_index=False)["weight"]
                .sum()
                .sort_values("weight", ascending=False)
            )
            fig_imp = px.bar(
                grouped,
                x="action",
                y="weight",
                text_auto=".1f",
                color="action",
                color_discrete_sequence=CHART_PALETTE,
                labels={"action": "Action", "weight": "Weight (kg)"},
            )
            fig_imp.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=310,
            )
            st.plotly_chart(fig_imp, use_container_width=True)
        else:
            render_empty_state(
                "No Impact Records Logged Yet",
                "Log repaired, reused, donated, resold, or recycled devices in the Impact Tracker to visualize diversion.",
            )

    st.divider()
    st.subheader("Recent Lifecycle Activity")
    if recent_events:
        for ev in recent_events:
            device_label = format_device_label(ev)
            st.markdown(
                f"""
                <div class="ww-card" style="padding:0.85rem 1.05rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <strong>{html.escape(device_label)}</strong>
                            &nbsp;{badge_html(ev['event_type'])}
                        </div>
                        <span style="font-size:0.82rem; color:#52606D;">{html.escape(ev['event_date'])}</span>
                    </div>
                    <div style="margin-top:0.4rem; color:#1F2933; font-size:0.92rem;">
                        {html.escape(ev.get('details') or '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        render_empty_state(
            "No Lifecycle Events Recorded Yet",
            "Device registrations, assessments, sanitization records, and manual milestones will appear here chronologically.",
        )

    st.caption(
        "Transparency Note: All metrics on this dashboard are calculated directly from saved user records in SQLite. "
        "Environmental figures are transparent category-based estimates, not independently audited savings."
    )
