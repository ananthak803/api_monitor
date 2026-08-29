# 🚀 API Performance Monitor

A comprehensive system to track and analyze API performance metrics in real-time. Built with Python (Flask), SQLite, and Chart.js for an interactive Grafana-style dashboard.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-green?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-blue?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Features

- **Real-time API Monitoring** — Automatically checks API endpoints at configurable intervals
- **Response Time Tracking** — Records and visualizes response times with min/avg/max statistics
- **Error Detection** — Identifies HTTP errors, timeouts, and connection failures
- **Interactive Dashboard** — Beautiful dark-themed dashboard with live charts and stats
- **Alert System** — Automatic alerts for slow responses and consecutive failures
- **Performance Insights** — Aggregated analytics including uptime percentage and trends
- **Endpoint Management** — Add, remove, toggle, and configure API endpoints via UI
- **Request Logging** — Detailed logs of every API check with filtering capability
- **REST API** — Full API for programmatic access to all monitoring data

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **Python 3** | Core programming language |
| **Flask** | Web framework & REST API |
| **SQLite** | Lightweight database for metrics storage |
| **Requests** | HTTP client for API health checks |
| **APScheduler** | Background job scheduler |
| **Chart.js** | Interactive charts and visualizations |
| **HTML/CSS/JS** | Frontend dashboard (Grafana-style) |

## 📂 Project Structure

```
apimon/
├── app.py              # Main Flask application & REST API
├── database.py         # SQLite database schema & helpers
├── monitor.py          # API monitoring engine & alert logic
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
└── templates/
    └── dashboard.html  # Web dashboard (charts, tables, UI)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

```bash
# 1. Clone / navigate to the project
cd apimon

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### Access the Dashboard
Open **http://127.0.0.1:5000** in your browser.

## 📊 Dashboard Sections

### Overview
- **Stat Cards** — Total endpoints, avg response time, uptime %, total checks, errors
- **Response Time Chart** — Line chart showing response time trends (1h/6h/24h)
- **Error Distribution** — Doughnut chart showing check distribution per endpoint
- **Performance Summary Table** — Per-endpoint stats with health status indicators

### Endpoints
- View all monitored API endpoints
- Add new endpoints via modal form
- Toggle active/inactive status
- Trigger manual checks per endpoint
- Delete endpoints with cascade cleanup

### Alerts
- View active and resolved alerts
- Alert types: Slow Response, Consecutive Failures
- One-click alert resolution

### Request Logs
- Chronological log of all API checks
- Filter by endpoint
- View status codes, response times, payload sizes, and errors

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/endpoints` | List all monitored endpoints |
| `POST` | `/api/endpoints` | Add a new endpoint |
| `DELETE` | `/api/endpoints/<id>` | Delete an endpoint |
| `POST` | `/api/endpoints/<id>/toggle` | Toggle endpoint active status |
| `GET` | `/api/metrics` | Get metrics (filterable) |
| `GET` | `/api/metrics/timeseries` | Get time-series data for charts |
| `GET` | `/api/metrics/summary` | Get per-endpoint summary stats |
| `GET` | `/api/dashboard` | Get dashboard aggregate stats |
| `GET` | `/api/insights` | Get performance insights |
| `GET` | `/api/alerts` | Get all alerts |
| `POST` | `/api/alerts/<id>/resolve` | Resolve an alert |
| `POST` | `/api/check` | Manual check (single/all) |
| `POST` | `/api/check-all` | Check all active endpoints |

## ⚙️ Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Check Interval | 30s (scheduler) | Background check frequency |
| Slow Response Threshold | 2000ms | Alert trigger for slow APIs |
| Consecutive Failures | 3 | Error count to trigger alert |
| Request Timeout | 10s | Max wait per API request |

## 📈 Sample Metrics Output

```json
{
  "total_endpoints": 6,
  "active_endpoints": 6,
  "avg_response_time": 245.32,
  "uptime_pct": 98.5,
  "total_checks_24h": 1440,
  "total_errors_24h": 12,
  "active_alerts": 1
}
```

## 🎓 Learning Outcomes

- Designing RESTful API architectures with Flask
- Working with SQLite for persistent data storage
- Implementing background task scheduling with APScheduler
- Building interactive dashboards with Chart.js
- Real-time data visualization and monitoring patterns
- Alert systems and threshold-based notifications
- HTTP client usage and error handling with Requests library

---

*Built as an Industrial Training Project — API Performance Monitoring System*
