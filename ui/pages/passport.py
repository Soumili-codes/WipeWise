"""Digital Device Lifecycle Passport page with per-device isolation and export."""

from __future__ import annotations

from datetime import date
import html
import json
import streamlit as st

from database.db import (
    add_device,
    add_lifecycle_event,
    format_device_label,
    get_device_by_id,
    get_safety_checklist,
    list_assessments,
    list_devices,
    list_impact_records,
    list_lifecycle_events,
    list_sanitization_records,
    update_device,
)
from services.assessment_engine import DEVICE_CATEGORIES
from ui.styles import badge_html, render_empty_state, render_page_header

LIFECYCLE_STATUSES = [
    "In Use",
    "Assessed",
    "Under Repair",
    "Ready for Reuse",
    "Ready for Donation",
    "Ready for Resale",
    "Reused",
    "Donated",
    "Resold",
    "Ready for Recycling",
    "Recycled",
]


def _build_markdown_passport(
    device: dict,
    assessments: list[dict],
    sanitizations: list[dict],
    events: list[dict],
    impacts: list[dict],
    checklist: dict | None,
) -> str:
    """Build a portable Markdown summary of a single device's Lifecycle Passport."""
    lines = [
        f"# WipeWise Device Lifecycle Passport — #{device['id']} {device.get('device_name') or device['device']}",
        "",
        f"- **Category:** {device['device']}",
        f"- **Brand:** {device.get('brand') or 'Not provided'}",
        f"- **Model:** {device.get('model') or 'Not provided'}",
        f"- **Serial / Asset ID:** {device.get('serial_or_asset_id') or 'Not provided'}",
        f"- **Lifecycle Status:** {device.get('status')}",
        f"- **Current Recommendation:** {device.get('current_recommendation') or 'Not assessed'}",
        f"- **Notes:** {device.get('notes') or 'None'}",
        "",
        "## Assessments",
    ]
    if assessments:
        for a in assessments:
            lines.append(
                f"- **{a['assessed_at'][:10]}** — Recommendation: **{a['recommendation']}** "
                f"(Age: {a['device_age']}, Physical: {a['physical_condition']}, Functional: {a['functional_condition']})"
            )
    else:
        lines.append("- No assessments recorded.")

    lines.append("")
    lines.append("## Data Safety Shield")
    if checklist:
        lines.append(
            f"- Purpose: {checklist['purpose']} | Storage: {checklist['storage_type']} | "
            f"Completed: {checklist['completed_count']}/{checklist['total_count']} (User-reported)"
        )
    else:
        lines.append("- Checklist not saved for this device.")

    lines.append("")
    lines.append("## Sanitization Records")
    if sanitizations:
        for s in sanitizations:
            lines.append(
                f"- **{s['date']}** — {s['storage_type']} | {s['method']} | "
                f"Status: **{s['verification']}** | Ref: {s.get('evidence_reference') or 'None'}"
            )
    else:
        lines.append("- No sanitization records linked to this device.")

    lines.append("")
    lines.append("## Lifecycle Timeline")
    if events:
        for e in events:
            lines.append(
                f"- **{e['event_date']}** — {e['event_type']}: {e['details']} "
                f"(Ref: {e.get('evidence_reference') or 'None'})"
            )
    else:
        lines.append("- No lifecycle events recorded.")

    lines.append("")
    lines.append("## Environmental Impact Estimates")
    if impacts:
        for i in impacts:
            lines.append(
                f"- {i['action']}: {float(i['weight']):.2f} kg "
                f"(Est. CO2e: {float(i.get('estimated_co2_saved_kg') or 0.0):.2f} kg)"
            )
    else:
        lines.append("- No impact records linked to this device.")

    lines.extend(
        [
            "",
            "---",
            "Note: WipeWise Passport records are user-maintained. Sanitization verification and environmental "
            "impact estimates depend on supporting documentation and standard category assumptions.",
        ]
    )
    return "\n".join(lines)


def render() -> None:
    """Render the Digital Device Lifecycle Passport registry and device inspector."""
    render_page_header(
        title="Digital Device Lifecycle Passport",
        subtitle=(
            "Maintain a persistent, device-isolated record covering assessments, Data Safety Shield status, "
            "sanitization records, lifecycle events, and environmental impact."
        ),
        kicker="Centralized Device Record",
    )

    with st.expander("➕ Register a New Device Passport", expanded=False):
        with st.form("passport_register_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input(
                    "Device Name *",
                    placeholder="e.g., Lab Dell OptiPlex, Mom's Galaxy S21",
                )
                new_category = st.selectbox("Device Category", DEVICE_CATEGORIES)
                new_brand = st.text_input("Brand / Manufacturer", placeholder="e.g., Apple, Lenovo")
            with c2:
                new_model = st.text_input("Model Name", placeholder="e.g., MacBook Pro 14")
                new_serial = st.text_input(
                    "Asset Tag / Serial Reference (Optional)",
                    placeholder="Optional internal tag (avoid sensitive full serials if shared)",
                )
                new_status = st.selectbox("Current Lifecycle Status", LIFECYCLE_STATUSES)

            new_notes = st.text_area(
                "Initial Notes (Optional)",
                placeholder="Purchase year, RAM/storage specs, cosmetic notes...",
            )
            create_clicked = st.form_submit_button("Create Device Passport", use_container_width=True)

        if create_clicked:
            if not new_name.strip():
                st.error("Device Name is required so each Passport stays clearly identifiable.")
            else:
                existing = list_devices(search=new_name.strip())
                exact_dup = any(
                    (d.get("device_name") or "").strip().lower() == new_name.strip().lower()
                    and (d.get("device") or "") == new_category
                    and (d.get("brand") or "").strip().lower() == new_brand.strip().lower()
                    and (d.get("model") or "").strip().lower() == new_model.strip().lower()
                    for d in existing
                )
                if exact_dup:
                    st.warning(
                        f"A device named '{new_name.strip()}' with the same category and brand/model already exists."
                    )
                else:
                    new_id = add_device(
                        device=new_category,
                        brand=new_brand,
                        model=new_model,
                        status=new_status,
                        notes=new_notes,
                        device_name=new_name,
                        serial_or_asset_id=new_serial,
                    )
                    add_lifecycle_event(
                        device_id=new_id,
                        event_type="Device registered",
                        event_date=date.today().isoformat(),
                        details=f"Created Device Passport #{new_id} ({new_name.strip()}, status: {new_status}).",
                    )
                    st.success(f"Created Device Passport #{new_id} for '{new_name.strip()}'.")
                    st.rerun()

    st.divider()
    st.subheader("Search & Inspect Device Passports")

    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        search_term = st.text_input(
            "Search Devices",
            placeholder="Search by name, brand, model, or asset ID...",
            key="passport_search",
        )
    with f2:
        cat_filter = st.selectbox(
            "Category",
            ["All"] + DEVICE_CATEGORIES,
            key="passport_cat_filter",
        )
    with f3:
        status_filter = st.selectbox(
            "Lifecycle Status",
            ["All"] + LIFECYCLE_STATUSES,
            key="passport_status_filter",
        )

    filtered_devices = list_devices(
        search=search_term,
        category=cat_filter,
        status=status_filter,
    )

    if not filtered_devices:
        render_empty_state(
            "No Matching Device Passports",
            "Register a device above, complete a Device Assessment, or adjust your search filters.",
        )
        return

    selected_device = st.selectbox(
        f"Select Device ({len(filtered_devices)} matching)",
        options=filtered_devices,
        format_func=format_device_label,
        key="passport_selected_device",
    )

    device = get_device_by_id(selected_device["id"]) or selected_device
    device_id = device["id"]

    assessments = list_assessments(device_id=device_id)
    sanitizations = list_sanitization_records(device_id=device_id)
    events = list_lifecycle_events(device_id=device_id, ascending=False)
    impacts = list_impact_records(device_id=device_id)
    checklist = get_safety_checklist(device_id)

    rec_badge = (
        badge_html(device["current_recommendation"])
        if device.get("current_recommendation")
        else badge_html("Not started")
    )
    status_badge = badge_html(device.get("status") or "In Use")

    st.markdown(
        f"""
        <div class="ww-card" style="border-left: 5px solid #1B4332;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.75rem;">
                <div>
                    <div style="font-size:0.78rem; text-transform:uppercase; letter-spacing:0.06em; color:#52606D; font-weight:700;">
                        Passport #{device['id']} · {html.escape(device['device'])}
                    </div>
                    <h2 style="margin:0.2rem 0 0.35rem; color:#1B4332;">
                        {html.escape(device.get('device_name') or device['device'])}
                    </h2>
                    <div style="color:#52606D; font-size:0.9rem;">
                        Brand: <strong>{html.escape(device.get('brand') or '—')}</strong> &nbsp;|&nbsp;
                        Model: <strong>{html.escape(device.get('model') or '—')}</strong> &nbsp;|&nbsp;
                        Asset ID: <strong>{html.escape(device.get('serial_or_asset_id') or '—')}</strong>
                    </div>
                </div>
                <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
                    {status_badge}
                    {rec_badge}
                </div>
            </div>
            <p style="margin:0.75rem 0 0; color:#1F2933; font-size:0.92rem;">
                <strong>Notes:</strong> {html.escape(device.get('notes') or 'No lifecycle notes recorded.')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Export Passport
    passport_payload = {
        "device": device,
        "assessments": assessments,
        "safety_checklist": checklist,
        "sanitization_records": sanitizations,
        "lifecycle_events": events,
        "impact_records": impacts,
    }
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Export Device Passport (JSON)",
            data=json.dumps(passport_payload, indent=2).encode("utf-8"),
            file_name=f"wipewise_passport_{device_id}.json",
            mime="application/json",
            key=f"export_passport_json_{device_id}",
            use_container_width=True,
        )
    with dl2:
        md_doc = _build_markdown_passport(
            device, assessments, sanitizations, events, impacts, checklist
        )
        st.download_button(
            "Export Device Passport (Markdown)",
            data=md_doc.encode("utf-8"),
            file_name=f"wipewise_passport_{device_id}.md",
            mime="text/markdown",
            key=f"export_passport_md_{device_id}",
            use_container_width=True,
        )

    tab_edit, tab_assess, tab_sanitize, tab_shield, tab_events, tab_impact = st.tabs(
        [
            "✏️ Update Details",
            f"🔍 Assessments ({len(assessments)})",
            f"🧹 Sanitization ({len(sanitizations)})",
            "🔐 Safety Shield",
            f"🕒 Timeline ({len(events)})",
            f"🌍 Impact ({len(impacts)})",
        ]
    )

    with tab_edit:
        with st.form(f"edit_device_form_{device_id}"):
            ec1, ec2 = st.columns(2)
            with ec1:
                edit_name = st.text_input("Device Name *", value=device.get("device_name") or "")
                edit_cat_idx = (
                    DEVICE_CATEGORIES.index(device["device"])
                    if device["device"] in DEVICE_CATEGORIES
                    else 0
                )
                edit_cat = st.selectbox("Category", DEVICE_CATEGORIES, index=edit_cat_idx)
                edit_brand = st.text_input("Brand", value=device.get("brand") or "")
            with ec2:
                edit_model = st.text_input("Model", value=device.get("model") or "")
                edit_serial = st.text_input(
                    "Asset / Serial Reference",
                    value=device.get("serial_or_asset_id") or "",
                )
                cur_status = device.get("status") or "In Use"
                status_choices = (
                    LIFECYCLE_STATUSES
                    if cur_status in LIFECYCLE_STATUSES
                    else [cur_status] + LIFECYCLE_STATUSES
                )
                edit_status = st.selectbox(
                    "Lifecycle Status",
                    status_choices,
                    index=status_choices.index(cur_status),
                )
            edit_notes = st.text_area("Lifecycle Notes", value=device.get("notes") or "")
            update_btn = st.form_submit_button("Save Passport Updates", use_container_width=True)

        if update_btn:
            if not edit_name.strip():
                st.error("Device Name cannot be empty.")
            else:
                old_status = device.get("status")
                update_device(
                    device_id,
                    device=edit_cat,
                    device_name=edit_name,
                    brand=edit_brand,
                    model=edit_model,
                    serial_or_asset_id=edit_serial,
                    status=edit_status,
                    notes=edit_notes,
                )
                if edit_status != old_status:
                    add_lifecycle_event(
                        device_id=device_id,
                        event_type="Other",
                        event_date=date.today().isoformat(),
                        details=f"Lifecycle status updated from '{old_status}' to '{edit_status}'.",
                    )
                st.success("Device Passport updated successfully.")
                st.rerun()

    with tab_assess:
        if assessments:
            for a in assessments:
                st.markdown(
                    f"""
                    <div class="ww-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>{html.escape(a['assessed_at'][:10])} — {html.escape(a['device_age'])}</strong>
                            {badge_html(a['recommendation'])}
                        </div>
                        <p style="margin:0.45rem 0 0.25rem; color:#1F2933;">{html.escape(a['explanation'])}</p>
                        <div style="font-size:0.84rem; color:#52606D;">
                            Physical: {html.escape(a['physical_condition'])} ·
                            Functional: {html.escape(a['functional_condition'])} ·
                            Battery: {html.escape(a['battery_condition'])} ·
                            Repairability: {html.escape(a['repair_feasibility'])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            render_empty_state(
                "No Assessments for This Device",
                "Run an assessment on the Device Assessment page and select this device to record it here.",
            )

    with tab_sanitize:
        if sanitizations:
            for s in sanitizations:
                st.markdown(
                    f"""
                    <div class="ww-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                            <strong>{html.escape(s['date'])} · {html.escape(s['method'])}</strong>
                            {badge_html(s['verification'])}
                        </div>
                        <div style="margin-top:0.35rem; font-size:0.88rem; color:#52606D;">
                            Storage: {html.escape(s['storage_type'])} ·
                            Responsible: {html.escape(s.get('responsible_person') or 'Not specified')} ·
                            Evidence Ref: {html.escape(s.get('evidence_reference') or 'None')}
                        </div>
                        <p style="margin:0.35rem 0 0; color:#1F2933; font-size:0.9rem;">
                            {html.escape(s.get('notes') or 'No additional notes.')}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            render_empty_state(
                "No Sanitization Records for This Device",
                "Log data sanitization details on the Sanitization Records page to attach them to this Passport.",
            )

    with tab_shield:
        if checklist:
            st.write(
                f"**Intended Purpose:** {checklist['purpose']} · "
                f"**Storage Type:** {checklist['storage_type']}"
            )
            st.progress(
                checklist["completed_count"] / max(1, checklist["total_count"])
            )
            st.write(
                f"**{checklist['completed_count']} of {checklist['total_count']}** preparation steps checked "
                f"(User-reported; last updated {checklist['updated_at'][:10]})."
            )
            if checklist["acknowledgment_confirmed"]:
                st.info("Owner acknowledged that checklist completion does not verify erasure.")
        else:
            render_empty_state(
                "Data Safety Shield Not Started",
                "Visit Data Safety Shield and select this device to track and save pre-transfer preparation steps.",
            )

    with tab_events:
        if events:
            for e in events:
                st.markdown(
                    f"""
                    <div class="ww-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            {badge_html(e['event_type'])}
                            <span style="font-size:0.84rem; color:#52606D;">{html.escape(e['event_date'])}</span>
                        </div>
                        <p style="margin:0.45rem 0 0.2rem; color:#1F2933;">{html.escape(e.get('details') or '')}</p>
                        <div style="font-size:0.82rem; color:#52606D;">
                            Evidence Ref: {html.escape(e.get('evidence_reference') or 'Not provided')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            render_empty_state(
                "No Timeline Events Yet",
                "Events from assessments, sanitization, and manual entries will appear here.",
            )

    with tab_impact:
        if impacts:
            total_w = sum(float(i["weight"]) for i in impacts)
            total_co2 = sum(float(i.get("estimated_co2_saved_kg") or 0.0) for i in impacts)
            st.write(
                f"**Total Reported Weight:** {total_w:.2f} kg · "
                f"**Estimated CO2e Impact:** {total_co2:.2f} kg (model estimate)"
            )
            for i in impacts:
                st.markdown(
                    f"- **{i['action']}** ({float(i['weight']):.2f} kg) — Est. CO2e: {float(i.get('estimated_co2_saved_kg') or 0.0):.2f} kg"
                )
        else:
            render_empty_state(
                "No Impact Records Linked",
                "Link an entry in Impact Tracker to this device to view its estimated environmental impact.",
            )
