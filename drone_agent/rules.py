from datetime import datetime

class AlertRulesEngine:
    def __init__(self, start_work_hour=6, end_work_hour=21):
        self.start_work_hour = start_work_hour
        self.end_work_hour = end_work_hour

    def evaluate(self, frame_log, telemetry_log):
        """
        Evaluates a synchronized frame and telemetry state against security/safety rules.
        Returns a list of triggered alerts: dict(severity, message, rule_triggered)
        """
        alerts = []
        
        # Parse timestamp from telemetry (default to now if parse fails)
        ts_str = telemetry_log.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            ts = datetime.now()
            
        hour = ts.hour
        is_after_hours = (hour < self.start_work_hour) or (hour >= self.end_work_hour)
        
        tags = frame_log.get("tags", [])
        description = frame_log.get("description", "").lower()
        location = telemetry_log.get("location_name", "")
        battery = telemetry_log.get("battery", 100)
        altitude = telemetry_log.get("altitude", 0.0)
        
        # --- RULE 1: INTRUSION & LOITERING (Security - CRITICAL) ---
        if "person" in tags or "loitering" in tags or "individual" in description:
            if is_after_hours:
                alerts.append({
                    "severity": "CRITICAL",
                    "message": f"SECURITY INTRUSION: Unauthorized person spotted near '{location}' at {ts.strftime('%H:%M')} (after hours). Description: {frame_log.get('description')}",
                    "rule_triggered": "IntrusionAfterHours"
                })
            elif "suspicious" in tags or "rear" in description or "window" in description:
                alerts.append({
                    "severity": "WARNING",
                    "message": f"SUSPICIOUS ACTIVITY: Individual observed behaving suspiciously around HQ Perimeter. Description: {frame_log.get('description')}",
                    "rule_triggered": "SuspiciousLoitering"
                })
                
        # --- RULE 2: UNAUTHORIZED VEHICLES (Security - WARNING / CRITICAL) ---
        if "vehicle" in tags or "truck" in tags or "sedan" in tags:
            # Check restricted zones like loading docks or hazmat zone
            if "loading docks" in location.lower() or "hazardous" in location.lower():
                if is_after_hours:
                    severity = "CRITICAL"
                    prefix = "UNAUTHORIZED RESTRICTED VEHICLE"
                else:
                    severity = "WARNING"
                    prefix = "UNAUTHORIZED VEHICLE PATROL EXCEPTION"
                    
                alerts.append({
                    "severity": severity,
                    "message": f"{prefix}: Vehicle detected at restricted area '{location}' after hours. Details: {frame_log.get('description')}",
                    "rule_triggered": "RestrictedAreaVehicle"
                })
            elif "suspicious" in tags or "dark" in description:
                alerts.append({
                    "severity": "WARNING",
                    "message": f"SUSPICIOUS VEHICLE: Vehicle parked with headlights off in unassigned zone at '{location}'. Details: {frame_log.get('description')}",
                    "rule_triggered": "SuspiciousVehicleParked"
                })

        # --- RULE 3: CHEMICAL SPILLS / HAZARDS (Safety - CRITICAL) ---
        hazard_tags = {"chemical", "leak", "tipped-over", "fire", "smoke", "safety-hazard"}
        triggered_hazard_tags = hazard_tags.intersection(set(tags))
        if triggered_hazard_tags or "tipped over" in description or "chemical leak" in description:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"SAFETY ALERT: Property damage or hazardous condition detected at '{location}'. Details: {frame_log.get('description')}",
                "rule_triggered": "HazardousConditionSpill"
            })

        # --- RULE 4: DRONE SAFETY AND BATTERY (Safety - WARNING) ---
        if battery < 20 and altitude > 5.0:
            alerts.append({
                "severity": "WARNING",
                "message": f"SYSTEM CRITICAL: Drone battery low ({battery}%) while performing high-altitude patrol ({altitude}m) near '{location}'. Immediate RTH (Return-To-Home) required.",
                "rule_triggered": "CriticalBatteryHighAltitude"
            })
        elif battery < 10:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"SYSTEM CRITICAL: Extreme battery drain ({battery}%). Force landing initiated near '{location}'.",
                "rule_triggered": "BatteryExhaustedForceLanding"
            })

        return alerts
