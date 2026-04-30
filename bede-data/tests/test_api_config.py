def test_create_schedule(client):
    response = client.post(
        "/api/config/schedules",
        json={
            "task_name": "Morning Briefing",
            "cron_expression": "0 8 * * 1-5",
            "prompt": "Deliver the morning briefing",
            "model": "sonnet",
            "timeout_seconds": 300,
            "interactive": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == "Morning Briefing"
    assert data["interactive"] is True


def test_list_schedules(client):
    client.post(
        "/api/config/schedules",
        json={"task_name": "Task A", "cron_expression": "0 8 * * *", "prompt": "A"},
    )
    client.post(
        "/api/config/schedules",
        json={"task_name": "Task B", "cron_expression": "0 21 * * *", "prompt": "B"},
    )
    response = client.get("/api/config/schedules")
    assert len(response.json()["schedules"]) == 2


def test_update_schedule(client):
    resp = client.post(
        "/api/config/schedules",
        json={"task_name": "Briefing", "cron_expression": "0 8 * * *", "prompt": "Old"},
    )
    sid = resp.json()["id"]
    response = client.put(
        f"/api/config/schedules/{sid}", json={"cron_expression": "30 7 * * *"}
    )
    assert response.status_code == 200
    assert response.json()["cron_expression"] == "30 7 * * *"


def test_set_and_get_setting(client):
    client.put("/api/config/settings/quiet_hours_start", json={"value": "22:00"})
    response = client.get("/api/config/settings/quiet_hours_start")
    assert response.status_code == 200
    assert response.json()["value"] == "22:00"


def test_list_settings(client):
    client.put("/api/config/settings/quiet_hours_start", json={"value": "22:00"})
    client.put("/api/config/settings/quiet_hours_end", json={"value": "07:00"})
    response = client.get("/api/config/settings")
    assert len(response.json()["settings"]) == 2


def test_create_monitored_item(client):
    response = client.post(
        "/api/config/monitored-items",
        json={
            "category": "deal",
            "name": "Camping Gear",
            "config": '{"retailers": ["anaconda.com.au"], "check_cadence": "weekly"}',
        },
    )
    assert response.status_code == 201
    assert response.json()["category"] == "deal"


def test_list_monitored_items_filter_category(client):
    client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Camping", "config": "{}"},
    )
    client.post(
        "/api/config/monitored-items",
        json={"category": "content_source", "name": "Hacker News", "config": "{}"},
    )
    response = client.get("/api/config/monitored-items", params={"category": "deal"})
    assert len(response.json()["items"]) == 1


def test_delete_monitored_item(client):
    resp = client.post(
        "/api/config/monitored-items",
        json={"category": "deal", "name": "Old", "config": "{}"},
    )
    item_id = resp.json()["id"]
    response = client.delete(f"/api/config/monitored-items/{item_id}")
    assert response.status_code == 200
    assert len(client.get("/api/config/monitored-items").json()["items"]) == 0
