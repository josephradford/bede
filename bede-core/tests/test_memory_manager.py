import pytest
from unittest.mock import AsyncMock

from bede_core.memory_manager import MemoryManager


@pytest.fixture
def data_client():
    return AsyncMock()


@pytest.fixture
def mm(data_client):
    return MemoryManager(data_client, max_context_chars=500)


class TestMemoryManager:
    async def test_get_context_returns_formatted_memories(self, mm, data_client):
        data_client.get.return_value = {
            "memories": [
                {"id": 1, "content": "Training for a half marathon", "type": "fact"},
                {"id": 2, "content": "Don't nag about meditation", "type": "preference"},
            ]
        }
        context = await mm.get_context()
        assert "half marathon" in context
        assert "meditation" in context
        assert "fact" in context.lower() or "preference" in context.lower()

    async def test_get_context_respects_budget(self, data_client):
        data_client.get.return_value = {
            "memories": [
                {"id": i, "content": f"Memory content number {i} " * 10, "type": "fact"}
                for i in range(20)
            ]
        }
        mm = MemoryManager(data_client, max_context_chars=200)
        context = await mm.get_context()
        assert len(context) <= 250  # some buffer for formatting

    async def test_get_context_empty(self, mm, data_client):
        data_client.get.return_value = {"memories": []}
        context = await mm.get_context()
        assert context == ""

    async def test_get_context_handles_error(self, mm, data_client):
        data_client.get.return_value = {"error": "bede-data unavailable"}
        context = await mm.get_context()
        assert context == ""

    async def test_propose_memory(self, mm, data_client):
        data_client.post.return_value = {"id": 5, "content": "Likes camping", "type": "fact"}
        result = await mm.store("Likes camping", "fact", source_conversation="sess-1")
        data_client.post.assert_called_once_with(
            "/api/memories",
            body={"content": "Likes camping", "type": "fact", "source_conversation": "sess-1"},
        )
        assert result["id"] == 5
