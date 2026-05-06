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


def test_get_task_history_filter_since(client):
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-28T08:00:00Z",
            "status": "success",
        },
    )
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
            "start_time": "2026-04-30T21:00:00Z",
            "status": "success",
        },
    )

    response = client.get(
        "/api/tasks/history", params={"since": "2026-04-29T00:00:00Z"}
    )
    assert response.status_code == 200
    execs = response.json()["executions"]
    assert len(execs) == 2
    assert all(e["start_time"] >= "2026-04-29T00:00:00Z" for e in execs)


def test_get_task_history_filter_until(client):
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-28T08:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "Morning Briefing",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "success",
        },
    )

    response = client.get(
        "/api/tasks/history", params={"until": "2026-04-28T23:59:59Z"}
    )
    assert response.status_code == 200
    execs = response.json()["executions"]
    assert len(execs) == 1
    assert execs[0]["start_time"] == "2026-04-28T08:00:00Z"


def test_get_task_history_filter_since_and_until(client):
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "A",
            "start_time": "2026-04-27T08:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "B",
            "start_time": "2026-04-28T08:00:00Z",
            "status": "success",
        },
    )
    client.post(
        "/api/tasks/log",
        json={
            "task_name": "C",
            "start_time": "2026-04-29T08:00:00Z",
            "status": "success",
        },
    )

    response = client.get(
        "/api/tasks/history",
        params={"since": "2026-04-28T00:00:00Z", "until": "2026-04-28T23:59:59Z"},
    )
    assert response.status_code == 200
    execs = response.json()["executions"]
    assert len(execs) == 1
    assert execs[0]["task_name"] == "B"
