import sqlite3
import os
from datetime import datetime, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "uptime.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT NOT NULL,
            status_code INTEGER,
            response_time_ms REAL,
            is_up INTEGER NOT NULL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_checks_url_time ON checks(site_url, checked_at);

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_url TEXT NOT NULL,
            event_type TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            duration_seconds REAL
        );
        CREATE INDEX IF NOT EXISTS idx_events_url ON events(site_url, started_at);
    """)
    conn.close()


def log_check(url, status_code, response_time_ms, is_up):
    conn = get_conn()
    conn.execute(
        "INSERT INTO checks (site_url, status_code, response_time_ms, is_up) VALUES (?, ?, ?, ?)",
        (url, status_code, response_time_ms, int(is_up)),
    )
    conn.commit()
    conn.close()


def log_event(url, event_type):
    conn = get_conn()
    if event_type == "DOWN":
        conn.execute(
            "INSERT INTO events (site_url, event_type) VALUES (?, ?)",
            (url, "DOWN"),
        )
    elif event_type == "UP":
        row = conn.execute(
            "SELECT id, started_at FROM events WHERE site_url = ? AND event_type = 'DOWN' AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (url,),
        ).fetchone()
        if row:
            started = datetime.fromisoformat(row["started_at"])
            now = datetime.utcnow()
            duration = (now - started).total_seconds()
            conn.execute(
                "UPDATE events SET ended_at = CURRENT_TIMESTAMP, duration_seconds = ? WHERE id = ?",
                (duration, row["id"]),
            )
    conn.commit()
    conn.close()


def get_uptime_percent(url, hours=24):
    conn = get_conn()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_up) as up_count FROM checks WHERE site_url = ? AND checked_at >= ?",
        (url, since),
    ).fetchone()
    conn.close()
    if not row or row["total"] == 0:
        return 100.0
    return round((row["up_count"] / row["total"]) * 100, 2)


def get_response_times(url, hours=24):
    conn = get_conn()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT response_time_ms, checked_at FROM checks WHERE site_url = ? AND checked_at >= ? ORDER BY checked_at",
        (url, since),
    ).fetchall()
    conn.close()
    return [{"time": row["checked_at"], "ms": row["response_time_ms"]} for row in rows]


def get_recent_events(limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_current_status(url):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM checks WHERE site_url = ? ORDER BY checked_at DESC LIMIT 1",
        (url,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def cleanup_old_data(days=90):
    conn = get_conn()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM checks WHERE checked_at < ?", (cutoff,))
    conn.execute("DELETE FROM events WHERE started_at < ?", (cutoff,))
    conn.commit()
    conn.close()
