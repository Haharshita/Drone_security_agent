import time
import math
from datetime import datetime, timedelta

# Realistic GPS waypoints for a commercial estate (centered around a warehouse/office park in San Francisco)
WAYPOINTS = [
    {"name": "Drone Docking Station", "lat": 37.774900, "lon": -122.419400, "alt": 0.0},
    {"name": "Main Entrance Gate", "lat": 37.775500, "lon": -122.419000, "alt": 15.0},
    {"name": "Visitor Parking Lot", "lat": 37.775800, "lon": -122.418000, "alt": 20.0},
    {"name": "Office HQ Perimeter", "lat": 37.775200, "lon": -122.417200, "alt": 25.0},
    {"name": "Warehouse Loading Docks", "lat": 37.774200, "lon": -122.417800, "alt": 18.0},
    {"name": "South Fenced Boundary", "lat": 37.773600, "lon": -122.418900, "alt": 22.0},
    {"name": "Hazardous Waste Zone", "lat": 37.774100, "lon": -122.420100, "alt": 20.0},
    {"name": "Drone Docking Station", "lat": 37.774900, "lon": -122.419400, "alt": 0.0}
]

class TelemetrySimulator:
    def __init__(self, step_seconds=5, battery_drain_rate=0.4):
        self.waypoints = WAYPOINTS
        self.step_seconds = step_seconds
        self.battery_drain_rate = battery_drain_rate
        
        # State variables
        self.current_waypoint_index = 0
        self.next_waypoint_index = 1
        self.segment_progress = 0.0  # 0.0 to 1.0 between current and next waypoint
        
        self.lat = WAYPOINTS[0]["lat"]
        self.lon = WAYPOINTS[0]["lon"]
        self.alt = WAYPOINTS[0]["alt"]
        self.battery = 100
        self.speed = 0.0  # m/s
        
        # Simulated time starting at 11:58 PM (to trigger the loitering at midnight safety rules!)
        self.simulated_time = datetime.strptime("2026-05-28T23:58:00", "%Y-%m-%dT%H:%M:%S")

    def step(self):
        """Advances the simulation state by step_seconds."""
        self.simulated_time += timedelta(seconds=self.step_seconds)
        
        # Calculate how much to advance progress
        # Speed of drone simulation: let's advance segment progress by 0.1 each step
        self.segment_progress += 0.1
        
        if self.segment_progress >= 1.0:
            self.segment_progress = 0.0
            self.current_waypoint_index = self.next_waypoint_index
            self.next_waypoint_index = (self.current_waypoint_index + 1) % len(self.waypoints)
            
        current_wp = self.waypoints[self.current_waypoint_index]
        next_wp = self.waypoints[self.next_waypoint_index]
        
        # Linear interpolation of coordinate values for smooth visual movement
        t = self.segment_progress
        self.lat = current_wp["lat"] + (next_wp["lat"] - current_wp["lat"]) * t
        self.lon = current_wp["lon"] + (next_wp["lon"] - current_wp["lon"]) * t
        self.alt = current_wp["alt"] + (next_wp["alt"] - current_wp["alt"]) * t
        
        # Drain battery gradually
        self.battery = max(0, int(100 - (self.battery_drain_rate * (self.current_waypoint_index * 10 + t * 10))))
        
        # Speed simulation: slow down when near docking station, speed up elsewhere
        location_name = current_wp["name"]
        if "Docking" in location_name and t < 0.3:
            self.speed = 1.2
        elif "Docking" in location_name:
            self.speed = 0.0
        else:
            self.speed = 8.5 # m/s
            
        return {
            "timestamp": self.simulated_time.isoformat(),
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "altitude": round(self.alt, 2),
            "battery": self.battery,
            "location_name": location_name,
            "speed": self.speed
        }
        
    def reset(self):
        """Resets the simulator state."""
        self.__init__(self.step_seconds, self.battery_drain_rate)
