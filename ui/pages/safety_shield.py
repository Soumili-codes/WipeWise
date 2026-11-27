"""Data Safety Shield page — persistent pre-transfer preparation checklist."""

from __future__ import annotations

import html
import streamlit as st

from database.db import (
    format_device_label,
    get_safety_checklist,
    list_devices,
    save_safety_checklist,
)
from ui.styles import badge_html, render_page_header

CHECKLIST_ITEMS: list[dict[str, str]] = [
    {
        "id": "backup_files",
        "title": "Back up important personal files and verify readability",
        "detail": "Copy documents, photos, SSH keys, and local app data to an encrypted backup drive or cloud account, then open sample files to verify integrity.",
    },
    {
        "id": "sign_out_accounts",
        "title": "Sign out of personal accounts and deauthorize software licenses",
        "detail": "Sign out of Apple ID, Google, Microsoft, browser profiles, password managers, VPNs, and licensed creative/work tools.",
    },
    {
        "id": "remove_associations",
        "title": "Remove device associations and check account recovery & device locks",
        "detail": "Disable Find My / Activation Lock / Factory Reset Protection (FRP), unenroll from MDM if permitted, and ensure MFA/recovery codes no longer rely solely on this device.",
    },
    {
        "id": "remove_external_media",
        "title": "Remove SIM cards, eSIM profiles, memory cards, and optical discs",
        "detail": "Physically eject SD cards, SIM trays, and USB dongles, and delete carrier eSIM profiles where applicable.",
    },
    {
        "id": "factory_reset_limits",
        "title": "Acknowledge factory reset limitations",
        "detail": "Understand that a standard OS factory reset alone may not guarantee unrecoverable destruction on unencrypted drives, failing media, or older storage architectures.",
    },
    {
        "id": "select_sanitization_method",
        "title": "Choose a sanitization method suited to the device's storage type",
        "detail": "Match the method (e.g., Cryptographic Erase, NVMe/ATA Sanitize, overwrite, or physical destruction) to SSD/NVMe, HDD, or mobile flash media.",
    },
    {
        "id": "retain_evidence",
        "title": "Record sanitization details and retain proof or documentation",
        "detail": "Log the date, storage type, method, responsible person, and any wipe log or recycler certificate in WipeWise Sanitization Records.",
    },
]

STORAGE_GUIDANCE: dict[str, dict[str, str]] = {
    "SSD / NVMe": {
        "nist": "Purge (Cryptographic Erase / NVMe Format / Sanitize) or Destroy",
        "note": (
            "Wear-leveling and over-provisioning on SSDs can prevent standard file deletion or "
            "single-file overwrites from reaching all flash blocks. Prefer hardware-level NVMe "
            "Sanitize, ATA Secure Erase, or full-disk encryption key destruction (Cryptographic Erase), "
            "or physical destruction for damaged drives."
        ),
    },
    "HDD (Magnetic)": {
        "nist": "Clear / Purge (Full-disk overwrite or ATA Secure Erase) or Destroy",
        "note": (
            "Magnetic hard drives respond well to full-sector overwrite or firmware ATA Secure Erase. "
            "If the drive is clicking or failing and cannot complete a full pass, physical destruction "
            "is recommended before recycling."
        ),
    },
    "Mobile Flash / eMMC / UFS": {
        "nist": "Purge (Encrypted Factory Reset + Key Zeroization) or Destroy",
        "note": (
            "Modern smartphones and tablets typically use hardware-backed file/full-disk encryption; "
            "removing accounts/locks first and resetting destroys the encryption key. Older unencrypted "
            "devices require physical destruction if sensitive data was stored."
        ),
    },
    "Removable Media (SD / USB)": {
        "nist": "Purge / Destroy",
        "note": (
            "Flash-based SD cards and USB drives rarely support reliable firmware sanitize commands. "
            "Because flash wear-leveling leaves remnants after quick formatting, physical shredding or "
            "destruction is safest for sensitive media."
        ),
    },
    "Hybrid / Unknown": {
        "nist": "Inspect storage architecture before selecting Clear, Purge, or Destroy",
        "note": (
            "Confirm whether the device uses an HDD, SSD, soldered eMMC, or dual drives so both "
            "volumes are addressed."
        ),
    },
}


def render() -> None:
    """Render the interactive Data Safety Shield preparation workflow."""
    render_page_header(
        title="Data Safety Shield",
        subtitle=(
            "Prepare your device responsibly before selling, donating, transferring, or recycling. "
            "Track preparation steps per device without mistaking a checklist for verified erasure."
        ),
        kicker="Pre-Transfer Data Protection",
    )

    st.warning(
        "Important Distinction: Completing this preparation checklist is USER-REPORTED ONLY. "
        "It does NOT prove that data has been securely erased, and a factory reset alone does not "
        "guarantee data destruction."
    )

    devices = list_devices()
    selected_device: dict | None = None
    saved_state: dict | None = None

    if devices:
        selected_device = st.selectbox(
            "Select Registered Device to Track Checklist Progress",
            options=devices,
            format_func=format_device_label,
            key="shield_device_select",
        )
        saved_state = get_safety_checklist(selected_device["id"])
    else:
        st.info(
            "No devices are registered yet. You can still preview the checklist below, or register a "
            "device on the Device Assessment or Lifecycle Passport page to save checklist progress."
        )

    purpose_options = ["Sell", "Donate", "Recycle", "Transfer / Give Away"]
    storage_options = list(STORAGE_GUIDANCE.keys())

    default_purpose = (
        saved_state["purpose"]
        if saved_state and saved_state.get("purpose") in purpose_options
        else "Sell"
    )
    default_storage = (
        saved_state["storage_type"]
        if saved_state and saved_state.get("storage_type") in storage_options
        else "SSD / NVMe"
    )

    c1, c2 = st.columns(2)
    device_key_suffix = str(selected_device["id"]) if selected_device else "preview"
    with c1:
        purpose = st.selectbox(
            "Intended Lifecycle Action",
            purpose_options,
            index=purpose_options.index(default_purpose),
            key=f"shield_purpose_{device_key_suffix}",
        )
    with c2:
        storage_type = st.selectbox(
            "Primary Storage / Media Type",
            storage_options,
            index=storage_options.index(default_storage),
            key=f"shield_storage_{device_key_suffix}",
        )

    guidance = STORAGE_GUIDANCE[storage_type]
    st.markdown(
        f"""
        <div class="ww-card" style="border-left:4px solid #2D6A4F;">
            <div style="font-weight:700; color:#1B4332;">
                Storage Guidance ({html.escape(storage_type)}) — NIST SP 800-88 Rev. 2 Concept: {html.escape(guidance['nist'])}
            </div>
            <p style="margin:0.4rem 0 0; color:#52606D; font-size:0.92rem;">
                {html.escape(guidance['note'])}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Preparation Checklist")
    saved_checks = saved_state.get("checklist_state", {}) if saved_state else {}
    current_checks: dict[str, bool] = {}

    for item in CHECKLIST_ITEMS:
        checked = st.checkbox(
            item["title"],
            value=bool(saved_checks.get(item["id"], False)),
            help=item["detail"],
            key=f"shield_chk_{device_key_suffix}_{item['id']}",
        )
        st.caption(item["detail"])
        current_checks[item["id"]] = checked

    completed = sum(1 for v in current_checks.values() if v)
    total = len(CHECKLIST_ITEMS)
    progress_ratio = completed / total

    st.divider()
    st.subheader("Preparation Progress & Verification Distinction")
    st.progress(progress_ratio)
    st.write(f"**{completed} of {total}** preparation steps marked complete (User-reported).")

    ack_default = bool(saved_state.get("acknowledgment_confirmed")) if saved_state else False
    acknowledgment_confirmed = st.checkbox(
        "I understand that completing this checklist is self-reported preparation only and does not verify data destruction.",
        value=ack_default,
        key=f"shield_ack_{device_key_suffix}",
    )

    if selected_device is not None:
        if st.button(
            "Save Checklist Progress for This Device",
            key=f"save_shield_btn_{device_key_suffix}",
            type="primary",
        ):
            save_safety_checklist(
                device_id=selected_device["id"],
                purpose=purpose,
                storage_type=storage_type,
                checklist_state=current_checks,
                acknowledgment_confirmed=acknowledgment_confirmed,
            )
            st.success(
                f"Saved checklist state ({completed}/{total} steps) for {format_device_label(selected_device)}."
            )

        if saved_state:
            st.caption(f"Last saved for this device: {saved_state['updated_at']}")

    if completed == total and acknowledgment_confirmed:
        st.success(
            "Preparation checklist completed and acknowledged. Next step: perform and record "
            "your actual sanitization method in the Sanitization Records page."
        )
    elif completed == total:
        st.info(
            "All checklist items are ticked. Confirm the acknowledgment above and proceed to "
            "Sanitization Records to document the actual erasure."
        )

    st.divider()
    st.subheader("Understanding Sanitization Trust Levels")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(
            f"""
            <div class="ww-card">
                {badge_html("User reported")}
                <h4 style="margin:0.5rem 0 0.3rem; color:#1B4332;">1. User-Reported Completion</h4>
                <p style="font-size:0.88rem; color:#52606D; margin:0;">
                    Checklist steps or a self-declared reset noted by the owner. Helpful for readiness,
                    <strong>not</strong> proof of erasure.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            f"""
            <div class="ww-card">
                {badge_html("Documented")}
                <h4 style="margin:0.5rem 0 0.3rem; color:#1B4332;">2. Documented Sanitization</h4>
                <p style="font-size:0.88rem; color:#52606D; margin:0;">
                    Specific media type, method, date, operator, and supporting reference (e.g., wipe log
                    or recycler receipt) recorded in Sanitization Records.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with t3:
        st.markdown(
            f"""
            <div class="ww-card">
                {badge_html("Independently verified")}
                <h4 style="margin:0.5rem 0 0.3rem; color:#1B4332;">3. Independently Verified</h4>
                <p style="font-size:0.88rem; color:#52606D; margin:0;">
                    Backed by a third-party sanitization certificate or independent read-back verification
                    report referenced in the device record.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "Reference: [NIST SP 800-88 Rev. 2 — Guidelines for Media Sanitization](https://csrc.nist.gov/pubs/sp/800/88/r2/final) "
        "(informational reference only; WipeWise does not issue compliance certifications)."
    )
