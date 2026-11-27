"""Device Lifecycle Timeline page with filtering, ordering, and duplicate protection."""

from __future__ import annotations

from datetime import date
import html
import pandas as pd
import streamlit as st

from database.db import (
    add_lifecycle_event,
    format_device_label,
    list_devices,
    list_lifecycle_events,
)
from ui.styles import badge_html, render_empty_state, render_page_header

EVENT_TYPES = [
    "Device registered",
    "Assessment completed",
    "Repair recommended",
    "Repair completed",
    "Device reused or donated",
    "Device resold",
    "Sanitization recorded",
    "Device recycled",
    "Other",
]


def render() -> None:
    """Render the chronological Device Lifecycle Timeline page."""
    render_page_header(
        title="Device Lifecycle Timeline",
        subtitle=(
            "Record and inspect the chronological journey of every device from registration "
            "and assessment to repair, sanitization, reuse, donation, or recycling."
        ),
        kicker="Chronological Audit History",
    )

    st.info(
        "Timeline entries are user-reported or system-logged records from your WipeWise actions. "
        "Events with an Evidence Reference indicate supporting external documentation, not automatic verification."
    )

    devices = list_devices()
    if not devices:
        render_empty_state(
            "No Registered Devices Found",
            "Please add a device through Device Assessment or Lifecycle Passport before recording timeline events.",
        )
        return

    st.subheader("Add a Lifecycle Event")
    with st.form("lifecycle_event_form"):
        c1, c2 = st.columns(2)
        with c1:
            target_device = st.selectbox(
                "Select Device *",
                options=devices,
                format_func=format_device_label,
            )
            event_type = st.selectbox("Lifecycle Event Type *", EVENT_TYPES)
            event_date = st.date_input("Event Date *", value=date.today())
        with c2:
            details = st.text_area(
                "Event Details *",
                placeholder="Describe what occurred (e.g., Replaced battery at local shop, shipped to recycler)...",
                height=115,
            )
            evidence_ref = st.text_input(
                "Evidence Reference (Optional)",
                placeholder="Receipt #, repair ticket, donation letter, or wipe log reference",
            )

        submitted = st.form_submit_button("Save Lifecycle Event", use_container_width=True)

    if submitted:
        clean_details = details.strip()
        if not clean_details:
            st.error("Please enter details describing this lifecycle event.")
        else:
            event_id, created = add_lifecycle_event(
                device_id=target_device["id"],
                event_type=event_type,
                event_date=event_date.isoformat(),
                details=clean_details,
                evidence_reference=evidence_ref.strip(),
                allow_duplicate=False,
            )
            if not created:
                st.warning(
                    "An identical lifecycle event (same device, type, date, and details) already exists. "
                    "Duplicate submission was prevented."
                )
            else:
                st.success(
                    f"Lifecycle event #{event_id} saved for {format_device_label(target_device)}."
                )
                st.rerun()

    st.divider()
    st.subheader("Lifecycle History")

    f1, f2 = st.columns([2, 1])
    with f1:
        filter_options = [{"id": None, "label": "All Devices"}] + [
            {"id": d["id"], "label": format_device_label(d)} for d in devices
        ]
        selected_filter = st.selectbox(
            "Filter by Device",
            options=filter_options,
            format_func=lambda opt: opt["label"],
            key="timeline_filter_device",
        )
    with f2:
        sort_order = st.radio(
            "Chronological Order",
            options=["Newest First", "Oldest First (Chronological)"],
            horizontal=False,
            key="timeline_sort_order",
        )

    ascending = sort_order == "Oldest First (Chronological)"
    events = list_lifecycle_events(
        device_id=selected_filter["id"],
        ascending=ascending,
    )

    if events:
        export_df = pd.DataFrame(
            [
                {
                    "Event ID": e["id"],
                    "Device ID": e["device_id"],
                    "Device": e.get("device_name") or e["device"],
                    "Category": e["device"],
                    "Event Date": e["event_date"],
                    "Event Type": e["event_type"],
                    "Details": e.get("details") or "",
                    "Evidence Reference": e.get("evidence_reference") or "",
                }
                for e in events
            ]
        )
        st.download_button(
            "Download Timeline (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="wipewise_lifecycle_timeline.csv",
            mime="text/csv",
            key="download_timeline_csv",
        )

        for ev in events:
            dev_label = format_device_label(ev)
            ev_ref = ev.get("evidence_reference") or "Not provided"
            st.markdown(
                f"""
                <div class="ww-card" style="border-left:4px solid #52B788;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <strong style="color:#1B4332;">{html.escape(ev['event_date'])}</strong>
                            &nbsp;·&nbsp;
                            {badge_html(ev['event_type'])}
                            &nbsp;·&nbsp;
                            <span style="color:#52606D; font-size:0.9rem;">{html.escape(dev_label)}</span>
                        </div>
                        <span style="font-size:0.78rem; color:#6B7D75;">Event #{ev['id']}</span>
                    </div>
                    <p style="margin:0.5rem 0 0.25rem; color:#1F2933;">
                        {html.escape(ev.get('details') or '')}
                    </p>
                    <div style="font-size:0.82rem; color:#52606D;">
                        Evidence Reference: <strong>{html.escape(ev_ref)}</strong> ·
                        <em>User-reported / logged event</em>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        render_empty_state(
            "No Lifecycle Events Yet",
            "No events match the selected device filter. Add an event above to start building the timeline.",
        )
