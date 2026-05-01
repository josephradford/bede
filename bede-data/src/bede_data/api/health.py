import sqlite3
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from bede_data.db.connection import get_db

SESSION_GAP_HOURS = 2
_AGGREGATED_PHASES = ("core", "deep", "rem", "awake", "asleep", "inBed")

router = APIRouter(prefix="/api/health", tags=["health"])


def _resolve_date(date_str: str) -> str:
    if date_str == "today":
        return date.today().isoformat()
    if date_str == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
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


def _build_session(phases: list[dict]) -> dict:
    total_hours = round(sum(p["hours"] for p in phases), 2)
    return {
        "total_hours": total_hours,
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
    d = _resolve_date(date)
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

    return {
        "date": d,
        "total_hours": total_hours,
        "bedtime": bedtime,
        "wake_time": wake_time,
        "sessions": sessions,
        "phases": detail_phases or summary_phases,
    }


@router.get("/activity")
def get_activity(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        """
        SELECT metric, MAX(value) AS value
        FROM health_metrics
        WHERE date = ?
          AND metric IN ('step_count', 'active_energy', 'apple_exercise_time', 'apple_stand_hour')
        GROUP BY metric
        """,
        (d,),
    )
    metrics = {row["metric"]: row["value"] for row in cursor.fetchall()}
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
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT workout_type, duration_minutes, active_energy_kj, avg_heart_rate, max_heart_rate, start_time FROM workouts WHERE date = ? ORDER BY start_time",
        (d,),
    )
    return {"date": d, "workouts": [dict(row) for row in cursor.fetchall()]}


@router.get("/heart-rate")
def get_heart_rate(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
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
    d = _resolve_date(date)

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
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT medication, quantity, unit, recorded_at FROM medications WHERE date = ? ORDER BY recorded_at",
        (d,),
    )
    return {"date": d, "medications": [dict(row) for row in cursor.fetchall()]}
