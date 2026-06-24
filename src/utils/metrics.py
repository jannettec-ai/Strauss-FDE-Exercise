"""
utils/metrics.py

Persistent metrics layer for FDE monitoring.
Writes every packet generation event to SQLite, capturing all five KPI
values (metrics.md §1-5) so the FDE dashboard tracks extraction quality
and relationship signals over time.

In production this layer would be replaced by an event pipeline into a
data warehouse (e.g. BigQuery via Pub/Sub). The SQLite schema mirrors
what that pipeline would capture.

Note: on Streamlit Cloud the SQLite file lives in the container filesystem
and resets on redeploy. Production would use a persistent store external
to the container.
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
    """Create metrics.db and events table if they don't exist. Call at app startup.
    Also migrates existing tables to add KPI columns if missing."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generation_events (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp               TEXT    NOT NULL,
                meeting_id              INTEGER,
                supplier_name           TEXT    NOT NULL,
                category                TEXT,
                duration_seconds        REAL    NOT NULL,
                packet_length_chars     INTEGER NOT NULL,
                kpi_response_days       REAL,
                kpi_open_issues         INTEGER,
                kpi_price_delta_pct     REAL,
                kpi_days_to_renewal     INTEGER,
                kpi_correction_rate_pct REAL
            )
        """)
        # Migrate: add KPI columns if they don't exist (safe to run repeatedly)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(generation_events)")}
        migrations = [
            ("kpi_response_days",       "REAL"),
            ("kpi_open_issues",         "INTEGER"),
            ("kpi_price_delta_pct",     "REAL"),
            ("kpi_days_to_renewal",     "INTEGER"),
            ("kpi_correction_rate_pct", "REAL"),
        ]
        for col, col_type in migrations:
            if col not in existing:
                conn.execute(f"ALTER TABLE generation_events ADD COLUMN {col} {col_type}")
        conn.commit()


def record_generation(
    supplier_name: str,
    duration_seconds: float,
    packet_length_chars: int,
    meeting_id: Optional[int] = None,
    category: Optional[str] = None,
    kpi_response_days: Optional[float] = None,
    kpi_open_issues: Optional[int] = None,
    kpi_price_delta_pct: Optional[float] = None,
    kpi_days_to_renewal: Optional[int] = None,
    kpi_correction_rate_pct: Optional[float] = None,
) -> None:
    """Insert one generation event row with all five KPI values."""
    ts = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO generation_events (
                timestamp, meeting_id, supplier_name, category,
                duration_seconds, packet_length_chars,
                kpi_response_days, kpi_open_issues, kpi_price_delta_pct,
                kpi_days_to_renewal, kpi_correction_rate_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts, meeting_id, supplier_name, category,
                round(duration_seconds, 2), packet_length_chars,
                kpi_response_days, kpi_open_issues,
                kpi_price_delta_pct, kpi_days_to_renewal,
                kpi_correction_rate_pct,
            ),
        )
        conn.commit()


def update_correction_rate(meeting_id: int, rate_pct: float) -> None:
    """
    Back-fill kpi_correction_rate_pct on the most recent generation event
    for a given meeting_id. Called when the PM saves field corrections in
    the Meeting Prep UI (metrics.md §5).
    """
    with _connect() as conn:
        conn.execute(
            """
            UPDATE generation_events
            SET kpi_correction_rate_pct = ?
            WHERE id = (
                SELECT MAX(id) FROM generation_events WHERE meeting_id = ?
            )
            """,
            (round(rate_pct, 1), meeting_id),
        )
        conn.commit()


def get_summary() -> dict:
    """
    Return aggregate metrics for the FDE dashboard, aligned to metrics.md §1-5.

    Keys:
        total_packets           int
        avg_duration_sec        float | None
        unique_suppliers        int
        kpi_summary             dict  — avg value per KPI across all packets
        daily_breakdown         list[dict]
        supplier_breakdown      list[dict]  — includes avg KPI values per supplier
        recent_events           list[dict]  — last 10 events with all KPI columns
    """
    if not DB_PATH.exists():
        return {
            "total_packets": 0,
            "avg_duration_sec": None,
            "unique_suppliers": 0,
            "kpi_summary": {},
            "daily_breakdown": [],
            "supplier_breakdown": [],
            "recent_events": [],
        }

    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) FROM generation_events").fetchone()[0]
        avg_dur = conn.execute("SELECT AVG(duration_seconds) FROM generation_events").fetchone()[0]
        unique = conn.execute("SELECT COUNT(DISTINCT supplier_name) FROM generation_events").fetchone()[0]

        kpi_row = conn.execute("""
            SELECT
                ROUND(AVG(kpi_response_days), 1)     AS avg_response_days,
                ROUND(AVG(kpi_open_issues), 1)        AS avg_open_issues,
                ROUND(AVG(kpi_price_delta_pct), 1)   AS avg_price_delta_pct,
                ROUND(AVG(kpi_days_to_renewal), 0)   AS avg_days_to_renewal,
                ROUND(AVG(kpi_correction_rate_pct), 1) AS avg_correction_rate_pct
            FROM generation_events
        """).fetchone()

        daily_rows = conn.execute("""
            SELECT
                substr(timestamp, 1, 10)             AS date,
                COUNT(*)                              AS packets,
                ROUND(AVG(duration_seconds), 1)       AS avg_duration_sec,
                ROUND(AVG(kpi_open_issues), 1)        AS avg_open_issues
            FROM generation_events
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """).fetchall()

        supplier_rows = conn.execute("""
            SELECT
                supplier_name,
                category,
                COUNT(*)                                AS packets,
                ROUND(AVG(duration_seconds), 1)         AS avg_duration_sec,
                ROUND(AVG(kpi_response_days), 1)        AS avg_response_days,
                ROUND(AVG(kpi_open_issues), 1)          AS avg_open_issues,
                ROUND(AVG(kpi_price_delta_pct), 1)      AS avg_price_delta_pct,
                ROUND(AVG(kpi_days_to_renewal), 0)      AS avg_days_to_renewal
            FROM generation_events
            GROUP BY supplier_name
            ORDER BY packets DESC
        """).fetchall()

        recent_rows = conn.execute("""
            SELECT
                substr(timestamp, 1, 19) AS timestamp,
                supplier_name, category,
                ROUND(duration_seconds, 1)       AS duration_sec,
                kpi_response_days                AS response_days,
                kpi_open_issues                  AS open_issues,
                kpi_price_delta_pct              AS price_delta_pct,
                kpi_days_to_renewal              AS days_to_renewal
            FROM generation_events
            ORDER BY timestamp DESC
            LIMIT 10
        """).fetchall()

    return {
        "total_packets": total,
        "avg_duration_sec": round(avg_dur, 1) if avg_dur is not None else None,
        "unique_suppliers": unique,
        "kpi_summary": dict(kpi_row) if kpi_row else {},
        "daily_breakdown": [dict(r) for r in daily_rows],
        "supplier_breakdown": [dict(r) for r in supplier_rows],
        "recent_events": [dict(r) for r in recent_rows],
    }
