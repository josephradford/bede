def test_create_goal(client):
    response = client.post(
        "/api/goals",
        json={
            "name": "AWS Solutions Architect cert",
            "description": "Pass the SAA-C03 exam",
            "deadline": "2026-09-01",
            "measurable_indicators": "Complete all practice exams with 80%+",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "AWS Solutions Architect cert"
    assert data["status"] == "active"


def test_list_goals(client):
    client.post("/api/goals", json={"name": "Goal 1"})
    client.post("/api/goals", json={"name": "Goal 2"})
    response = client.get("/api/goals")
    assert response.status_code == 200
    assert len(response.json()["goals"]) == 2


def test_list_goals_filter_status(client):
    resp = client.post("/api/goals", json={"name": "Active goal"})
    gid = resp.json()["id"]
    client.post("/api/goals", json={"name": "Another goal"})
    client.put(f"/api/goals/{gid}", json={"status": "completed"})

    response = client.get("/api/goals", params={"status": "active"})
    assert len(response.json()["goals"]) == 1
    assert response.json()["goals"][0]["name"] == "Another goal"


def test_update_goal(client):
    resp = client.post("/api/goals", json={"name": "Read 2 books"})
    gid = resp.json()["id"]
    response = client.put(
        f"/api/goals/{gid}",
        json={"description": "Read 2 fiction books in May", "status": "active"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Read 2 fiction books in May"


def test_complete_goal(client):
    resp = client.post("/api/goals", json={"name": "Run 5k"})
    gid = resp.json()["id"]
    response = client.put(f"/api/goals/{gid}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_drop_goal(client):
    resp = client.post("/api/goals", json={"name": "Dropped goal"})
    gid = resp.json()["id"]
    response = client.put(f"/api/goals/{gid}", json={"status": "dropped"})
    assert response.status_code == 200
    assert response.json()["status"] == "dropped"


def test_get_goal_not_found(client):
    response = client.get("/api/goals/999")
    assert response.status_code == 404
