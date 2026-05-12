import json

import pytest

from bede_data.config import settings


@pytest.fixture
def sessions_dir(tmp_path):
    settings.claude_sessions_dir = str(tmp_path)

    jsonl_file = tmp_path / "abc-123.jsonl"
    lines = [
        json.dumps(
            {
                "type": "human",
                "message": "Hello Bede",
                "timestamp": "2026-04-29T08:00:00Z",
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": "Good morning!",
                "timestamp": "2026-04-29T08:00:05Z",
            }
        ),
    ]
    jsonl_file.write_text("\n".join(lines))

    jsonl_file2 = tmp_path / "def-456.jsonl"
    lines2 = [
        json.dumps(
            {
                "type": "human",
                "message": "What's the weather?",
                "timestamp": "2026-04-29T14:00:00Z",
            }
        ),
    ]
    jsonl_file2.write_text("\n".join(lines2))

    return tmp_path


def test_list_conversations(client, sessions_dir):
    response = client.get("/api/conversations")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2


def test_list_conversations_has_metadata(client, sessions_dir):
    response = client.get("/api/conversations")
    sessions = response.json()["sessions"]
    abc = next(s for s in sessions if s["session_id"] == "abc-123")
    assert abc["message_count"] == 2
    assert abc["first_timestamp"] == "2026-04-29T08:00:00Z"


def test_get_conversation(client, sessions_dir):
    response = client.get("/api/conversations/abc-123")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "abc-123"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["message"] == "Hello Bede"


def test_get_conversation_not_found(client, sessions_dir):
    response = client.get("/api/conversations/nonexistent")
    assert response.status_code == 404


def test_list_conversations_empty_dir(client, tmp_path):
    settings.claude_sessions_dir = str(tmp_path)
    response = client.get("/api/conversations")
    assert response.json()["sessions"] == []


def test_list_conversations_ignores_non_jsonl_files(client, sessions_dir):
    (sessions_dir / "README.md").write_text("not a session")
    response = client.get("/api/conversations")
    assert len(response.json()["sessions"]) == 2
