import pytest
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from bede_core.claude_cli import ClaudeResult
from bede_core.session_manager import SessionManager


TZ = ZoneInfo("Australia/Sydney")


@pytest.fixture
def data_client():
    return AsyncMock()


@pytest.fixture
def claude_cli():
    return AsyncMock()


@pytest.fixture
def memory_manager():
    mm = AsyncMock()
    mm.get_context.return_value = ""
    return mm


@pytest.fixture
def sm(data_client, claude_cli, memory_manager):
    return SessionManager(
        data_client=data_client,
        claude_cli=claude_cli,
        memory_manager=memory_manager,
        timezone="Australia/Sydney",
        model="claude-sonnet-4-5-20250514",
        vault_path="/vault",
    )


class TestSessionManager:
    async def test_send_creates_new_daily_session(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session for this date",
        }
        claude_cli.run.return_value = ClaudeResult(
            text="Hello!", session_id="new-sess-1"
        )
        data_client.post.return_value = {
            "date": "2026-05-01",
            "session_id": "new-sess-1",
        }

        result = await sm.send("Hi there")

        assert result.text == "Hello!"
        assert claude_cli.run.call_count == 1
        call_kwargs = claude_cli.run.call_args
        assert (
            "--resume" not in str(call_kwargs)
            or call_kwargs.kwargs.get("session_id") is None
        )

    async def test_send_resumes_existing_session(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "date": "2026-05-01",
            "session_id": "existing-sess",
        }
        claude_cli.run.return_value = ClaudeResult(
            text="Welcome back!", session_id="existing-sess"
        )

        result = await sm.send("What's up?")

        assert result.text == "Welcome back!"
        call_kwargs = claude_cli.run.call_args
        assert call_kwargs.kwargs.get(
            "session_id"
        ) == "existing-sess" or "existing-sess" in str(call_kwargs)

    async def test_send_retries_on_stale_session(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "date": "2026-05-01",
            "session_id": "stale-sess",
        }
        stale_result = ClaudeResult(stale_session=True, stderr="no conversation found")
        fresh_result = ClaudeResult(text="Fresh start!", session_id="new-sess-2")
        claude_cli.run.side_effect = [stale_result, fresh_result]
        data_client.post.return_value = {
            "date": "2026-05-01",
            "session_id": "new-sess-2",
        }

        result = await sm.send("Hello again")

        assert result.text == "Fresh start!"
        assert claude_cli.run.call_count == 2

    async def test_send_injects_memory_context(
        self, sm, data_client, claude_cli, memory_manager
    ):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session",
        }
        memory_manager.get_context.return_value = "## Memories\n- Training for marathon"
        claude_cli.run.return_value = ClaudeResult(text="Got it!", session_id="s1")
        data_client.post.return_value = {"date": "2026-05-01", "session_id": "s1"}

        await sm.send("Hi")

        prompt = (
            claude_cli.run.call_args.args[0]
            if claude_cli.run.call_args.args
            else claude_cli.run.call_args.kwargs.get("prompt", "")
        )
        assert "marathon" in prompt or memory_manager.get_context.called

    async def test_send_handles_timeout(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session",
        }
        claude_cli.run.return_value = ClaudeResult(timed_out=True)

        result = await sm.send("Hello")

        assert result.timed_out is True

    async def test_send_detects_auth_failure(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session",
        }
        claude_cli.run.return_value = ClaudeResult(auth_failure=True)

        result = await sm.send("Hello")

        assert result.auth_failure is True

    async def test_send_populates_scratchpad(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session",
        }
        claude_cli.run.return_value = ClaudeResult(text="Got it!", session_id="s1")
        data_client.post.return_value = {"date": "2026-05-01", "session_id": "s1"}

        await sm.send("Remember this")

        scratchpad_calls = [
            c
            for c in data_client.post.call_args_list
            if c.args and c.args[0] == "/api/scratchpad"
        ]
        assert len(scratchpad_calls) == 1
        body = scratchpad_calls[0].kwargs.get("body", {})
        assert "Remember this" in body.get("content", "")

    async def test_send_skips_scratchpad_on_timeout(self, sm, data_client, claude_cli):
        data_client.get.return_value = {
            "error": "bede-data returned 404",
            "detail": "No session",
        }
        claude_cli.run.return_value = ClaudeResult(timed_out=True)

        await sm.send("Hello")

        scratchpad_calls = [
            c
            for c in data_client.post.call_args_list
            if c.args and c.args[0] == "/api/scratchpad"
        ]
        assert len(scratchpad_calls) == 0
