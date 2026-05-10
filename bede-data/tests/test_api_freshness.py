def test_get_freshness_empty(client):
    response = client.get("/api/freshness")
    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_get_freshness_with_data(client, db):
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
    data = response.json()
    assert len(data["sources"]) == 2
    assert all(
        "source" in s and "last_received_at" in s and "always_expected" in s
        for s in data["sources"]
    )


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
