SCHEMA_VERSION = 4

# Tables whose column names changed from the prototype bede schema.
# init_db drops these if they have old-style columns, then SCHEMA_SQL recreates them.
_PROTOTYPE_COLUMNS = {
    "sleep_phases": "stage",
    "workouts": "workout_name",
    "screen_time": "identifier",
    "medications": "name",
    "bede_sessions": "project",
    "state_of_mind": "associations",  # missing in prototype — presence means new schema
}


def tables_needing_reset(conn) -> list[str]:
    """Return table names that still have the prototype schema."""
    to_reset = []
    for table, marker_col in _PROTOTYPE_COLUMNS.items():
        cols = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if not cols:
            continue
        if table == "state_of_mind":
            if marker_col not in cols:
                to_reset.append(table)
        else:
            if marker_col in cols:
                to_reset.append(table)
    return to_reset


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS health_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    metric      TEXT NOT NULL,
    value       REAL NOT NULL,
    source      TEXT,
    recorded_at TEXT,
    UNIQUE (date, metric, source, recorded_at)
);

CREATE TABLE IF NOT EXISTS sleep_phases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    phase       TEXT NOT NULL,
    hours       REAL NOT NULL,
    start_time  TEXT,
    end_time    TEXT,
    source      TEXT,
    UNIQUE (date, phase, source)
);

CREATE TABLE IF NOT EXISTS workouts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL,
    workout_type        TEXT NOT NULL,
    duration_minutes    REAL,
    active_energy_kj    REAL,
    avg_heart_rate      REAL,
    max_heart_rate      REAL,
    start_time          TEXT,
    UNIQUE (date, start_time)
);

CREATE TABLE IF NOT EXISTS state_of_mind (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    valence     REAL,
    labels      TEXT,
    context     TEXT,
    associations TEXT,
    recorded_at TEXT,
    UNIQUE (date, recorded_at)
);

CREATE TABLE IF NOT EXISTS medications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    medication  TEXT NOT NULL,
    quantity    REAL,
    unit        TEXT,
    recorded_at TEXT,
    UNIQUE (date, medication, recorded_at)
);

CREATE TABLE IF NOT EXISTS screen_time (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    device      TEXT NOT NULL,
    entry_type  TEXT NOT NULL,
    name        TEXT NOT NULL,
    seconds     INTEGER NOT NULL,
    UNIQUE (date, device, entry_type, name)
);

CREATE TABLE IF NOT EXISTS safari_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    device      TEXT NOT NULL,
    domain      TEXT,
    title       TEXT,
    url         TEXT NOT NULL,
    visited_at  TEXT NOT NULL,
    UNIQUE (url, visited_at)
);

CREATE TABLE IF NOT EXISTS youtube_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    title       TEXT,
    url         TEXT NOT NULL,
    visited_at  TEXT NOT NULL,
    UNIQUE (url, visited_at)
);

CREATE TABLE IF NOT EXISTS podcasts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT NOT NULL,
    podcast          TEXT NOT NULL,
    episode          TEXT NOT NULL,
    duration_seconds INTEGER,
    played_at        TEXT NOT NULL,
    UNIQUE (episode, played_at)
);

CREATE TABLE IF NOT EXISTS claude_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    project      TEXT,
    start_time   TEXT,
    end_time     TEXT,
    duration_min REAL,
    turns        INTEGER,
    summary      TEXT,
    UNIQUE (project, start_time)
);

CREATE TABLE IF NOT EXISTS bede_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    task_name    TEXT,
    start_time   TEXT,
    end_time     TEXT,
    duration_min REAL,
    turns        INTEGER,
    summary      TEXT,
    UNIQUE (task_name, start_time)
);

CREATE TABLE IF NOT EXISTS music_listens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    track       TEXT NOT NULL,
    artist      TEXT NOT NULL,
    album       TEXT,
    listened_at TEXT NOT NULL,
    UNIQUE (track, artist, listened_at)
);

CREATE TABLE IF NOT EXISTS memories (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    content              TEXT NOT NULL,
    type                 TEXT NOT NULL CHECK (type IN ('fact', 'preference', 'correction', 'commitment')),
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    last_referenced_at   TEXT,
    source_conversation  TEXT,
    superseded_by        INTEGER REFERENCES memories(id),
    active               INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS goals (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    description          TEXT,
    deadline             TEXT,
    measurable_indicators TEXT,
    status               TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'dropped')),
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_executions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name        TEXT NOT NULL,
    start_time       TEXT NOT NULL,
    end_time         TEXT,
    duration_seconds REAL,
    status           TEXT NOT NULL CHECK (status IN ('running', 'success', 'failure', 'timeout')),
    error_detail     TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analytics_flags (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    signal       TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('info', 'nudge', 'concern', 'alert')),
    detail       TEXT,
    data         TEXT,
    computed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analytics_thresholds (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    signal  TEXT NOT NULL UNIQUE,
    config  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name        TEXT NOT NULL UNIQUE,
    cron_expression  TEXT NOT NULL,
    prompt           TEXT NOT NULL,
    model            TEXT,
    timeout_seconds  INTEGER DEFAULT 300,
    interactive      INTEGER NOT NULL DEFAULT 0,
    task_config      TEXT,
    enabled          INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitored_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category   TEXT NOT NULL,
    name       TEXT NOT NULL,
    config     TEXT NOT NULL,
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_scratchpads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    content    TEXT NOT NULL,
    UNIQUE (date, entry_time)
);

CREATE TABLE IF NOT EXISTS daily_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vault_publish_queue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,
    content      TEXT NOT NULL,
    vault_path   TEXT,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'published', 'failed')),
    error_detail TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS message_queue (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    message      TEXT NOT NULL,
    source       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS data_freshness (
    source                   TEXT PRIMARY KEY,
    last_received_at         TEXT NOT NULL,
    expected_interval_seconds INTEGER NOT NULL,
    updated_at               TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS retention_policies (
    data_type      TEXT PRIMARY KEY,
    retention_days INTEGER NOT NULL,
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
