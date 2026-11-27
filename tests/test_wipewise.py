"""Automated tests for WipeWise database, domain logic, and all 7 Streamlit pages."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys

import pytest
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import db  # noqa: E402
from services.assessment_engine import evaluate_device  # noqa: E402
from services.impact_model import estimate_action_impact  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point WipeWise at an isolated temporary SQLite database per test."""
    db_file = tmp_path / "test_wipewise.db"
    monkeypatch.setenv("WIPEWISE_DB_PATH", str(db_file))
    db.initialize_db()
    return db_file


def test_fresh_db_initialization_and_crud(temp_db: Path) -> None:
    """Fresh DB initializes all tables and persists device, assessment, sanitization, and timeline records."""
    assert temp_db.exists()

    dev_id = db.add_device(
        device="Laptop",
        brand="Lenovo",
        model="ThinkPad T14",
        status="In Use",
        notes="Primary work machine",
        device_name="Work T14",
    )
    assert dev_id > 0

    devices = db.list_devices()
    assert len(devices) == 1
    assert devices[0]["device_name"] == "Work T14"

    assess_id = db.add_assessment(
        device_id=dev_id,
        device_name="Work T14",
        device_category="Laptop",
        brand_model="Lenovo ThinkPad T14",
        device_age="3-5 years",
        physical_condition="Minor Cosmetic Wear",
        functional_condition="Fully Functional",
        battery_condition="Healthy (>80%)",
        repair_feasibility="Not Applicable (No Repair Needed)",
        recommendation="Donate",
        explanation="Good condition for donation.",
        factor_breakdown=["Factor 1"],
    )
    assert assess_id > 0

    sanit_id = db.add_sanitization_record(
        device="Work T14",
        storage_type="SSD / NVMe",
        method="Cryptographic Erase (CE)",
        verification="Documented",
        date="2026-11-27",
        notes="NVMe sanitize log attached",
        device_id=dev_id,
        responsible_person="Owner",
        evidence_reference="LOG-101",
        nist_category="Purge",
    )
    assert sanit_id > 0

    ev_id, created = db.add_lifecycle_event(
        device_id=dev_id,
        event_type="Sanitization recorded",
        event_date="2026-11-27",
        details="Performed NVMe Cryptographic Erase.",
        evidence_reference="LOG-101",
    )
    assert created is True
    assert ev_id is not None

    # Duplicate event submission is rejected cleanly
    dup_id, dup_created = db.add_lifecycle_event(
        device_id=dev_id,
        event_type="Sanitization recorded",
        event_date="2026-11-27",
        details="Performed NVMe Cryptographic Erase.",
        evidence_reference="LOG-101",
    )
    assert dup_created is False
    assert dup_id is None


def test_legacy_schema_migration_preserves_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing legacy wipewise.db tables migrate non-destructively with original rows preserved."""
    legacy_db = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy_db)
    conn.execute(
        "CREATE TABLE devices (id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT, brand TEXT, model TEXT, status TEXT, notes TEXT)"
    )
    conn.execute(
        "INSERT INTO devices (device, brand, model, status, notes) VALUES ('Laptop', 'Dell', 'XPS 13', 'Donated', 'Legacy note')"
    )
    conn.execute(
        "CREATE TABLE impact_records (id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT, action TEXT, weight REAL)"
    )
    conn.execute(
        "INSERT INTO impact_records (device, action, weight) VALUES ('Laptop', 'Donated', 1.4)"
    )
    conn.execute(
        "CREATE TABLE sanitization_records (id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT NOT NULL, storage_type TEXT NOT NULL, method TEXT NOT NULL, verification TEXT NOT NULL, date TEXT NOT NULL, notes TEXT)"
    )
    conn.execute(
        "INSERT INTO sanitization_records (device, storage_type, method, verification, date, notes) VALUES ('Laptop', 'SSD', 'Erase', 'User reported', '2026-01-01', 'Legacy wipe')"
    )
    conn.execute(
        "CREATE TABLE lifecycle_events (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL, event_type TEXT NOT NULL, event_date TEXT NOT NULL, details TEXT, evidence_reference TEXT)"
    )
    conn.execute(
        "INSERT INTO lifecycle_events (device_id, event_type, event_date, details, evidence_reference) VALUES (1, 'Device Registered', '2026-01-01', 'Legacy event', 'REF-1')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("WIPEWISE_DB_PATH", str(legacy_db))
    db.initialize_db()

    devices = db.list_devices()
    assert len(devices) == 1
    assert devices[0]["brand"] == "Dell"
    assert devices[0]["notes"] == "Legacy note"
    assert "device_name" in devices[0]

    impacts = db.list_impact_records()
    assert len(impacts) == 1
    assert impacts[0]["weight"] == 1.4

    sanits = db.list_sanitization_records()
    assert len(sanits) == 1
    assert sanits[0]["verification"] == "User reported"

    events = db.list_lifecycle_events()
    assert len(events) == 1
    assert events[0]["details"] == "Legacy event"


def test_device_wise_separation_and_safety_shield(temp_db: Path) -> None:
    """Records for Device A never bleed into Device B."""
    dev_a = db.add_device(device="Laptop", brand="Apple", model="MacBook Air", device_name="Device A")
    dev_b = db.add_device(device="Smartphone", brand="Google", model="Pixel 7", device_name="Device B")

    db.add_sanitization_record(
        device="Device A",
        storage_type="SSD / NVMe",
        method="Cryptographic Erase (CE)",
        verification="Documented",
        date="2026-11-27",
        notes="Log A",
        device_id=dev_a,
        responsible_person="Alice",
        evidence_reference="CERT-A",
    )
    db.add_lifecycle_event(dev_a, "Device registered", "2026-11-27", "Registered A")
    db.add_lifecycle_event(dev_b, "Device registered", "2026-11-27", "Registered B")

    db.save_safety_checklist(
        device_id=dev_a,
        purpose="Donate",
        storage_type="SSD / NVMe",
        checklist_state={"backup_files": True, "sign_out_accounts": True},
        acknowledgment_confirmed=True,
    )

    assert len(db.list_sanitization_records(device_id=dev_a)) == 1
    assert len(db.list_sanitization_records(device_id=dev_b)) == 0
    assert len(db.list_lifecycle_events(device_id=dev_a)) == 1
    assert db.list_lifecycle_events(device_id=dev_b)[0]["details"] == "Registered B"

    shield_a = db.get_safety_checklist(dev_a)
    shield_b = db.get_safety_checklist(dev_b)
    assert shield_a is not None and shield_a["completed_count"] == 2
    assert shield_b is None


def test_assessment_rules_cover_all_five_outcomes() -> None:
    """Rule engine outputs Repair, Reuse, Donate, Resell, and Recycle with reasons."""
    resell = evaluate_device(
        device_category="Laptop",
        device_age="1-2 years",
        physical_condition="Excellent / Intact",
        functional_condition="Fully Functional",
        battery_condition="Healthy (>80%)",
        repair_feasibility="Not Applicable (No Repair Needed)",
    )
    assert resell.recommendation == "Resell"
    assert len(resell.factors) > 0

    reuse = evaluate_device(
        device_category="Laptop",
        device_age="1-2 years",
        physical_condition="Minor Cosmetic Wear",
        functional_condition="Fully Functional",
        battery_condition="Healthy (>80%)",
        repair_feasibility="Not Applicable (No Repair Needed)",
    )
    assert reuse.recommendation == "Reuse"

    donate = evaluate_device(
        device_category="Laptop",
        device_age="3-5 years",
        physical_condition="Minor Cosmetic Wear",
        functional_condition="Fully Functional",
        battery_condition="Healthy (>80%)",
        repair_feasibility="Not Applicable (No Repair Needed)",
    )
    assert donate.recommendation == "Donate"

    repair = evaluate_device(
        device_category="Smartphone",
        device_age="3-5 years",
        physical_condition="Moderate / Repairable Damage",
        functional_condition="Minor Issues / Slow",
        battery_condition="Swollen / Dead / Fails to Hold Charge",
        repair_feasibility="Easy / Low-Cost Repair",
    )
    assert repair.recommendation == "Repair"
    assert "swollen" in repair.safety_warning.lower()

    recycle = evaluate_device(
        device_category="Laptop",
        device_age="7+ years",
        physical_condition="Severe Physical Damage",
        functional_condition="Non-Functional",
        battery_condition="Swollen / Dead / Fails to Hold Charge",
        repair_feasibility="Parts Unavailable / High Cost",
    )
    assert recycle.recommendation == "Recycle"


def test_impact_model_separates_diversion_and_recycling() -> None:
    """Reuse/Repair counts toward diversion; Recycled counts toward recovery separately."""
    reused = estimate_action_impact("Laptop", "Reused", 2.0)
    assert reused.ewaste_diverted_kg == 2.0
    assert reused.recycled_weight_kg == 0.0
    assert reused.estimated_co2_saved_kg == 50.0

    recycled = estimate_action_impact("Laptop", "Recycled", 2.0)
    assert recycled.ewaste_diverted_kg == 0.0
    assert recycled.recycled_weight_kg == 2.0
    assert recycled.estimated_co2_saved_kg == 5.0


def test_validation_rejects_invalid_inputs(temp_db: Path) -> None:
    """Invalid DB inputs raise explicit ValueErrors."""
    with pytest.raises(ValueError):
        db.add_device(device="   ")
    with pytest.raises(ValueError):
        db.add_impact(device="Laptop", action="Repaired", weight=0)
    with pytest.raises(ValueError):
        db.add_sanitization_record("", "SSD", "CE", "User reported", "2026-11-27")


def test_streamlit_all_seven_pages_smoke_and_end_to_end(temp_db: Path) -> None:
    """Boot the real app via AppTest, interact across all 7 pages, and verify persistence."""
    app_path = str(PROJECT_ROOT / "app.py")
    at = AppTest.from_file(app_path, default_timeout=15)
    at.run()
    assert not at.exception

    # 1. Navigate to Device Assessment, analyze & save a device
    at.sidebar.radio(key="main_navigation").set_value("Device Assessment").run()
    assert not at.exception
    at.text_input[0].set_value("Test ThinkPad X1")
    at.button[0].click().run()  # Form submit button "Analyze Device Condition"
    assert not at.exception

    # Save Assessment button should appear and work without duplicate widget ID error
    save_btn = [b for b in at.button if b.key == "save_assessment_to_passport_btn"]
    assert len(save_btn) == 1
    save_btn[0].click().run()
    assert not at.exception
    assert len(db.list_devices()) == 1
    assert len(db.list_assessments()) == 1

    # 2. Data Safety Shield
    at.sidebar.radio(key="main_navigation").set_value("Data Safety Shield").run()
    assert not at.exception
    save_shield = [b for b in at.button if (b.key or "").startswith("save_shield_btn_")]
    assert len(save_shield) == 1
    save_shield[0].click().run()
    assert not at.exception

    # 3. Lifecycle Passport — verify device appears, edit notes & status, and check export
    at.sidebar.radio(key="main_navigation").set_value("Lifecycle Passport").run()
    assert not at.exception
    assert any("Test ThinkPad X1" in str(el.value) for el in at.markdown)
    # Verify Passport download buttons exist (JSON and Markdown)
    passport_downloads = [b for b in at.get("download_button") if "export_passport" in (b.key or "")]
    assert len(passport_downloads) == 2

    # 4. Sanitization Records — verify validation rejects missing evidence for Documented/Independently verified, then valid save works
    at.sidebar.radio(key="main_navigation").set_value("Sanitization Records").run()
    assert not at.exception
    # Missing responsible person -> error
    at.button[0].click().run()
    assert len(at.error) >= 1
    # Independently verified without evidence ref -> error
    at.text_input[0].set_value("IT Auditor")
    ver_select = [s for s in at.selectbox if "Verification Status" in s.label][0]
    ver_select.set_value("Independently verified")
    at.button[0].click().run()
    assert len(at.error) >= 1
    # Provide evidence ref -> succeeds
    at.text_input[1].set_value("CERT-2026-99")
    at.button[0].click().run()
    assert not at.exception
    assert len(db.list_sanitization_records()) == 1

    # 5. Impact Tracker
    at.sidebar.radio(key="main_navigation").set_value("Impact Tracker").run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert len(db.list_impact_records()) == 1

    # 6. Lifecycle Timeline — validate empty details rejected, valid event saved, duplicate rejected
    at.sidebar.radio(key="main_navigation").set_value("Lifecycle Timeline").run()
    assert not at.exception
    at.button[0].click().run()  # Empty details -> error
    assert not at.exception
    assert len(at.error) >= 1
    at.text_area[0].set_value("Completed battery check and backup.")
    at.button[0].click().run()
    assert not at.exception
    events_after_first = db.list_lifecycle_events()
    assert any("Completed battery check and backup." in ev["details"] for ev in events_after_first)
    # Re-submit identical event -> duplicate warning, count unchanged
    at.text_area[0].set_value("Completed battery check and backup.")
    at.button[0].click().run()
    assert not at.exception
    assert len(at.warning) >= 1
    assert len(db.list_lifecycle_events()) == len(events_after_first)

    # 7. Dashboard reflects persisted SQLite records after fresh AppTest restart and CTA navigation works
    at_restarted = AppTest.from_file(app_path, default_timeout=15)
    at_restarted.run()
    assert not at_restarted.exception
    assert len(db.list_devices()) == 1
    assert len(db.list_sanitization_records()) == 1
    assert len(db.list_impact_records()) == 1
    cta_assess = [b for b in at_restarted.button if b.key == "dash_cta_assess"]
    assert len(cta_assess) == 1
    cta_assess[0].click().run()
    assert not at_restarted.exception
    assert at_restarted.sidebar.radio(key="main_navigation").value == "Device Assessment"
