import streamlit as st
import time
import os
import sys
import pandas as pd
import json
from datetime import datetime

# Add the parent directory to python path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drone_agent import database, telemetry, video_processor, rules, agent

# ---------------------------------------------------------
# STYLING & CORE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="SkySentinel AI - Drone Security Analyst",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech CSS Injection for visual WOW factor
st.markdown("""
<style>
    /* Main Layout */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Headers & Text */
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
    }
    
    /* Metrics Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        text-transform: uppercase;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em;
    }
    
    /* High-tech custom alerts box */
    .critical-alert-box {
        background-color: rgba(239, 68, 68, 0.15);
        border: 2px solid #ef4444;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 8px 0;
        animation: pulse 2s infinite;
    }
    .warning-alert-box {
        background-color: rgba(245, 158, 11, 0.12);
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 8px 0;
    }
    
    @keyframes pulse {
        0% { border-color: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,0.2); }
        50% { border-color: #f87171; box-shadow: 0 0 15px rgba(239,68,68,0.6); }
        100% { border-color: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,0.2); }
    }
    
    /* Drone Camera Mock Visual */
    .hud-container {
        border: 2px solid #0284c7;
        border-radius: 8px;
        position: relative;
        overflow: hidden;
        margin-bottom: 10px;
        background-color: #020617;
        height: 380px;
    }
    .hud-header {
        position: absolute;
        top: 10px;
        left: 10px;
        right: 10px;
        display: flex;
        justify-content: space-between;
        font-family: monospace;
        color: #38bdf8;
        font-size: 11px;
        z-index: 10;
        background-color: rgba(15, 23, 42, 0.6);
        padding: 4px 8px;
        border-radius: 4px;
    }
    .hud-overlay {
        position: absolute;
        bottom: 15px;
        left: 15px;
        color: #22c55e;
        font-family: monospace;
        font-size: 12px;
        z-index: 10;
        background: rgba(15,23,42,0.7);
        padding: 8px;
        border-radius: 4px;
        border-left: 3px solid #22c55e;
    }
    .hud-crosshair {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60px;
        height: 60px;
        border: 1px dashed rgba(56, 189, 248, 0.4);
        border-radius: 50%;
        pointer-events: none;
    }
    .hud-crosshair::before {
        content: '';
        position: absolute;
        top: 50%; width: 100%; height: 1px;
        background-color: rgba(56, 189, 248, 0.3);
    }
    .hud-crosshair::after {
        content: '';
        position: absolute;
        left: 50%; height: 100%; width: 1px;
        background-color: rgba(56, 189, 248, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
database.init_db()

# ---------------------------------------------------------
# SESSION STATE MANAGEMENT
# ---------------------------------------------------------
if "patrol_state" not in st.session_state:
    st.session_state.patrol_state = {
        "active": False,
        "step_idx": 0,
        "completed": False,
        "current_telemetry": None,
        "current_frame": None,
        "telemetry_history": [],
        "alerts_triggered": []
    }

if "messages" not in st.session_state:
    # Default greeting
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 Greetings! I am your SkySentinel Drone Security Assistant. You can ask me any questions about the recent drone patrol mission. For example:\n- *Were there any after-hours security alerts?*\n- *Show me all vehicle sightings.*\n- *Was there any property damage or safety hazards detected?*"}
    ]

# Keep static simulators/agents in st.session_state to preserve lifecycle
if "sim_telemetry" not in st.session_state:
    st.session_state.sim_telemetry = telemetry.TelemetrySimulator()
if "agent_model" not in st.session_state:
    st.session_state.agent_model = agent.DroneSecurityAgent()
if "rules_engine" not in st.session_state:
    st.session_state.rules_engine = rules.AlertRulesEngine()

# ---------------------------------------------------------
# APPLICATION HEADER
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("<h1>🛸 SkySentinel AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; margin-top: -15px;'>Real-Time Intelligent Drone Security Analyst Agent & Patrol Control Center</p>", unsafe_allow_html=True)
with col_h2:
    # Heartbeat Indicator
    pulse_color = "#22c55e" if st.session_state.patrol_state["active"] else "#64748b"
    pulse_text = "LIVE ACTIVE PATROL" if st.session_state.patrol_state["active"] else "PATROL DOCKED"
    st.markdown(
        f"<div style='text-align: right; margin-top: 15px; font-weight: bold; color: {pulse_color}; letter-spacing: 0.1em; font-family: monospace;'>"
        f"● {pulse_text}"
        f"</div>",
        unsafe_allow_html=True
    )

st.write("---")

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ MISSION CONTROLS")
    
    # Selection Mode
    mode = st.radio("VLM Analytics Engine Mode:", ["Simulated (Offline Mode)", "Live API Model Mode"])
    
    api_key_openai = st.text_input("OpenAI API Key (for Agent RAG Q&A):", type="password")
    api_key_gemini = st.text_input("Gemini API Key (for Live Video VLM):", type="password")
    
    # Store keys in env vars for modules to pick up
    if api_key_openai:
        os.environ["OPENAI_API_KEY"] = api_key_openai
    if api_key_gemini:
        os.environ["GEMINI_API_KEY"] = api_key_gemini
        
    st.write("---")
    
    st.markdown("### 🛰️ COMMAND DECK")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ Launch Patrol", use_container_width=True):
            st.session_state.patrol_state["active"] = True
            st.session_state.patrol_state["completed"] = False
            st.session_state.patrol_state["step_idx"] = 0
            database.clear_database() # Clear old runs for a clean visual experience
            st.session_state.sim_telemetry.reset()
            # Clear st chat history on restart
            st.session_state.messages = [st.session_state.messages[0]]
            st.rerun()
            
    with col_btn2:
        if st.button("⏹️ Reset/Dock", use_container_width=True):
            st.session_state.patrol_state["active"] = False
            st.session_state.patrol_state["completed"] = False
            st.session_state.patrol_state["step_idx"] = 0
            database.clear_database()
            st.session_state.sim_telemetry.reset()
            st.rerun()
            
    st.write("---")
    
    # Quick Telemetry readout in sidebar
    st.markdown("### 📡 CURRENT TELEMETRY STATE")
    if st.session_state.patrol_state["current_telemetry"]:
        t_data = st.session_state.patrol_state["current_telemetry"]
        st.markdown(f"**Location**: `{t_data['location_name']}`")
        st.markdown(f"**GPS**: `{t_data['latitude']:.6f}, {t_data['longitude']:.6f}`")
        st.markdown(f"**Altitude**: `{t_data['altitude']} m`")
        st.markdown(f"**Battery**: `{t_data['battery']}%`")
        st.markdown(f"**Ground Speed**: `{t_data['speed']} m/s`")
    else:
        st.markdown("<p style='color: #64748b; font-style: italic;'>Telemetry offline. Click Launch Patrol to initialize.</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIMULATION WORKFLOW STEPPING
# ---------------------------------------------------------
# This drives the visual stepping of our simulated drone flight path
if st.session_state.patrol_state["active"] and not st.session_state.patrol_state["completed"]:
    # Run a step
    t_sim = st.session_state.sim_telemetry
    t_data = t_sim.step()
    
    # Connect video processor
    v_proc = video_processor.VideoProcessor(mode="simulated" if "Simulated" in mode else "live")
    # For simulation, frame description maps to current location
    f_data = v_proc.get_simulated_frame(t_data["location_name"])
    
    # Save step to SQLite
    database.insert_telemetry(
        timestamp=t_data["timestamp"],
        latitude=t_data["latitude"],
        longitude=t_data["longitude"],
        altitude=t_data["altitude"],
        battery=t_data["battery"],
        location_name=t_data["location_name"]
    )
    
    database.insert_frame(
        timestamp=t_data["timestamp"],
        frame_index=f_data["frame_index"],
        description=f_data["description"],
        tags=f_data["tags"]
    )
    
    # Evaluate safety / security rules
    r_engine = st.session_state.rules_engine
    triggered_alerts = r_engine.evaluate(f_data, t_data)
    for alert in triggered_alerts:
        database.insert_alert(
            timestamp=t_data["timestamp"],
            severity=alert["severity"],
            message=alert["message"],
            rule_triggered=alert["rule_triggered"]
        )
        st.session_state.patrol_state["alerts_triggered"].insert(0, {
            "timestamp": t_data["timestamp"],
            "severity": alert["severity"],
            "message": alert["message"]
        })
        
    # Update Session State
    st.session_state.patrol_state["current_telemetry"] = t_data
    st.session_state.patrol_state["current_frame"] = f_data
    st.session_state.patrol_state["telemetry_history"].append(t_data)
    st.session_state.patrol_state["step_idx"] += 1
    
    # Patrol boundary loop: simulation runs for 8 steps (full circuit)
    if st.session_state.patrol_state["step_idx"] >= len(telemetry.WAYPOINTS):
        st.session_state.patrol_state["active"] = False
        st.session_state.patrol_state["completed"] = True
        
        # Instantiate/Re-init the agent to index the final records
        st.session_state.agent_model = agent.DroneSecurityAgent()
        
    # Auto-stepping pacing control
    time.sleep(1.8)
    st.rerun()

# ---------------------------------------------------------
# TABS DASHBOARD VIEW
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🛸 LIVE MISSION CONTROL",
    "📊 PATROL DATA INDEX",
    "💬 AI SECURITY ANALYST CHAT",
    "📋 EXECUTIVE PATROL SUMMARY"
])

# ---------------------------------------------------------
# TAB 1: LIVE MISSION CONTROL
# ---------------------------------------------------------
with tab1:
    p_data = st.session_state.patrol_state["current_telemetry"]
    f_data = st.session_state.patrol_state["current_frame"]
    
    # 1. TOP METRICS PANEL
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        bat = p_data["battery"] if p_data else 0
        bat_color = "🟢" if bat > 40 else "🟡" if bat > 20 else "🔴"
        st.metric("Battery Charge", f"{bat_color} {bat}%", delta="-0.4% per cycle")
    with col_m2:
        alt = p_data["altitude"] if p_data else 0.0
        st.metric("Flight Altitude", f"✈️ {alt} m")
    with col_m3:
        speed = p_data["speed"] if p_data else 0.0
        st.metric("Ground Speed", f"🚀 {speed} m/s")
    with col_m4:
        loc = p_data["location_name"] if p_data else "DOCKED"
        st.metric("Target Patrol Segment", f"📍 {loc}")
        
    st.write("")
    
    # 2. MAIN CAMERA STREAM & VISUAL INTELLIGENCE
    col_cam, col_info = st.columns([3, 2])
    with col_cam:
        st.markdown("### 📷 PRIMARY OPTICAL FEED")
        
        # HUD View
        hud_timestamp = p_data["timestamp"].replace("T", " ") if p_data else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hud_gps = f"{p_data['latitude']:.5f} N, {p_data['longitude']:.5f} W" if p_data else "37.77490 N, 122.41940 W"
        hud_battery = f"BAT: {p_data['battery']}%" if p_data else "BAT: CHARGING"
        
        # Draw mock camera stream using custom HTML layout
        hud_html = f"""
        <div class="hud-container">
            <div class="hud-header">
                <div>SYS: OK | SENS: MULTI-SPECTRAL</div>
                <div>{hud_timestamp}</div>
            </div>
            <div class="hud-crosshair"></div>
            <div class="hud-overlay">
                GPS: {hud_gps}<br>
                ALT: {alt}m | {hud_battery}<br>
                CAMERA: THERMAL / HD-OPTICAL FEED
            </div>
        """
        
        # Check if the drone is at the Warehouse Loading Dock checkpoint.
        # If so, show the custom AI-generated image asset we created!
        # Otherwise, show a premium stylized graphic.
        if p_data and "Warehouse" in p_data["location_name"]:
            # Display our premium generated intrusion mockup!
            # Since warehouse_breach is generated in the brain directory, we will embed it as base64 or copy it.
            # Let's write a python placeholder to see if we can find the image file and render it
            image_found = False
            brain_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Scan files to find the generated warehouse breach image
            for file in os.listdir(brain_dir):
                if file.startswith("warehouse_breach") and file.endswith(".png"):
                    img_path = os.path.join(brain_dir, file)
                    # Convert to base64 to embed in HTML
                    with open(img_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode()
                    st.markdown(hud_html + f"<img src='data:image/png;base64,{encoded_string}' style='width: 100%; height: 100%; object-fit: cover;'/></div>", unsafe_allow_html=True)
                    image_found = True
                    break
            
            if not image_found:
                st.markdown(hud_html + "<div style='display: flex; align-items: center; justify-content: center; height: 100%; color: #38bdf8; font-family: monospace; font-size: 16px;'>📷 WAREHOUSE BAY 3 - DETECTING SUSPICIOUS ACTIVITY</div></div>", unsafe_allow_html=True)
        else:
            # Draw standard premium drone optical camera mock
            st.markdown(
                hud_html + 
                f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; background: linear-gradient(135deg, #090d16 0%, #111827 100%); color: #0284c7; font-family: monospace; font-size: 14px; text-align: center;'>"
                f"<span style='font-size: 40px; margin-bottom: 10px;'>🛰️</span>"
                f"<span style='font-weight: bold; color: #38bdf8;'>SCANNING CHECKPOINT: {loc}</span>"
                f"<span style='color: #64748b; font-size: 11px; margin-top: 5px;'>THERMAL STABILIZATION IN PROGRESS...</span>"
                f"</div></div>", 
                unsafe_allow_html=True
            )
            
    with col_info:
        st.markdown("### 🧠 VLM COGNITIVE REPORT")
        if f_data:
            st.markdown(
                f"<div style='background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 18px; border-radius: 8px; font-size: 15px; min-height: 140px;'>"
                f"<strong style='color: #38bdf8;'>Visual Description:</strong><br>{f_data['description']}"
                f"</div>",
                unsafe_allow_html=True
            )
            
            # Tags Rendering
            st.write("")
            st.markdown("**Context Tags:**")
            tag_html = ""
            for tag in f_data["tags"]:
                # Color code tags
                bg_c = "#ef4444" if tag in ["intrusion", "suspicious", "loitering", "leak", "safety-hazard"] else "#0ea5e9"
                tag_html += f"<span style='background-color: {bg_c}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; margin-right: 6px; font-family: monospace;'>#{tag.upper()}</span>"
            st.markdown(tag_html, unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #64748b; font-style: italic; padding: 20px;'>Awaiting visual feed. Start patrol to activate VLM processor.</p>", unsafe_allow_html=True)
            
    st.write("---")
    
    # 3. REAL-TIME ALERTS & LOCATION MAP
    col_alerts, col_map = st.columns([3, 2])
    with col_alerts:
        st.markdown("### 🚨 SECURITY & SAFETY ALERTS CONSOLE")
        alerts_list = database.get_alerts(limit=10)
        
        if not alerts_list:
            st.markdown("<div style='background-color: rgba(34, 197, 94, 0.1); border: 1px solid #22c55e; border-radius: 8px; color: #22c55e; padding: 12px 18px; font-family: monospace;'>🟢 ALL PROPERTY BOUNDARIES NOMINAL - SECURE</div>", unsafe_allow_html=True)
        else:
            for a in alerts_list:
                box_class = "critical-alert-box" if a["severity"] == "CRITICAL" else "warning-alert-box"
                ts_formatted = a["timestamp"].split("T")[1][:8] if "T" in a["timestamp"] else a["timestamp"]
                st.markdown(
                    f"<div class='{box_class}'>"
                    f"<div style='display: flex; justify-content: space-between; font-weight: bold; font-family: monospace; font-size: 12px; margin-bottom: 4px;'>"
                    f"<span>🚨 [{a['severity']}] - {a['rule_triggered']}</span>"
                    f"<span>TIME: {ts_formatted}</span>"
                    f"</div>"
                    f"<div style='font-size: 13.5px; color: #f1f5f9;'>{a['message']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
    with col_map:
        st.markdown("### 🗺️ SPATIAL PATROL ROUTE")
        hist = st.session_state.patrol_state["telemetry_history"]
        if hist:
            df = pd.DataFrame(hist)
            # Display coordinates on Streamlit map
            st.map(df, latitude="latitude", longitude="longitude", size=20, zoom=16)
        else:
            st.markdown("<p style='color: #64748b; font-style: italic; text-align: center; padding: 50px;'>Drone coordinate tracking offline. Map will load when flight path begins.</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: PATROL DATA INDEX
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📊 SQLite Relational Index Audit")
    st.write("This table shows the synchronized live records indexed inside the local SQLite database. Each frame analysis is joined on timestamp with corresponding GPS and battery telemetry.")
    
    logs = database.get_synced_logs()
    if logs:
        df_logs = pd.DataFrame(logs)
        # Reorder columns for optimal readability
        cols = ['timestamp', 'location_name', 'frame_index', 'description', 'altitude', 'battery', 'latitude', 'longitude']
        df_logs = df_logs[[c for c in cols if c in df_logs.columns]]
        st.dataframe(df_logs, use_container_width=True)
        
        # Export option
        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Patrol Audit Logs (CSV)",
            data=csv,
            file_name="drone_patrol_audit_log.csv",
            mime="text/csv"
        )
    else:
        st.markdown("<p style='color: #64748b; font-style: italic; padding: 20px;'>Database is currently empty. Run a simulation patrol to generate indices.</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: AI SECURITY ANALYST CHAT (RAG Chatbot)
# ---------------------------------------------------------
with tab3:
    st.markdown("### 💬 Chat with SkySentinel AI Agent")
    st.write("Analyze patrol anomalies, security logs, or telemetry in natural language. Powered by SQLite full-text search indexing.")
    
    # Display message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Suggestions list
    st.markdown("**Quick Query Suggestions:**")
    col_sq1, col_sq2, col_sq3 = st.columns(3)
    
    quick_q = None
    with col_sq1:
        if st.button("🚨 Were there any after-hours security alerts?", use_container_width=True):
            quick_q = "Were there any after-hours security alerts?"
    with col_sq2:
        if st.button("🚚 Was there any blue truck spotted near loading docks?", use_container_width=True):
            quick_q = "Was there any blue truck spotted near loading docks?"
    with col_sq3:
        if st.button("⚠️ Was there any safety hazard or property damage?", use_container_width=True):
            quick_q = "Was there any safety hazard or property damage?"
            
    # Catch user chat input
    user_input = st.chat_input("Ask a question about the drone patrol history...")
    
    # Process if either keyboard input or quick-button clicked
    active_query = user_input or quick_q
    
    if active_query:
        # User message
        st.session_state.messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)
            
        # Agent response
        with st.chat_message("assistant"):
            with st.spinner("AI security analyst auditing database records..."):
                agent_runner = st.session_state.agent_model
                response = agent_runner.run(active_query)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------------------------------------------------
# TAB 4: EXECUTIVE PATROL SUMMARY
# ---------------------------------------------------------
with tab4:
    st.markdown("### 📋 Executive Patrol Summary Dashboard")
    st.write("Generates formal summary insights of the mission for reporting to executive property managers and insurance audits (Bonus Feature).")
    
    if st.session_state.patrol_state["completed"] or len(database.get_synced_logs()) > 0:
        agent_runner = st.session_state.agent_model
        
        # 1-sentence summarization
        with st.spinner("Compiling summary details..."):
            exec_summary = agent_runner.generate_video_summary()
            
        st.markdown(
            f"<div style='background-color: #0f172a; border: 1.5px solid #22d3ee; border-radius: 8px; padding: 24px; font-size: 16px; line-height: 1.6;'>"
            f"<h4>📊 Drone Security Mission Narrative</h4>"
            f"<p style='color: #e2e8f0; font-weight: 500;'>{exec_summary}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        st.write("")
        st.markdown("#### ⏳ Patrol Flight Timeline & Events")
        
        logs = database.get_synced_logs()
        alerts = database.get_alerts()
        
        # Display timeline
        for idx, l in enumerate(logs):
            time_str = l["timestamp"].split("T")[1][:8] if "T" in l["timestamp"] else l["timestamp"]
            
            # Check if there is an alert at this checkpoint
            checkpoint_alerts = [a for a in alerts if a["timestamp"] == l["timestamp"]]
            
            alert_indicator = ""
            if checkpoint_alerts:
                severity = checkpoint_alerts[0]["severity"]
                c = "🔴" if severity == "CRITICAL" else "🟡"
                alert_indicator = f"<span style='color: #ef4444; font-weight: bold;'> {c} [{severity} ALERT]</span>"
                
            st.markdown(
                f"<div style='background-color: #1e293b; padding: 12px; margin-bottom: 8px; border-radius: 6px; font-size: 13.5px;'>"
                f"🕰️ <strong>{time_str}</strong> | 📍 Checkpoint: <strong>{l['location_name']}</strong> (Alt: {l['altitude']}m | Bat: {l['battery']}%){alert_indicator}<br>"
                f"<span style='color: #94a3b8;'>Visual: {l['description']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<p style='color: #64748b; font-style: italic; padding: 20px;'>Narrative generation offline. Please launch and run the drone security patrol circuit first.</p>", unsafe_allow_html=True)
