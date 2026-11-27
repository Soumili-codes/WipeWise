
import sqlite3

DB_NAME = "wipewise.db"

# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection():
    connection = sqlite3.connect(DB_NAME)
    return connection

# ==========================================
# INITIALIZE ALL DATABASE TABLES
# ==========================================

def initialize_db():

    connection = get_connection()
    cursor = connection.cursor()

    # Device records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            brand TEXT,
            model TEXT,
            status TEXT,
            notes TEXT
        )
    """)

    # Environmental impact records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS impact_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            action TEXT,
            weight REAL
        )
    """)

    # Sanitization records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sanitization_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT NOT NULL,
            storage_type TEXT NOT NULL,
            method TEXT NOT NULL,
            verification TEXT NOT NULL,
            date TEXT NOT NULL,
            notes TEXT
        )
    """)

    # Device lifecycle timeline events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            details TEXT,
            evidence_reference TEXT,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    """)

    connection.commit()
    connection.close()

# ==========================================
# DEVICE MANAGEMENT
# ==========================================

def add_device(device, brand, model, status, notes):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO devices (device, brand, model, status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (device, brand, model, status, notes))

    connection.commit()
    connection.close()

def get_devices():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM devices ORDER BY id DESC")

    records = cursor.fetchall()

    connection.close()

    return records

# ==========================================
# ENVIRONMENTAL IMPACT MANAGEMENT
# ==========================================

def add_impact(device, action, weight):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO impact_records (device, action, weight)
        VALUES (?, ?, ?)
    """, (device, action, weight))

    connection.commit()
    connection.close()

def get_impact():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM impact_records ORDER BY rowid DESC")

    records = cursor.fetchall()

    connection.close()

    return records

# ==========================================
# SANITIZATION RECORD MANAGEMENT
# ==========================================

def add_sanitization_record(
    device,
    storage_type,
    method,
    verification,
    date,
    notes
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sanitization_records
        (device, storage_type, method, verification, date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        device,
        storage_type,
        method,
        verification,
        date,
        notes
    ))

    connection.commit()
    connection.close()

def get_sanitization_records():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM sanitization_records
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records

# ==========================================
# DEVICE LIFECYCLE TIMELINE
# ==========================================

def add_lifecycle_event(
    device_id,
    event_type,
    event_date,
    details,
    evidence_reference
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO lifecycle_events
        (
            device_id,
            event_type,
            event_date,
            details,
            evidence_reference
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        device_id,
        event_type,
        event_date,
        details,
        evidence_reference
    ))

    connection.commit()
    connection.close()

def get_lifecycle_events(device_id=None):

    connection = get_connection()
    cursor = connection.cursor()

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

    if device_id is not None:

        query += """
            WHERE e.device_id = ?
            ORDER BY e.event_date DESC, e.id DESC
        """

        cursor.execute(query, (device_id,))

    else:

        query += """
            ORDER BY e.event_date DESC, e.id DESC
        """

        cursor.execute(query)

    records = cursor.fetchall()

    connection.close()

    return records