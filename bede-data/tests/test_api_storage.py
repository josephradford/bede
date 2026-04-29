def test_get_storage_stats(client, db):
    db.execute("INSERT INTO health_metrics (date, metric, value, source) VALUES ('2026-04-29', 'steps', 8000, 'test')")
    db.execute("INSERT INTO memories (content, type) VALUES ('test', 'fact')")
    db.commit()

    response = client.get("/api/storage")
    assert response.status_code == 200
    data = response.json()
    assert "db_size_bytes" in data
    assert "tables" in data
    assert any(t["name"] == "health_metrics" for t in data["tables"])
