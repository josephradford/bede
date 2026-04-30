from bede_data_mcp.server import (
    create_memory,
    delete_memory,
    list_memories,
    reference_memory,
    update_memory,
)


async def test_create_memory(api):
    api.post.return_value = {
        "id": 1,
        "content": "Training for marathon",
        "type": "fact",
        "active": True,
    }
    result = await create_memory("Training for marathon", "fact")
    api.post.assert_called_once_with(
        "/api/memories", {"content": "Training for marathon", "type": "fact"}
    )
    assert result["id"] == 1


async def test_create_memory_with_supersedes(api):
    api.post.return_value = {
        "id": 2,
        "content": "Half-marathon, not full",
        "type": "correction",
        "active": True,
    }
    await create_memory("Half-marathon, not full", "correction", supersedes=1)
    api.post.assert_called_once_with(
        "/api/memories",
        {"content": "Half-marathon, not full", "type": "correction", "supersedes": 1},
    )


async def test_create_memory_with_source(api):
    api.post.return_value = {"id": 3, "content": "Likes camping", "type": "fact"}
    await create_memory("Likes camping", "fact", source_conversation="session-abc")
    api.post.assert_called_once_with(
        "/api/memories",
        {
            "content": "Likes camping",
            "type": "fact",
            "source_conversation": "session-abc",
        },
    )


async def test_list_memories(api):
    api.get.return_value = {"memories": [{"id": 1, "content": "Training for marathon"}]}
    result = await list_memories()
    api.get.assert_called_once_with("/api/memories")
    assert len(result["memories"]) == 1


async def test_list_memories_with_filters(api):
    api.get.return_value = {"memories": []}
    await list_memories(type="fact", search="marathon", limit=10)
    api.get.assert_called_once_with(
        "/api/memories", type="fact", search="marathon", limit=10
    )


async def test_update_memory(api):
    api.put.return_value = {"id": 1, "content": "Updated content", "type": "fact"}
    result = await update_memory(1, content="Updated content")
    api.put.assert_called_once_with("/api/memories/1", {"content": "Updated content"})
    assert result["content"] == "Updated content"


async def test_update_memory_type(api):
    api.put.return_value = {"id": 1, "content": "Same", "type": "preference"}
    await update_memory(1, type="preference")
    api.put.assert_called_once_with("/api/memories/1", {"type": "preference"})


async def test_delete_memory(api):
    api.delete.return_value = {"status": "deleted", "id": 1}
    result = await delete_memory(1)
    api.delete.assert_called_once_with("/api/memories/1")
    assert result["status"] == "deleted"


async def test_reference_memory(api):
    api.post.return_value = {"id": 1, "last_referenced_at": "2026-04-30T10:00:00Z"}
    result = await reference_memory(1)
    api.post.assert_called_once_with("/api/memories/1/reference")
    assert "last_referenced_at" in result
