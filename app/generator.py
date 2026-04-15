import requests
import random
import time
import threading

# The gateway URL — when running locally this is localhost
GATEWAY_URL = "http://localhost:8000/telemetry"

# 5 vehicles with names and starting conditions
VEHICLES = [
    {"id": "V001", "name": "Truck — Delhi",   "base_temp": 82, "fuel": 75},
    {"id": "V002", "name": "Truck — Mumbai",  "base_temp": 78, "fuel": 60},
    {"id": "V003", "name": "Van   — Pune",    "base_temp": 85, "fuel": 45},
    {"id": "V004", "name": "Van   — Bhopal",  "base_temp": 80, "fuel": 30},
    {"id": "V005", "name": "Truck — Jaipur",  "base_temp": 76, "fuel": 90},
]

def simulate_vehicle(vehicle: dict):
    """
    Runs forever for one vehicle.
    Every second it generates realistic sensor data and POSTs it to the gateway.
    Values drift naturally — fuel drains, temp fluctuates, speed changes.
    """
    vid       = vehicle["id"]
    fuel      = vehicle["fuel"]       # starts at different levels
    temp      = vehicle["base_temp"]  # starts at a realistic idle temp
    speed     = 0.0
    battery   = 12.8
    rpm       = 800.0

    print(f"[{vid}] Starting simulation — {vehicle['name']}")

    while True:
        # ── Drift values naturally each second ──────────────────────────
        # Fuel drains slowly (about 1% every 30 seconds)
        fuel     = max(0, fuel - random.uniform(0.01, 0.05))

        # Speed changes — vehicle accelerates and brakes
        speed    = max(0, min(130, speed + random.uniform(-8, 10)))

        # Engine temp rises with speed, cools when slow
        temp_target = 75 + (speed / 120) * 40
        temp     = temp + (temp_target - temp) * 0.1 + random.uniform(-1, 1)

        # RPM tracks speed
        rpm      = 800 + (speed / 130) * 3200 + random.uniform(-100, 100)

        # Battery drains very slowly
        battery  = max(11.0, min(14.8, battery + random.uniform(-0.02, 0.01)))

        # ── Occasionally inject anomalies (for demo purposes) ────────────
        # 2% chance of a spike in engine temp
        if random.random() < 0.02:
            temp += random.uniform(20, 35)
            print(f"[{vid}] ANOMALY: Engine temp spike → {temp:.1f}°C")

        # 1% chance of low fuel simulation
        if random.random() < 0.01:
            fuel = max(0, fuel - random.uniform(10, 20))
            print(f"[{vid}] ANOMALY: Fuel drop → {fuel:.1f}%")

        # ── Send data to the gateway ─────────────────────────────────────
        payload = {
            "vehicle_id":  vid,
            "engine_temp": round(temp, 2),
            "fuel_level":  round(fuel, 2),
            "speed":       round(speed, 2),
            "battery":     round(battery, 3),
            "rpm":         round(rpm, 1),
        }

        try:
            response = requests.post(GATEWAY_URL, json=payload, timeout=2)
            result   = response.json()
            status   = result.get("vehicle_status", "?")
            health   = result.get("health_score", 0)
            print(f"[{vid}] temp={temp:.1f}°C  fuel={fuel:.1f}%  "
                  f"speed={speed:.1f}km/h  health={health:.0f}  status={status}")
        except requests.exceptions.ConnectionError:
            print(f"[{vid}] Gateway not reachable — retrying...")
        except Exception as e:
            print(f"[{vid}] Error: {e}")

        time.sleep(1)  # send data every 1 second


def main():
    print("=" * 55)
    print("  SmartFleet — Vehicle Simulator Starting")
    print(f"  Sending data to: {GATEWAY_URL}")
    print("  5 vehicles will start in parallel")
    print("  Press Ctrl+C to stop")
    print("=" * 55)

    # Start one thread per vehicle — they all run at the same time
    threads = []
    for vehicle in VEHICLES:
        t = threading.Thread(target=simulate_vehicle, args=(vehicle,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.2)  # stagger starts slightly

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
