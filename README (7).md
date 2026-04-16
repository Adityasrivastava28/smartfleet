# 🚛 SmartFleet — Real-Time Vehicle Fleet Health Monitoring System

A production-grade IoT monitoring platform that simulates a fleet of 5 delivery vehicles generating live telemetry data — engine temperature, fuel level, speed, battery voltage, and RPM — and visualizes their health in real time through a full DevOps stack.

---

## 📸 Dashboard Preview

![SmartFleet Grafana Dashboard](/monitoring/dashboard1.png
)
![SmartFleet Grafana Dashboard2](/monitoring/dashboard2.png)


---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SmartFleet System                       │
│                                                             │
│  ┌──────────┐     POST /telemetry      ┌─────────────────┐ │
│  │ Vehicle  │ ──────────────────────── │  FastAPI        │ │
│  │Simulator │   (every 1 second)       │  Gateway        │ │
│  │V001-V005 │                          │  main.py        │ │
│  └──────────┘                          └────────┬────────┘ │
│                                                 │           │
│                          ┌──────────────────────┤           │
│                          │                      │           │
│                 ┌────────▼──────┐    ┌──────────▼───────┐  │
│                 │   SQLite DB   │    │   /metrics       │  │
│                 │  telemetry.db │    │   endpoint       │  │
│                 └───────────────┘    └──────────┬───────┘  │
│                                                 │           │
│  ┌─────────────────┐               ┌────────────▼───────┐  │
│  │    Streamlit    │               │    Prometheus      │  │
│  │    Dashboard    │               │  scrapes every 15s │  │
│  │  port 8501      │               │  port 9090         │  │
│  └─────────────────┘               └────────────┬───────┘  │
│                                                 │           │
│                                      ┌──────────▼───────┐  │
│                                      │     Grafana      │  │
│                                      │  22 live panels  │  │
│                                      │  port 3000       │  │
│                                      └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Tool | Purpose | Why |
|---|---|---|
| **Python + FastAPI** | REST API gateway | Receives telemetry, detects anomalies, exposes metrics |
| **Streamlit** | Live UI dashboard | Shows real-time vehicle health without page reloads |
| **SQLite + PVC** | Data persistence | Stores all telemetry — survives pod restarts |
| **Prometheus** | Metrics storage | Scrapes /metrics every 15s, stores time series data |
| **Grafana** | Visualization | Draws live gauges, charts, and alert panels |
| **Docker** | Containerisation | Packages app into portable containers |
| **Kubernetes** | Orchestration | Runs 2-6 pods, auto-scales, auto-restarts on crash |
| **Jenkins** | CI/CD pipeline | Builds, tests, deploys, and rolls back automatically |
| **Git + GitHub** | Version control | Full commit history, branch protection, tagged releases |

---

## 📁 Project Structure

```
smartfleet/
│
├── app/
│   ├── main.py          # FastAPI gateway — receives telemetry,
│   │                    # detects anomalies, exposes /metrics
│   ├── generator.py     # Vehicle simulator — 5 threads,
│   │                    # one per vehicle, sends data every 1s
│   └── dashboard.py     # Streamlit UI — live fleet view,
│                        # refreshes every 3 seconds
│
├── k8s/
│   ├── deployment.yaml  # 2 replicas, resource limits, health probes
│   ├── service.yaml     # ClusterIP service for gateway
│   ├── hpa.yaml         # Auto-scales 2-6 pods at 60% CPU
│   └── ingress.yaml     # Routes smartfleet.local → gateway
│
├── monitoring/
│   ├── prometheus.yml          # Scrape config — targets gateway:8000
│   └── smartfleet-dashboard.json  # Grafana dashboard export
│
├── Dockerfile           # python:3.11-slim, installs deps, runs uvicorn
├── docker-compose.yml   # Runs gateway + generator + dashboard together
├── Jenkinsfile          # 5 stages: lint → build → push → deploy → healthcheck
├── requirements.txt     # All Python dependencies
└── .gitignore           # Ignores venv/, *.db, __pycache__
```

---

## 🚗 What Each Vehicle Generates

Each of the 5 vehicles runs as a separate thread and sends this data every second:

| Metric | Range | Anomaly threshold |
|---|---|---|
| `engine_temp` | 70°C – 120°C | > 105°C → CRITICAL |
| `fuel_level` | 0% – 100% | < 15% → WARNING |
| `speed` | 0 – 130 km/h | > 110 km/h → ALERT |
| `battery_voltage` | 11.0V – 14.8V | < 11.5V → WARNING |
| `rpm` | 600 – 4000 | — |

The generator also randomly injects anomalies (2% chance of engine spike, 1% chance of fuel drop) to simulate real-world failure conditions.

---

## 📊 Grafana Dashboard Panels

| Panel | Type | Query |
|---|---|---|
| Fleet Health Scores | Gauge | `vehicle_health_score` |
| Fuel Levels | Gauge | `vehicle_fuel_level` |
| Engine Temperature | Time series | `vehicle_engine_temp` |
| Vehicle Speed | Time series | `vehicle_speed` |
| Battery Voltage | Stat | `vehicle_battery` |
| Total Anomalies | Stat | `vehicle_anomaly_count` |

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/telemetry` | POST | Receives sensor data from vehicles |
| `/vehicles` | GET | Returns latest status for all 5 vehicles |
| `/alerts` | GET | Returns most recent anomaly alerts |
| `/health` | GET | Health check — used by Jenkins and K8s probes |
| `/metrics` | GET | Prometheus scrape endpoint |

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.11+
- Git

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOURUSERNAME/smartfleet.git
cd smartfleet
```

### Step 2 — Set up virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Run the system (3 terminals)

**Terminal 1 — Gateway:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Vehicle simulator:**
```bash
python app/generator.py
```

**Terminal 3 — Dashboard:**
```bash
streamlit run app/dashboard.py
```

### Step 5 — Open the dashboards
| Service | URL |
|---|---|
| Streamlit dashboard | http://localhost:8501 |
| FastAPI docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

---

## 🐳 Run with Docker

```bash
docker-compose up --build
```

All 3 services start automatically — gateway, generator, and dashboard.

---

## ⚙️ Jenkins Pipeline

The Jenkinsfile defines 5 stages that run on every push to `main`:

```
Lint → Build Image → Push to DockerHub → Deploy to K8s → Health Check
```

If the health check fails after deployment, Jenkins automatically runs:
```bash
kubectl rollout undo deployment/smartfleet-gateway
```
rolling back to the last working version. You can never ship broken code.

---

## ☸️ Kubernetes

```bash
kubectl apply -f k8s/
```

| Resource | Config |
|---|---|
| Deployment | 2 replicas, 256Mi RAM limit, 250m CPU limit |
| HPA | Scales 2–6 pods at 60% CPU utilization |
| PVC | 1Gi persistent disk for SQLite database |
| Ingress | smartfleet.local → gateway, smartfleet-ui.local → dashboard |

Liveness and readiness probes hit `/health` every 10 seconds. Crashed pods restart automatically.

---

## 🧠 Key Learnings

- How to build a REST API with FastAPI and expose Prometheus metrics
- How Docker containers work and why they make deployments reliable
- How Kubernetes manages pods, scaling, and self-healing
- How Jenkins CI/CD pipelines prevent bad code from reaching production
- How Prometheus scrapes and stores time series metrics
- How Grafana turns raw numbers into meaningful visual dashboards
- How Git branching and GitHub workflows are used in real teams

---

## 👨‍💻 Author

Built as a hands-on DevOps learning project covering the full stack:
Python → Git → Docker → Jenkins → Kubernetes → Prometheus → Grafana
