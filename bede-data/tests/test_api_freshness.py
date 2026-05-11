def test_get_freshness_empty_shows_always_expected_placeholders(client, monkeypatch):
    import httpx

    def raise_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.get", raise_error)

    response = client.get("/api/freshness")
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert len(sources) == 8
    assert all(s["always_expected"] == 1 for s in sources)
    assert all(s["last_received_at"] is None for s in sources)
    names = {s["source"] for s in sources}
    assert names == {
        "health_metrics",
        "sleep",
        "workouts",
        "medications",
        "state_of_mind",
        "screen_time_mac",
        "screen_time_iphone",
        "safari_history",
    }


def test_get_freshness_with_data(client, db, monkeypatch):
    import httpx

    monkeypatch.setattr(
        "httpx.get", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError(""))
    )

    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds, always_expected) VALUES (?, ?, ?, ?)",
        ("health_metrics", "2026-04-29T08:00:00Z", 1800, 1),
    )
    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds, always_expected) VALUES (?, ?, ?, ?)",
        ("screen_time_mac", "2026-04-29T06:00:00Z", 10800, 1),
    )
    db.commit()

    response = client.get("/api/freshness")
    sources = {s["source"]: s for s in response.json()["sources"]}
    assert len(sources) == 8
    assert sources["health_metrics"]["last_received_at"] == "2026-04-29T08:00:00Z"
    assert sources["screen_time_mac"]["last_received_at"] == "2026-04-29T06:00:00Z"
    assert sources["sleep"]["last_received_at"] is None


def test_health_ingest_updates_granular_freshness(client, db):
    from bede_data.config import settings

    settings.ingest_write_token = "test-token"
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "data": [
                        {
                            "date": "2026-05-10 00:00:00 +1000",
                            "qty": 8000,
                            "source": "Apple Watch",
                        }
                    ],
                }
            ]
        }
    }
    response = client.post(
        "/ingest/health",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200

    cursor = db.execute(
        "SELECT source, expected_interval_seconds, always_expected FROM data_freshness ORDER BY source"
    )
    sources = {row["source"]: row for row in cursor.fetchall()}
    assert "health_metrics" in sources
    assert sources["health_metrics"]["expected_interval_seconds"] == 1800
    assert sources["health_metrics"]["always_expected"] == 1
    assert "health" not in sources


def test_freshness_includes_always_expected_field(client, db, monkeypatch):
    import httpx

    monkeypatch.setattr(
        "httpx.get", lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError(""))
    )

    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds, always_expected) VALUES (?, ?, ?, ?)",
        ("youtube_history", "2026-05-10T08:00:00Z", 10800, 0),
    )
    db.commit()

    response = client.get("/api/freshness")
    sources = {s["source"]: s for s in response.json()["sources"]}
    assert len(sources) == 9
    assert sources["youtube_history"]["always_expected"] == 0
    assert sources["youtube_history"]["last_received_at"] == "2026-05-10T08:00:00Z"


def test_freshness_includes_owntracks(client, db, monkeypatch):
    import httpx

    mock_response = httpx.Response(
        200,
        json=[{"tst": 1715320500, "_type": "location"}],
    )
    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: mock_response)

    response = client.get("/api/freshness")
    sources = {s["source"]: s for s in response.json()["sources"]}
    assert "owntracks" in sources
    assert sources["owntracks"]["expected_interval_seconds"] == 3600
    assert sources["owntracks"]["always_expected"] == 1
    assert sources["owntracks"]["updated_at"] is None


def test_freshness_omits_owntracks_when_recorder_unreachable(client, db, monkeypatch):
    import httpx

    def raise_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.get", raise_error)

    response = client.get("/api/freshness")
    assert response.status_code == 200
    sources = [s["source"] for s in response.json()["sources"]]
    assert "owntracks" not in sources
