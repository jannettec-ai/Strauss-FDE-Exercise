"""
utils/metrics.py

Persistent metrics layer for FDE monitoring.
Writes every packet generation event to a local SQLite database.
No new pip dependencies — sqlite3 is Python stdlib.

In production this layer would be replaced by an event pipeline
into a data warehouse (e.g. BigQuery via Pub/Sub).

Note: on Streamlit Cloud the SQLite file lives in the container
filesystem and resets on redeploy. Acceptable for prototype monitoring;
production would use a persistent store outside the container.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "metrics.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db() -> None:
    """Create metrics.db and events table if they don't exist. Call at app startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generation_events (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp           TEXT    NOT NULL,
                meeting_id          INTEGER,
                supplier_name       TEXT    NOT NULL,
                category            TEXT,
                duration_seconds    REAL    NOT NULL,
                packet_length_chars INTEGER NOT NULL,
                open_issues_count   INTEGER,
                correction_rate_pct REAL
            )
        """)
        conn.commit()


def record_generation(
    supplier_name: str,
    duration_seconds: float,
    packet_length_chars: int,
    meeting_id: Optional[int] = None,
    category: Optional[str] = None,
    open_issues_count: Optional[int] = None,
    correction_rate_pct: Optional[float] = None,
) -> None:
    """Insert one generation event row."""
    ts = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO generation_events
                (timestamp, meeting_id, supplier_name, category,
                 duration_seconds, packet_length_chars,
                 open_issues_count, correction_rate_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, meeting_id, supplier_name, category,
             round(duration_seconds, 2), packet_length_chars,
             open_issues_count, correction_rate_pct),
        )
        conn.commit()


def get_summary() -> dict:
    """
    Return aggregate metrics for the FDE dashboard.

    Keys:
        total_packets       int
        avg_duration_sec    float | None
        unique_suppliers    int
        daily_breakdown     list[dict]  — [{date, count, avg_duration_sec}]
        supplier_breakdown  list[dict]  — [{supplier_name, count, avg_duration_sec, avg_issues}]
        recent_events       list[dict]  — last 10 events
    """
    if not DB_PATH.exists():
        return {
            "total_packets": 0,
            "avg_duration_sec": None,
            "unique_suppliers": 0,
            "daily_breakdown": [],
            "supplier_breakdown": [],
            "recent_events": [],
        }

    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) FROM generation_events").fetchone()[0]
        avg_dur = conn.execute(
            "SELECT AVG(duration_seconds) FROM generation_events"
        ).fetchone()[0]
        unique = conn.execute(
            "SELECT COUNT(DISTINCT supplier_name) FROM generation_events"
        ).fetchone()[0]

        daily_rows = conn.execute("""
            SELECT
                substr(timestamp, 1, 10)        AS date,
                COUNT(*)                         AS count,
                ROUND(AVG(duration_seconds), 1)  AS avg_duration_sec
            FROM generation_events
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """).fetchall()

        supplier_rows = conn.execute("""
            SELECT
                supplier_name,
                COUNT(*)                            AS count,
                ROUND(AVG(duration_seconds), 1)     AS avg_duration_sec,
                ROUND(AVG(open_issues_count), 1)    AS avg_issues
            FROM generation_events
            GROUP BY supplier_name
            ORDER BY count DESC
        """).fetchall()

        recent_rows = conn.execute("""
            SELECT timestamp, supplier_name, category,
                   duration_seconds, open_issues_count
            FROM generation_events
            ORDER BY timestamp DESC
            LIMIT 10
        """).fetchall()

    return {
        "total_packets": total,
        "avg_duration_sec": round(avg_dur, 1) if avg_dur is not None else None,
        "unique_suppliers": unique,
        "daily_breakdown": [dict(r) for r in daily_rows],
        "supplier_breakdown": [dict(r) for r in supplier_rows],
        "recent_events": [dict(r) for r in recent_rows],
    }
