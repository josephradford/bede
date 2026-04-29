def test_get_freshness_empty(client):
    response = client.get("/api/freshness")
    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_get_freshness_with_data(client, db):
    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds) VALUES (?, ?, ?)",
        ("health", "2026-04-29T08:00:00Z", 86400),
    )
    db.execute(
        "INSERT INTO data_freshness (source, last_received_at, expected_interval_seconds) VALUES (?, ?, ?)",
        ("vault", "2026-04-29T06:00:00Z", 86400),
    )
    db.commit()

    response = client.get("/api/freshness")
    data = response.json()
    assert len(data["sources"]) == 2
    assert all("source" in s and "last_received_at" in s for s in data["sources"])
