"""Deterministic, rule-based device lifecycle assessment engine."""

from __future__ import annotations

from dataclasses import dataclass

DEVICE_CATEGORIES = [
    "Laptop",
    "Smartphone",
    "Tablet",
    "Desktop",
    "Monitor",
    "Hard Drive / SSD",
    "Other",
]

DEVICE_AGES = [
    "< 1 year",
    "1-2 years",
    "3-5 years",
    "5-7 years",
    "7+ years",
]

PHYSICAL_CONDITIONS = [
    "Excellent / Intact",
    "Minor Cosmetic Wear",
    "Moderate / Repairable Damage",
    "Severe Physical Damage",
]

FUNCTIONAL_CONDITIONS = [
    "Fully Functional",
    "Minor Issues / Slow",
    "Intermittent / Partial Failure",
    "Non-Functional",
]

BATTERY_CONDITIONS = [
    "Healthy (>80%)",
    "Degraded (Needs Replacement Soon)",
    "Swollen / Dead / Fails to Hold Charge",
    "Not Applicable (No Battery)",
]

REPAIR_FEASIBILITIES = [
    "Not Applicable (No Repair Needed)",
    "Easy / Low-Cost Repair",
    "Moderate Repair Effort",
    "Parts Unavailable / High Cost",
]

RECOMMENDATION_TO_STATUS = {
    "Repair": "Under Repair",
    "Reuse": "Ready for Reuse",
    "Donate": "Ready for Donation",
    "Resell": "Ready for Resale",
    "Recycle": "Ready for Recycling",
}


@dataclass(frozen=True)
class AssessmentResult:
    """Structured output from the rule-based device assessment engine."""

    recommendation: str
    suggested_status: str
    explanation: str
    factors: list[str]
    next_steps: list[str]
    safety_warning: str = ""


def evaluate_device(
    *,
    device_category: str,
    device_age: str,
    physical_condition: str,
    functional_condition: str,
    battery_condition: str,
    repair_feasibility: str,
) -> AssessmentResult:
    """Evaluate device attributes using transparent deterministic rules.

    Note: This is a rule-based decision system, not an AI model.
    """
    factors: list[str] = []
    safety_warning = ""

    if battery_condition == "Swollen / Dead / Fails to Hold Charge":
        safety_warning = (
            "Battery safety notice: If the battery is swollen, do not charge, "
            "puncture, or ship the device in standard mail. Consult a certified "
            "repair technician or hazardous e-waste drop-off point."
        )

    is_storage_media = device_category == "Hard Drive / SSD"
    is_non_functional = functional_condition == "Non-Functional"
    has_partial_issues = functional_condition in (
        "Minor Issues / Slow",
        "Intermittent / Partial Failure",
    )
    has_repairable_damage = physical_condition in (
        "Moderate / Repairable Damage",
        "Severe Physical Damage",
    )
    battery_needs_service = battery_condition in (
        "Degraded (Needs Replacement Soon)",
        "Swollen / Dead / Fails to Hold Charge",
    )
    repair_blocked = repair_feasibility == "Parts Unavailable / High Cost"
    old_device = device_age == "7+ years"

    # 1. Storage media with any functional failure should be securely sanitized/destroyed and recycled
    if is_storage_media and functional_condition != "Fully Functional":
        factors.append(
            "Dedicated storage media showing errors or failure risks permanent data loss if reused."
        )
        factors.append(
            f"Functional condition reported as '{functional_condition}'."
        )
        return AssessmentResult(
            recommendation="Recycle",
            suggested_status=RECOMMENDATION_TO_STATUS["Recycle"],
            explanation=(
                "Degraded or failing storage drives should not be relied on for "
                "reuse or resale. Prioritize data recovery if needed, perform "
                "appropriate sanitization or physical destruction, and recycle via "
                "an authorized e-waste facility."
            ),
            factors=factors,
            next_steps=[
                "Back up any recoverable data immediately.",
                "Complete the Data Safety Shield checklist for storage media.",
                "Perform physical destruction or verified Purge/Destroy sanitization before recycling.",
                "Log the sanitization record and recycling event in WipeWise.",
            ],
            safety_warning=safety_warning,
        )

    # 2. Recycle when non-viable for repair or end-of-life with blocked parts
    if (
        (is_non_functional and (physical_condition == "Severe Physical Damage" or repair_blocked))
        or (physical_condition == "Severe Physical Damage" and repair_blocked)
        or (battery_condition == "Swollen / Dead / Fails to Hold Charge" and repair_blocked)
        or (old_device and (is_non_functional or has_partial_issues) and repair_blocked)
    ):
        factors.append(
            f"Device age is '{device_age}' with physical condition '{physical_condition}' "
            f"and functional state '{functional_condition}'."
        )
        factors.append(
            f"Repair feasibility was marked '{repair_feasibility}', making refurbishment impractical."
        )
        if battery_needs_service:
            factors.append(f"Battery state ('{battery_condition}') further reduces viable reuse.")
        return AssessmentResult(
            recommendation="Recycle",
            suggested_status=RECOMMENDATION_TO_STATUS["Recycle"],
            explanation=(
                "Repairing this device appears impractical due to severe damage, "
                "non-functional hardware, or unavailable parts. Responsible "
                "recycling recovers valuable materials while keeping hazardous "
                "components out of landfills."
            ),
            factors=factors,
            next_steps=[
                "Complete the Data Safety Shield checklist before handing off the device.",
                "Remove SIM/SD cards and deauthorize linked personal accounts.",
                "Document sanitization or physical storage removal in Sanitization Records.",
                "Drop off at an authorized e-waste recycler and record the weight in Impact Tracker.",
            ],
            safety_warning=safety_warning,
        )

    # 3. Repair when there are functional, physical, or battery issues that can be fixed
    if is_non_functional or has_partial_issues or has_repairable_damage or battery_needs_service:
        if is_non_functional or has_partial_issues:
            factors.append(f"Functional condition reported as '{functional_condition}'.")
        if has_repairable_damage:
            factors.append(f"Physical condition reported as '{physical_condition}'.")
        if battery_needs_service:
            factors.append(f"Battery condition reported as '{battery_condition}'.")
        factors.append(f"Repair feasibility is '{repair_feasibility}', indicating service is viable.")

        if repair_blocked:
            # Minor issues or battery degradation on a still-working unit with blocked parts -> Donate or Recycle
            if functional_condition == "Minor Issues / Slow" and not has_repairable_damage and not old_device:
                factors.append(
                    "Although OEM parts may be scarce, the unit remains operational for basic tasks."
                )
                return AssessmentResult(
                    recommendation="Reuse",
                    suggested_status=RECOMMENDATION_TO_STATUS["Reuse"],
                    explanation=(
                        "Replacement parts are limited, but the device still operates "
                        "with minor slowdowns. Consider lightweight secondary reuse "
                        "(e.g., media playback, dedicated terminal, or offline tasks) "
                        "before recycling."
                    ),
                    factors=factors,
                    next_steps=[
                        "Clean up startup apps or switch to a lightweight OS if compatible.",
                        "Monitor battery health and avoid unattended charging if degraded.",
                        "Log the reuse decision in the device's Lifecycle Timeline.",
                    ],
                    safety_warning=safety_warning,
                )

            return AssessmentResult(
                recommendation="Recycle",
                suggested_status=RECOMMENDATION_TO_STATUS["Recycle"],
                explanation=(
                    "Because replacement parts are unavailable or cost-prohibitive "
                    "while the device has functional or physical defects, authorized "
                    "recycling is the most practical end-of-life path."
                ),
                factors=factors,
                next_steps=[
                    "Back up data and complete the Data Safety Shield checklist.",
                    "Perform and document storage sanitization prior to disposal.",
                    "Send the device to an authorized e-waste recycler.",
                ],
                safety_warning=safety_warning,
            )

        return AssessmentResult(
            recommendation="Repair",
            suggested_status=RECOMMENDATION_TO_STATUS["Repair"],
            explanation=(
                "The device has addressable functional, physical, or battery issues "
                "and repair appears feasible. Extending its useful life through "
                "repair typically saves more resources than early replacement."
            ),
            factors=factors,
            next_steps=[
                "Back up important data before submitting the device for repair.",
                "Obtain a repair quote (battery, screen, storage, or thermal maintenance).",
                "After repair, update the device status and log 'Repair completed' in Lifecycle Timeline.",
            ],
            safety_warning=safety_warning,
        )

    # 4. Fully functional devices: distinguish Resell, Reuse, and Donate
    factors.append("Device is fully functional with no major physical or battery faults.")

    if device_age in ("< 1 year", "1-2 years") and physical_condition == "Excellent / Intact":
        factors.append(
            f"Recent device age ('{device_age}') and '{physical_condition}' appearance retain strong market value."
        )
        return AssessmentResult(
            recommendation="Resell",
            suggested_status=RECOMMENDATION_TO_STATUS["Resell"],
            explanation=(
                "This device is recent, intact, and fully functional. If you no "
                "longer need it, reselling it puts high-value hardware back into "
                "circulation while recovering residual value. (You may also keep "
                "reusing it internally.)"
            ),
            factors=factors,
            next_steps=[
                "Complete every preparation step in Data Safety Shield.",
                "Perform and document NIST-aligned Clear/Purge sanitization before listing.",
                "Update the Lifecycle Passport status once transferred.",
            ],
            safety_warning=safety_warning,
        )

    if device_age in ("< 1 year", "1-2 years", "3-5 years") and physical_condition in (
        "Excellent / Intact",
        "Minor Cosmetic Wear",
    ):
        if device_age == "3-5 years" and physical_condition == "Minor Cosmetic Wear":
            factors.append(
                "At 3-5 years old with minor wear, the device is ideal for community, student, or nonprofit donation if no longer needed."
            )
            return AssessmentResult(
                recommendation="Donate",
                suggested_status=RECOMMENDATION_TO_STATUS["Donate"],
                explanation=(
                    "The device is fully functional with minor cosmetic wear and a "
                    "healthy battery. Donating it to a school, nonprofit, or family "
                    "member meaningfully extends its productive lifespan."
                ),
                factors=factors,
                next_steps=[
                    "Run through the Data Safety Shield checklist before transfer.",
                    "Sanitize storage and document the method in Sanitization Records.",
                    "Record the donation in Lifecycle Timeline and Impact Tracker.",
                ],
                safety_warning=safety_warning,
            )

        factors.append(
            f"Device age ('{device_age}') and condition ('{physical_condition}') support continued primary or secondary reuse."
        )
        return AssessmentResult(
            recommendation="Reuse",
            suggested_status=RECOMMENDATION_TO_STATUS["Reuse"],
            explanation=(
                "Your device remains healthy and capable. Continuing to use it or "
                "repurposing it (for study, home server, backup workstation, or "
                "another household member) maximizes its environmental value."
            ),
            factors=factors,
            next_steps=[
                "Keep firmware and security updates current.",
                "Update the Lifecycle Passport status to 'In Use' or 'Reused'.",
                "Track extended use in Impact Tracker if repurposed.",
            ],
            safety_warning=safety_warning,
        )

    # Older fully functional devices (5-7 or 7+ years) -> Donate (or Reuse if very old)
    if device_age == "5-7 years":
        factors.append(
            "Although 5-7 years old, the device is fully functional and can still serve everyday productivity or educational needs."
        )
        return AssessmentResult(
            recommendation="Donate",
            suggested_status=RECOMMENDATION_TO_STATUS["Donate"],
            explanation=(
                "Even at 5-7 years old, a fully working device can support basic "
                "browsing, document editing, or classroom use. Consider donating it "
                "to a local community organization after sanitizing personal data."
            ),
            factors=factors,
            next_steps=[
                "Verify software/OS security update availability for the recipient.",
                "Complete Data Safety Shield and log sanitization before donating.",
                "Log the donation in Impact Tracker.",
            ],
            safety_warning=safety_warning,
        )

    factors.append(
        "At 7+ years old, OS security support may be limited; lightweight local reuse is best before eventual recycling."
    )
    return AssessmentResult(
        recommendation="Reuse",
        suggested_status=RECOMMENDATION_TO_STATUS["Reuse"],
        explanation=(
            "The device is over 7 years old yet still fully functional. Because "
            "older hardware may lack official security updates for internet-facing "
            "donation, consider dedicated local or offline reuse until end-of-life."
        ),
        factors=factors,
        next_steps=[
            "Check if security patches or a lightweight OS are still supported.",
            "Keep the device registered in Lifecycle Passport for eventual sanitization and recycling.",
        ],
        safety_warning=safety_warning,
    )
