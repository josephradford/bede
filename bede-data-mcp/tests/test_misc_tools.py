from bede_data_mcp.server import (
    enqueue_vault_item,
    get_conversation,
    get_data_freshness,
    get_storage,
    get_task_history,
    list_conversations,
)


async def test_get_data_freshness(api):
    api.get.return_value = {
        "sources": [{"source": "health", "last_received_at": "2026-04-30T06:00:00Z"}]
    }
    result = await get_data_freshness()
    api.get.assert_called_once_with("/api/freshness")
    assert len(result["sources"]) == 1


async def test_get_storage(api):
    api.get.return_value = {
        "db_size_bytes": 1048576,
        "tables": [{"name": "health_metrics", "row_count": 500}],
    }
    result = await get_storage()
    api.get.assert_called_once_with("/api/storage")
    assert result["db_size_bytes"] == 1048576


async def test_list_conversations(api):
    api.get.return_value = {"sessions": [{"session_id": "abc123", "message_count": 42}]}
    result = await list_conversations()
    api.get.assert_called_once_with("/api/conversations")
    assert result["sessions"][0]["session_id"] == "abc123"


async def test_get_conversation(api):
    api.get.return_value = {
        "session_id": "abc123",
        "messages": [{"role": "user", "content": "hello"}],
    }
    result = await get_conversation("abc123")
    api.get.assert_called_once_with("/api/conversations/abc123")
    assert len(result["messages"]) == 1


async def test_get_task_history(api):
    api.get.return_value = {
        "executions": [{"task_name": "morning_briefing", "status": "success"}]
    }
    result = await get_task_history()
    api.get.assert_called_once_with("/api/tasks/history")
    assert result["executions"][0]["status"] == "success"


async def test_get_task_history_with_filters(api):
    api.get.return_value = {"executions": []}
    await get_task_history(task_name="morning_briefing", limit=10)
    api.get.assert_called_once_with(
        "/api/tasks/history", task_name="morning_briefing", limit=10
    )


async def test_enqueue_vault_item(api):
    api.post.return_value = {"id": 1, "content_type": "journal", "status": "pending"}
    result = await enqueue_vault_item("journal", "# April 30\n\nGood day.")
    api.post.assert_called_once_with(
        "/api/vault-queue",
        {"content_type": "journal", "content": "# April 30\n\nGood day."},
    )
    assert result["status"] == "pending"


async def test_enqueue_vault_item_with_path(api):
    api.post.return_value = {"id": 2, "vault_path": "Journal/2026-04-30.md"}
    await enqueue_vault_item("journal", "content", vault_path="Journal/2026-04-30.md")
    api.post.assert_called_once_with(
        "/api/vault-queue",
        {
            "content_type": "journal",
            "content": "content",
            "vault_path": "Journal/2026-04-30.md",
        },
    )
