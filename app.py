"""
API Performance Monitor - Flask Application
Main application file with REST API endpoints and web dashboard.
"""

import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, get_db, seed_demo_endpoints
from monitor import run_all_checks, check_endpoint, get_performance_insights

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ─── Scheduler Setup ────────────────────────────────────────────────
scheduler = BackgroundScheduler(daemon=True)


def scheduled_checks():
    """Run scheduled API checks."""
    with app.app_context():
        run_all_checks()


# ─── Web Dashboard ──────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Serve the main dashboard page."""
    return render_template("dashboard.html")


# ─── API: Endpoints Management ──────────────────────────────────────

@app.route("/api/endpoints", methods=["GET"])
def list_endpoints():
    """List all monitored API endpoints."""
    conn = get_db()
    endpoints = conn.execute("SELECT * FROM api_endpoints ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(e) for e in endpoints])


@app.route("/api/endpoints", methods=["POST"])
def add_endpoint():
    """Add a new API endpoint to monitor."""
    data = request.get_json()

    if not data or not data.get("url"):
        return jsonify({"error": "URL is required"}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO api_endpoints (name, url, method, headers, body, check_interval)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.get("name", data["url"]),
                data["url"],
                data.get("method", "GET"),
                json.dumps(data.get("headers", {})),
                data.get("body", ""),
                data.get("check_interval", 60),
            ),
        )
        conn.commit()
        endpoint_id = cursor.lastrowid

        # Fetch the created endpoint
        endpoint = conn.execute(
            "SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,)
        ).fetchone()
        conn.close()

        return jsonify(dict(endpoint)), 201

    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/endpoints/<int:endpoint_id>", methods=["DELETE"])
def delete_endpoint(endpoint_id):
    """Remove an API endpoint and its associated data."""
    conn = get_db()
    conn.execute("DELETE FROM api_endpoints WHERE id = ?", (endpoint_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Endpoint deleted"}), 200


@app.route("/api/endpoints/<int:endpoint_id>/toggle", methods=["POST"])
def toggle_endpoint(endpoint_id):
    """Toggle active/inactive status of an endpoint."""
    conn = get_db()
    conn.execute(
        "UPDATE api_endpoints SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (endpoint_id,),
    )
    conn.commit()
    endpoint = conn.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,)).fetchone()
    conn.close()
    return jsonify(dict(endpoint))


# ─── API: Metrics & Analytics ───────────────────────────────────────

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get metrics with optional filtering."""
    endpoint_id = request.args.get("endpoint_id")
    hours = request.args.get("hours", 24, type=int)
    limit = request.args.get("limit", 500, type=int)

    conn = get_db()

    query = """
        SELECT m.*, e.name as endpoint_name, e.url as endpoint_url
        FROM metrics m
        JOIN api_endpoints e ON m.endpoint_id = e.id
        WHERE m.recorded_at >= datetime('now', ? || ' hours')
    """
    params = [f"-{hours}"]

    if endpoint_id:
        query += " AND m.endpoint_id = ?"
        params.append(endpoint_id)

    query += " ORDER BY m.recorded_at DESC LIMIT ?"
    params.append(limit)

    metrics = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(m) for m in metrics])


@app.route("/api/metrics/timeseries", methods=["GET"])
def get_timeseries():
    """Get time-series data for charting. Groups by 1-minute intervals."""
    endpoint_id = request.args.get("endpoint_id")
    hours = request.args.get("hours", 1, type=int)

    conn = get_db()

    query = """
        SELECT 
            endpoint_id,
            e.name as endpoint_name,
            strftime('%Y-%m-%d %H:%M:00', m.recorded_at) as time_bucket,
            AVG(m.response_time_ms) as avg_response_time,
            MIN(m.response_time_ms) as min_response_time,
            MAX(m.response_time_ms) as max_response_time,
            COUNT(*) as check_count,
            SUM(CASE WHEN m.is_error = 1 THEN 1 ELSE 0 END) as error_count
        FROM metrics m
        JOIN api_endpoints e ON m.endpoint_id = e.id
        WHERE m.recorded_at >= datetime('now', ? || ' hours')
    """
    params = [f"-{hours}"]

    if endpoint_id:
        query += " AND m.endpoint_id = ?"
        params.append(endpoint_id)

    query += " GROUP BY m.endpoint_id, time_bucket ORDER BY time_bucket ASC"

    data = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(d) for d in data])


@app.route("/api/metrics/summary", methods=["GET"])
def get_summary():
    """Get summary statistics for all endpoints."""
    hours = request.args.get("hours", 24, type=int)

    conn = get_db()
    summary = conn.execute(
        """
        SELECT 
            e.id,
            e.name,
            e.url,
            e.is_active,
            COUNT(m.id) as total_checks,
            SUM(CASE WHEN m.is_error = 1 THEN 1 ELSE 0 END) as total_errors,
            ROUND(AVG(m.response_time_ms), 2) as avg_response_time,
            ROUND(MIN(m.response_time_ms), 2) as min_response_time,
            ROUND(MAX(m.response_time_ms), 2) as max_response_time,
            ROUND(AVG(CASE WHEN m.is_error = 0 THEN 100.0 ELSE 0.0 END), 2) as uptime_pct
        FROM api_endpoints e
        LEFT JOIN metrics m ON e.id = m.endpoint_id 
            AND m.recorded_at >= datetime('now', ? || ' hours')
        GROUP BY e.id
        ORDER BY e.name
    """,
        (f"-{hours}",),
    ).fetchall()
    conn.close()

    return jsonify([dict(s) for s in summary])


# ─── API: Insights & Alerts ────────────────────────────────────────

@app.route("/api/insights", methods=["GET"])
def insights():
    """Get performance insights and analytics."""
    return jsonify(get_performance_insights())


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get all alerts, optionally filtered by status."""
    resolved = request.args.get("resolved")
    conn = get_db()

    query = """
        SELECT a.*, e.name as endpoint_name 
        FROM alerts a
        JOIN api_endpoints e ON a.endpoint_id = e.id
    """
    params = []

    if resolved is not None:
        query += " WHERE a.is_resolved = ?"
        params.append(int(resolved))

    query += " ORDER BY a.created_at DESC LIMIT 100"

    alerts = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(a) for a in alerts])


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    """Mark an alert as resolved."""
    conn = get_db()
    conn.execute(
        "UPDATE alerts SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (alert_id,),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Alert resolved"})


# ─── API: Manual Check ──────────────────────────────────────────────

@app.route("/api/check", methods=["POST"])
def manual_check():
    """Trigger a manual check for all or specific endpoints."""
    data = request.get_json() or {}
    endpoint_id = data.get("endpoint_id")

    conn = get_db()

    if endpoint_id:
        endpoint = conn.execute(
            "SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,)
        ).fetchone()
        conn.close()
        if not endpoint:
            return jsonify({"error": "Endpoint not found"}), 404
        result = check_endpoint(dict(endpoint))
        return jsonify(result)
    else:
        conn.close()
        results = run_all_checks()
        return jsonify(results)


@app.route("/api/check-all", methods=["POST"])
def check_all():
    """Trigger checks for all active endpoints."""
    results = run_all_checks()
    return jsonify({"checked": len(results), "results": results})


# ─── API: Dashboard Stats ──────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard_stats():
    """Get aggregated dashboard statistics."""
    conn = get_db()

    # Total endpoints
    total_endpoints = conn.execute("SELECT COUNT(*) FROM api_endpoints").fetchone()[0]
    active_endpoints = conn.execute(
        "SELECT COUNT(*) FROM api_endpoints WHERE is_active = 1"
    ).fetchone()[0]

    # Metrics in last 24h
    stats_24h = conn.execute("""
        SELECT 
            COUNT(*) as total_checks,
            SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as total_errors,
            ROUND(AVG(response_time_ms), 2) as avg_response_time,
            ROUND(MIN(response_time_ms), 2) as fastest,
            ROUND(MAX(response_time_ms), 2) as slowest
        FROM metrics
        WHERE recorded_at >= datetime('now', '-24 hours')
    """).fetchone()

    # Active alerts
    active_alerts = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE is_resolved = 0"
    ).fetchone()[0]

    # Last check time
    last_check = conn.execute(
        "SELECT MAX(recorded_at) FROM metrics"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "total_endpoints": total_endpoints,
        "active_endpoints": active_endpoints,
        "total_checks_24h": stats_24h["total_checks"] if stats_24h else 0,
        "total_errors_24h": stats_24h["total_errors"] if stats_24h else 0,
        "avg_response_time": stats_24h["avg_response_time"] if stats_24h else 0,
        "fastest_response": stats_24h["fastest"] if stats_24h else 0,
        "slowest_response": stats_24h["slowest"] if stats_24h else 0,
        "active_alerts": active_alerts,
        "last_check": last_check,
        "uptime_pct": round(
            (1 - (stats_24h["total_errors"] or 0) / max(stats_24h["total_checks"] or 1, 1)) * 100, 2
        ) if stats_24h else 100,
    })


# ─── Initialization ────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    seed_demo_endpoints()

    # Schedule checks every 30 seconds
    scheduler.add_job(scheduled_checks, "interval", seconds=30, id="api_checks")
    scheduler.start()

    print("\n" + "=" * 60)
    print("  API Performance Monitor")
    print("  Dashboard:  http://127.0.0.1:5000")
    print("  API Docs:   http://127.0.0.1:5000/api/endpoints")
    print("=" * 60 + "\n")

    app.run(debug=True, use_reloader=False, port=5000)
