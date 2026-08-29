"""
Monitor module for API Performance Monitor.
Handles background API health checking and metric collection.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from database import get_db

# Thresholds for alerts
SLOW_RESPONSE_THRESHOLD_MS = 2000  # 2 seconds
ERROR_RATE_THRESHOLD = 0.3  # 30% error rate triggers alert
CONSECUTIVE_FAILURES_THRESHOLD = 3


def check_endpoint(endpoint):
    """
    Send a request to an API endpoint and record the performance metrics.
    Returns the metric data dictionary.
    """
    url = endpoint["url"]
    method = endpoint["method"]
    headers = json.loads(endpoint["headers"]) if endpoint["headers"] else {}
    body = endpoint["body"] or ""

    metric = {
        "endpoint_id": endpoint["id"],
        "status_code": None,
        "response_time_ms": 0,
        "content_length": 0,
        "is_error": 0,
        "error_message": "",
    }

    try:
        start_time = time.time()

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, data=body, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, data=body, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            response = requests.get(url, headers=headers, timeout=10)

        elapsed_ms = (time.time() - start_time) * 1000

        metric["status_code"] = response.status_code
        metric["response_time_ms"] = round(elapsed_ms, 2)
        metric["content_length"] = len(response.content)

        if response.status_code >= 400:
            metric["is_error"] = 1
            metric["error_message"] = f"HTTP {response.status_code}: {response.reason}"

    except requests.exceptions.Timeout:
        metric["is_error"] = 1
        metric["error_message"] = "Request timed out (10s)"
        metric["response_time_ms"] = 10000
    except requests.exceptions.ConnectionError:
        metric["is_error"] = 1
        metric["error_message"] = "Connection refused or DNS failure"
    except requests.exceptions.RequestException as e:
        metric["is_error"] = 1
        metric["error_message"] = str(e)[:200]

    # Save to database
    save_metric(metric)

    # Check for alert conditions
    check_alerts(endpoint, metric)

    return metric


def save_metric(metric):
    """Persist a metric record to the database."""
    conn = get_db()
    conn.execute(
        """INSERT INTO metrics (endpoint_id, status_code, response_time_ms, 
           content_length, is_error, error_message) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            metric["endpoint_id"],
            metric["status_code"],
            metric["response_time_ms"],
            metric["content_length"],
            metric["is_error"],
            metric["error_message"],
        ),
    )
    conn.commit()
    conn.close()


def check_alerts(endpoint, metric):
    """Evaluate alert conditions and create alerts if needed."""
    conn = get_db()

    # Check for slow response
    if metric["response_time_ms"] > SLOW_RESPONSE_THRESHOLD_MS and not metric["is_error"]:
        conn.execute(
            "INSERT INTO alerts (endpoint_id, alert_type, message) VALUES (?, ?, ?)",
            (
                endpoint["id"],
                "SLOW_RESPONSE",
                f"Response time {metric['response_time_ms']:.0f}ms exceeds threshold of {SLOW_RESPONSE_THRESHOLD_MS}ms",
            ),
        )

    # Check for consecutive failures
    if metric["is_error"]:
        cursor = conn.execute(
            """SELECT COUNT(*) FROM metrics 
               WHERE endpoint_id = ? AND is_error = 1 
               AND recorded_at >= datetime('now', '-5 minutes')""",
            (endpoint["id"],),
        )
        error_count = cursor.fetchone()[0]

        if error_count >= CONSECUTIVE_FAILURES_THRESHOLD:
            # Check if an unresolved alert already exists
            existing = conn.execute(
                """SELECT id FROM alerts 
                   WHERE endpoint_id = ? AND alert_type = 'CONSECUTIVE_FAILURES' 
                   AND is_resolved = 0""",
                (endpoint["id"],),
            ).fetchone()

            if not existing:
                conn.execute(
                    "INSERT INTO alerts (endpoint_id, alert_type, message) VALUES (?, ?, ?)",
                    (
                        endpoint["id"],
                        "CONSECUTIVE_FAILURES",
                        f"{error_count} consecutive errors detected. Last error: {metric['error_message']}",
                    ),
                )

    conn.commit()
    conn.close()


def run_all_checks():
    """Run health checks on all active endpoints."""
    conn = get_db()
    endpoints = conn.execute(
        "SELECT * FROM api_endpoints WHERE is_active = 1"
    ).fetchall()
    conn.close()

    results = []
    for ep in endpoints:
        result = check_endpoint(dict(ep))
        results.append(result)

    return results


def get_performance_insights():
    """Generate performance insights from collected metrics."""
    conn = get_db()
    insights = []

    # Overall stats (last 24 hours)
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_checks,
            SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as total_errors,
            AVG(response_time_ms) as avg_response_time,
            MIN(response_time_ms) as min_response_time,
            MAX(response_time_ms) as max_response_time
        FROM metrics 
        WHERE recorded_at >= datetime('now', '-24 hours')
    """).fetchone()

    # Per-endpoint stats
    endpoint_stats = conn.execute("""
        SELECT 
            e.name,
            e.url,
            COUNT(m.id) as check_count,
            SUM(CASE WHEN m.is_error = 1 THEN 1 ELSE 0 END) as error_count,
            AVG(m.response_time_ms) as avg_time,
            MIN(m.response_time_ms) as min_time,
            MAX(m.response_time_ms) as max_time,
            ROUND(AVG(CASE WHEN m.is_error = 0 THEN 1.0 ELSE 0.0 END) * 100, 2) as uptime_pct
        FROM api_endpoints e
        LEFT JOIN metrics m ON e.id = m.endpoint_id 
            AND m.recorded_at >= datetime('now', '-24 hours')
        WHERE e.is_active = 1
        GROUP BY e.id
        ORDER BY avg_time DESC
    """).fetchall()

    # Slowest endpoints
    slowest = conn.execute("""
        SELECT e.name, AVG(m.response_time_ms) as avg_time
        FROM metrics m
        JOIN api_endpoints e ON m.endpoint_id = e.id
        WHERE m.recorded_at >= datetime('now', '-24 hours')
        GROUP BY m.endpoint_id
        ORDER BY avg_time DESC
        LIMIT 5
    """).fetchall()

    # Recent alerts
    recent_alerts = conn.execute("""
        SELECT a.*, e.name as endpoint_name
        FROM alerts a
        JOIN api_endpoints e ON a.endpoint_id = e.id
        ORDER BY a.created_at DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return {
        "overall": dict(stats) if stats else {},
        "endpoints": [dict(e) for e in endpoint_stats],
        "slowest": [dict(s) for s in slowest],
        "recent_alerts": [dict(a) for a in recent_alerts],
    }
