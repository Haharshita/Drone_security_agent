import os
import pytest
import sqlite3
from datetime import datetime
from drone_agent import database

TEST_DB_PATH = "test_drone_patrol.db"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Initializes a test database before each test and removes it after."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    database.init_db(TEST_DB_PATH)
    yield
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_database_init():
    """Verify that tables are created correctly."""
    conn = database.get_connection(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "frames" in tables
    assert "telemetry" in tables
    assert "alerts" in tables
    conn.close()

def test_insert_and_retrieve_frame():
    """Verify insert and search frames function correctly."""
    timestamp = datetime.now().isoformat()
    frame_id = database.insert_frame(
        timestamp=timestamp,
        frame_index=1,
        description="A suspicious red pickup truck parked at loading dock.",
        tags=["vehicle", "truck", "suspicious"],
        db_path=TEST_DB_PATH
    )
    
    assert frame_id is not None
    
    # Test text search matching
    results = database.search_frames("truck", db_path=TEST_DB_PATH)
    assert len(results) == 1
    assert results[0]["id"] == frame_id
    assert results[0]["description"] == "A suspicious red pickup truck parked at loading dock."

def test_insert_telemetry():
    """Verify insert telemetry stores data properly."""
    timestamp = datetime.now().isoformat()
    database.insert_telemetry(
        timestamp=timestamp,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.5,
        battery=85,
        location_name="Warehouse Dock",
        db_path=TEST_DB_PATH
    )
    
    history = database.get_telemetry_history(db_path=TEST_DB_PATH)
    assert len(history) == 1
    assert history[0]["location_name"] == "Warehouse Dock"
    assert history[0]["battery"] == 85

def test_insert_alert():
    """Verify insert alert logs security exceptions."""
    timestamp = datetime.now().isoformat()
    database.insert_alert(
        timestamp=timestamp,
        severity="CRITICAL",
        message="Intruder loitering near front entrance.",
        rule_triggered="IntrusionAfterHours",
        db_path=TEST_DB_PATH
    )
    
    alerts = database.get_alerts(db_path=TEST_DB_PATH)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["rule_triggered"] == "IntrusionAfterHours"
