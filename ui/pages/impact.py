"""Environmental Impact Tracker page with transparent estimation assumptions."""

from __future__ import annotations

import html
import pandas as pd
import plotly.express as px
import streamlit as st

from database.db import (
    add_impact,
    format_device_label,
    list_devices,
    list_impact_records,
)
from services.assessment_engine import DEVICE_CATEGORIES
from services.impact_model import (
    IMPACT_ACTIONS,
    estimate_action_impact,
    get_assumptions_table,
    get_default_weight,
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


def render() -> None:
    """Render the Environmental Impact Tracker page."""
    render_page_header(
        title="Environmental Impact Tracker",
        subtitle=(
            "Estimate e-waste diverted and directional embodied-carbon savings from repairing, "
            "reusing, donating, reselling, or responsibly recycling electronics."
        ),
        kicker="Transparent Impact Estimation",
    )

    st.info(
        "Estimation Disclaimer: Impact numbers are calculated from user-reported device weights "
        "and transparent category assumptions. They are directional estimates, not independently "
        "measured environmental savings or verified carbon offsets."
    )

    devices = list_devices()

    st.subheader("Record a Lifecycle Impact Action")
    device_options = [{"id": None, "label": "Standalone Entry (Not linked to a Passport)"}] + [
        {"id": d["id"], "label": format_device_label(d), "raw": d} for d in devices
    ]
    selected_link = st.selectbox(
        "Link to Registered Device (Optional)",
        options=device_options,
        format_func=lambda opt: opt["label"],
        key="impact_device_link",
    )

    linked_raw = selected_link.get("raw")
    default_cat = linked_raw["device"] if linked_raw else "Laptop"
    cat_idx = DEVICE_CATEGORIES.index(default_cat) if default_cat in DEVICE_CATEGORIES else 0
    impact_suffix = str(selected_link["id"]) if selected_link["id"] is not None else "standalone"

    with st.form(f"impact_form_{impact_suffix}"):
        c1, c2 = st.columns(2)
        with c1:
            device_category = st.selectbox(
                "Device Category *",
                DEVICE_CATEGORIES,
                index=cat_idx,
            )
            action = st.selectbox("Lifecycle Action *", IMPACT_ACTIONS)
        with c2:
            suggested_w = get_default_weight(device_category)
            weight_kg = st.number_input(
                "Device Weight (kg) *",
                min_value=0.05,
                max_value=500.0,
                value=float(suggested_w),
                step=0.1,
                help="Adjust to match actual device weight; pre-filled with category average.",
            )
            notes = st.text_input(
                "Notes (Optional)",
                placeholder="e.g., Donated to community center, battery replaced",
            )

        save_impact = st.form_submit_button(
            "Save Impact Record",
            use_container_width=True,
        )

    if save_impact:
        estimate = estimate_action_impact(device_category, action, weight_kg)
        linked_name = (
            (linked_raw.get("device_name") or linked_raw["device"])
            if linked_raw
            else device_category
        )
        add_impact(
            device=device_category,
            action=action,
            weight=weight_kg,
            device_id=selected_link["id"],
            device_name=linked_name,
            estimated_ewaste_diverted_kg=estimate.ewaste_diverted_kg,
            estimated_co2_saved_kg=estimate.estimated_co2_saved_kg,
            notes=notes,
        )
        st.success(
            f"Saved {action} record ({weight_kg:.2f} kg). Formula: {estimate.formula_summary}"
        )
        st.rerun()

    st.divider()
    entries = list_impact_records()

    if entries:
        reused_count = sum(1 for e in entries if e["action"] in {"Reused", "Donated", "Resold"})
        repaired_count = sum(1 for e in entries if e["action"] == "Repaired")
        recycled_count = sum(1 for e in entries if e["action"] == "Recycled")

        diverted_kg = sum(
            float(e.get("estimated_ewaste_diverted_kg") or 0.0)
            if e["action"] != "Recycled"
            else 0.0
            for e in entries
        )
        if diverted_kg == 0.0:
            diverted_kg = sum(
                float(e["weight"])
                for e in entries
                if e["action"] in {"Repaired", "Reused", "Donated", "Resold"}
            )

        recycled_kg = sum(float(e["weight"]) for e in entries if e["action"] == "Recycled")
        co2_total_kg = sum(float(e.get("estimated_co2_saved_kg") or 0.0) for e in entries)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            render_kpi_card("Reused / Donated / Resold", reused_count, "Units kept in use", FOREST_DARK)
        with k2:
            render_kpi_card("Devices Repaired", repaired_count, "Units restored", "#D97706")
        with k3:
            render_kpi_card("Devices Recycled", recycled_count, f"{recycled_kg:.1f} kg processed", "#2B4C65")
        with k4:
            render_kpi_card("Est. E-Waste Diverted", f"{diverted_kg:.1f} kg", "Via lifespan extension", FOREST_MID)
        with k5:
            render_kpi_card("Est. CO2e Impact", f"{co2_total_kg:.1f} kg", "Category model estimate", LIME_ACCENT)

        df = pd.DataFrame(entries)
        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("Weight by Lifecycle Action (kg)")
            by_action = df.groupby("action", as_index=False)["weight"].sum()
            fig_a = px.bar(
                by_action,
                x="action",
                y="weight",
                text_auto=".2f",
                color="action",
                color_discrete_sequence=CHART_PALETTE,
                labels={"action": "Action", "weight": "Weight (kg)"},
            )
            fig_a.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
            )
            st.plotly_chart(fig_a, use_container_width=True)

        with ch2:
            st.subheader("Estimated CO2e Avoided by Category (kg)")
            by_cat = df.groupby("device", as_index=False)["estimated_co2_saved_kg"].sum()
            fig_c = px.bar(
                by_cat,
                x="device",
                y="estimated_co2_saved_kg",
                text_auto=".1f",
                color="device",
                color_discrete_sequence=CHART_PALETTE,
                labels={"device": "Category", "estimated_co2_saved_kg": "Est. CO2e (kg)"},
            )
            fig_c.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
            )
            st.plotly_chart(fig_c, use_container_width=True)

        st.subheader("Saved Impact Records")
        export_df = pd.DataFrame(
            [
                {
                    "ID": e["id"],
                    "Device ID": e.get("device_id"),
                    "Device Name": e.get("linked_device_name") or e.get("device_name") or e["device"],
                    "Category": e["device"],
                    "Action": e["action"],
                    "Weight (kg)": e["weight"],
                    "Est. E-Waste Diverted (kg)": e.get("estimated_ewaste_diverted_kg") or 0.0,
                    "Est. CO2e Impact (kg)": e.get("estimated_co2_saved_kg") or 0.0,
                    "Notes": e.get("notes") or "",
                    "Recorded At": e.get("recorded_at") or "",
                }
                for e in entries
            ]
        )
        st.download_button(
            "Download Impact Report (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="wipewise_environmental_impact.csv",
            mime="text/csv",
            key="download_impact_csv",
        )

        for e in entries:
            dev_label = e.get("linked_device_name") or e.get("device_name") or e["device"]
            st.markdown(
                f"""
                <div class="ww-card" style="padding:0.85rem 1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <strong>#{e['id']} — {html.escape(dev_label)}</strong>
                            <span style="color:#52606D;">({html.escape(e['device'])})</span>
                            &nbsp;{badge_html(e['action'])}
                        </div>
                        <span style="font-weight:600; color:#1B4332;">
                            {float(e['weight']):.2f} kg · Est. {float(e.get('estimated_co2_saved_kg') or 0.0):.1f} kg CO2e
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        render_empty_state(
            "No Environmental Impact Records Yet",
            "Log your first repaired, reused, donated, resold, or recycled device above.",
        )

    st.divider()
    with st.expander("📐 How Estimates Are Calculated (Assumptions & Formulas)"):
        st.write(
            "WipeWise separates **lifespan extension** (Repair, Reuse, Donation, Resale) from "
            "**end-of-life material recovery** (Recycling):"
        )
        st.markdown(
            "- **E-Waste Diverted (kg):** Equals reported weight for Repaired, Reused, Donated, or Resold devices "
            "(Recycling weight is tracked separately so recycling is not conflated with reuse diversion).\n"
            "- **Estimated CO2e Avoided (kg):** `Weight (kg) × Category Factor (kg CO2e/kg) × Action Multiplier`.\n"
            "- **Recycling Recovery Estimate:** `Weight (kg) × 2.5 kg CO2e/kg` for basic material recovery."
        )
        st.dataframe(pd.DataFrame(get_assumptions_table()), use_container_width=True, hide_index=True)

    with st.expander("♻️ Responsible E-Waste Disposal Guide"):
        st.markdown(
            "- **Check Right-to-Repair & Local Refurbishers First:** Many slow devices only need an SSD or battery swap.\n"
            "- **Protect Personal Data Before Hand-off:** Always use Data Safety Shield and log Sanitization Records.\n"
            "- **Never Trash Lithium Batteries:** Swollen or dead batteries pose fire hazards in municipal waste streams; "
            "use certified e-waste or battery drop-off facilities (e.g., R2v3 / e-Stewards certified recyclers where available)."
        )
