def test_enqueue_message(client):
    response = client.post(
        "/api/message-queue",
        json={"message": "What's the weather?", "source": "telegram"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_list_pending_messages(client):
    client.post("/api/message-queue", json={"message": "Msg 1", "source": "telegram"})
    client.post("/api/message-queue", json={"message": "Msg 2", "source": "scheduler"})
    response = client.get("/api/message-queue", params={"status": "pending"})
    assert len(response.json()["messages"]) == 2


def test_process_message(client):
    resp = client.post(
        "/api/message-queue", json={"message": "Hello", "source": "telegram"}
    )
    msg_id = resp.json()["id"]
    response = client.put(f"/api/message-queue/{msg_id}", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["processed_at"] is not None
