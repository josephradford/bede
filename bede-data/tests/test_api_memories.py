def test_create_memory(client):
    response = client.post(
        "/api/memories",
        json={
            "content": "Training for a half marathon",
            "type": "fact",
            "source_conversation": "session-123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["content"] == "Training for a half marathon"
    assert data["type"] == "fact"
    assert data["active"] is True


def test_create_memory_invalid_type(client):
    response = client.post(
        "/api/memories",
        json={"content": "test", "type": "invalid"},
    )
    assert response.status_code == 422


def test_list_memories(client):
    client.post("/api/memories", json={"content": "Fact one", "type": "fact"})
    client.post("/api/memories", json={"content": "Pref one", "type": "preference"})
    response = client.get("/api/memories")
    assert response.status_code == 200
    data = response.json()
    assert len(data["memories"]) == 2


def test_list_memories_filter_type(client):
    client.post("/api/memories", json={"content": "Fact one", "type": "fact"})
    client.post("/api/memories", json={"content": "Pref one", "type": "preference"})
    response = client.get("/api/memories", params={"type": "fact"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["memories"]) == 1
    assert data["memories"][0]["type"] == "fact"


def test_list_memories_search(client):
    client.post("/api/memories", json={"content": "Training for a half marathon", "type": "fact"})
    client.post("/api/memories", json={"content": "Likes Thai food", "type": "preference"})
    response = client.get("/api/memories", params={"search": "marathon"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["memories"]) == 1


def test_update_memory(client):
    resp = client.post("/api/memories", json={"content": "Training for 10k", "type": "fact"})
    mem_id = resp.json()["id"]
    response = client.put(f"/api/memories/{mem_id}", json={"content": "Training for half marathon"})
    assert response.status_code == 200
    assert response.json()["content"] == "Training for half marathon"


def test_delete_memory(client):
    resp = client.post("/api/memories", json={"content": "Old info", "type": "fact"})
    mem_id = resp.json()["id"]
    response = client.delete(f"/api/memories/{mem_id}")
    assert response.status_code == 200

    listing = client.get("/api/memories")
    assert len(listing.json()["memories"]) == 0


def test_correction_supersedes_previous(client):
    resp1 = client.post("/api/memories", json={"content": "Favourite colour is blue", "type": "fact"})
    old_id = resp1.json()["id"]
    resp2 = client.post(
        "/api/memories",
        json={"content": "Favourite colour is green", "type": "correction", "supersedes": old_id},
    )
    assert resp2.status_code == 201

    listing = client.get("/api/memories")
    active = [m for m in listing.json()["memories"] if m["active"]]
    assert len(active) == 1
    assert active[0]["content"] == "Favourite colour is green"


def test_reference_memory(client):
    resp = client.post("/api/memories", json={"content": "Likes camping", "type": "fact"})
    mem_id = resp.json()["id"]
    response = client.post(f"/api/memories/{mem_id}/reference")
    assert response.status_code == 200
    assert response.json()["last_referenced_at"] is not None


def test_list_memories_respects_limit(client):
    for i in range(10):
        client.post("/api/memories", json={"content": f"Memory {i}", "type": "fact"})
    response = client.get("/api/memories", params={"limit": 5})
    assert len(response.json()["memories"]) == 5
