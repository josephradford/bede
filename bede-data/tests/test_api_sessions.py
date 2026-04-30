def test_store_daily_session(client):
    response = client.post(
        "/api/sessions/daily",
        json={"date": "2026-04-29", "session_id": "abc-123"},
    )
    assert response.status_code == 201
    assert response.json()["session_id"] == "abc-123"


def test_get_daily_session(client):
    client.post(
        "/api/sessions/daily", json={"date": "2026-04-29", "session_id": "abc-123"}
    )
    response = client.get("/api/sessions/daily", params={"date": "2026-04-29"})
    assert response.status_code == 200
    assert response.json()["session_id"] == "abc-123"


def test_get_daily_session_not_found(client):
    response = client.get("/api/sessions/daily", params={"date": "2026-04-29"})
    assert response.status_code == 404


def test_upsert_daily_session(client):
    client.post(
        "/api/sessions/daily", json={"date": "2026-04-29", "session_id": "old-session"}
    )
    client.post(
        "/api/sessions/daily", json={"date": "2026-04-29", "session_id": "new-session"}
    )
    response = client.get("/api/sessions/daily", params={"date": "2026-04-29"})
    assert response.json()["session_id"] == "new-session"


def test_append_scratchpad(client):
    response = client.post(
        "/api/scratchpad",
        json={
            "date": "2026-04-29",
            "entry_time": "08:00",
            "content": "[08:00] Morning Briefing: 2 calendar events, flagged poor sleep.",
        },
    )
    assert response.status_code == 201


def test_get_scratchpad(client):
    client.post(
        "/api/scratchpad",
        json={"date": "2026-04-29", "entry_time": "08:00", "content": "Morning entry"},
    )
    client.post(
        "/api/scratchpad",
        json={"date": "2026-04-29", "entry_time": "12:30", "content": "Midday entry"},
    )

    response = client.get("/api/scratchpad", params={"date": "2026-04-29"})
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 2
    assert entries[0]["entry_time"] == "08:00"
    assert entries[1]["entry_time"] == "12:30"


def test_get_scratchpad_empty(client):
    response = client.get("/api/scratchpad", params={"date": "2026-04-29"})
    assert response.status_code == 200
    assert response.json()["entries"] == []
