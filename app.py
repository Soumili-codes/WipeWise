
import streamlit as st

from database.db import (
    initialize_db,
    add_device,
    get_devices,
    add_impact,
    get_impact,
    add_sanitization_record,
    get_sanitization_records,
    add_lifecycle_event,
    get_lifecycle_events
)



st.set_page_config(
    page_title="WipeWise",
    page_icon="♻️",
    layout="wide"
)
initialize_db()
if "device_records" not in st.session_state:
    st.session_state["device_records"] = []

if "impact_entries" not in st.session_state:
    st.session_state["impact_entries"] = []

if "assessment_saved" not in st.session_state:
    st.session_state["assessment_saved"] = False

st.title("♻️ WipeWise")
st.subheader("Secure Your Data. Save Your Device.")

st.write(
    "A smart device lifecycle assistant that helps "
    "you make responsible e-waste and data safety decisions."
)

st.divider()


page = st.sidebar.radio(
    "Navigation",
    options=[
        "Dashboard",
        "Device Assessment",
        "Data Safety Shield",
        "Lifecycle Passport",
        "Impact Tracker",
        "Sanitization Records",
        "Lifecycle Timeline"
    ],
    key="main_navigation"
)




if page == "Dashboard":
    st.title("♻️ WipeWise")
    st.subheader("Secure Your Data. Save Your Device.")

    st.divider()

    devices = get_devices()
    impacts = get_impact()

    total_devices = len(devices)

    reused_devices = sum(
        1 for record in devices
        if record[4] in ["Donated", "Reused"]
    )

    recycled_weight = sum(
        record[3] for record in impacts
        if record[2] == "Recycled"
    )

    st.subheader("Your Sustainability Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Device Passport Records",
        total_devices
    )

    col2.metric(
        "Devices Donated / Reused",
        reused_devices
    )

    col3.metric(
        "Reported Recycled Weight",
        f"{recycled_weight:.1f} kg"
    )

    st.divider()

    st.subheader("Explore WipeWise")

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            "**Device Assessment**\n\n"
            "Evaluate your electronic device and get a preliminary recommendation."
        )

        st.info(
            "**Data Safety Shield**\n\n"
            "Prepare your personal data before transferring a device."
        )

    with col2:
        st.info(
            "**Lifecycle Passport**\n\n"
            "Maintain permanent records of your electronic devices."
        )

        st.info(
            "**Impact Tracker**\n\n"
            "Track user-reported reuse, repair, donation and recycling records."
        )

    st.divider()

    st.caption(
        "Dashboard figures are calculated from saved user records. "
        "They are not independently verified environmental outcomes."
    )


elif page == "Device Assessment":
    st.header("🔍 Device Assessment")
    st.write("Evaluate your old electronic device.")

    st.divider()

    with st.form("assessment_form"):

        device = st.selectbox(
            "Device type",
            ["Laptop", "Smartphone", "Tablet", "Desktop", "Hard Drive", "Other"]
        )

        age = st.selectbox(
            "Device age",
            ["0-2 years", "3-5 years", "More than 5 years"]
        )

        condition = st.selectbox(
            "Physical condition",
            ["Fully Working", "Minor Damage", "Major Damage", "Not Working"]
        )

        performance = st.selectbox(
            "Performance",
            ["Good", "Slow", "Not Functional"]
        )

        submitted = st.form_submit_button("Analyze My Device")

    if submitted:

        if condition == "Not Working" or performance == "Not Functional":
            recommendation = "Professional Repair Assessment"
            explanation = (
                "The device is not functional. Get a repair estimate "
                "and check whether safe refurbishment is practical "
                "before deciding to recycle it."
            )

        elif condition == "Major Damage":
            recommendation = "Repair Assessment"
            explanation = (
                "Get a professional inspection to determine "
                "whether repairing the device is worthwhile."
            )

        elif condition == "Minor Damage" or performance == "Slow":
            recommendation = "REPAIR"
            explanation = (
                "The device may have a useful life remaining. "
                "Consider repair or maintenance before replacing it."
            )

        elif age == "0-2 years":
            recommendation = "KEEP / REUSE"
            explanation = (
                "The device is relatively recent and functional. "
                "Continue using it or consider responsible reuse."
            )

        elif age == "3-5 years":
            recommendation = "DONATE / REUSE"
            explanation = (
                "If the device is fully functional and suitable "
                "for another user, consider donating it."
            )

        else:
            recommendation = "REUSE OR RECYCLE ASSESSMENT"
            explanation = (
                "Check battery health, compatibility and repair cost. "
                "If reuse is not practical, choose an authorized recycler."
            )

        st.session_state["assessment"] = {
            "device": device,
            "age": age,
            "condition": condition,
            "performance": performance,
            "recommendation": recommendation,
            "explanation": explanation
        }

    if "assessment" in st.session_state:

        result = st.session_state["assessment"]

        st.divider()
        st.subheader("Your Assessment Result")

        st.success("Recommendation: " + result["recommendation"])
        st.write(result["explanation"])

        st.write("**Device:**", result["device"])
        st.write("**Age:**", result["age"])
        st.write("**Condition:**", result["condition"])
        st.write("**Performance:**", result["performance"])

        st.warning(
            "This is a preliminary recommendation, not a professional inspection."
        )

        if st.button(
    "Save Assessment to Lifecycle Passport",
    key="save_assessment_to_passport"
):

            if not st.session_state["assessment_saved"]:

                passport_record = {
                    "device": result["device"],
                    "brand": "",
                    "model": "",
                    "status": result["recommendation"],
                    "notes": (
                        f"Age: {result['age']}; "
                        f"Condition: {result['condition']}; "
                        f"Performance: {result['performance']}"
                    )
                }

                st.session_state["device_records"].append(passport_record)

                st.session_state["assessment_saved"] = True

                st.success("Assessment saved to your Lifecycle Passport!")

            
        if st.button(
    "Save Assessment to Lifecycle Passport",
    key="save_assessment_to_passport"
):
            if not st.session_state["assessment_saved"]:

                add_device(
                    result["device"],
                    "",
                    "",
                    result["recommendation"],
                    (
                        f"Age: {result['age']}; "
                        f"Condition: {result['condition']}; "
                        f"Performance: {result['performance']}"
                    )
                )

                st.session_state["assessment_saved"] = True

                st.success(
                    "Assessment saved permanently to Lifecycle Passport!"
                )

            else:
                st.info("This assessment has already been saved.")



elif page == "Data Safety Shield":
    st.header("🔐 Data Safety Shield")
    st.write("Protect your personal information before transferring a device.")

    st.warning(
        "Completing this checklist does not prove that data has been securely erased."
    )

    st.subheader("1. Device Information")

    device_type = st.selectbox(
        "Select your device",
        ["Laptop", "Smartphone", "Tablet", "Desktop", "External Hard Drive"],
        key="shield_device"
    )

    purpose = st.selectbox(
        "What will you do with this device?",
        ["Sell", "Donate", "Recycle", "Give to someone else"],
        key="shield_purpose"
    )

    st.divider()
    st.subheader("2. Data Safety Checklist")

    tasks = [
        "Back up important personal files",
        "Sign out of personal accounts",
        "Remove SIM and memory cards, if applicable",
        "Check for sensitive files and saved passwords",
        "Check manufacturer guidance for data sanitization",
        "Arrange an appropriate sanitization method",
        "Verify the sanitization result before transfer"
    ]

    completed = 0

    for index, task in enumerate(tasks):
        if st.checkbox(task, key=f"shield_task_{index}"):
            completed += 1

    progress = completed / len(tasks)

    st.divider()
    st.subheader("3. Preparation Progress")

    st.progress(progress)

    st.write(f"{completed} of {len(tasks)} steps completed.")

    if completed == len(tasks):
        st.success("Preparation checklist completed.")
        st.info(
            "Remember: verify that appropriate data sanitization "
            "was actually performed. Checklist completion is not proof."
        )
    else:
        st.info("Continue completing the preparation checklist.")

    st.divider()

    st.subheader("Security Reference")

    st.write(
        "WipeWise follows the concepts of NIST SP 800-88 Rev. 2 "
        "for media sanitization guidance."
    )

    st.markdown(
        "[Read the official NIST publication](https://csrc.nist.gov/pubs/sp/800/88/r2/final)"
    )



elif page == "Lifecycle Passport":
    st.header("📋 Device Lifecycle Passport")

    st.write("Create and maintain permanent device lifecycle records.")

    st.divider()
    st.subheader("Create a Device Passport")

    with st.form("passport_form"):

        passport_device = st.selectbox(
            "Device Type",
            ["Laptop", "Smartphone", "Tablet", "Desktop", "Hard Drive", "Other"],
            key="passport_device"
        )

        brand = st.text_input("Brand / Manufacturer")
        model = st.text_input("Model Name")

        status = st.selectbox(
            "Current Lifecycle Status",
            ["In Use", "Under Repair", "Ready for Donation",
             "Donated", "Ready for Recycling", "Recycled", "Reused"]
        )

        notes = st.text_area("Maintenance or lifecycle notes")

        save_passport = st.form_submit_button("Create Passport")

    if save_passport:
        add_device(
            passport_device,
            brand,
            model,
            status,
            notes
        )
        st.success("Device Passport saved permanently!")

    st.divider()
    st.subheader("Your Saved Device Records")

    records = get_devices()

    if records:
        for record in records:
            with st.expander(f"Passport #{record[0]} — {record[1]}"):
                st.write("**Brand:**", record[2] or "Not provided")
                st.write("**Model:**", record[3] or "Not provided")
                st.write("**Status:**", record[4])
                st.write("**Notes:**", record[5] or "No notes")
    else:
        st.info("No device passports created yet.")



elif page == "Impact Tracker":
    st.header("🌍 Environmental Impact Tracker")

    st.write(
        "Track the actual weight of devices repaired, reused, "
        "donated or recycled."
    )

    st.divider()
    st.subheader("Add an Impact Record")

    with st.form("impact_form"):

        device_type = st.selectbox(
            "Device Type",
            ["Laptop", "Smartphone", "Tablet", "Desktop", "Monitor", "Other"]
        )

        action = st.selectbox(
            "What happened to the device?",
            ["Repaired", "Reused", "Donated", "Recycled"]
        )

        weight = st.number_input(
            "Device weight (kg)",
            min_value=0.1,
            max_value=1000.0,
            value=1.0,
            step=0.1
        )

        submitted = st.form_submit_button("Save Impact Record")

    if submitted:
        st.session_state["assessment_saved"] = False
        add_impact(device_type, action, weight)
        st.success("Impact record saved permanently!")

    st.divider()
    st.subheader("Your Environmental Impact")

    entries = get_impact()

    if entries:

        diverted_weight = sum(
            record[3]
            for record in entries
            if record[2] in ["Repaired", "Reused", "Donated"]
        )

        recycled_weight = sum(
            record[3]
            for record in entries
            if record[2] == "Recycled"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("Devices Tracked", len(entries))

        col2.metric(
            "Reuse / Repair / Donation",
            f"{diverted_weight:.1f} kg"
        )

        col3.metric(
            "Sent for Recycling",
            f"{recycled_weight:.1f} kg"
        )

        st.divider()
        st.subheader("Saved Impact Records")

        for record in entries:
            st.write(
                f"**Record #{record[0]}:** "
                f"{record[1]} — {record[2]} — {record[3]:.1f} kg"
            )

        st.caption(
            "These figures are based on user-reported records. "
            "They are not independently verified environmental savings."
        )

    else:
        st.info("No impact records yet. Add your first record above.")

elif page == "Lifecycle Timeline":

    st.header("Device Lifecycle Timeline")

    st.write(
        "Track the journey of your electronic devices "
        "from registration to reuse, donation or recycling."
    )

    st.info(
        "Timeline events are user-reported records. "
        "They are not independently verified."
    )

    st.divider()

    # Get registered devices
    devices = get_devices()

    if not devices:

        st.warning(
            "No registered devices found. "
            "Please add a device through the Device Assessment "
            "or Lifecycle Passport page first."
        )

    else:

        st.subheader("Record a Lifecycle Event")

        # Device selection
        selected_device = st.selectbox(
            "Select Device",
            devices,
            format_func=lambda d: (
                f"{d[1]} - {d[2] or 'Unknown Brand'} "
                f"{d[3] or ''}"
            ),
            key="lifecycle_device_select"
        )

        # Event form
        with st.form("lifecycle_event_form"):

            event_type = st.selectbox(
                "Lifecycle Event",
                [
                    "Device Registered",
                    "Condition Assessed",
                    "Data Sanitization",
                    "Repair",
                    "Reuse",
                    "Donation",
                    "Recycling",
                    "Other"
                ]
            )

            event_date = st.date_input(
                "Event Date"
            )

            details = st.text_area(
                "Event Details",
                placeholder=(
                    "Describe what happened to the device..."
                )
            )

            evidence_reference = st.text_input(
                "Evidence Reference (Optional)",
                placeholder=(
                    "Receipt number, report reference, "
                    "or document name"
                )
            )

            submitted = st.form_submit_button(
                "Save Lifecycle Event"
            )

        if submitted:
            st.session_state["assessment_saved"] = False

            if not details.strip():

                st.error(
                    "Please enter some details about this event."
                )

            else:

                add_lifecycle_event(
                    selected_device[0],
                    event_type,
                    event_date.isoformat(),
                    details.strip(),
                    evidence_reference.strip()
                )

                st.success(
                    "Lifecycle event saved successfully!"
                )

                st.rerun()

        st.divider()

        # Display timeline
        st.subheader("Device Lifecycle History")

        events = get_lifecycle_events(selected_device[0])

        if events:

            for event in events:

                with st.expander(
                    f"{event[2]} | {event[1]}",
                    expanded=True
                ):

                    st.write(
                        "**Device:**",
                        f"{event[5]} {event[6] or ''} "
                        f"{event[7] or ''}"
                    )

                    st.write(
                        "**Event:**",
                        event[1]
                    )

                    st.write(
                        "**Date:**",
                        event[2]
                    )

                    st.write(
                        "**Details:**",
                        event[3] or "No details provided"
                    )

                    st.write(
                        "**Evidence Reference:**",
                        event[4] or "Not provided"
                    )

                    st.caption(
                        "User-reported event — "
                        "independent verification not established."
                    )

        else:

            st.info(
                "No lifecycle events recorded for this device yet."
            )

