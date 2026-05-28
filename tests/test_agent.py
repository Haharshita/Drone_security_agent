import pytest
import os
from drone_agent import database, agent

TEST_DB_PATH = "test_drone_patrol.db"

@pytest.fixture(autouse=True)
def setup_db():
    """Initializes a temporary test database and fills it with sample logs."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    database.init_db(TEST_DB_PATH)
    
    # Insert sample records
    database.insert_telemetry(
        timestamp="2026-05-28T00:00:10",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.0,
        battery=90,
        location_name="Office Gate",
        db_path=TEST_DB_PATH
    )
    database.insert_frame(
        timestamp="2026-05-28T00:00:10",
        frame_index=1,
        description="A suspicious blue truck is parked near the loading dock.",
        tags=["vehicle", "truck", "suspicious"],
        db_path=TEST_DB_PATH
    )
    
    database.insert_telemetry(
        timestamp="2026-05-28T00:02:10",
        latitude=37.7752,
        longitude=-122.4188,
        altitude=18.0,
        battery=80,
        location_name="Hazmat Yard",
        db_path=TEST_DB_PATH
    )
    database.insert_frame(
        timestamp="2026-05-28T00:02:10",
        frame_index=2,
        description="A yellow chemical drum tipped over.",
        tags=["chemical", "safety-hazard"],
        db_path=TEST_DB_PATH
    )
    
    # Alert insert
    database.insert_alert(
        timestamp="2026-05-28T00:02:10",
        severity="CRITICAL",
        message="SAFETY ALERT: yellow drum tipped over.",
        rule_triggered="HazardousConditionSpill",
        db_path=TEST_DB_PATH
    )
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_agent_fallback_search_alert():
    """Verify standard fallback handles alert queries correctly."""
    # Point default database path to test database path temporarily
    # Since agent imports database, we can patch the default path
    original_db = database.DEFAULT_DB_PATH
    database.DEFAULT_DB_PATH = TEST_DB_PATH
    
    try:
        sec_agent = agent.DroneSecurityAgent()
        # Force fallback mode
        sec_agent.is_llm_mode = False
        
        # Test alert query
        resp = sec_agent.run("Were there any security alerts?")
        assert "🚨 **Triggered Security & Safety Alerts:**" in resp
        assert "SAFETY ALERT: yellow drum tipped over" in resp
    finally:
        database.DEFAULT_DB_PATH = original_db

def test_agent_fallback_search_objects():
    """Verify standard fallback handles search queries correctly."""
    original_db = database.DEFAULT_DB_PATH
    database.DEFAULT_DB_PATH = TEST_DB_PATH
    
    try:
        sec_agent = agent.DroneSecurityAgent()
        sec_agent.is_llm_mode = False
        
        # Test object query
        resp = sec_agent.run("Was there a truck spotted?")
        assert "Search Results for:" in resp
        assert "Office Gate" in resp
        assert "suspicious blue truck" in resp
    finally:
        database.DEFAULT_DB_PATH = original_db

def test_executive_summary_generation():
    """Verify narrative executive summary contains relevant logged events."""
    original_db = database.DEFAULT_DB_PATH
    database.DEFAULT_DB_PATH = TEST_DB_PATH
    
    try:
        sec_agent = agent.DroneSecurityAgent()
        sec_agent.is_llm_mode = False
        
        summary = sec_agent.generate_video_summary()
        assert "patrol completed" in summary.lower() or "aerial patrol" in summary.lower()
        assert "tipped-over" in summary or "chemical" in summary
    finally:
        database.DEFAULT_DB_PATH = original_db
