def test_enqueue_journal(client):
    response = client.post(
        "/api/vault-queue",
        json={
            "content_type": "journal",
            "content": "# 2026-04-29\n\nA productive day.",
            "vault_path": "Journal/2026-04-29.md",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["content_type"] == "journal"


def test_list_queue(client):
    client.post("/api/vault-queue", json={"content_type": "journal", "content": "Entry 1", "vault_path": "a.md"})
    client.post("/api/vault-queue", json={"content_type": "capture", "content": "Idea", "vault_path": "b.md"})
    response = client.get("/api/vault-queue")
    assert len(response.json()["items"]) == 2


def test_list_queue_filter_status(client):
    client.post("/api/vault-queue", json={"content_type": "journal", "content": "Entry", "vault_path": "a.md"})
    response = client.get("/api/vault-queue", params={"status": "pending"})
    assert len(response.json()["items"]) == 1


def test_update_queue_item_published(client):
    resp = client.post("/api/vault-queue", json={"content_type": "journal", "content": "Entry", "vault_path": "a.md"})
    item_id = resp.json()["id"]
    response = client.put(
        f"/api/vault-queue/{item_id}",
        json={"status": "published"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["published_at"] is not None


def test_update_queue_item_failed(client):
    resp = client.post("/api/vault-queue", json={"content_type": "journal", "content": "Entry", "vault_path": "a.md"})
    item_id = resp.json()["id"]
    response = client.put(
        f"/api/vault-queue/{item_id}",
        json={"status": "failed", "error_detail": "git push failed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_detail"] == "git push failed"
