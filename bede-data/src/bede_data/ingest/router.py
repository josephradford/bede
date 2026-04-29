import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from bede_data.db.connection import get_db
from bede_data.ingest.auth import verify_ingest_token
from bede_data.ingest.health_parser import parse_health_payload
from bede_data.ingest.vault_parser import parse_vault_payload

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _upsert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    for row in rows:
        conn.execute(sql, [row[c] for c in columns])
    conn.commit()
    return len(rows)


def _replace_daily(conn: sqlite3.Connection, table: str, date: str, device: str | None, rows: list[dict]) -> int:
    if not rows:
        return 0
    if device:
        conn.execute(f"DELETE FROM {table} WHERE date = ? AND device = ?", (date, device))
    else:
        conn.execute(f"DELETE FROM {table} WHERE date = ?", (date,))
    return _upsert_rows(conn, table, rows)


def _update_freshness(conn: sqlite3.Connection, source: str, expected_interval: int):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """INSERT OR REPLACE INTO data_freshness (source, last_received_at, expected_interval_seconds, updated_at)
           VALUES (?, ?, ?, ?)""",
        (source, now, expected_interval, now),
    )
    conn.commit()


VAULT_DAILY_REPLACE_TABLES = {"screen_time"}


@router.post("/health")
def ingest_health(
    payload: dict,
    _token: str = Depends(verify_ingest_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    parsed = parse_health_payload(payload)
    total = 0
    total += _upsert_rows(conn, "health_metrics", parsed["health_metrics"])
    total += _upsert_rows(conn, "sleep_phases", parsed["sleep_phases"])
    total += _upsert_rows(conn, "workouts", parsed["workouts"])
    total += _upsert_rows(conn, "medications", parsed["medications"])
    total += _upsert_rows(conn, "state_of_mind", parsed["state_of_mind"])
    _update_freshness(conn, "health", 86400)
    return {"status": "ok", "records": total}


@router.post("/vault")
def ingest_vault(
    payload: dict,
    _token: str = Depends(verify_ingest_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    parsed = parse_vault_payload(payload)
    date = payload.get("date", "")
    total = 0

    if parsed["screen_time"]:
        devices = {r["device"] for r in parsed["screen_time"]}
        for device in devices:
            device_rows = [r for r in parsed["screen_time"] if r["device"] == device]
            total += _replace_daily(conn, "screen_time", date, device, device_rows)

    total += _upsert_rows(conn, "safari_history", parsed["safari_history"])
    total += _upsert_rows(conn, "youtube_history", parsed["youtube_history"])
    total += _upsert_rows(conn, "podcasts", parsed["podcasts"])
    total += _upsert_rows(conn, "claude_sessions", parsed["claude_sessions"])
    total += _upsert_rows(conn, "bede_sessions", parsed["bede_sessions"])

    _update_freshness(conn, "vault", 86400)
    return {"status": "ok", "records": total}
