import json
import sqlite3
from datetime import datetime, timezone

from bede_data.analytics.signals import (
    compute_activity_flags,
    compute_bedtime_flags,
    compute_goal_flags,
    compute_medication_flags,
    compute_screen_time_flags,
    compute_sleep_flags,
)


def run_analytics(conn: sqlite3.Connection) -> list[dict]:
    all_flags = []
    all_flags.extend(compute_sleep_flags(conn))
    all_flags.extend(compute_activity_flags(conn))
    all_flags.extend(compute_goal_flags(conn))
    all_flags.extend(compute_screen_time_flags(conn))
    all_flags.extend(compute_medication_flags(conn))
    all_flags.extend(compute_bedtime_flags(conn))
    return all_flags


def store_flags(conn: sqlite3.Connection, flags: list[dict]) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for flag in flags:
        conn.execute(
            "INSERT INTO analytics_flags (signal, severity, detail, data, computed_at) VALUES (?, ?, ?, ?, ?)",
            (flag["signal"], flag["severity"], flag.get("detail"), json.dumps(flag.get("data", {})), now),
        )
    conn.commit()
    return len(flags)
