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
        "price_history",
        "dead_urls",
        "articles",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_wal_mode_enabled(db):
    cursor = db.execute("PRAGMA journal_mode")
    assert cursor.fetchone()[0] == "wal"


def test_schema_version_is_set(db):
    cursor = db.execute("SELECT MAX(version) FROM schema_version")
    version = cursor.fetchone()[0]
    assert version == 11


def test_health_metrics_upsert_by_natural_key(db):
    db.execute(
        "INSERT INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "steps", 8000, "apple_health", "2026-04-29T00:00:00Z"),
    )
    db.execute(
        "INSERT OR REPLACE INTO health_metrics (date, metric, value, source, recorded_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "steps", 9000, "apple_health", "2026-04-29T00:00:00Z"),
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


def test_prototype_schema_detection(tmp_path):
    from bede_data.db.schema import tables_needing_reset

    db_path = str(tmp_path / "prototype.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE sleep_phases (id INTEGER PRIMARY KEY, date TEXT, stage TEXT, hours REAL, sleep_start TEXT, sleep_end TEXT, source TEXT)"
    )
    conn.execute(
        "CREATE TABLE workouts (id INTEGER PRIMARY KEY, date TEXT, workout_name TEXT, start_time TEXT, end_time TEXT, duration_min REAL, active_energy_kj REAL, avg_heart_rate_bpm REAL, max_heart_rate_bpm REAL)"
    )
    conn.execute(
        "CREATE TABLE screen_time (id INTEGER PRIMARY KEY, date TEXT, device TEXT, entry_type TEXT, identifier TEXT, seconds INTEGER)"
    )
    conn.commit()

    reset = tables_needing_reset(conn)
    assert "sleep_phases" in reset
    assert "workouts" in reset
    assert "screen_time" in reset
    conn.close()


def test_prototype_schema_not_detected_for_new_tables(db):
    from bede_data.db.schema import tables_needing_reset

    assert tables_needing_reset(db) == []


def test_price_history_table_exists(db):
    db.execute(
        "INSERT INTO monitored_items (category, name, config) VALUES ('deal', 'Test', '{}')"
    )
    db.execute(
        "INSERT INTO price_history (monitored_item_id, url, price, currency, in_stock, checked_at) "
        "VALUES (1, 'https://example.com', 99.95, 'AUD', 1, '2026-05-07T00:00:00Z')"
    )
    row = db.execute("SELECT * FROM price_history WHERE id = 1").fetchone()
    assert row is not None
    assert row["price"] == 99.95


def test_dead_urls_table_exists(db):
    db.execute(
        "INSERT INTO dead_urls (url, category, last_error, checked_at) "
        "VALUES ('https://dead.example.com', 'deal', '404 Not Found', '2026-05-07T00:00:00Z')"
    )
    row = db.execute("SELECT * FROM dead_urls WHERE id = 1").fetchone()
    assert row is not None
    assert row["fail_count"] == 1


def test_articles_table_exists(db):
    db.execute(
        "INSERT INTO articles (url, title, source_name, category, summary, fetched_at) "
        "VALUES ('https://example.com/article', 'Test Article', 'Hacker News', 'tech', 'Summary text', '2026-05-07T00:00:00Z')"
    )
    row = db.execute("SELECT * FROM articles WHERE id = 1").fetchone()
    assert row is not None
    assert row["title"] == "Test Article"


def test_articles_url_unique(db):
    db.execute(
        "INSERT INTO articles (url, title, source_name, category, fetched_at) "
        "VALUES ('https://example.com/a', 'First', 'src', 'tech', '2026-05-07T00:00:00Z')"
    )
    import sqlite3 as _sqlite3

    try:
        db.execute(
            "INSERT INTO articles (url, title, source_name, category, fetched_at) "
            "VALUES ('https://example.com/a', 'Duplicate', 'src', 'tech', '2026-05-07T01:00:00Z')"
        )
        assert False, "Should have raised IntegrityError"
    except _sqlite3.IntegrityError:
        pass


def test_data_freshness_has_always_expected_column(db):
    cols = {row[1] for row in db.execute("PRAGMA table_info(data_freshness)").fetchall()}
    assert "always_expected" in cols
    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds, always_expected) VALUES (?, ?, ?, ?)",
        ("test_source", "2026-05-10T00:00:00Z", 1800, 1),
    )
    db.commit()
    row = db.execute("SELECT always_expected FROM data_freshness WHERE source = 'test_source'").fetchone()
    assert row["always_expected"] == 1


def test_data_freshness_always_expected_defaults_to_true(db):
    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds) VALUES (?, ?, ?)",
        ("test_default", "2026-05-10T00:00:00Z", 1800),
    )
    db.commit()
    row = db.execute("SELECT always_expected FROM data_freshness WHERE source = 'test_default'").fetchone()
    assert row["always_expected"] == 1
