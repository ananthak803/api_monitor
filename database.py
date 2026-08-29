"""
Database module for API Performance Monitor.
Handles SQLite database initialization and query helpers.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apimon.db")


def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS api_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            method TEXT DEFAULT 'GET',
            headers TEXT DEFAULT '{}',
            body TEXT DEFAULT '',
            check_interval INTEGER DEFAULT 60,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            status_code INTEGER,
            response_time_ms REAL,
            content_length INTEGER DEFAULT 0,
            is_error INTEGER DEFAULT 0,
            error_message TEXT DEFAULT '',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            is_resolved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_endpoint_id ON metrics(endpoint_id);
        CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);
        CREATE INDEX IF NOT EXISTS idx_alerts_endpoint_id ON alerts(endpoint_id);
    """)

    conn.commit()
    conn.close()


def seed_demo_endpoints():
    """Seed the database with demo API endpoints if empty."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM api_endpoints")
    count = cursor.fetchone()[0]

    if count == 0:
        demo_endpoints = [
            ("JSONPlaceholder - Posts", "https://jsonplaceholder.typicode.com/posts", "GET", 30),
            ("JSONPlaceholder - Users", "https://jsonplaceholder.typicode.com/users", "GET", 30),
            ("JSONPlaceholder - Comments", "https://jsonplaceholder.typicode.com/comments", "GET", 45),
            ("HTTPBin - GET", "https://httpbin.org/get", "GET", 60),
            ("HTTPBin - Status 200", "https://httpbin.org/status/200", "GET", 60),
            ("ReqRes - Users", "https://reqres.in/api/users", "GET", 30),
        ]

        cursor.executemany(
            "INSERT INTO api_endpoints (name, url, method, check_interval) VALUES (?, ?, ?, ?)",
            demo_endpoints,
        )
        conn.commit()

    conn.close()
