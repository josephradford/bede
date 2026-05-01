def _seed_health_data(db):
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "step_count", 8500, "iPhone"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "active_energy", 2100.5, "Apple Watch"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "apple_exercise_time", 35, "Apple Watch"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "apple_stand_hour", 10, "Apple Watch"),
    )
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "2026-04-29",
            "asleepCore",
            3.5,
            "2026-04-28T23:00:00Z",
            "2026-04-29T02:30:00Z",
            "Apple Watch",
        ),
    )
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "2026-04-29",
            "asleepDeep",
            1.5,
            "2026-04-29T02:30:00Z",
            "2026-04-29T04:00:00Z",
            "Apple Watch",
        ),
    )
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "2026-04-29",
            "asleepREM",
            2.0,
            "2026-04-29T04:00:00Z",
            "2026-04-29T06:00:00Z",
            "Apple Watch",
        ),
    )
    db.execute(
        "INSERT INTO workouts (date, workout_type, duration_minutes, active_energy_kj, avg_heart_rate, max_heart_rate, start_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2026-04-29", "Running", 45.0, 1800, 155, 178, "2026-04-29T07:00:00Z"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "resting_heart_rate", 62, "Apple Watch"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "heart_rate_variability", 45, "Apple Watch"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "mindful_minutes", 15, "iPhone"),
    )
    db.execute(
        "INSERT INTO state_of_mind (date, valence, labels, context, associations, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "2026-04-29",
            0.7,
            "Happy,Calm",
            "Work",
            "Productivity",
            "2026-04-29T14:00:00Z",
        ),
    )
    db.execute(
        "INSERT INTO medications (date, medication, quantity, unit, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "Lexapro", 1, "tablet", "2026-04-29T08:00:00Z"),
    )
    db.commit()


def test_get_sleep(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/sleep", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-04-29"
    assert data["total_hours"] == 7.0
    assert len(data["phases"]) == 3
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["total_hours"] == 7.0


def test_get_activity(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/activity", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-04-29"
    assert data["steps"] == 8500
    assert data["active_energy"] == 2100.5
    assert data["exercise_minutes"] == 35
    assert data["stand_hours"] == 10


def test_get_activity_sums_multiple_readings(client, db):
    """Step count should be the sum of all readings, not just the last one."""
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 100, "Apple Watch", "2026-04-30T08:00:00Z"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 250, "Apple Watch", "2026-04-30T09:00:00Z"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 400, "Apple Watch", "2026-04-30T10:00:00Z"),
    )
    db.commit()
    response = client.get("/api/health/activity", params={"date": "2026-04-30"})
    assert response.status_code == 200
    data = response.json()
    assert data["steps"] == 750


def test_get_activity_deduplicates_across_sources(client, db):
    """Same reading from multiple sources should not be double-counted."""
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 100, "Apple Watch", "2026-04-30T08:00:00Z"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 100, "GymKit|Apple Watch|iPhone", "2026-04-30T08:00:00Z"),
    )
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-30", "step_count", 200, "Apple Watch", "2026-04-30T09:00:00Z"),
    )
    db.commit()
    response = client.get("/api/health/activity", params={"date": "2026-04-30"})
    assert response.status_code == 200
    data = response.json()
    assert data["steps"] == 300


def test_get_workouts(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/workouts", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["workouts"]) == 1
    assert data["workouts"][0]["workout_type"] == "Running"
    assert data["workouts"][0]["duration_minutes"] == 45.0


def test_get_heart_rate(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/heart-rate", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert data["resting_heart_rate"] == 62
    assert data["heart_rate_variability"] == 45


def test_get_wellbeing(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/wellbeing", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert data["mindful_minutes"] == 15
    assert len(data["state_of_mind"]) == 1
    assert data["state_of_mind"][0]["valence"] == 0.7


def test_get_medications(client, db):
    _seed_health_data(db)
    response = client.get("/api/health/medications", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["medications"]) == 1
    assert data["medications"][0]["medication"] == "Lexapro"


def test_get_sleep_separates_nap_from_overnight(client, db):
    """Overnight sleep + afternoon nap should be separate sessions."""
    # Overnight: 11:18 PM -> phases through ~6:20 AM (UTC times)
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-30", "core", 4.0, "2026-04-29T13:18:00Z", "2026-04-29T17:18:00Z", "Apple Watch"),
    )
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-30", "rem", 1.5, "2026-04-29T17:18:00Z", "2026-04-29T18:48:00Z", "Apple Watch"),
    )
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-30", "deep", 0.5, "2026-04-29T18:48:00Z", "2026-04-29T19:18:00Z", "Apple Watch"),
    )
    # Afternoon nap: 3:12 PM -> 4:20 PM AEST = 05:12 -> 06:20 UTC (3h+ gap from overnight)
    db.execute(
        "INSERT INTO sleep_phases (date, phase, hours, start_time, end_time, source) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-30", "asleep", 1.1, "2026-04-30T05:12:00Z", "2026-04-30T06:18:00Z", "Apple Watch"),
    )
    db.commit()

    response = client.get("/api/health/sleep", params={"date": "2026-04-30"})
    assert response.status_code == 200
    data = response.json()

    assert len(data["sessions"]) == 2
    assert data["sessions"][0]["total_hours"] == 6.0
    assert data["sessions"][1]["total_hours"] == 1.1
    assert data["total_hours"] == 7.1
    # bedtime/wake_time should be from the primary (first) session
    assert data["bedtime"] == "2026-04-29T13:18:00Z"
    assert data["wake_time"] == "2026-04-29T19:18:00Z"


def test_get_sleep_no_data(client, db):
    response = client.get("/api/health/sleep", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_hours"] == 0
    assert data["phases"] == []
    assert data["sessions"] == []
