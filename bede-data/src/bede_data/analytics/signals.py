import sqlite3
from datetime import date, datetime, timedelta


def _today_str(reference_date: str | None = None) -> str:
    return reference_date or date.today().isoformat()


def _date_range(reference: str, window_days: int) -> tuple[str, str]:
    end = datetime.strptime(reference, "%Y-%m-%d").date()
    start = end - timedelta(days=window_days - 1)
    return start.isoformat(), end.isoformat()


def compute_sleep_flags(
    conn: sqlite3.Connection,
    target_hours: float = 7.0,
    window_days: int = 3,
    reference_date: str | None = None,
) -> list[dict]:
    ref = _today_str(reference_date)
    start, end = _date_range(ref, window_days)
    cursor = conn.execute(
        "SELECT date, SUM(hours) as total FROM sleep_phases WHERE date BETWEEN ? AND ? GROUP BY date ORDER BY date",
        (start, end),
    )
    rows = cursor.fetchall()
    if len(rows) < window_days:
        return []
    avg = sum(r["total"] for r in rows) / len(rows)
    if avg < target_hours:
        return [{
            "signal": "sleep_declining",
            "severity": "concern",
            "detail": f"avg {avg:.1f}h vs {target_hours}h target over {window_days} days",
            "data": {"avg_hours": round(avg, 1), "target_hours": target_hours, "window_days": window_days},
        }]
    return []


def compute_activity_flags(
    conn: sqlite3.Connection,
    gap_threshold_days: int = 5,
    reference_date: str | None = None,
) -> list[dict]:
    ref = _today_str(reference_date)
    cursor = conn.execute(
        "SELECT MAX(date) as last_date FROM workouts"
    )
    row = cursor.fetchone()
    if not row or not row["last_date"]:
        return [{"signal": "exercise_gap", "severity": "nudge", "detail": "No workouts recorded", "data": {}}]
    last = datetime.strptime(row["last_date"], "%Y-%m-%d").date()
    today = datetime.strptime(ref, "%Y-%m-%d").date()
    gap = (today - last).days
    if gap >= gap_threshold_days:
        return [{
            "signal": "exercise_gap",
            "severity": "nudge",
            "detail": f"{gap} days since last workout",
            "data": {"days_since": gap},
        }]
    return []


def compute_goal_flags(
    conn: sqlite3.Connection,
    stale_threshold_days: int = 14,
    reference_date: str | None = None,
) -> list[dict]:
    ref = _today_str(reference_date)
    ref_date = datetime.strptime(ref, "%Y-%m-%d").date()
    cutoff = (ref_date - timedelta(days=stale_threshold_days)).isoformat()

    cursor = conn.execute(
        "SELECT id, name, updated_at FROM goals WHERE status = 'active' AND updated_at < ?",
        (cutoff,),
    )
    flags = []
    for row in cursor.fetchall():
        updated = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")).date()
        days_inactive = (ref_date - updated).days
        flags.append({
            "signal": "goal_stale",
            "severity": "nudge",
            "detail": f"'{row['name']}' inactive for {days_inactive} days",
            "data": {"goal_id": row["id"], "goal_name": row["name"], "days_inactive": days_inactive},
        })

    cursor = conn.execute(
        "SELECT id, name, deadline, updated_at FROM goals WHERE status = 'active' AND deadline IS NOT NULL AND deadline > ?",
        (ref,),
    )
    for row in cursor.fetchall():
        deadline = datetime.strptime(row["deadline"], "%Y-%m-%d").date()
        days_remaining = (deadline - ref_date).days
        updated = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")).date()
        days_since_update = (ref_date - updated).days

        if days_remaining <= 14 and days_since_update >= 7:
            flags.append({
                "signal": "goal_drifting",
                "severity": "concern",
                "detail": f"'{row['name']}' deadline in {days_remaining} days, no update for {days_since_update} days",
                "data": {"goal_id": row["id"], "goal_name": row["name"], "days_remaining": days_remaining, "days_since_update": days_since_update},
            })

    return flags


def compute_screen_time_flags(
    conn: sqlite3.Connection,
    spike_threshold_pct: float = 40,
    window_days: int = 7,
    reference_date: str | None = None,
) -> list[dict]:
    ref = _today_str(reference_date)
    start, end = _date_range(ref, window_days)
    ref_date = datetime.strptime(ref, "%Y-%m-%d").date()
    mid = (ref_date - timedelta(days=window_days // 2)).isoformat()

    cursor = conn.execute(
        "SELECT name, SUM(seconds) as total FROM screen_time WHERE date BETWEEN ? AND ? AND date < ? AND entry_type = 'app' GROUP BY name",
        (start, end, mid),
    )
    early = {row["name"]: row["total"] for row in cursor.fetchall()}

    cursor = conn.execute(
        "SELECT name, SUM(seconds) as total FROM screen_time WHERE date BETWEEN ? AND ? AND date >= ? AND entry_type = 'app' GROUP BY name",
        (start, end, mid),
    )
    late = {row["name"]: row["total"] for row in cursor.fetchall()}

    flags = []
    for app_name, late_total in late.items():
        early_total = early.get(app_name, 0)
        if early_total > 0:
            pct_change = ((late_total - early_total) / early_total) * 100
            if pct_change >= spike_threshold_pct:
                flags.append({
                    "signal": "passive_screen_up",
                    "severity": "info",
                    "detail": f"{app_name} +{pct_change:.0f}% this week",
                    "data": {"app": app_name, "pct_change": round(pct_change, 1)},
                })
    return flags


def compute_medication_flags(
    conn: sqlite3.Connection,
    reference_date: str | None = None,
) -> list[dict]:
    ref = _today_str(reference_date)
    yesterday = (datetime.strptime(ref, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()

    cursor = conn.execute(
        "SELECT DISTINCT medication FROM medications WHERE date >= ?",
        (yesterday,),
    )
    recent_meds = {row["medication"] for row in cursor.fetchall()}

    cursor = conn.execute(
        "SELECT DISTINCT medication FROM medications"
    )
    all_meds = {row["medication"] for row in cursor.fetchall()}

    flags = []
    for med in all_meds - recent_meds:
        cursor2 = conn.execute(
            "SELECT MAX(date) as last_date FROM medications WHERE medication = ?", (med,)
        )
        last = cursor2.fetchone()
        flags.append({
            "signal": "medication_missed",
            "severity": "alert",
            "detail": f"{med} not logged since {last['last_date'] if last else 'unknown'}",
            "data": {"medication": med},
        })
    return flags


def compute_bedtime_flags(
    conn: sqlite3.Connection,
    drift_threshold_minutes: int = 30,
    window_days: int = 7,
) -> list[dict]:
    cursor = conn.execute(
        "SELECT date, MIN(start_time) as bedtime FROM sleep_phases WHERE start_time IS NOT NULL GROUP BY date ORDER BY date DESC LIMIT ?",
        (window_days,),
    )
    rows = cursor.fetchall()
    if len(rows) < 4:
        return []

    def _extract_hour_min(ts: str) -> float:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hour = dt.hour + dt.minute / 60
            if hour < 12:
                hour += 24
            return hour
        except (ValueError, AttributeError):
            return 23.0

    bedtimes = [_extract_hour_min(r["bedtime"]) for r in rows]
    early_avg = sum(bedtimes[len(bedtimes)//2:]) / len(bedtimes[len(bedtimes)//2:])
    late_avg = sum(bedtimes[:len(bedtimes)//2]) / len(bedtimes[:len(bedtimes)//2])
    drift_minutes = (late_avg - early_avg) * 60

    if abs(drift_minutes) >= drift_threshold_minutes:
        return [{
            "signal": "bedtime_drifting",
            "severity": "info",
            "detail": f"avg bedtime shifted {abs(drift_minutes):.0f}min {'later' if drift_minutes > 0 else 'earlier'}",
            "data": {"drift_minutes": round(drift_minutes, 1)},
        }]
    return []
