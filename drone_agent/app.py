import streamlit as st
import time
import os
import sys
import pandas as pd
import json
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Add the parent directory to python path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drone_agent import database, telemetry, video_processor, rules, agent

# ---------------------------------------------------------
# STYLING & CORE CONFIG (Ultra Premium Edition)
# ---------------------------------------------------------
st.set_page_config(
    page_title="SkySentinel AI - Drone Security Command Center",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphic, Neon Cyberpunk CSS Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Share+Tech+Mono&display=swap');

    /* Main App Background Override */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0d1527 0%, #070a13 100%);
        color: #e2e8f0;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Glowing Glassmorphism Panels */
    .glass-card {
        background: rgba(15, 23, 42, 0.45);
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 15px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.35);
        box-shadow: 0 8px 32px 0 rgba(56, 189, 248, 0.08);
    }
    
    /* Neon Headers */
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.35);
    }
    
    /* Custom High-Tech Dashboard Metrics Cards */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 22px;
    }
    
    .metric-card {
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #38bdf8;
        border-radius: 10px;
        padding: 16px;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }
    
    .metric-label {
        color: #94a3b8;
        font-size: 0.75rem;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
        letter-spacing: 0.1em;
    }
    
    .metric-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 6px;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Glowing HUD Drone Camera Stream */
    .hud-container {
        border: 2px solid #38bdf8;
        border-radius: 12px;
        position: relative;
        overflow: hidden;
        margin-bottom: 12px;
        background-color: #020617;
        height: 380px;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.15);
    }
    
    /* High-tech Animated Laser Scanline */
    .hud-scanline {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: rgba(34, 197, 94, 0.4);
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.8);
        animation: scan 4s linear infinite;
        z-index: 5;
        pointer-events: none;
    }
    
    @keyframes scan {
        0% { top: 0%; }
        100% { top: 100%; }
    }
    
    .hud-header {
        position: absolute;
        top: 12px;
        left: 12px;
        right: 12px;
        display: flex;
        justify-content: space-between;
        font-family: 'Share Tech Mono', monospace;
        color: #38bdf8;
        font-size: 11px;
        z-index: 10;
        background-color: rgba(15, 23, 42, 0.75);
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    
    .hud-overlay {
        position: absolute;
        bottom: 15px;
        left: 15px;
        color: #22c55e;
        font-family: 'Share Tech Mono', monospace;
        font-size: 12px;
        z-index: 10;
        background: rgba(15, 23, 42, 0.8);
        padding: 10px;
        border-radius: 6px;
        border-left: 3px solid #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-left: 4px solid #22c55e;
    }
    
    .hud-crosshair {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 80px;
        height: 80px;
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

    /* Blinking Neon Alerts */
    .critical-alert-box {
        background-color: rgba(239, 68, 68, 0.12);
        border: 2px solid #ef4444;
        border-radius: 10px;
        padding: 14px 20px;
        margin: 10px 0;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
        animation: pulseAlert 2.5s infinite;
    }
    
    .warning-alert-box {
        background-color: rgba(245, 158, 11, 0.08);
        border: 1px solid #f59e0b;
        border-radius: 10px;
        padding: 14px 20px;
        margin: 10px 0;
        box-shadow: 0 0 10px rgba(245, 158, 11, 0.05);
    }
    
    @keyframes pulseAlert {
        0% { border-color: #ef4444; box-shadow: 0 0 5px rgba(239, 68, 68, 0.15); }
        50% { border-color: #f87171; box-shadow: 0 0 18px rgba(239, 68, 68, 0.45); }
        100% { border-color: #ef4444; box-shadow: 0 0 5px rgba(239, 68, 68, 0.15); }
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
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 Greetings! I am your SkySentinel Drone Security Assistant. You can ask me any questions about the recent drone patrol mission. For example:\n- *Were there any after-hours security alerts?*\n- *Show me all vehicle sightings.*\n- *Was there any property damage or safety hazards detected?*"}
    ]

# Preserving lifecycle modules
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
    st.markdown("<p style='color: #64748b; margin-top: -15px; font-family: monospace; font-size: 13.5px; letter-spacing: 0.05em;'>[STATUS: SECURE_COMM_ESTABLISHED] // AUTOMATED PERIMETER SCAN</p>", unsafe_allow_html=True)
with col_h2:
    # Heartbeat Pulse
    pulse_color = "#22c55e" if st.session_state.patrol_state["active"] else "#ef4444" if st.session_state.patrol_state["completed"] else "#64748b"
    pulse_text = "LIVE PERIMETER PATROL" if st.session_state.patrol_state["active"] else "PATROL SUMMARY COMPILED" if st.session_state.patrol_state["completed"] else "DRONE DOCKED // CHARGING"
    st.markdown(
        f"<div style='text-align: right; margin-top: 15px; font-weight: bold; color: {pulse_color}; letter-spacing: 0.12em; font-family: \"Share Tech Mono\", monospace; font-size: 12px;'>"
        f"● {pulse_text}"
        f"</div>",
        unsafe_allow_html=True
    )

st.write("---")

# ---------------------------------------------------------
# SIDEBAR COMMAND CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='margin-top: 0;'>⚙️ SENSOR INTEGRATIONS</h3>", unsafe_allow_html=True)
    
    mode = st.radio("VLM Analytics Engine Mode:", ["Simulated (Offline Mode)", "Live API Model Mode"])
    
    api_key_openai = st.text_input("OpenAI API Key (for Agent RAG Q&A):", type="password")
    api_key_gemini = st.text_input("Gemini API Key (for Live Video VLM):", type="password")
    
    if api_key_openai:
        os.environ["OPENAI_API_KEY"] = api_key_openai
    if api_key_gemini:
        os.environ["GEMINI_API_KEY"] = api_key_gemini
        
    st.write("---")
    
    st.markdown("<h3>🛰️ COMMAND DECK</h3>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶️ Launch Patrol", use_container_width=True):
            st.session_state.patrol_state["active"] = True
            st.session_state.patrol_state["completed"] = False
            st.session_state.patrol_state["step_idx"] = 0
            database.clear_database()
            st.session_state.sim_telemetry.reset()
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
    
    st.markdown("<h3>📡 TELEMETRY HUB</h3>", unsafe_allow_html=True)
    if st.session_state.patrol_state["current_telemetry"]:
        t_data = st.session_state.patrol_state["current_telemetry"]
        st.markdown(
            f"<div style='background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(56, 189, 248, 0.2); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 12px; line-height: 1.6;'>"
            f"<span style='color: #94a3b8;'>CHECKPOINT:</span> <strong style='color: #f8fafc;'>{t_data['location_name']}</strong><br>"
            f"<span style='color: #94a3b8;'>POSITION:</span> <strong style='color: #38bdf8;'>{t_data['latitude']:.6f}, {t_data['longitude']:.6f}</strong><br>"
            f"<span style='color: #94a3b8;'>ALTITUDE:</span> <strong style='color: #38bdf8;'>{t_data['altitude']} m</strong><br>"
            f"<span style='color: #94a3b8;'>BATTERY:</span> <strong style='color: #22c55e;'>{t_data['battery']}%</strong><br>"
            f"<span style='color: #94a3b8;'>VELOCITY:</span> <strong style='color: #38bdf8;'>{t_data['speed']} m/s</strong>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown("<p style='color: #64748b; font-style: italic; font-size: 13px;'>Diagnostic link offline. Click Launch Patrol to sync.</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIMULATION FLIGHT STEPPING
# ---------------------------------------------------------
if st.session_state.patrol_state["active"] and not st.session_state.patrol_state["completed"]:
    t_sim = st.session_state.sim_telemetry
    t_data = t_sim.step()
    
    v_proc = video_processor.VideoProcessor(mode="simulated" if "Simulated" in mode else "live")
    f_data = v_proc.get_simulated_frame(t_data["location_name"])
    
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
        
    st.session_state.patrol_state["current_telemetry"] = t_data
    st.session_state.patrol_state["current_frame"] = f_data
    st.session_state.patrol_state["telemetry_history"].append(t_data)
    st.session_state.patrol_state["step_idx"] += 1
    
    if st.session_state.patrol_state["step_idx"] >= len(telemetry.WAYPOINTS):
        st.session_state.patrol_state["active"] = False
        st.session_state.patrol_state["completed"] = True
        st.session_state.agent_model = agent.DroneSecurityAgent()
        
    time.sleep(1.8)
    st.rerun()

# ---------------------------------------------------------
# TAB CHANNELS
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🛸 LIVE MISSION CONTROL",
    "📊 PATROL DATA INDEX",
    "💬 AI SECURITY ANALYST CHAT",
    "📋 EXECUTIVE PATROL SUMMARY"
])

# ---------------------------------------------------------
# TAB 1: LIVE MISSION CONTROL (Engaging HUD Design)
# ---------------------------------------------------------
with tab1:
    p_data = st.session_state.patrol_state["current_telemetry"]
    f_data = st.session_state.patrol_state["current_frame"]
    
    # 1. PREMIUM GLASSMORPHIC METRICS GRID
    bat = p_data["battery"] if p_data else 0
    bat_icon = "🟢" if bat > 40 else "🟡" if bat > 20 else "🔴"
    
    alt = p_data["altitude"] if p_data else 0.0
    speed = p_data["speed"] if p_data else 0.0
    loc = p_data["location_name"] if p_data else "DOCKED // GROUND"
    
    # Set dynamic left border colors based on active alerts
    alerts_check = database.get_alerts(limit=1)
    status_border = "#22c55e" # secure
    if alerts_check:
        status_border = "#ef4444" if alerts_check[0]["severity"] == "CRITICAL" else "#f59e0b"
        
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card" style="border-left-color: {status_border};">
            <div class="metric-label">Drone System Health</div>
            <div class="metric-value" style="color: {status_border};">{"NOMINAL" if status_border == "#22c55e" else "WARNING" if status_border == "#f59e0b" else "CRITICAL"}</div>
        </div>
        <div class="metric-card" style="border-left-color: #38bdf8;">
            <div class="metric-label">Multi-Spectral Alt</div>
            <div class="metric-value">✈️ {alt} m</div>
        </div>
        <div class="metric-card" style="border-left-color: #22c55e;">
            <div class="metric-label">Power Core (Battery)</div>
            <div class="metric-value">{bat_icon} {bat}%</div>
        </div>
        <div class="metric-card" style="border-left-color: #a855f7;">
            <div class="metric-label">Target Zone</div>
            <div class="metric-value" style="font-size: 1.15rem; font-weight: bold; margin-top: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">📍 {loc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. MAIN OPTICAL FEED & VLM COGNITIVE REPORT
    col_cam, col_info = st.columns([3, 2])
    with col_cam:
        st.markdown("### 📷 PRIMARY OPTICAL FEED")
        
        hud_timestamp = p_data["timestamp"].replace("T", " ") if p_data else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hud_gps = f"{p_data['latitude']:.5f} N, {p_data['longitude']:.5f} W" if p_data else "37.77490 N, 122.41940 W"
        hud_battery = f"BAT: {p_data['battery']}%" if p_data else "BAT: CHARGING"
        
        # HUD Panel with scanline animation
        hud_html = f"""
        <div class="hud-container">
            <div class="hud-scanline"></div>
            <div class="hud-header">
                <div>SYS: MULTI-SPECTRAL OPTICAL // FEED_ONLINE</div>
                <div>{hud_timestamp}</div>
            </div>
            <div class="hud-crosshair"></div>
            <div class="hud-overlay">
                GPS: {hud_gps}<br>
                ALT: {alt}m | SPEED: {speed} m/s<br>
                CORD: {hud_battery}
            </div>
        """
        
        if p_data and "Warehouse" in p_data["location_name"]:
            image_found = False
            brain_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for file in os.listdir(brain_dir):
                if file.startswith("warehouse_breach") and file.endswith(".png"):
                    img_path = os.path.join(brain_dir, file)
                    with open(img_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode()
                    st.markdown(hud_html + f"<img src='data:image/png;base64,{encoded_string}' style='width: 100%; height: 100%; object-fit: cover; filter: brightness(1.1) contrast(1.1);'/></div>", unsafe_allow_html=True)
                    image_found = True
                    break
            
            if not image_found:
                st.markdown(hud_html + "<div style='display: flex; align-items: center; justify-content: center; height: 100%; color: #38bdf8; font-family: monospace; font-size: 16px;'>📷 WAREHOUSE BAY 3 - DETECTING SUSPICIOUS ACTIVITY</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(
                hud_html + 
                f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; background: linear-gradient(135deg, #070b13 0%, #0f172a 100%); color: #0284c7; font-family: monospace; font-size: 13px; text-align: center;'>"
                f"<span style='font-size: 45px; margin-bottom: 8px; filter: drop-shadow(0 0 10px rgba(56,189,248,0.4));'>🛰️</span>"
                f"<span style='font-weight: bold; color: #38bdf8; letter-spacing: 0.1em;'>SCANNING CHECKPOINT: {loc}</span>"
                f"<span style='color: #22c55e; font-size: 11px; margin-top: 5px; font-family: \"Share Tech Mono\", monospace;'>[INFRARED TELEMETRY DEPLOYED]</span>"
                f"</div></div>", 
                unsafe_allow_html=True
            )
            
    with col_info:
        st.markdown("### 🧠 VLM COGNITIVE REPORT")
        if f_data:
            st.markdown(
                f"<div class='glass-card' style='border-left: 4px solid #38bdf8; min-height: 160px; font-size: 14.5px; line-height: 1.6;'>"
                f"<strong style='color: #38bdf8; font-family: monospace; font-size: 11px;'>// COGNITIVE VISUAL ANALYSIS:</strong><br><span style='color: #f1f5f9;'>{f_data['description']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            
            st.write("")
            st.markdown("**Core Entity Identifiers (VLM Tags):**")
            tag_html = ""
            for tag in f_data["tags"]:
                bg_c = "#ef4444" if tag in ["intrusion", "suspicious", "loitering", "leak", "safety-hazard"] else "#0ea5e9"
                glow = "0 0 10px rgba(239, 68, 68, 0.4)" if bg_c == "#ef4444" else "0 0 10px rgba(14, 165, 233, 0.2)"
                tag_html += f"<span style='background-color: {bg_c}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; margin-right: 8px; font-family: monospace; display: inline-block; margin-bottom: 8px; box-shadow: {glow};'>#{tag.upper()}</span>"
            st.markdown(tag_html, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='glass-card' style='text-align: center; padding: 40px; color: #64748b; font-style: italic;'>"
                "🛰️ System docked. Awaiting multi-spectral flight feed."
                "</div>", 
                unsafe_allow_html=True
            )
            
    st.write("---")
    
    # 3. REAL-TIME ALERTS & SENSOR TELEMETRY GRAPH
    col_alerts, col_chart = st.columns([3, 2])
    with col_alerts:
        st.markdown("### 🚨 REAL-TIME SECURITY ALERTS")
        alerts_list = database.get_alerts(limit=10)
        
        if not alerts_list:
            st.markdown("<div style='background-color: rgba(34, 197, 94, 0.08); border: 1.5px solid #22c55e; border-radius: 10px; color: #22c55e; padding: 14px 20px; font-family: monospace; font-size: 13.5px; box-shadow: 0 0 15px rgba(34, 197, 94, 0.05);'>🟢 SYSTEM STATE: ALL BOUNDARIES SECURE // NO THREATS</div>", unsafe_allow_html=True)
        else:
            for a in alerts_list:
                box_class = "critical-alert-box" if a["severity"] == "CRITICAL" else "warning-alert-box"
                ts_formatted = a["timestamp"].split("T")[1][:8] if "T" in a["timestamp"] else a["timestamp"]
                st.markdown(
                    f"<div class='{box_class}'>"
                    f"<div style='display: flex; justify-content: space-between; font-weight: bold; font-family: \"Share Tech Mono\", monospace; font-size: 12px; margin-bottom: 6px;'>"
                    f"<span>🚨 [{a['severity']}] - {a['rule_triggered']}</span>"
                    f"<span>UTC: {ts_formatted}</span>"
                    f"</div>"
                    f"<div style='font-size: 13.5px; color: #f1f5f9; line-height: 1.5;'>{a['message']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
    with col_chart:
        st.markdown("### 📊 LIVE SENSOR DATA ANALYTICS")
        hist = st.session_state.patrol_state["telemetry_history"]
        if hist:
            df = pd.DataFrame(hist)
            # Create interactive dual-line plot for Battery and Altitude
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df['location_name'], 
                y=df['battery'],
                name="Battery Power (%)",
                line=dict(color='#22c55e', width=3),
                mode='lines+markers'
            ))
            
            fig.add_trace(go.Scatter(
                x=df['location_name'], 
                y=df['altitude'],
                name="Altitude (m)",
                line=dict(color='#38bdf8', width=3, dash='dash'),
                mode='lines+markers',
                yaxis="y2"
            ))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#94a3b8', size=11)),
                font=dict(color='#94a3b8', family="monospace"),
                xaxis=dict(gridcolor='rgba(255,255,255,0.05)', showline=True, linecolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title=dict(text="Battery %", font=dict(color='#22c55e')), gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#22c55e')),
                yaxis2=dict(
                    title=dict(text="Altitude (m)", font=dict(color='#38bdf8')),
                    tickfont=dict(color='#38bdf8'),
                    anchor="x",
                    overlaying="y",
                    side="right"
                ),
                height=260
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            # Draw standard 2D Grid map when no telemetry exists
            st.markdown(
                "<div class='glass-card' style='text-align: center; padding: 80px; color: #64748b; font-family: monospace; font-size: 13.5px; height: 260px; display: flex; align-items: center; justify-content: center;'>"
                "📊 Telemetry stream offline. Plots will compile dynamically during patrol."
                "</div>", 
                unsafe_allow_html=True
            )

# ---------------------------------------------------------
# TAB 2: PATROL DATA INDEX
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📊 SQLite Relational Index Audit")
    st.write("This table shows the synchronized live records indexed inside the local SQLite database. Each frame analysis is joined on timestamp with corresponding GPS and battery telemetry.")
    
    logs = database.get_synced_logs()
    if logs:
        df_logs = pd.DataFrame(logs)
        cols = ['timestamp', 'location_name', 'frame_index', 'description', 'altitude', 'battery', 'latitude', 'longitude']
        df_logs = df_logs[[c for c in cols if c in df_logs.columns]]
        st.dataframe(df_logs, use_container_width=True)
        
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
            
    user_input = st.chat_input("Ask a question about the drone patrol history...")
    active_query = user_input or quick_q
    
    if active_query:
        st.session_state.messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)
            
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
        
        for idx, l in enumerate(logs):
            time_str = l["timestamp"].split("T")[1][:8] if "T" in l["timestamp"] else l["timestamp"]
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
