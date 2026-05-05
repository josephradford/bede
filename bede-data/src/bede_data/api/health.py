import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from bede_data.config import settings
from bede_data.db.connection import get_db
from bede_data.tz import utc_to_local

SESSION_GAP_HOURS = 2
_AGGREGATED_PHASES = ("core", "deep", "rem", "awake", "asleep", "inBed")

router = APIRouter(prefix="/api/health", tags=["health"])


def _resolve_date(date_str: str, tz_name: str = settings.timezone) -> str:
    tz = ZoneInfo(tz_name)
    if date_str == "today":
        return datetime.now(tz).strftime("%Y-%m-%d")
    if date_str == "yesterday":
        return (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    return date_str


def _parse_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _group_into_sessions(phases: list[dict]) -> list[list[dict]]:
    if not phases:
        return []
    sessions: list[list[dict]] = [[phases[0]]]
    for phase in phases[1:]:
        prev_end = _parse_utc(sessions[-1][-1]["end_time"])
        curr_start = _parse_utc(phase["start_time"])
        if (
            prev_end
            and curr_start
            and (curr_start - prev_end).total_seconds() > SESSION_GAP_HOURS * 3600
        ):
            sessions.append([phase])
        else:
            sessions[-1].append(phase)
    return sessions


_SLEEP_STAGES = frozenset(("asleep", "core", "deep", "rem"))


def _sleep_hours(phases: list[dict]) -> float:
    stage_phases = [p for p in phases if p["phase"] in _SLEEP_STAGES]
    if stage_phases:
        return sum(p["hours"] for p in stage_phases)
    return sum(p["hours"] for p in phases)


def _build_session(phases: list[dict]) -> dict:
    return {
        "total_hours": round(_sleep_hours(phases), 2),
        "bedtime": phases[0]["start_time"],
        "wake_time": phases[-1]["end_time"],
        "phases": phases,
    }


@router.get("/sleep")
def get_sleep(
    date: str = Query(..., description="YYYY-MM-DD, 'today', or 'yesterday'"),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)
    placeholders = ",".join("?" for _ in _AGGREGATED_PHASES)
    cursor = conn.execute(
        f"SELECT phase, hours, start_time, end_time, source FROM sleep_phases WHERE date = ? AND phase IN ({placeholders}) ORDER BY start_time",
        (d, *_AGGREGATED_PHASES),
    )
    summary_phases = [dict(row) for row in cursor.fetchall()]

    cursor = conn.execute(
        f"SELECT phase, hours, start_time, end_time, source FROM sleep_phases WHERE date = ? AND phase NOT IN ({placeholders}) ORDER BY start_time",
        (d, *_AGGREGATED_PHASES),
    )
    detail_phases = [dict(row) for row in cursor.fetchall()]

    phases_for_totals = summary_phases or detail_phases
    session_groups = _group_into_sessions(phases_for_totals)
    sessions = [_build_session(s) for s in session_groups]

    total_hours = round(sum(s["total_hours"] for s in sessions), 2)
    bedtime = sessions[0]["bedtime"] if sessions else None
    wake_time = sessions[0]["wake_time"] if sessions else None

    for p in summary_phases:
        p["start_time"] = utc_to_local(p.get("start_time"), timezone)
        p["end_time"] = utc_to_local(p.get("end_time"), timezone)
    for p in detail_phases:
        p["start_time"] = utc_to_local(p.get("start_time"), timezone)
        p["end_time"] = utc_to_local(p.get("end_time"), timezone)
    for s in sessions:
        s["bedtime"] = utc_to_local(s.get("bedtime"), timezone)
        s["wake_time"] = utc_to_local(s.get("wake_time"), timezone)

    return {
        "date": d,
        "total_hours": total_hours,
        "bedtime": utc_to_local(bedtime, timezone),
        "wake_time": utc_to_local(wake_time, timezone),
        "sessions": sessions,
        "phases": detail_phases or summary_phases,
    }


_ACTIVITY_METRICS = (
    "step_count",
    "active_energy",
    "apple_exercise_time",
    "apple_stand_hour",
)


def _midnight_utc(local_date: str, tz_name: str) -> str:
    """UTC ISO timestamp for midnight on local_date in the given timezone."""
    tz = ZoneInfo(tz_name)
    dt = datetime.strptime(local_date, "%Y-%m-%d").replace(tzinfo=tz)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aggregate_activity(
    d: str, tz_name: str, conn: sqlite3.Connection
) -> dict[str, float]:
    """Return activity metrics for a date. Prefer HAE's daily aggregate
    (the entry at midnight local time) when available; fall back to
    SUM(MAX per timestamp) for metrics without an aggregate."""
    midnight = _midnight_utc(d, tz_name)
    placeholders = ",".join("?" for _ in _ACTIVITY_METRICS)

    agg_cursor = conn.execute(
        f"SELECT metric, value FROM health_metrics "
        f"WHERE date = ? AND recorded_at = ? AND metric IN ({placeholders})",
        (d, midnight, *_ACTIVITY_METRICS),
    )
    metrics = {row["metric"]: row["value"] for row in agg_cursor.fetchall()}

    missing = [m for m in _ACTIVITY_METRICS if m not in metrics]
    if missing:
        mp = ",".join("?" for _ in missing)
        fallback = conn.execute(
            f"""
            SELECT metric, SUM(max_val) AS value
            FROM (
                SELECT metric, recorded_at, MAX(value) AS max_val
                FROM health_metrics
                WHERE date = ? AND metric IN ({mp})
                GROUP BY metric, recorded_at
            )
            GROUP BY metric
            """,
            (d, *missing),
        )
        for row in fallback.fetchall():
            metrics[row["metric"]] = row["value"]

    return metrics


@router.get("/activity")
def get_activity(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)
    metrics = _aggregate_activity(d, timezone, conn)
    return {
        "date": d,
        "steps": round(metrics.get("step_count", 0)),
        "active_energy": round(metrics.get("active_energy", 0), 1),
        "exercise_minutes": round(metrics.get("apple_exercise_time", 0)),
        "stand_hours": round(metrics.get("apple_stand_hour", 0)),
    }


@router.get("/workouts")
def get_workouts(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)
    cursor = conn.execute(
        "SELECT workout_type, duration_minutes, active_energy_kj, avg_heart_rate, max_heart_rate, start_time FROM workouts WHERE date = ? ORDER BY start_time",
        (d,),
    )
    workouts = [dict(row) for row in cursor.fetchall()]
    for w in workouts:
        w["start_time"] = utc_to_local(w.get("start_time"), timezone)
    return {"date": d, "workouts": workouts}


@router.get("/heart-rate")
def get_heart_rate(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)
    cursor = conn.execute(
        "SELECT metric, value FROM health_metrics WHERE date = ? AND metric IN ('resting_heart_rate', 'heart_rate_variability')",
        (d,),
    )
    metrics = {row["metric"]: row["value"] for row in cursor.fetchall()}
    return {
        "date": d,
        "resting_heart_rate": metrics.get("resting_heart_rate"),
        "heart_rate_variability": metrics.get("heart_rate_variability"),
    }


@router.get("/wellbeing")
def get_wellbeing(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)

    cursor = conn.execute(
        "SELECT value FROM health_metrics WHERE date = ? AND metric = 'mindful_minutes'",
        (d,),
    )
    row = cursor.fetchone()
    mindful_minutes = row["value"] if row else 0

    cursor = conn.execute(
        "SELECT valence, labels, context, associations, recorded_at FROM state_of_mind WHERE date = ? ORDER BY recorded_at",
        (d,),
    )
    state_of_mind = [dict(row) for row in cursor.fetchall()]
    for s in state_of_mind:
        s["recorded_at"] = utc_to_local(s.get("recorded_at"), timezone)

    return {
        "date": d,
        "mindful_minutes": mindful_minutes,
        "state_of_mind": state_of_mind,
    }


@router.get("/medications")
def get_medications(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date, timezone)
    cursor = conn.execute(
        "SELECT medication, quantity, unit, recorded_at, status FROM medications WHERE date = ? ORDER BY recorded_at",
        (d,),
    )
    meds = [dict(row) for row in cursor.fetchall()]
    for m in meds:
        m["recorded_at"] = utc_to_local(m.get("recorded_at"), timezone)
    return {"date": d, "medications": meds}
