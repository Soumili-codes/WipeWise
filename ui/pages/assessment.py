"""Device Assessment page with deterministic rule engine and persistent history."""

from __future__ import annotations

from datetime import date
import html
import pandas as pd
import streamlit as st

from database.db import (
    add_assessment,
    add_device,
    add_lifecycle_event,
    format_device_label,
    list_assessments,
    list_devices,
    update_device,
)
from services.assessment_engine import (
    BATTERY_CONDITIONS,
    DEVICE_AGES,
    DEVICE_CATEGORIES,
    FUNCTIONAL_CONDITIONS,
    PHYSICAL_CONDITIONS,
    REPAIR_FEASIBILITIES,
    evaluate_device,
)
from ui.styles import badge_html, render_empty_state, render_page_header


def render() -> None:
    """Render the Device Assessment form, rule-based output, and history."""
    render_page_header(
        title="Device Assessment",
        subtitle=(
            "Evaluate hardware condition, battery health, and repair feasibility using "
            "transparent lifecycle rules to decide whether to Repair, Reuse, Donate, Resell, or Recycle."
        ),
        kicker="Rule-Based Decision Support",
    )

    st.info(
        "This tool uses transparent, deterministic rules (not AI) to provide a preliminary "
        "lifecycle recommendation. Always inspect safety risks and back up important data before acting."
    )

    devices = list_devices()

    target_mode = st.radio(
        "Assessment Target",
        options=(
            ["Register as a new device", "Assess an existing registered device"]
            if devices
            else ["Register as a new device"]
        ),
        horizontal=True,
        key="assess_target_mode",
    )

    selected_existing: dict | None = None
    if target_mode == "Assess an existing registered device" and devices:
        selected_existing = st.selectbox(
            "Select Registered Device",
            options=devices,
            format_func=format_device_label,
            key="assess_existing_device_select",
        )

    default_name = (
        selected_existing.get("device_name", "") if selected_existing else ""
    )
    default_cat = (
        selected_existing.get("device", "Laptop") if selected_existing else "Laptop"
    )
    cat_index = (
        DEVICE_CATEGORIES.index(default_cat)
        if default_cat in DEVICE_CATEGORIES
        else 0
    )
    default_brand = selected_existing.get("brand", "") if selected_existing else ""
    default_model = selected_existing.get("model", "") if selected_existing else ""
    form_key_suffix = str(selected_existing["id"]) if selected_existing else "new"

    with st.form(f"assessment_form_{form_key_suffix}"):
        col1, col2 = st.columns(2)
        with col1:
            device_name = st.text_input(
                "Device Name *",
                value=default_name,
                placeholder="e.g., Home ThinkPad X1 or Personal Pixel 7",
            )
            device_category = st.selectbox(
                "Device Category",
                DEVICE_CATEGORIES,
                index=cat_index,
            )
            brand = st.text_input(
                "Brand (Optional)",
                value=default_brand,
                placeholder="e.g., Dell, Apple, Lenovo, Samsung",
            )
            model = st.text_input(
                "Model (Optional)",
                value=default_model,
                placeholder="e.g., Latitude 5420, iPhone 13",
            )
            device_age = st.selectbox("Device Age", DEVICE_AGES)

        with col2:
            physical_condition = st.selectbox(
                "Physical Condition",
                PHYSICAL_CONDITIONS,
            )
            functional_condition = st.selectbox(
                "Functional Condition",
                FUNCTIONAL_CONDITIONS,
            )
            battery_condition = st.selectbox(
                "Battery Condition (if applicable)",
                BATTERY_CONDITIONS,
            )
            repair_feasibility = st.selectbox(
                "Repair Feasibility",
                REPAIR_FEASIBILITIES,
            )
            notes = st.text_area(
                "Additional Notes (Optional)",
                placeholder="Screen cracks, missing charger, slow HDD, liquid exposure, etc.",
                height=86,
            )

        submitted = st.form_submit_button(
            "Analyze Device Condition",
            use_container_width=True,
        )

    if submitted:
        clean_name = device_name.strip()
        clean_brand = brand.strip()
        clean_model = model.strip()
        if not clean_name:
            st.error("Please enter a Device Name so this assessment can be tracked accurately.")
        else:
            evaluation = evaluate_device(
                device_category=device_category,
                device_age=device_age,
                physical_condition=physical_condition,
                functional_condition=functional_condition,
                battery_condition=battery_condition,
                repair_feasibility=repair_feasibility,
            )
            st.session_state["current_assessment"] = {
                "target_device_id": selected_existing["id"] if selected_existing else None,
                "device_name": clean_name,
                "device_category": device_category,
                "brand": clean_brand,
                "model": clean_model,
                "brand_model": " ".join(p for p in [clean_brand, clean_model] if p),
                "device_age": device_age,
                "physical_condition": physical_condition,
                "functional_condition": functional_condition,
                "battery_condition": battery_condition,
                "repair_feasibility": repair_feasibility,
                "notes": notes.strip(),
                "recommendation": evaluation.recommendation,
                "suggested_status": evaluation.suggested_status,
                "explanation": evaluation.explanation,
                "factors": evaluation.factors,
                "next_steps": evaluation.next_steps,
                "safety_warning": evaluation.safety_warning,
            }
            st.session_state["current_assessment_saved"] = False

    if "current_assessment" in st.session_state:
        res = st.session_state["current_assessment"]
        st.divider()
        st.subheader("Assessment Result")

        if res.get("safety_warning"):
            st.error(res["safety_warning"])

        st.markdown(
            f"""
            <div class="ww-card" style="border-left:5px solid #1B4332;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                    <span style="font-size:1.15rem; font-weight:700; color:#1B4332;">
                        {html.escape(res['device_name'])} ({html.escape(res['device_category'])})
                    </span>
                    {badge_html(res['recommendation'])}
                </div>
                <p style="margin-top:0.65rem; color:#1F2933; font-size:0.98rem;">
                    {html.escape(res['explanation'])}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Why this recommendation was generated**")
            for factor in res["factors"]:
                st.markdown(f"- {factor}")

        with col_b:
            st.markdown("**Suggested Next Steps**")
            for step in res["next_steps"]:
                st.markdown(f"- {step}")

        st.warning(
            "Preliminary rule-based guidance only — not an AI diagnosis or a certified repair inspection."
        )

        already_saved = st.session_state.get("current_assessment_saved", False)
        if not already_saved:
            if st.button(
                "Save Assessment to Lifecycle Passport",
                key="save_assessment_to_passport_btn",
                type="primary",
            ):
                today_iso = date.today().isoformat()
                device_id = res["target_device_id"]
                summary_notes = (
                    f"Age: {res['device_age']} | Physical: {res['physical_condition']} | "
                    f"Functional: {res['functional_condition']} | Battery: {res['battery_condition']}"
                )
                if res["notes"]:
                    summary_notes += f" | Notes: {res['notes']}"

                if device_id is None:
                    device_id = add_device(
                        device=res["device_category"],
                        brand=res["brand"],
                        model=res["model"],
                        status=res["suggested_status"],
                        notes=res["notes"] or summary_notes,
                        device_name=res["device_name"],
                        current_recommendation=res["recommendation"],
                    )
                    add_lifecycle_event(
                        device_id=device_id,
                        event_type="Device registered",
                        event_date=today_iso,
                        details=f"Registered '{res['device_name']}' ({res['device_category']}) via Device Assessment.",
                    )
                else:
                    update_device(
                        device_id,
                        device=res["device_category"],
                        device_name=res["device_name"],
                        brand=res["brand"],
                        model=res["model"],
                        status=res["suggested_status"],
                        current_recommendation=res["recommendation"],
                    )

                add_assessment(
                    device_id=device_id,
                    device_name=res["device_name"],
                    device_category=res["device_category"],
                    brand_model=res["brand_model"],
                    device_age=res["device_age"],
                    physical_condition=res["physical_condition"],
                    functional_condition=res["functional_condition"],
                    battery_condition=res["battery_condition"],
                    repair_feasibility=res["repair_feasibility"],
                    recommendation=res["recommendation"],
                    explanation=res["explanation"],
                    factor_breakdown=res["factors"],
                    notes=res["notes"],
                )

                add_lifecycle_event(
                    device_id=device_id,
                    event_type="Assessment completed",
                    event_date=today_iso,
                    details=(
                        f"Assessed '{res['device_name']}' -> Recommendation: {res['recommendation']}. "
                        f"{summary_notes}"
                    ),
                )
                if res["recommendation"] == "Repair":
                    add_lifecycle_event(
                        device_id=device_id,
                        event_type="Repair recommended",
                        event_date=today_iso,
                        details=res["explanation"],
                    )

                st.session_state["current_assessment_saved"] = True
                st.success(
                    f"Assessment saved permanently to Lifecycle Passport (Device #{device_id})."
                )
                st.rerun()
        else:
            st.success("This assessment has been saved to the Lifecycle Passport and Timeline.")

    st.divider()
    st.subheader("Saved Assessment History")
    history = list_assessments()

    if history:
        f1, f2 = st.columns(2)
        with f1:
            rec_filter = st.selectbox(
                "Filter by Recommendation",
                ["All", "Repair", "Reuse", "Donate", "Resell", "Recycle"],
                key="assess_history_rec_filter",
            )
        with f2:
            cat_filter = st.selectbox(
                "Filter by Category",
                ["All"] + DEVICE_CATEGORIES,
                key="assess_history_cat_filter",
            )

        filtered = [
            item
            for item in history
            if (rec_filter == "All" or item["recommendation"] == rec_filter)
            and (cat_filter == "All" or item["device_category"] == cat_filter)
        ]

        if filtered:
            export_df = pd.DataFrame(
                [
                    {
                        "Assessment ID": item["id"],
                        "Device ID": item["device_id"],
                        "Device Name": item["device_name"],
                        "Category": item["device_category"],
                        "Brand / Model": item["brand_model"],
                        "Age": item["device_age"],
                        "Physical Condition": item["physical_condition"],
                        "Functional Condition": item["functional_condition"],
                        "Battery Condition": item["battery_condition"],
                        "Repair Feasibility": item["repair_feasibility"],
                        "Recommendation": item["recommendation"],
                        "Explanation": item["explanation"],
                        "Assessed At": item["assessed_at"],
                    }
                    for item in filtered
                ]
            )
            st.download_button(
                "Download Assessment History (CSV)",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name="wipewise_assessments.csv",
                mime="text/csv",
                key="download_assessments_csv",
            )

            for item in filtered:
                with st.expander(
                    f"#{item['id']} — {item['device_name']} ({item['device_category']}) · {item['recommendation']}"
                ):
                    st.markdown(
                        f"**Recommendation:** {badge_html(item['recommendation'])} "
                        f"&nbsp;|&nbsp; **Device ID:** #{item['device_id']} "
                        f"&nbsp;|&nbsp; **Assessed:** {item['assessed_at'][:10]}",
                        unsafe_allow_html=True,
                    )
                    st.write(item["explanation"])
                    st.caption(
                        f"Age: {item['device_age']} · Physical: {item['physical_condition']} · "
                        f"Functional: {item['functional_condition']} · Battery: {item['battery_condition']} · "
                        f"Repair Feasibility: {item['repair_feasibility']}"
                    )
                    if item.get("factors"):
                        st.markdown("**Rule Factors:**")
                        for factor in item["factors"]:
                            st.markdown(f"- {factor}")
                    if item.get("notes"):
                        st.write("**Notes:**", item["notes"])
        else:
            render_empty_state(
                "No Matching Assessments",
                "Try clearing your recommendation or category filter.",
            )
    else:
        render_empty_state(
            "No Assessments Recorded Yet",
            "Complete the form above to analyze a device and save its assessment to your Lifecycle Passport.",
        )
