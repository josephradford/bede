import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/retention", tags=["retention"])

RETAINABLE_TABLES = {
    "health_metrics": "date",
    "sleep_phases": "date",
    "workouts": "date",
    "state_of_mind": "date",
    "medications": "date",
    "screen_time": "date",
    "safari_history": "date",
    "youtube_history": "date",
    "podcasts": "date",
    "claude_sessions": "date",
    "bede_sessions": "date",
    "music_listens": "date",
    "task_executions": "created_at",
    "analytics_flags": "computed_at",
    "daily_scratchpads": "date",
}


class RetentionPolicy(BaseModel):
    retention_days: int


@router.post("/cleanup")
def run_cleanup(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("SELECT data_type, retention_days FROM retention_policies")
    policies = {row["data_type"]: row["retention_days"] for row in cursor.fetchall()}

    total_deleted = 0
    for table, date_col in RETAINABLE_TABLES.items():
        days = policies.get(table)
        if days is None:
            continue
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        result = conn.execute(f"DELETE FROM [{table}] WHERE [{date_col}] < ?", (cutoff,))
        total_deleted += result.rowcount

    conn.commit()
    return {"status": "ok", "rows_deleted": total_deleted}


@router.put("/policies/{data_type}")
def set_policy(
    data_type: str,
    body: RetentionPolicy,
    conn: sqlite3.Connection = Depends(get_db),
):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO retention_policies (data_type, retention_days, updated_at) VALUES (?, ?, ?)",
        (data_type, body.retention_days, now),
    )
    conn.commit()
    return {"data_type": data_type, "retention_days": body.retention_days}


@router.get("/policies")
def list_policies(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "SELECT data_type, retention_days, updated_at FROM retention_policies ORDER BY data_type"
    )
    return {"policies": [dict(r) for r in cursor.fetchall()]}
