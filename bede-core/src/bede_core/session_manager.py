import logging
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from bede_core.claude_cli import ClaudeCli, ClaudeResult
from bede_core.data_client import DataClient
from bede_core.memory_manager import MemoryManager

log = logging.getLogger(__name__)


class SessionManager:
    def __init__(
        self,
        data_client: DataClient,
        claude_cli: ClaudeCli,
        memory_manager: MemoryManager,
        timezone: str,
        model: str,
        vault_path: str,
        interactive_idle_timeout: float = 1800,
        interactive_max_age: float = 7200,
    ):
        self._data = data_client
        self._cli = claude_cli
        self._memory = memory_manager
        self._tz = ZoneInfo(timezone)
        self._model = model
        self._vault_path = vault_path
        self._session_cleared = False
        self._idle_timeout = interactive_idle_timeout
        self._max_age = interactive_max_age
        self._interactive: dict | None = None

    def register_interactive(self, model: str):
        now = time.monotonic()
        self._interactive = {"model": model, "idle_ts": now, "created_ts": now}
        log.info("Interactive session registered (model: %s)", model)

    def clear_interactive(self):
        self._interactive = None

    @property
    def is_interactive(self) -> bool:
        return self._get_interactive_model() is not None

    @property
    def interactive_model(self) -> str | None:
        return self._get_interactive_model()

    def _get_interactive_model(self) -> str | None:
        if self._interactive is None:
            return None
        now = time.monotonic()
        idle_ok = (now - self._interactive["idle_ts"]) < self._idle_timeout
        age_ok = (now - self._interactive["created_ts"]) < self._max_age
        if idle_ok and age_ok:
            return self._interactive["model"]
        log.info(
            "Interactive session expired (idle_ok=%s, age_ok=%s).", idle_ok, age_ok
        )
        self._interactive = None
        return None

    def _today(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d")

    def _now_str(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d %H:%M")

    async def _get_daily_session_id(self) -> str | None:
        if self._session_cleared:
            return None
        date = self._today()
        result = await self._data.get("/api/sessions/daily", date=date)
        if "error" in result:
            return None
        return result.get("session_id")

    async def _store_daily_session(self, session_id: str):
        date = self._today()
        await self._data.post(
            "/api/sessions/daily", body={"date": date, "session_id": session_id}
        )
        self._session_cleared = False

    async def _get_scratchpad(self) -> str:
        date = self._today()
        result = await self._data.get("/api/scratchpad", date=date)
        entries = result.get("entries", [])
        if not entries:
            return ""
        lines = [f"[{e['entry_time']}] {e['content']}" for e in entries]
        return "## Earlier today\n\n" + "\n".join(lines)

    async def _append_scratchpad(self, content: str):
        date = self._today()
        entry_time = datetime.now(self._tz).strftime("%H:%M")
        await self._data.post(
            "/api/scratchpad",
            body={
                "date": date,
                "entry_time": entry_time,
                "content": content,
            },
        )

    async def _build_context(self, message: str, is_new_session: bool) -> str:
        parts: list[str] = []

        now = datetime.now(self._tz)
        parts.append(
            f"Current date and time: {now.strftime('%A, %d %B %Y %H:%M')} ({self._tz})"
        )

        memory_context = await self._memory.get_context()
        if memory_context:
            parts.append(memory_context)

        if is_new_session:
            scratchpad = await self._get_scratchpad()
            if scratchpad:
                parts.append(scratchpad)

        parts.append(message)
        return "\n\n".join(parts)

    def _pull_vault(self):
        import os

        if not os.path.isdir(f"{self._vault_path}/.git"):
            return
        try:
            subprocess.run(
                ["git", "-C", self._vault_path, "pull", "--ff-only"],
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            log.warning("Vault pull failed: %s", e)

    async def send(
        self,
        message: str,
        model: str | None = None,
        timeout: int | None = None,
    ) -> ClaudeResult:
        import asyncio

        await asyncio.to_thread(self._pull_vault)

        interactive_model = self._get_interactive_model()
        if interactive_model:
            effective_model = model or interactive_model
        else:
            effective_model = model or self._model

        session_id = await self._get_daily_session_id()
        is_new_session = session_id is None

        if is_new_session:
            prompt = await self._build_context(message, is_new_session=True)
        else:
            prompt = await self._build_context(message, is_new_session=False)

        result = await self._cli.run(
            prompt=prompt,
            model=effective_model,
            session_id=session_id,
            timeout=timeout,
        )

        if result.stale_session and session_id:
            log.warning("Stale session %s, retrying fresh.", session_id)
            prompt = await self._build_context(message, is_new_session=True)
            result = await self._cli.run(
                prompt=prompt,
                model=effective_model,
                session_id=None,
                timeout=timeout,
            )
            result.stale_session = False

        if result.session_id and result.session_id != session_id:
            await self._store_daily_session(result.session_id)

        if result.text and not result.timed_out and not result.auth_failure:
            summary = f"User: {message[:100]}\nBede: {result.text[:200]}"
            await self._append_scratchpad(summary)

        if self._interactive and not result.timed_out and not result.auth_failure:
            self._interactive["idle_ts"] = time.monotonic()

        return result

    async def send_task(
        self,
        prompt: str,
        model: str | None = None,
        timeout: int | None = None,
    ) -> ClaudeResult:
        """Send a scheduled task prompt through the daily session."""
        return await self.send(prompt, model=model, timeout=timeout)

    async def clear_daily_session(self):
        """Clear the daily session so the next message starts fresh."""
        self._session_cleared = True

    async def append_scratchpad_entry(self, content: str):
        """Public method to add a scratchpad entry after a completed interaction."""
        await self._append_scratchpad(content)
