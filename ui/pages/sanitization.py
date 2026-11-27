"""Sanitization Records page with NIST SP 800-88 Rev. 2 concept tagging and exports."""

from __future__ import annotations

from datetime import date
import html
import json
import pandas as pd
import streamlit as st

from database.db import (
    add_lifecycle_event,
    add_sanitization_record,
    format_device_label,
    list_devices,
    list_sanitization_records,
)
from ui.styles import badge_html, render_empty_state, render_page_header

STORAGE_TYPES = [
    "SSD / NVMe",
    "HDD (Magnetic)",
    "Mobile Flash / eMMC / UFS",
    "Removable Media (SD / USB)",
    "Other / Unknown",
]

SANITIZATION_METHODS = [
    "Cryptographic Erase (CE)",
    "Firmware Secure Erase (ATA / NVMe Sanitize)",
    "Full-Disk Overwrite (HDD)",
    "Encrypted Factory Reset (Mobile OS)",
    "Physical Destruction (Shredding / Disintegration)",
    "Authorized Recycler Hand-off (Pending Destruction)",
    "Not Yet Performed / Planned",
]

NIST_CONCEPTS = [
    "Clear (Logical overwrite / reset)",
    "Purge (Cryptographic Erase / Firmware Sanitize)",
    "Destroy (Physical shredding / disintegration)",
    "Not Applicable / Planned",
]

VERIFICATION_STATUSES = [
    "Not started",
    "User reported",
    "Documented",
    "Independently verified",
]


def render() -> None:
    """Render the database-backed Sanitization Records management page."""
    render_page_header(
        title="Sanitization Records",
        subtitle=(
            "Maintain honest, auditable records of data sanitization activities per device, "
            "referencing NIST SP 800-88 Rev. 2 concepts without overstating verification."
        ),
        kicker="Data Sanitization & Evidence Log",
    )

    st.info(
        "Honesty & Reference Notice: WipeWise uses NIST SP 800-88 Rev. 2 terminology (Clear, Purge, Destroy) "
        "as an educational categorization reference only. Recording an entry here does NOT constitute "
        "NIST compliance certification or independent verification unless backed by actual third-party evidence."
    )

    devices = list_devices()

    if not devices:
        render_empty_state(
            "Register a Device First",
            "Create a device on the Device Assessment or Lifecycle Passport page before logging sanitization records.",
        )
        return

    st.subheader("Log a Sanitization Record")
    with st.form("sanitization_record_form"):
        c1, c2 = st.columns(2)
        with c1:
            selected_device = st.selectbox(
                "Associated Device *",
                options=devices,
                format_func=format_device_label,
            )
            sanitization_date = st.date_input(
                "Sanitization Date *",
                value=date.today(),
            )
            storage_type = st.selectbox("Storage / Media Type *", STORAGE_TYPES)
            method = st.selectbox("Sanitization Method *", SANITIZATION_METHODS)

        with c2:
            nist_category = st.selectbox(
                "NIST SP 800-88 Rev. 2 Reference Concept",
                NIST_CONCEPTS,
            )
            verification_status = st.selectbox(
                "Verification Status *",
                VERIFICATION_STATUSES,
                help=(
                    "'Documented' requires supporting notes or an evidence reference. "
                    "'Independently verified' requires an external report/certificate reference."
                ),
            )
            responsible_person = st.text_input(
                "Responsible Person / Source of Record *",
                placeholder="e.g., Device Owner, IT Admin (A. Patel), Certified Recycler Inc.",
            )
            evidence_reference = st.text_input(
                "Evidence Reference / Certificate ID",
                placeholder="e.g., Wipe log #2026-041, Recycler Certificate #RC-882",
            )

        notes = st.text_area(
            "Supporting Notes",
            placeholder="Tool used (e.g., nvme sanitize, PartedMagic, OEM reset), outcome observations...",
        )

        save_clicked = st.form_submit_button(
            "Save Sanitization Record",
            use_container_width=True,
        )

    if save_clicked:
        clean_person = responsible_person.strip()
        clean_ref = evidence_reference.strip()
        clean_notes = notes.strip()

        if not clean_person:
            st.error("Please enter the Responsible Person or Source of Record.")
        elif verification_status == "Independently verified" and not clean_ref:
            st.error(
                "An 'Independently verified' status requires an Evidence Reference (e.g., certificate ID or verification report)."
            )
        elif verification_status == "Documented" and not (clean_ref or clean_notes):
            st.error(
                "A 'Documented' status requires either an Evidence Reference or Supporting Notes describing the record."
            )
        else:
            device_label = selected_device.get("device_name") or selected_device["device"]
            rec_id = add_sanitization_record(
                device=device_label,
                storage_type=storage_type,
                method=method,
                verification=verification_status,
                date=sanitization_date.isoformat(),
                notes=clean_notes,
                device_id=selected_device["id"],
                responsible_person=clean_person,
                record_source=clean_person,
                evidence_reference=clean_ref,
                nist_category=nist_category,
            )
            add_lifecycle_event(
                device_id=selected_device["id"],
                event_type="Sanitization recorded",
                event_date=sanitization_date.isoformat(),
                details=(
                    f"Sanitization #{rec_id}: {method} on {storage_type} — "
                    f"Status: {verification_status} (Responsible: {clean_person})."
                ),
                evidence_reference=clean_ref,
            )
            st.success(
                f"Sanitization Record #{rec_id} saved for {format_device_label(selected_device)}."
            )
            st.rerun()

    st.divider()
    st.subheader("Saved Sanitization Records")

    f1, f2 = st.columns(2)
    with f1:
        device_filter_options = [{"id": None, "label": "All Devices"}] + [
            {"id": d["id"], "label": format_device_label(d)} for d in devices
        ]
        selected_filter_device = st.selectbox(
            "Filter by Device",
            options=device_filter_options,
            format_func=lambda opt: opt["label"],
            key="sanit_filter_device",
        )
    with f2:
        ver_filter = st.selectbox(
            "Filter by Verification Status",
            ["All"] + VERIFICATION_STATUSES,
            key="sanit_filter_ver",
        )

    records = list_sanitization_records(
        device_id=selected_filter_device["id"],
        verification_filter=ver_filter,
    )

    if records:
        export_df = pd.DataFrame(
            [
                {
                    "Record ID": r["id"],
                    "Device ID": r.get("device_id"),
                    "Device": r.get("linked_device_name") or r["device"],
                    "Date": r["date"],
                    "Storage Type": r["storage_type"],
                    "Method": r["method"],
                    "NIST SP 800-88 Rev.2 Concept": r.get("nist_category") or "",
                    "Verification Status": r["verification"],
                    "Responsible Person / Source": r.get("responsible_person") or "",
                    "Evidence Reference": r.get("evidence_reference") or "",
                    "Notes": r.get("notes") or "",
                }
                for r in records
            ]
        )
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download Sanitization Log (CSV)",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name="wipewise_sanitization_records.csv",
                mime="text/csv",
                key="download_sanit_csv",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download Sanitization Log (JSON)",
                data=json.dumps(records, indent=2).encode("utf-8"),
                file_name="wipewise_sanitization_records.json",
                mime="application/json",
                key="download_sanit_json",
                use_container_width=True,
            )

        for r in records:
            dev_title = r.get("linked_device_name") or r["device"]
            dev_id_str = f"Device #{r['device_id']}" if r.get("device_id") else "Unlinked"
            st.markdown(
                f"""
                <div class="ww-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <strong>#{r['id']} — {html.escape(dev_title)}</strong>
                            <span style="color:#52606D; font-size:0.86rem;">({html.escape(dev_id_str)} · {html.escape(r['date'])})</span>
                        </div>
                        {badge_html(r['verification'])}
                    </div>
                    <div style="margin-top:0.45rem; font-size:0.9rem; color:#1F2933;">
                        <strong>Method:</strong> {html.escape(r['method'])} &nbsp;|&nbsp;
                        <strong>Storage:</strong> {html.escape(r['storage_type'])} &nbsp;|&nbsp;
                        <strong>Reference Concept:</strong> {html.escape(r.get('nist_category') or 'Not specified')}
                    </div>
                    <div style="margin-top:0.3rem; font-size:0.86rem; color:#52606D;">
                        <strong>Responsible / Source:</strong> {html.escape(r.get('responsible_person') or 'Not provided')} &nbsp;|&nbsp;
                        <strong>Evidence Ref:</strong> {html.escape(r.get('evidence_reference') or 'None')}
                    </div>
                    <div style="margin-top:0.35rem; font-size:0.88rem; color:#1F2933;">
                        {html.escape(r.get('notes') or 'No supporting notes.')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        render_empty_state(
            "No Sanitization Records Found",
            "Log a sanitization record above or broaden your device/status filters.",
        )
