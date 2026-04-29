def _seed_vault_data(db):
    db.execute(
        "INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "mac", "app", "Safari", 3600),
    )
    db.execute(
        "INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "mac", "app", "Terminal", 1800),
    )
    db.execute(
        "INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "mac", "web", "github.com", 900),
    )
    db.execute(
        "INSERT INTO screen_time (date, device, entry_type, name, seconds) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "iphone", "app", "Instagram", 2400),
    )
    db.execute(
        "INSERT INTO safari_history (date, device, domain, title, url, visited_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-29", "mac", "github.com", "GitHub", "https://github.com", "2026-04-29T10:00:00Z"),
    )
    db.execute(
        "INSERT INTO safari_history (date, device, domain, title, url, visited_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-04-29", "mac", "docs.python.org", "Python Docs", "https://docs.python.org/3/", "2026-04-29T11:00:00Z"),
    )
    db.execute(
        "INSERT INTO youtube_history (date, title, url, visited_at) VALUES (?, ?, ?, ?)",
        ("2026-04-29", "Cool Video", "https://youtube.com/watch?v=abc", "2026-04-29T14:00:00Z"),
    )
    db.execute(
        "INSERT INTO podcasts (date, podcast, episode, duration_seconds, played_at) VALUES (?, ?, ?, ?, ?)",
        ("2026-04-29", "The Daily", "Episode 123", 1800, "2026-04-29T08:00:00Z"),
    )
    db.execute(
        "INSERT INTO claude_sessions (date, project, start_time, end_time, duration_min, turns, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2026-04-29", "home-server-stack", "2026-04-29 09:00", "2026-04-29 10:30", 90, 25, "Worked on Bede plan"),
    )
    db.execute(
        "INSERT INTO bede_sessions (date, task_name, start_time, end_time, duration_min, turns, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2026-04-29", "Morning Briefing", "2026-04-29 08:00", "2026-04-29 08:05", 5, 3, "Delivered briefing"),
    )
    db.commit()


def test_get_screen_time(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/screen-time", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 4


def test_get_screen_time_filter_device(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/screen-time", params={"date": "2026-04-29", "device": "mac"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 3
    assert all(e["device"] == "mac" for e in data["entries"])


def test_get_screen_time_top_n(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/screen-time", params={"date": "2026-04-29", "device": "mac", "top_n": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["seconds"] >= data["entries"][1]["seconds"]


def test_get_safari(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/safari", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2


def test_get_safari_filter_domain(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/safari", params={"date": "2026-04-29", "domain": "github.com"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["domain"] == "github.com"


def test_get_youtube(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/youtube", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["title"] == "Cool Video"


def test_get_podcasts(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/podcasts", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["podcast"] == "The Daily"


def test_get_claude_sessions(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/claude-sessions", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["project"] == "home-server-stack"


def test_get_bede_sessions(client, db):
    _seed_vault_data(db)
    response = client.get("/api/vault/bede-sessions", params={"date": "2026-04-29"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["task_name"] == "Morning Briefing"
