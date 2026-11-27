"""Transparent environmental impact estimation model for WipeWise."""

from __future__ import annotations

from dataclasses import dataclass

IMPACT_ACTIONS = ["Repaired", "Reused", "Donated", "Resold", "Recycled"]

CATEGORY_DEFAULT_WEIGHT_KG: dict[str, float] = {
    "Laptop": 1.8,
    "Smartphone": 0.2,
    "Tablet": 0.5,
    "Desktop": 7.5,
    "Monitor": 4.8,
    "Hard Drive / SSD": 0.4,
    "Other": 1.5,
}

# Conservative embodied-carbon avoidance factors (kg CO2e per kg of device weight)
# used purely for directional estimates when extending device lifespan.
CATEGORY_CO2_PER_KG: dict[str, float] = {
    "Laptop": 25.0,
    "Smartphone": 35.0,
    "Tablet": 25.0,
    "Desktop": 18.0,
    "Monitor": 15.0,
    "Hard Drive / SSD": 15.0,
    "Other": 15.0,
}

ACTION_MULTIPLIERS: dict[str, float] = {
    "Reused": 1.0,
    "Donated": 1.0,
    "Resold": 1.0,
    "Repaired": 0.85,
    "Recycled": 0.0,
}

RECYCLING_CO2_PER_KG = 2.5


@dataclass(frozen=True)
class ImpactEstimate:
    """Estimated environmental figures derived from transparent assumptions."""

    ewaste_diverted_kg: float
    recycled_weight_kg: float
    estimated_co2_saved_kg: float
    formula_summary: str


def get_default_weight(category: str) -> float:
    """Return typical reference weight (kg) for a device category."""
    return CATEGORY_DEFAULT_WEIGHT_KG.get(category, 1.5)


def estimate_action_impact(
    category: str,
    action: str,
    weight_kg: float,
) -> ImpactEstimate:
    """Estimate e-waste diverted and CO2e impact using explicit category factors.

    Important: All outputs are directional estimates based on user-reported
    weights and conservative reference multipliers, not independently audited
    lifecycle assessments.
    """
    safe_weight = max(0.0, float(weight_kg))
    base_co2_factor = CATEGORY_CO2_PER_KG.get(category, 15.0)

    if action == "Recycled":
        co2_est = round(safe_weight * RECYCLING_CO2_PER_KG, 2)
        return ImpactEstimate(
            ewaste_diverted_kg=0.0,
            recycled_weight_kg=round(safe_weight, 2),
            estimated_co2_saved_kg=co2_est,
            formula_summary=(
                f"{safe_weight:.2f} kg × {RECYCLING_CO2_PER_KG:.1f} kg CO2e/kg "
                f"(material recovery estimate)"
            ),
        )

    multiplier = ACTION_MULTIPLIERS.get(action, 0.85)
    co2_est = round(safe_weight * base_co2_factor * multiplier, 2)
    return ImpactEstimate(
        ewaste_diverted_kg=round(safe_weight, 2),
        recycled_weight_kg=0.0,
        estimated_co2_saved_kg=co2_est,
        formula_summary=(
            f"{safe_weight:.2f} kg × {base_co2_factor:.1f} kg CO2e/kg "
            f"× {multiplier:.2f} ({action} factor)"
        ),
    )


def get_assumptions_table() -> list[dict[str, str | float]]:
    """Return transparent assumption rows for user inspection."""
    rows: list[dict[str, str | float]] = []
    for category, default_weight in CATEGORY_DEFAULT_WEIGHT_KG.items():
        rows.append(
            {
                "Category": category,
                "Typical Weight (kg)": default_weight,
                "Lifespan Extension Factor (kg CO2e / kg)": CATEGORY_CO2_PER_KG[category],
                "Repair Multiplier": ACTION_MULTIPLIERS["Repaired"],
                "Reuse / Donate / Resell Multiplier": ACTION_MULTIPLIERS["Reused"],
                "Recycling Recovery Factor (kg CO2e / kg)": RECYCLING_CO2_PER_KG,
            }
        )
    return rows
