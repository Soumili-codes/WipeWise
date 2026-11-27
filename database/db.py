"""SQLite persistence layer and schema migrations for WipeWise."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Iterator

DB_NAME = "wipewise.db"


def get_db_path() -> str:
    """Return the configured SQLite database file path."""
    return os.environ.get("WIPEWISE_DB_PATH", DB_NAME)


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    db_path = get_db_path()
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10.0)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Context manager for safe transactional SQLite operations."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()


def _existing_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    """Return the set of column names currently defined on a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_columns(
    cursor: sqlite3.Cursor,
    table_name: str,
    columns: list[tuple[str, str]],
) -> None:
    """Safely add missing columns to an existing table without losing data."""
    existing = _existing_columns(cursor, table_name)
    for column_name, column_def in columns:
        if column_name not in existing:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
            )


def initialize_db() -> None:
    """Initialize all WipeWise tables and run non-destructive migrations."""
    with db_session() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                brand TEXT DEFAULT '',
                model TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'In Use',
                notes TEXT DEFAULT ''
            )
            """
        )
        _ensure_columns(
            cursor,
            "devices",
            [
                ("device_name", "TEXT DEFAULT ''"),
                ("serial_or_asset_id", "TEXT DEFAULT ''"),
                ("current_recommendation", "TEXT DEFAULT ''"),
                ("created_at", "TEXT DEFAULT ''"),
                ("updated_at", "TEXT DEFAULT ''"),
            ],
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                device_name TEXT NOT NULL,
                device_category TEXT NOT NULL,
                brand_model TEXT DEFAULT '',
                device_age TEXT NOT NULL,
                physical_condition TEXT NOT NULL,
                functional_condition TEXT NOT NULL,
                battery_condition TEXT DEFAULT 'Not Applicable',
                repair_feasibility TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                explanation TEXT NOT NULL,
                factor_breakdown TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                assessed_at TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL UNIQUE,
                purpose TEXT NOT NULL DEFAULT 'Sell',
                storage_type TEXT NOT NULL DEFAULT 'SSD / NVMe',
                checklist_json TEXT NOT NULL DEFAULT '{}',
                completed_count INTEGER NOT NULL DEFAULT 0,
                total_count INTEGER NOT NULL DEFAULT 0,
                acknowledgment_confirmed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS impact_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                action TEXT NOT NULL,
                weight REAL NOT NULL
            )
            """
        )
        _ensure_columns(
            cursor,
            "impact_records",
            [
                ("device_id", "INTEGER REFERENCES devices(id) ON DELETE SET NULL"),
                ("device_name", "TEXT DEFAULT ''"),
                ("estimated_ewaste_diverted_kg", "REAL DEFAULT 0.0"),
                ("estimated_co2_saved_kg", "REAL DEFAULT 0.0"),
                ("notes", "TEXT DEFAULT ''"),
                ("recorded_at", "TEXT DEFAULT ''"),
            ],
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sanitization_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                storage_type TEXT NOT NULL,
                method TEXT NOT NULL,
                verification TEXT NOT NULL,
                date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
            """
        )
        _ensure_columns(
            cursor,
            "sanitization_records",
            [
                ("device_id", "INTEGER REFERENCES devices(id) ON DELETE SET NULL"),
                ("responsible_person", "TEXT DEFAULT ''"),
                ("record_source", "TEXT DEFAULT 'User entry'"),
                ("evidence_reference", "TEXT DEFAULT ''"),
                ("nist_category", "TEXT DEFAULT ''"),
                ("created_at", "TEXT DEFAULT ''"),
            ],
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                details TEXT DEFAULT '',
                evidence_reference TEXT DEFAULT '',
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_columns(
            cursor,
            "lifecycle_events",
            [
                ("created_at", "TEXT DEFAULT ''"),
            ],
        )


# ==========================================
# DEVICE MANAGEMENT
# ==========================================


def add_device(
    device: str,
    brand: str = "",
    model: str = "",
    status: str = "In Use",
    notes: str = "",
    device_name: str = "",
    serial_or_asset_id: str = "",
    current_recommendation: str = "",
) -> int:
    """Insert a new device record and return its generated ID."""
    category = (device or "").strip()
    if not category:
        raise ValueError("Device category is required.")

    clean_brand = (brand or "").strip()
    clean_model = (model or "").strip()
    clean_name = (device_name or "").strip()
    if not clean_name:
        parts = [p for p in [clean_brand, clean_model] if p]
        clean_name = " ".join(parts) if parts else category

    now = _utc_now_iso()
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO devices (
                device,
                brand,
                model,
                status,
                notes,
                device_name,
                serial_or_asset_id,
                current_recommendation,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                clean_brand,
                clean_model,
                (status or "In Use").strip(),
                (notes or "").strip(),
                clean_name,
                (serial_or_asset_id or "").strip(),
                (current_recommendation or "").strip(),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def update_device(
    device_id: int,
    *,
    device: str | None = None,
    device_name: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    serial_or_asset_id: str | None = None,
    status: str | None = None,
    current_recommendation: str | None = None,
    notes: str | None = None,
) -> bool:
    """Update mutable fields on an existing device record."""
    updates: list[str] = []
    params: list[Any] = []

    field_map = {
        "device": device,
        "device_name": device_name,
        "brand": brand,
        "model": model,
        "serial_or_asset_id": serial_or_asset_id,
        "status": status,
        "current_recommendation": current_recommendation,
        "notes": notes,
    }
    for column, value in field_map.items():
        if value is not None:
            updates.append(f"{column} = ?")
            params.append(value.strip())

    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(_utc_now_iso())
    params.append(device_id)

    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE devices SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def get_devices() -> list[tuple[Any, ...]]:
    """Return raw device rows ordered newest first."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM devices ORDER BY id DESC")
        return cursor.fetchall()


def list_devices(
    search: str = "",
    category: str = "All",
    status: str = "All",
) -> list[dict[str, Any]]:
    """Return filtered devices as structured dictionaries."""
    query = "SELECT * FROM devices WHERE 1=1"
    params: list[Any] = []

    if category and category != "All":
        query += " AND device = ?"
        params.append(category)

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += (
            " AND (device_name LIKE ? OR device LIKE ? OR brand LIKE ? "
            "OR model LIKE ? OR serial_or_asset_id LIKE ?)"
        )
        params.extend([term, term, term, term, term])

    query += " ORDER BY id DESC"

    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_device_by_id(device_id: int) -> dict[str, Any] | None:
    """Fetch a single device record by ID."""
    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def format_device_label(device_row: dict[str, Any]) -> str:
    """Create a human-readable unique display label for a device dictionary."""
    dev_id = device_row.get("device_id") or device_row["id"]
    name = (device_row.get("device_name") or "").strip()
    category = (device_row.get("device") or "").strip()
    brand = (device_row.get("brand") or "").strip()
    model = (device_row.get("model") or "").strip()
    brand_model = " ".join(p for p in [brand, model] if p)

    if name and brand_model and name.lower() != brand_model.lower():
        descriptor = f"{name} ({category} · {brand_model})"
    elif name and name.lower() != category.lower():
        descriptor = f"{name} ({category})"
    elif brand_model:
        descriptor = f"{category} · {brand_model}"
    else:
        descriptor = category

    return f"#{dev_id} — {descriptor}"


# ==========================================
# DEVICE ASSESSMENTS
# ==========================================


def add_assessment(
    device_id: int,
    device_name: str,
    device_category: str,
    brand_model: str,
    device_age: str,
    physical_condition: str,
    functional_condition: str,
    battery_condition: str,
    repair_feasibility: str,
    recommendation: str,
    explanation: str,
    factor_breakdown: list[str],
    notes: str = "",
) -> int:
    """Persist a device assessment record linked to a device."""
    now = _utc_now_iso()
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO assessments (
                device_id,
                device_name,
                device_category,
                brand_model,
                device_age,
                physical_condition,
                functional_condition,
                battery_condition,
                repair_feasibility,
                recommendation,
                explanation,
                factor_breakdown,
                notes,
                assessed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                device_name.strip(),
                device_category.strip(),
                brand_model.strip(),
                device_age.strip(),
                physical_condition.strip(),
                functional_condition.strip(),
                battery_condition.strip(),
                repair_feasibility.strip(),
                recommendation.strip(),
                explanation.strip(),
                json.dumps(factor_breakdown),
                notes.strip(),
                now,
            ),
        )
        return int(cursor.lastrowid)


def list_assessments(device_id: int | None = None) -> list[dict[str, Any]]:
    """Return saved assessment records, optionally filtered by device_id."""
    query = """
        SELECT a.*, d.status AS current_device_status
        FROM assessments a
        LEFT JOIN devices d ON a.device_id = d.id
    """
    params: list[Any] = []
    if device_id is not None:
        query += " WHERE a.device_id = ?"
        params.append(device_id)
    query += " ORDER BY a.id DESC"

    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params)
        results: list[dict[str, Any]] = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item["factors"] = json.loads(item.get("factor_breakdown") or "[]")
            except json.JSONDecodeError:
                item["factors"] = []
            results.append(item)
        return results


# ==========================================
# DATA SAFETY SHIELD CHECKLISTS
# ==========================================


def save_safety_checklist(
    device_id: int,
    purpose: str,
    storage_type: str,
    checklist_state: dict[str, bool],
    acknowledgment_confirmed: bool,
) -> None:
    """Create or update the persistent Data Safety Shield checklist for a device."""
    completed_count = sum(1 for v in checklist_state.values() if v)
    total_count = len(checklist_state)
    now = _utc_now_iso()

    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO safety_checklists (
                device_id,
                purpose,
                storage_type,
                checklist_json,
                completed_count,
                total_count,
                acknowledgment_confirmed,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                purpose = excluded.purpose,
                storage_type = excluded.storage_type,
                checklist_json = excluded.checklist_json,
                completed_count = excluded.completed_count,
                total_count = excluded.total_count,
                acknowledgment_confirmed = excluded.acknowledgment_confirmed,
                updated_at = excluded.updated_at
            """,
            (
                device_id,
                purpose.strip(),
                storage_type.strip(),
                json.dumps(checklist_state),
                completed_count,
                total_count,
                1 if acknowledgment_confirmed else 0,
                now,
            ),
        )


def get_safety_checklist(device_id: int) -> dict[str, Any] | None:
    """Return the saved Data Safety Shield state for a device, if any."""
    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM safety_checklists WHERE device_id = ?",
            (device_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["checklist_state"] = json.loads(data.get("checklist_json") or "{}")
        except json.JSONDecodeError:
            data["checklist_state"] = {}
        data["acknowledgment_confirmed"] = bool(data.get("acknowledgment_confirmed"))
        return data


# ==========================================
# ENVIRONMENTAL IMPACT MANAGEMENT
# ==========================================


def add_impact(
    device: str,
    action: str,
    weight: float,
    device_id: int | None = None,
    device_name: str = "",
    estimated_ewaste_diverted_kg: float = 0.0,
    estimated_co2_saved_kg: float = 0.0,
    notes: str = "",
) -> int:
    """Insert an environmental impact record and return its ID."""
    if weight <= 0:
        raise ValueError("Device weight must be greater than zero.")
    if not (device or "").strip():
        raise ValueError("Device category is required.")
    if not (action or "").strip():
        raise ValueError("Lifecycle action is required.")

    now = _utc_now_iso()
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO impact_records (
                device,
                action,
                weight,
                device_id,
                device_name,
                estimated_ewaste_diverted_kg,
                estimated_co2_saved_kg,
                notes,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.strip(),
                action.strip(),
                float(weight),
                device_id,
                (device_name or device).strip(),
                float(estimated_ewaste_diverted_kg),
                float(estimated_co2_saved_kg),
                notes.strip(),
                now,
            ),
        )
        return int(cursor.lastrowid)


def get_impact() -> list[tuple[Any, ...]]:
    """Return raw impact records ordered newest first."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM impact_records ORDER BY id DESC")
        return cursor.fetchall()


def list_impact_records(device_id: int | None = None) -> list[dict[str, Any]]:
    """Return impact records as structured dictionaries."""
    query = """
        SELECT i.*, d.device_name AS linked_device_name
        FROM impact_records i
        LEFT JOIN devices d ON i.device_id = d.id
    """
    params: list[Any] = []
    if device_id is not None:
        query += " WHERE i.device_id = ?"
        params.append(device_id)
    query += " ORDER BY i.id DESC"

    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# SANITIZATION RECORD MANAGEMENT
# ==========================================


def add_sanitization_record(
    device: str,
    storage_type: str,
    method: str,
    verification: str,
    date: str,
    notes: str = "",
    device_id: int | None = None,
    responsible_person: str = "",
    record_source: str = "User entry",
    evidence_reference: str = "",
    nist_category: str = "",
) -> int:
    """Insert a sanitization record and return its ID."""
    if not (device or "").strip():
        raise ValueError("Associated device is required.")
    if not (storage_type or "").strip():
        raise ValueError("Storage/media type is required.")
    if not (method or "").strip():
        raise ValueError("Sanitization method is required.")
    if not (verification or "").strip():
        raise ValueError("Verification status is required.")
    if not (date or "").strip():
        raise ValueError("Sanitization date is required.")

    now = _utc_now_iso()
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO sanitization_records (
                device,
                storage_type,
                method,
                verification,
                date,
                notes,
                device_id,
                responsible_person,
                record_source,
                evidence_reference,
                nist_category,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.strip(),
                storage_type.strip(),
                method.strip(),
                verification.strip(),
                date.strip(),
                (notes or "").strip(),
                device_id,
                (responsible_person or "").strip(),
                (record_source or "User entry").strip(),
                (evidence_reference or "").strip(),
                (nist_category or "").strip(),
                now,
            ),
        )
        return int(cursor.lastrowid)


def get_sanitization_records() -> list[tuple[Any, ...]]:
    """Return raw sanitization records ordered newest first."""
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM sanitization_records ORDER BY id DESC")
        return cursor.fetchall()


def list_sanitization_records(
    device_id: int | None = None,
    verification_filter: str = "All",
) -> list[dict[str, Any]]:
    """Return sanitization records as structured dictionaries."""
    query = """
        SELECT s.*, d.device_name AS linked_device_name, d.device AS linked_device_category
        FROM sanitization_records s
        LEFT JOIN devices d ON s.device_id = d.id
        WHERE 1=1
    """
    params: list[Any] = []
    if device_id is not None:
        query += " AND s.device_id = ?"
        params.append(device_id)
    if verification_filter and verification_filter != "All":
        query += " AND s.verification = ?"
        params.append(verification_filter)
    query += " ORDER BY s.date DESC, s.id DESC"

    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# DEVICE LIFECYCLE TIMELINE
# ==========================================


def add_lifecycle_event(
    device_id: int,
    event_type: str,
    event_date: str,
    details: str,
    evidence_reference: str = "",
    *,
    allow_duplicate: bool = False,
) -> tuple[int | None, bool]:
    """Insert a lifecycle event while guarding against duplicate submissions.

    Returns a tuple of (event_id, created_flag). When an identical event
    already exists and allow_duplicate is False, returns (None, False).
    """
    clean_type = (event_type or "").strip()
    clean_date = (event_date or "").strip()
    clean_details = (details or "").strip()
    clean_ref = (evidence_reference or "").strip()

    if not clean_type:
        raise ValueError("Event type is required.")
    if not clean_date:
        raise ValueError("Event date is required.")
    if not clean_details:
        raise ValueError("Event details are required.")

    now = _utc_now_iso()
    with db_session() as connection:
        cursor = connection.cursor()
        if not allow_duplicate:
            cursor.execute(
                """
                SELECT id FROM lifecycle_events
                WHERE device_id = ? AND event_type = ? AND event_date = ? AND details = ?
                LIMIT 1
                """,
                (device_id, clean_type, clean_date, clean_details),
            )
            if cursor.fetchone() is not None:
                return None, False

        cursor.execute(
            """
            INSERT INTO lifecycle_events (
                device_id,
                event_type,
                event_date,
                details,
                evidence_reference,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                clean_type,
                clean_date,
                clean_details,
                clean_ref,
                now,
            ),
        )
        return int(cursor.lastrowid), True


def get_lifecycle_events(device_id: int | None = None) -> list[tuple[Any, ...]]:
    """Return raw lifecycle event rows joined with device metadata."""
    query = """
        SELECT
            e.id,
            e.event_type,
            e.event_date,
            e.details,
            e.evidence_reference,
            d.device,
            d.brand,
            d.model
        FROM lifecycle_events e
        JOIN devices d ON e.device_id = d.id
    """
    with db_session() as connection:
        cursor = connection.cursor()
        if device_id is not None:
            query += " WHERE e.device_id = ? ORDER BY e.event_date DESC, e.id DESC"
            cursor.execute(query, (device_id,))
        else:
            query += " ORDER BY e.event_date DESC, e.id DESC"
            cursor.execute(query)
        return cursor.fetchall()


def list_lifecycle_events(
    device_id: int | None = None,
    ascending: bool = False,
) -> list[dict[str, Any]]:
    """Return lifecycle events as structured dictionaries in chosen chronological order."""
    order_dir = "ASC" if ascending else "DESC"
    query = f"""
        SELECT
            e.id,
            e.device_id,
            e.event_type,
            e.event_date,
            e.details,
            e.evidence_reference,
            e.created_at,
            d.device,
            d.device_name,
            d.brand,
            d.model
        FROM lifecycle_events e
        JOIN devices d ON e.device_id = d.id
    """
    params: list[Any] = []
    if device_id is not None:
        query += " WHERE e.device_id = ?"
        params.append(device_id)
    query += f" ORDER BY e.event_date {order_dir}, e.id {order_dir}"

    with db_session() as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
