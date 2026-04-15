import streamlit as st
import requests
import time
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartFleet Dashboard",
    page_icon="🚛",
    layout="wide",
)

GATEWAY_URL = "http://localhost:8000"

# ── Helper functions ─────────────────────────────────────────────────────────
def get_vehicles():
    try:
        r = requests.get(f"{GATEWAY_URL}/vehicles", timeout=3)
        return r.json().get("vehicles", [])
    except Exception:
        return []

def get_alerts():
    try:
        r = requests.get(f"{GATEWAY_URL}/alerts?limit=10", timeout=3)
        return r.json().get("alerts", [])
    except Exception:
        return []

def status_color(status):
    return {"OK": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}.get(status, "⚪")

def health_color(score):
    if score >= 80: return "normal"
    if score >= 50: return "inverse"
    return "off"

def fuel_bar(pct):
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🚛 SmartFleet — Fleet Health Monitor")
st.caption("Live telemetry dashboard · refreshes every 3 seconds")

# ── Fetch data ───────────────────────────────────────────────────────────────
vehicles = get_vehicles()
alerts   = get_alerts()

# ── Summary metrics row ──────────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

total     = len(vehicles)
ok_count  = sum(1 for v in vehicles if v["status"] == "OK")
warn      = sum(1 for v in vehicles if v["status"] == "WARNING")
critical  = sum(1 for v in vehicles if v["status"] == "CRITICAL")
avg_fuel  = sum(v["fuel_level"] for v in vehicles) / total if total else 0
avg_health= sum(v["health_score"] for v in vehicles) / total if total else 0

with col1:
    st.metric("Total vehicles", total)
with col2:
    st.metric("Fleet health avg", f"{avg_health:.0f}/100",
              delta=f"{ok_count} OK · {warn} warn · {critical} critical")
with col3:
    st.metric("Avg fuel level", f"{avg_fuel:.1f}%")
with col4:
    st.metric("Active alerts", len(alerts),
              delta="critical" if critical > 0 else "all clear",
              delta_color="inverse" if critical > 0 else "normal")

st.markdown("---")

# ── Per-vehicle cards ────────────────────────────────────────────────────────
if not vehicles:
    st.warning("No data yet — make sure the gateway and generator are running.")
else:
    st.subheader("Vehicle status")

    for v in vehicles:
        icon   = status_color(v["status"])
        health = v["health_score"]
        ts     = datetime.fromtimestamp(v["timestamp"]).strftime("%H:%M:%S") if v.get("timestamp") else "—"

        with st.expander(f"{icon}  {v['vehicle_id']}  —  Health: {health:.0f}/100  —  {v['status']}  (last update {ts})", expanded=True):
            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                temp = v["engine_temp"]
                delta_color = "inverse" if temp > 105 else "normal"
                st.metric("Engine temp", f"{temp:.1f} °C",
                          delta="OVERHEATING" if temp > 105 else "normal",
                          delta_color=delta_color)

            with c2:
                fuel = v["fuel_level"]
                st.metric("Fuel level", f"{fuel:.1f}%",
                          delta="LOW FUEL" if fuel < 15 else "ok",
                          delta_color="inverse" if fuel < 15 else "normal")
                st.caption(fuel_bar(fuel))

            with c3:
                st.metric("Speed", f"{v['speed']:.1f} km/h",
                          delta="SPEEDING" if v["speed"] > 110 else "normal",
                          delta_color="inverse" if v["speed"] > 110 else "normal")

            with c4:
                bat = v["battery"]
                st.metric("Battery", f"{bat:.2f} V",
                          delta="LOW" if bat < 11.5 else "ok",
                          delta_color="inverse" if bat < 11.5 else "normal")

            with c5:
                st.metric("RPM", f"{v['rpm']:.0f}")
                st.metric("Anomalies", v.get("anomaly_count", 0))

# ── Alert feed ───────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Recent alerts")

if not alerts:
    st.success("No alerts — all vehicles operating normally.")
else:
    for alert in alerts:
        ts  = datetime.fromtimestamp(alert["timestamp"]).strftime("%H:%M:%S")
        sev = alert["severity"]
        icon = {"CRITICAL": "🔴", "WARNING": "🟡", "ALERT": "🟠"}.get(sev, "⚪")
        if sev == "CRITICAL":
            st.error(f"{icon} [{ts}] {alert['vehicle_id']} — {alert['message']}")
        elif sev == "WARNING":
            st.warning(f"{icon} [{ts}] {alert['vehicle_id']} — {alert['message']}")
        else:
            st.info(f"{icon} [{ts}] {alert['vehicle_id']} — {alert['message']}")

# ── Footer + auto-refresh ────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Last fetched: {datetime.now().strftime('%H:%M:%S')}  ·  Refreshing every 3 seconds")

time.sleep(3)
st.rerun()
