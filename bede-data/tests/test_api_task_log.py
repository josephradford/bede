def test_log_task_start(client):
    response = client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "running",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "running"


def test_update_task_completion(client):
    resp = client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "running",
        },
    )
    task_id = resp.json()["id"]
    response = client.put(
        f"/api/tasks/log/{task_id}",
        json={
            "status": "success",
            "end_time": "2026-04-29T08:05:00Z",
            "duration_seconds": 300,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["duration_seconds"] == 300


def test_log_task_failure(client):
    resp = client.post(
        "/api/tasks/log",
        json={
            "task_name": "Deal Scout",
            "start_time": "2026-04-29T14:00:00Z",
            "status": "running",
        },
    )
    task_id = resp.json()["id"]
    response = client.put(
        f"/api/tasks/log/{task_id}",
        json={"status": "failure", "error_detail": "Claude session timeout"},
    )
    assert response.status_code == 200
    assert response.json()["error_detail"] == "Claude session timeout"


def test_get_task_history(client):
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Evening Reflection",
            "start_time": "2026-04-29T21:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-30T08:00:00Z",
            "status": "failure",
        },
    )

    response = client.get("/api/tasks/history")
    assert response.status_code == 200
    assert len(response.json()["executions"]) == 3


def test_get_task_history_filter_name(client):
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Evening Reflection",
            "start_time": "2026-04-29T21:00:00Z",
            "status": "success",
        },
    )

    response = client.get(
        "/api/tasks/history", params={"task_name": "Morning Briefing"}
    )
    assert len(response.json()["executions"]) == 1
