import sqlite3

import pytest


def _seed_sleep_data(db: sqlite3.Connection, days: list[tuple[str, float]]):
    for date, hours in days:
        db.execute(
            "INSERT INTO sleep_phases (date, phase, hours, source) VALUES (?, 'total', ?, 'test')",
            (date, hours),
        )
    db.commit()


def _seed_activity_data(db: sqlite3.Connection, days: list[tuple[str, float]]):
    for date, steps in days:
        db.execute(
            "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, 'step_count', ?, 'test')",
            (date, steps),
        )
    db.commit()


def _seed_workout_data(db: sqlite3.Connection, dates: list[str]):
    for date in dates:
        db.execute(
            "INSERT INTO workouts (date, workout_type, duration_minutes, start_time) VALUES (?, 'Running', 30, ?)",
            (date, f"{date}T07:00:00Z"),
        )
    db.commit()


def test_sleep_declining_signal(db):
    from bede_data.analytics.signals import compute_sleep_flags

    _seed_sleep_data(db, [
        ("2026-04-26", 5.0),
        ("2026-04-27", 4.5),
        ("2026-04-28", 5.2),
    ])
    flags = compute_sleep_flags(db, target_hours=7.0, window_days=3, reference_date="2026-04-28")
    assert len(flags) == 1
    assert flags[0]["signal"] == "sleep_declining"
    assert flags[0]["severity"] == "concern"


def test_sleep_ok_no_flag(db):
    from bede_data.analytics.signals import compute_sleep_flags

    _seed_sleep_data(db, [
        ("2026-04-26", 7.5),
        ("2026-04-27", 7.0),
        ("2026-04-28", 8.0),
    ])
    flags = compute_sleep_flags(db, target_hours=7.0, window_days=3, reference_date="2026-04-28")
    assert len(flags) == 0


def test_exercise_gap_signal(db):
    from bede_data.analytics.signals import compute_activity_flags

    _seed_workout_data(db, ["2026-04-20"])
    flags = compute_activity_flags(db, gap_threshold_days=5, reference_date="2026-04-29")
    assert len(flags) == 1
    assert flags[0]["signal"] == "exercise_gap"
    assert flags[0]["severity"] == "nudge"


def test_exercise_recent_no_flag(db):
    from bede_data.analytics.signals import compute_activity_flags

    _seed_workout_data(db, ["2026-04-28"])
    flags = compute_activity_flags(db, gap_threshold_days=5, reference_date="2026-04-29")
    assert len(flags) == 0


def test_goal_stale_signal(db):
    from bede_data.analytics.signals import compute_goal_flags

    db.execute(
        "INSERT INTO goals (name, status, created_at, updated_at) VALUES (?, 'active', ?, ?)",
        ("AWS cert", "2026-04-01T00:00:00Z", "2026-04-01T00:00:00Z"),
    )
    db.commit()
    flags = compute_goal_flags(db, stale_threshold_days=14, reference_date="2026-04-29")
    assert len(flags) == 1
    assert flags[0]["signal"] == "goal_stale"


def test_goal_recently_updated_no_flag(db):
    from bede_data.analytics.signals import compute_goal_flags

    db.execute(
        "INSERT INTO goals (name, status, created_at, updated_at) VALUES (?, 'active', ?, ?)",
        ("AWS cert", "2026-04-01T00:00:00Z", "2026-04-28T00:00:00Z"),
    )
    db.commit()
    flags = compute_goal_flags(db, stale_threshold_days=14, reference_date="2026-04-29")
    assert len(flags) == 0


def test_screen_time_spike_signal(db):
    from bede_data.analytics.signals import compute_screen_time_flags

    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-22', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-23', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-24', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-25', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-26', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-27', 'iphone', 'app', 'YouTube', 3600)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-28', 'iphone', 'app', 'YouTube', 7200)")
    db.execute("INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES ('2026-04-29', 'iphone', 'app', 'YouTube', 7200)")
    db.commit()

    flags = compute_screen_time_flags(db, spike_threshold_pct=40, window_days=7, reference_date="2026-04-29")
    assert any(f["signal"] == "passive_screen_up" for f in flags)


def test_medication_missed_signal(db):
    from bede_data.analytics.signals import compute_medication_flags

    db.execute("INSERT INTO medications (date, medication, quantity, unit, recorded_at) VALUES ('2026-04-27', 'Lexapro', 1, 'tablet', '2026-04-27T08:00:00Z')")
    db.commit()

    flags = compute_medication_flags(db, reference_date="2026-04-29")
    assert len(flags) == 1
    assert flags[0]["signal"] == "medication_missed"
    assert flags[0]["severity"] == "alert"


def test_bedtime_drift_signal(db):
    from bede_data.analytics.signals import compute_bedtime_flags

    _seed_sleep_data(db, [])
    for i, date in enumerate(["2026-04-22", "2026-04-23", "2026-04-24", "2026-04-25", "2026-04-26", "2026-04-27", "2026-04-28"]):
        bedtime_hour = 23 if i < 4 else 0
        db.execute(
            "INSERT OR REPLACE INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, 'inBed', 8, ?, ?, 'test')",
            (date, f"{date}T{bedtime_hour:02d}:00:00Z", f"{date}T07:00:00Z"),
        )
    db.commit()

    flags = compute_bedtime_flags(db, drift_threshold_minutes=30, window_days=7)
    assert any(f["signal"] == "bedtime_drifting" for f in flags)


def test_goal_drifting_signal(db):
    from bede_data.analytics.signals import compute_goal_flags

    db.execute(
        "INSERT INTO goals (name, description, deadline, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)",
        ("Read 2 books", "Read 2 fiction books in May", "2026-05-10", "2026-04-01T00:00:00Z", "2026-04-01T00:00:00Z"),
    )
    db.commit()
    flags = compute_goal_flags(db, stale_threshold_days=14, reference_date="2026-04-29")
    drifting = [f for f in flags if f["signal"] == "goal_drifting"]
    assert len(drifting) == 1
    assert "11 days" in drifting[0]["detail"]
