import sqlite3

import pytest


def test_schema_creates_all_tables(db):
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cursor.fetchall()}
    expected = {
        "schema_version",
        "health_metrics",
        "sleep_phases",
        "workouts",
        "state_of_mind",
        "medications",
        "screen_time",
        "safari_history",
        "youtube_history",
        "podcasts",
        "claude_sessions",
        "bede_sessions",
        "music_listens",
        "memories",
        "goals",
        "task_executions",
        "analytics_flags",
        "analytics_thresholds",
        "schedules",
        "monitored_items",
        "settings",
        "daily_scratchpads",
        "daily_sessions",
        "vault_publish_queue",
        "message_queue",
        "data_freshness",
        "retention_policies",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_wal_mode_enabled(db):
    cursor = db.execute("PRAGMA journal_mode")
    assert cursor.fetchone()[0] == "wal"


def test_schema_version_is_set(db):
    cursor = db.execute("SELECT MAX(version) FROM schema_version")
    version = cursor.fetchone()[0]
    assert version == 1


def test_health_metrics_upsert_by_natural_key(db):
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "steps", 8000, "apple_health"),
    )
    db.execute(
        "INSERT OR REPLACE INTO health_metrics (date, metric, value, source) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "steps", 9000, "apple_health"),
    )
    db.commit()
    cursor = db.execute(
        "SELECT value FROM health_metrics WHERE date = ? AND metric = ? AND source = ?",
        ("2026-04-29", "steps", "apple_health"),
    )
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 9000


def test_memories_check_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO memories (content, type) VALUES (?, ?)",
            ("test", "invalid_type"),
        )


def test_goals_status_check_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO goals (name, status) VALUES (?, ?)",
            ("test goal", "invalid_status"),
        )
