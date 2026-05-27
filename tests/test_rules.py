import pytest
from datetime import datetime
from drone_agent import rules

def test_intrusion_rule_triggers_after_hours():
    """Verify that a person detected outside work hours triggers a CRITICAL alert."""
    engine = rules.AlertRulesEngine(start_work_hour=6, end_work_hour=21)
    
    # Midnight (after hours)
    telemetry_log = {
        "timestamp": "2026-05-28T00:15:00",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.0,
        "battery": 80,
        "location_name": "Main Office Gate"
    }
    
    frame_log = {
        "tags": ["person", "loitering"],
        "description": "A person wearing a dark jacket stands close to the entrance window."
    }
    
    alerts = engine.evaluate(frame_log, telemetry_log)
    
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["rule_triggered"] == "IntrusionAfterHours"
    assert "SECURITY INTRUSION" in alerts[0]["message"]

def test_no_alert_for_person_during_working_hours():
    """Verify that a person spotted during normal working hours does not trigger a critical intrusion alert."""
    engine = rules.AlertRulesEngine(start_work_hour=6, end_work_hour=21)
    
    # 12:00 PM (working hours)
    telemetry_log = {
        "timestamp": "2026-05-28T12:00:00",
        "location_name": "Main Office Gate"
    }
    
    frame_log = {
        "tags": ["person", "staff"],
        "description": "Standard staff member arriving at the front gate entrance."
    }
    
    alerts = engine.evaluate(frame_log, telemetry_log)
    
    # Should not trigger after-hours intrusion alert
    assert not any(a["rule_triggered"] == "IntrusionAfterHours" for a in alerts)

def test_low_battery_rule():
    """Verify drone safety trigger flags low battery while at altitude."""
    engine = rules.AlertRulesEngine()
    
    telemetry_log = {
        "timestamp": "2026-05-28T12:00:00",
        "battery": 15,
        "altitude": 15.0,
        "location_name": "Boundary Perimeter A"
    }
    
    frame_log = {
        "tags": ["secure"],
        "description": "Scanning perimeter fence line. All clear."
    }
    
    alerts = engine.evaluate(frame_log, telemetry_log)
    
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "WARNING"
    assert alerts[0]["rule_triggered"] == "CriticalBatteryHighAltitude"

def test_tipped_drum_chemical_hazard_rule():
    """Verify that chemical container damage triggers safety alerts."""
    engine = rules.AlertRulesEngine()
    
    telemetry_log = {
        "timestamp": "2026-05-28T12:00:00",
        "location_name": "Hazardous Waste Zone"
    }
    
    frame_log = {
        "tags": ["chemical", "tipped-over", "leak"],
        "description": "A yellow chemical drum has fallen on its side with a green liquid puddle nearby."
    }
    
    alerts = engine.evaluate(frame_log, telemetry_log)
    
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["rule_triggered"] == "HazardousConditionSpill"
