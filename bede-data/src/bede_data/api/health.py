import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/health", tags=["health"])


def _resolve_date(date_str: str) -> str:
    if date_str == "today":
        return date.today().isoformat()
    if date_str == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return date_str


@router.get("/sleep")
def get_sleep(
    date: str = Query(..., description="YYYY-MM-DD, 'today', or 'yesterday'"),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT phase, hours, start_time, end_time, source FROM sleep_phases WHERE date = ? ORDER BY start_time",
        (d,),
    )
    phases = [dict(row) for row in cursor.fetchall()]
    total_hours = round(sum(p["hours"] for p in phases), 2)

    bedtime = phases[0]["start_time"] if phases else None
    wake_time = phases[-1]["end_time"] if phases else None

    return {
        "date": d,
        "total_hours": total_hours,
        "bedtime": bedtime,
        "wake_time": wake_time,
        "phases": phases,
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
        SELECT metric, SUM(max_val) AS value
        FROM (
            SELECT metric, recorded_at, MAX(value) AS max_val
            FROM health_metrics
            WHERE date = ?
              AND metric IN ('step_count', 'active_energy', 'apple_exercise_time', 'apple_stand_hour')
            GROUP BY metric, recorded_at
        )
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
