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


def _load_thresholds(conn: sqlite3.Connection) -> dict:
    cursor = conn.execute("SELECT signal, config FROM analytics_thresholds")
    result = {}
    for row in cursor.fetchall():
        try:
            result[row["signal"]] = json.loads(row["config"])
        except (json.JSONDecodeError, TypeError):
            continue
    return result


def run_analytics(conn: sqlite3.Connection) -> list[dict]:
    thresholds = _load_thresholds(conn)
    all_flags = []

    sleep_cfg = thresholds.get("sleep_declining", {})
    all_flags.extend(compute_sleep_flags(
        conn,
        target_hours=sleep_cfg.get("target_hours", 7.0),
        window_days=sleep_cfg.get("window_days", 3),
    ))

    activity_cfg = thresholds.get("exercise_gap", {})
    all_flags.extend(compute_activity_flags(
        conn,
        gap_threshold_days=activity_cfg.get("gap_threshold_days", 5),
    ))

    goal_cfg = thresholds.get("goal_stale", {})
    all_flags.extend(compute_goal_flags(
        conn,
        stale_threshold_days=goal_cfg.get("stale_threshold_days", 14),
    ))

    screen_cfg = thresholds.get("passive_screen_up", {})
    all_flags.extend(compute_screen_time_flags(
        conn,
        spike_threshold_pct=screen_cfg.get("spike_threshold_pct", 40),
        window_days=screen_cfg.get("window_days", 7),
    ))

    all_flags.extend(compute_medication_flags(conn))

    bedtime_cfg = thresholds.get("bedtime_drifting", {})
    all_flags.extend(compute_bedtime_flags(
        conn,
        drift_threshold_minutes=bedtime_cfg.get("drift_threshold_minutes", 30),
        window_days=bedtime_cfg.get("window_days", 7),
    ))

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
