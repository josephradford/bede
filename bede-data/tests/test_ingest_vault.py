from bede_data.config import settings
from bede_data.ingest.vault_parser import parse_vault_payload


def test_parse_screen_time_csv():
    payload = {
        "date": "2026-04-29",
        "files": {
            "screentime.csv": (
                "device,entry_type,name,seconds\n"
                "mac,app,Safari,3600\n"
                "mac,app,Terminal,1800\n"
                "mac,web,github.com,900\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["screen_time"]) == 3
    assert result["screen_time"][0]["device"] == "mac"
    assert result["screen_time"][0]["name"] == "Safari"
    assert result["screen_time"][0]["seconds"] == 3600


def test_parse_iphone_screen_time_csv():
    payload = {
        "date": "2026-04-29",
        "files": {
            "iphone-screentime.csv": (
                "device,entry_type,name,seconds\niphone,app,Instagram,2400\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["screen_time"]) == 1
    assert result["screen_time"][0]["device"] == "iphone"


def test_parse_safari_csv():
    payload = {
        "date": "2026-04-29",
        "files": {
            "safari.csv": (
                "device,domain,title,url,visited_at\n"
                "mac,github.com,GitHub,https://github.com,2026-04-29T10:00:00Z\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["safari_history"]) == 1
    assert result["safari_history"][0]["domain"] == "github.com"
    assert result["safari_history"][0]["url"] == "https://github.com"


def test_parse_youtube_csv():
    payload = {
        "date": "2026-04-29",
        "files": {
            "youtube.csv": (
                "title,url,visited_at\n"
                "Cool Video,https://youtube.com/watch?v=abc,2026-04-29T14:00:00Z\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["youtube_history"]) == 1
    assert result["youtube_history"][0]["title"] == "Cool Video"


def test_parse_podcasts_csv():
    payload = {
        "date": "2026-04-29",
        "files": {
            "podcasts.csv": (
                "podcast,episode,duration_seconds,played_at\n"
                "The Daily,Episode 123,1800,2026-04-29T08:00:00Z\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["podcasts"]) == 1
    assert result["podcasts"][0]["podcast"] == "The Daily"
    assert result["podcasts"][0]["duration_seconds"] == 1800


def test_parse_claude_sessions_markdown():
    payload = {
        "date": "2026-04-29",
        "files": {
            "claude-sessions.md": (
                "## home-server-stack\n"
                "- Start: 2026-04-29 09:00\n"
                "- End: 2026-04-29 10:30\n"
                "- Duration: 90 min\n"
                "- Turns: 25\n"
                "\n"
                "Worked on Bede implementation plan.\n"
            ),
        },
    }
    result = parse_vault_payload(payload)
    assert len(result["claude_sessions"]) == 1
    assert result["claude_sessions"][0]["project"] == "home-server-stack"
    assert result["claude_sessions"][0]["duration_min"] == 90


def test_parse_empty_files():
    payload = {"date": "2026-04-29", "files": {}}
    result = parse_vault_payload(payload)
    assert result["screen_time"] == []
    assert result["safari_history"] == []


def test_ingest_vault_stores_data(client, db):
    settings.ingest_write_token = "test-token"
    payload = {
        "date": "2026-04-29",
        "files": {
            "screentime.csv": ("device,entry_type,name,seconds\nmac,app,Safari,3600\n"),
        },
    }
    response = client.post(
        "/ingest/vault",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json()["records"] > 0

    cursor = db.execute("SELECT * FROM screen_time WHERE date = '2026-04-29'")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Safari"


def test_ingest_vault_replaces_daily_data(client, db):
    settings.ingest_write_token = "test-token"
    headers = {"Authorization": "Bearer test-token"}

    payload1 = {
        "date": "2026-04-29",
        "files": {
            "screentime.csv": (
                "device,entry_type,name,seconds\n"
                "mac,app,Safari,3600\n"
                "mac,app,Terminal,1200\n"
            ),
        },
    }
    client.post("/ingest/vault", json=payload1, headers=headers)

    payload2 = {
        "date": "2026-04-29",
        "files": {
            "screentime.csv": ("device,entry_type,name,seconds\nmac,app,Safari,5400\n"),
        },
    }
    response = client.post("/ingest/vault", json=payload2, headers=headers)
    assert response.status_code == 200

    cursor = db.execute(
        "SELECT * FROM screen_time WHERE date = '2026-04-29' AND device = 'mac'"
    )
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Safari"
    assert rows[0]["seconds"] == 5400
