import json

import pytest

from bede_data.config import settings


@pytest.fixture
def sessions_dir(tmp_path):
    settings.claude_sessions_dir = str(tmp_path)

    session_dir = tmp_path / "abc-123"
    session_dir.mkdir()
    jsonl_file = session_dir / "session.jsonl"
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

    session_dir2 = tmp_path / "def-456"
    session_dir2.mkdir()
    jsonl_file2 = session_dir2 / "session.jsonl"
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
