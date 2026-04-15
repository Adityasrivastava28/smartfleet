from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import sqlite3
import time
import os

app = FastAPI(title="SmartFleet Gateway")

# ── Database setup ──────────────────────────────────────────────────────────
DB_PATH = "smartfleet.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id  TEXT,
            engine_temp REAL,
            fuel_level  REAL,
            speed       REAL,
            battery     REAL,
            rpm         REAL,
            status      TEXT,
            timestamp   REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            message    TEXT,
            severity   TEXT,
            timestamp  REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Prometheus metrics (these are what Grafana reads) ───────────────────────
engine_temp_gauge   = Gauge("vehicle_engine_temp",   "Engine temperature °C",  ["vehicle_id"])
fuel_level_gauge    = Gauge("vehicle_fuel_level",    "Fuel level %",            ["vehicle_id"])
speed_gauge         = Gauge("vehicle_speed",         "Speed km/h",              ["vehicle_id"])
battery_gauge       = Gauge("vehicle_battery",       "Battery voltage V",       ["vehicle_id"])
health_score_gauge  = Gauge("vehicle_health_score",  "Health score 0-100",      ["vehicle_id"])
anomaly_counter     = Gauge("vehicle_anomaly_count", "Total anomalies detected",["vehicle_id"])

# Track anomaly counts in memory
anomaly_counts = {"V001": 0, "V002": 0, "V003": 0, "V004": 0, "V005": 0}

# ── Data model ───────────────────────────────────────────────────────────────
class TelemetryData(BaseModel):
    vehicle_id:  str
    engine_temp: float   # °C
    fuel_level:  float   # %
    speed:       float   # km/h
    battery:     float   # Volts
    rpm:         float

# ── Anomaly detection ────────────────────────────────────────────────────────
def check_anomaly(data: TelemetryData) -> list[dict]:
    alerts = []
    if data.engine_temp > 105:
        alerts.append({"message": f"Engine overheating: {data.engine_temp:.1f}°C", "severity": "CRITICAL"})
    if data.fuel_level < 15:
        alerts.append({"message": f"Low fuel: {data.fuel_level:.1f}%", "severity": "WARNING"})
    if data.battery < 11.5:
        alerts.append({"message": f"Low battery: {data.battery:.2f}V", "severity": "WARNING"})
    if data.speed > 110:
        alerts.append({"message": f"Speeding: {data.speed:.1f} km/h", "severity": "ALERT"})
    return alerts

# ── Health score calculation (0-100) ────────────────────────────────────────
def calc_health(data: TelemetryData) -> float:
    score = 100.0
    # Engine temp: ideal 70-95°C
    if data.engine_temp > 105:
        score -= 40
    elif data.engine_temp > 95:
        score -= 15
    # Fuel: penalise below 20%
    if data.fuel_level < 15:
        score -= 25
    elif data.fuel_level < 20:
        score -= 10
    # Battery: ideal 12-14.5V
    if data.battery < 11.5:
        score -= 20
    elif data.battery < 12.0:
        score -= 8
    # Speed: penalise over 110
    if data.speed > 110:
        score -= 15
    return max(0.0, score)

# ── Routes ───────────────────────────────────────────────────────────────────
@app.post("/telemetry")
def receive_telemetry(data: TelemetryData):
    """Vehicles call this every second to send their sensor data."""
    alerts = check_anomaly(data)
    health = calc_health(data)
    status = "CRITICAL" if any(a["severity"] == "CRITICAL" for a in alerts) else \
             "WARNING"  if alerts else "OK"

    # Save to database
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO telemetry (vehicle_id, engine_temp, fuel_level, speed, battery, rpm, status, timestamp) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (data.vehicle_id, data.engine_temp, data.fuel_level,
         data.speed, data.battery, data.rpm, status, time.time())
    )
    for alert in alerts:
        anomaly_counts[data.vehicle_id] = anomaly_counts.get(data.vehicle_id, 0) + 1
        conn.execute(
            "INSERT INTO alerts (vehicle_id, message, severity, timestamp) VALUES (?,?,?,?)",
            (data.vehicle_id, alert["message"], alert["severity"], time.time())
        )
    conn.commit()
    conn.close()

    # Update Prometheus gauges
    vid = data.vehicle_id
    engine_temp_gauge.labels(vehicle_id=vid).set(data.engine_temp)
    fuel_level_gauge.labels(vehicle_id=vid).set(data.fuel_level)
    speed_gauge.labels(vehicle_id=vid).set(data.speed)
    battery_gauge.labels(vehicle_id=vid).set(data.battery)
    health_score_gauge.labels(vehicle_id=vid).set(health)
    anomaly_counter.labels(vehicle_id=vid).set(anomaly_counts.get(vid, 0))

    return {"status": "ok", "vehicle_status": status, "health_score": health, "alerts": alerts}


@app.get("/vehicles")
def get_vehicles():
    """Streamlit dashboard calls this to get the latest data for all 5 vehicles."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT vehicle_id, engine_temp, fuel_level, speed, battery, rpm, status, timestamp
        FROM telemetry
        WHERE id IN (
            SELECT MAX(id) FROM telemetry GROUP BY vehicle_id
        )
        ORDER BY vehicle_id
    """).fetchall()
    conn.close()

    vehicles = []
    for r in rows:
        vid = r[0]
        data = TelemetryData(
            vehicle_id=vid, engine_temp=r[1], fuel_level=r[2],
            speed=r[3], battery=r[4], rpm=r[5]
        )
        vehicles.append({
            "vehicle_id":  vid,
            "engine_temp": round(r[1], 1),
            "fuel_level":  round(r[2], 1),
            "speed":       round(r[3], 1),
            "battery":     round(r[4], 2),
            "rpm":         round(r[5], 0),
            "status":      r[6],
            "health_score": round(calc_health(data), 1),
            "timestamp":   r[7],
            "anomaly_count": anomaly_counts.get(vid, 0)
        })
    return {"vehicles": vehicles, "total": len(vehicles)}


@app.get("/alerts")
def get_alerts(limit: int = 20):
    """Returns the most recent alerts across all vehicles."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT vehicle_id, message, severity, timestamp FROM alerts "
        "ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {"alerts": [{"vehicle_id": r[0], "message": r[1], "severity": r[2], "timestamp": r[3]} for r in rows]}


@app.get("/health")
def health_check():
    """Jenkins uses this to verify the app is running after deployment."""
    return {"status": "healthy", "service": "smartfleet-gateway"}


@app.get("/metrics")
def metrics():
    """Prometheus scrapes this endpoint every 15 seconds."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)