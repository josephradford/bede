from datetime import datetime, timedelta, timezone


def test_retention_cleanup(client, db):
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).strftime("%Y-%m-%d")
    recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")

    db.execute("INSERT INTO health_metrics (date, metric, value, source) VALUES (?, 'steps', 8000, 'test')", (old_date,))
    db.execute("INSERT INTO health_metrics (date, metric, value, source) VALUES (?, 'steps', 9000, 'test')", (recent_date,))
    db.execute("INSERT INTO retention_policies (data_type, retention_days) VALUES ('health_metrics', 90)")
    db.commit()

    response = client.post("/api/retention/cleanup")
    assert response.status_code == 200
    assert response.json()["rows_deleted"] > 0

    cursor = db.execute("SELECT COUNT(*) as cnt FROM health_metrics")
    assert cursor.fetchone()["cnt"] == 1


def test_set_retention_policy(client):
    response = client.put(
        "/api/retention/policies/health_metrics",
        json={"retention_days": 90},
    )
    assert response.status_code == 200
    assert response.json()["data_type"] == "health_metrics"
    assert response.json()["retention_days"] == 90


def test_list_retention_policies(client):
    client.put("/api/retention/policies/health_metrics", json={"retention_days": 90})
    client.put("/api/retention/policies/task_executions", json={"retention_days": 30})
    response = client.get("/api/retention/policies")
    assert len(response.json()["policies"]) == 2
