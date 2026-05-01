import logging

from bede_core.data_client import DataClient

log = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, data_client: DataClient, max_context_chars: int = 2000):
        self._client = data_client
        self._max_chars = max_context_chars

    async def get_context(self) -> str:
        result = await self._client.get("/api/memories", limit=50)
        if "error" in result:
            log.warning("Failed to fetch memories: %s", result["error"])
            return ""
        memories = result.get("memories", [])
        if not memories:
            return ""

        lines: list[str] = []
        total = 0
        for m in memories:
            line = f"- [{m['type']}] {m['content']}"
            if total + len(line) > self._max_chars:
                break
            lines.append(line)
            total += len(line)

        if not lines:
            return ""
        return "## Your memories about the user\n\n" + "\n".join(lines)

    async def store(
        self,
        content: str,
        type: str,
        source_conversation: str | None = None,
        supersedes: int | None = None,
    ) -> dict:
        body: dict = {"content": content, "type": type}
        if source_conversation:
            body["source_conversation"] = source_conversation
        if supersedes is not None:
            body["supersedes"] = supersedes
        return await self._client.post("/api/memories", body=body)
