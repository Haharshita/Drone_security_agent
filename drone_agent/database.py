import sqlite3
import os
from datetime import datetime
import json

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "drone_patrol.db")

def get_connection(db_path=None):
    """Returns a connection to the SQLite database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes the database schema and full-text search tables."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Frames table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        frame_index INTEGER NOT NULL,
        description TEXT NOT NULL,
        tags TEXT
    );
    """)
    
    # 2. Telemetry table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        altitude REAL NOT NULL,
        battery INTEGER NOT NULL,
        location_name TEXT NOT NULL
    );
    """)
    
    # 3. Alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        severity TEXT NOT NULL,
        message TEXT NOT NULL,
        rule_triggered TEXT NOT NULL
    );
    """)
    
    # Try initializing Full-Text Search (FTS5) for fast visual query search
    try:
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS frames_fts USING fts5(
            frame_id UNINDEXED,
            description,
            tags
        );
        """)
        # Create triggers to keep FTS table in sync
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_frames_insert AFTER INSERT ON frames BEGIN
            INSERT INTO frames_fts(frame_id, description, tags) 
            VALUES (new.id, new.description, new.tags);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_frames_delete AFTER DELETE ON frames BEGIN
            DELETE FROM frames_fts WHERE frame_id = old.id;
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_frames_update AFTER UPDATE ON frames BEGIN
            UPDATE frames_fts SET 
                description = new.description,
                tags = new.tags
            WHERE frame_id = old.id;
        END;
        """)
    except sqlite3.OperationalError as e:
        # FTS5 might be disabled in some environments, log warning and use standard searches
        print(f"FTS5 initialization warning: {e}. Falling back to standard query search.")
        
    conn.commit()
    conn.close()

def insert_frame(timestamp, frame_index, description, tags=None, db_path=None):
    """Inserts a processed video frame log into the database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    tags_str = json.dumps(tags) if tags else "[]"
    
    # Standardize ISO timestamp format
    if isinstance(timestamp, datetime):
        ts_str = timestamp.isoformat()
    else:
        ts_str = timestamp

    cursor.execute(
        "INSERT INTO frames (timestamp, frame_index, description, tags) VALUES (?, ?, ?, ?)",
        (ts_str, frame_index, description, tags_str)
    )
    frame_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return frame_id

def insert_telemetry(timestamp, latitude, longitude, altitude, battery, location_name, db_path=None):
    """Inserts drone telemetry data into the database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if isinstance(timestamp, datetime):
        ts_str = timestamp.isoformat()
    else:
        ts_str = timestamp

    cursor.execute(
        "INSERT INTO telemetry (timestamp, latitude, longitude, altitude, battery, location_name) VALUES (?, ?, ?, ?, ?, ?)",
        (ts_str, latitude, longitude, altitude, battery, location_name)
    )
    conn.commit()
    conn.close()

def insert_alert(timestamp, severity, message, rule_triggered, db_path=None):
    """Inserts generated alert into the database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if isinstance(timestamp, datetime):
        ts_str = timestamp.isoformat()
    else:
        ts_str = timestamp

    cursor.execute(
        "INSERT INTO alerts (timestamp, severity, message, rule_triggered) VALUES (?, ?, ?, ?)",
        (ts_str, severity.upper(), message, rule_triggered)
    )
    conn.commit()
    conn.close()

def search_frames(query_text, db_path=None):
    """Searches frame descriptions using FTS5 if available, falling back to LIKE."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    results = []
    try:
        # FTS5 search
        cursor.execute("""
            SELECT f.id, f.timestamp, f.frame_index, f.description, f.tags, t.location_name, t.altitude, t.battery
            FROM frames f
            JOIN frames_fts fts ON f.id = fts.frame_id
            LEFT JOIN telemetry t ON f.timestamp = t.timestamp
            WHERE frames_fts MATCH ?
            ORDER BY f.timestamp ASC
        """, (query_text,))
        results = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Fallback to standard LIKE matching if FTS5 fails or is missing
        wildcard_query = f"%{query_text}%"
        cursor.execute("""
            SELECT f.id, f.timestamp, f.frame_index, f.description, f.tags, t.location_name, t.altitude, t.battery
            FROM frames f
            LEFT JOIN telemetry t ON f.timestamp = t.timestamp
            WHERE f.description LIKE ? OR f.tags LIKE ?
            ORDER BY f.timestamp ASC
        """, (wildcard_query, wildcard_query))
        results = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    return results

def get_synced_logs(db_path=None):
    """Retrieves all frames joined with matching telemetry data."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.timestamp, f.frame_index, f.description, f.tags,
               t.latitude, t.longitude, t.altitude, t.battery, t.location_name
        FROM frames f
        LEFT JOIN telemetry t ON f.timestamp = t.timestamp
        ORDER BY f.timestamp ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_alerts(limit=50, db_path=None):
    """Retrieves all generated security/safety alerts."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_telemetry_history(limit=100, db_path=None):
    """Retrieves telemetry logs."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM telemetry ORDER BY timestamp ASC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def clear_database(db_path=None):
    """Clears all records in the database tables."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM frames")
    cursor.execute("DELETE FROM telemetry")
    cursor.execute("DELETE FROM alerts")
    try:
        cursor.execute("DELETE FROM frames_fts")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
