import pytest
from unittest.mock import AsyncMock, MagicMock

from bede_core.claude_cli import ClaudeResult


class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakeChat:
    def __init__(self, cid):
        self.id = cid


class FakeMessage:
    def __init__(self, text, user_id=12345, chat_id=12345):
        self.text = text
        self.reply_text = AsyncMock()
        self.from_user = FakeUser(user_id)
        self.chat = FakeChat(chat_id)


class FakeUpdate:
    def __init__(self, text, user_id=12345, chat_id=12345):
        self.message = FakeMessage(text, user_id, chat_id)
        self.effective_user = FakeUser(user_id)
        self.effective_chat = FakeChat(chat_id)


class FakeContext:
    def __init__(self):
        self.bot = AsyncMock()


@pytest.fixture
def session_manager():
    return AsyncMock()


@pytest.fixture
def quiet_hours_check():
    return MagicMock(return_value=False)


class TestBotHandlers:
    async def test_rejects_unauthorized_user(self, session_manager):
        from bede_core.bot import create_message_handler

        handler = create_message_handler(
            session_manager, allowed_user_id=12345, timezone="Australia/Sydney"
        )

        update = FakeUpdate("hello", user_id=99999)
        context = FakeContext()
        await handler(update, context)

        session_manager.send.assert_not_called()
        update.message.reply_text.assert_not_called()

    async def test_handles_normal_message(self, session_manager):
        from bede_core.bot import create_message_handler

        handler = create_message_handler(
            session_manager, allowed_user_id=12345, timezone="Australia/Sydney"
        )

        session_manager.send.return_value = ClaudeResult(
            text="Hi there!", session_id="s1"
        )
        update = FakeUpdate("hello", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        session_manager.send.assert_called_once()
        update.message.reply_text.assert_called()

    async def test_handles_timeout(self, session_manager):
        from bede_core.bot import create_message_handler

        handler = create_message_handler(
            session_manager, allowed_user_id=12345, timezone="Australia/Sydney"
        )

        session_manager.send.return_value = ClaudeResult(timed_out=True)
        update = FakeUpdate("hello", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        calls = [str(c) for c in update.message.reply_text.call_args_list]
        assert any("timed out" in c.lower() for c in calls)

    async def test_handles_auth_failure(self, session_manager):
        from bede_core.bot import create_message_handler

        handler = create_message_handler(
            session_manager, allowed_user_id=12345, timezone="Australia/Sydney"
        )

        session_manager.send.return_value = ClaudeResult(auth_failure=True)
        update = FakeUpdate("hello", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        calls = [str(c) for c in update.message.reply_text.call_args_list]
        assert any("auth" in c.lower() or "expired" in c.lower() for c in calls)


class TestResetHandler:
    async def test_reset_clears_session(self, session_manager):
        from bede_core.bot import create_reset_handler

        handler = create_reset_handler(session_manager, allowed_user_id=12345)

        update = FakeUpdate("/reset", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        session_manager.clear_daily_session.assert_called_once()
        update.message.reply_text.assert_called_once()
        assert "cleared" in update.message.reply_text.call_args.args[0].lower()

    async def test_reset_rejects_unauthorized(self, session_manager):
        from bede_core.bot import create_reset_handler

        handler = create_reset_handler(session_manager, allowed_user_id=12345)

        update = FakeUpdate("/reset", user_id=99999)
        context = FakeContext()
        await handler(update, context)

        session_manager.clear_daily_session.assert_not_called()


class TestInteractiveCorrections:
    async def test_appends_correction_during_interactive(self, session_manager):
        from bede_core.bot import create_message_handler

        session_manager.send.return_value = ClaudeResult(
            text="Noted!", session_id="s1"
        )
        session_manager.is_interactive = True

        correction_calls = []

        def fake_append(text):
            correction_calls.append(text)

        handler = create_message_handler(
            session_manager,
            allowed_user_id=12345,
            timezone="Australia/Sydney",
            append_correction_fn=fake_append,
        )

        update = FakeUpdate("Actually the tone was wrong", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        assert len(correction_calls) == 1
        assert "tone was wrong" in correction_calls[0]

    async def test_no_correction_when_not_interactive(self, session_manager):
        from bede_core.bot import create_message_handler

        session_manager.send.return_value = ClaudeResult(
            text="Hello!", session_id="s1"
        )
        session_manager.is_interactive = False

        correction_calls = []

        def fake_append(text):
            correction_calls.append(text)

        handler = create_message_handler(
            session_manager,
            allowed_user_id=12345,
            timezone="Australia/Sydney",
            append_correction_fn=fake_append,
        )

        update = FakeUpdate("Hello", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        assert len(correction_calls) == 0


class TestResetCancellation:
    async def test_reset_cancels_running_tasks(self, session_manager):
        from bede_core.bot import create_reset_handler

        runner = MagicMock()
        runner.cancel_all.return_value = ["Morning Briefing", "Deal Scout"]

        handler = create_reset_handler(
            session_manager, allowed_user_id=12345, runner=runner
        )

        update = FakeUpdate("/reset", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        runner.cancel_all.assert_called_once()
        session_manager.clear_interactive.assert_called_once()
        reply_text = update.message.reply_text.call_args.args[0]
        assert "Morning Briefing" in reply_text
        assert "Deal Scout" in reply_text

    async def test_reset_no_tasks_running(self, session_manager):
        from bede_core.bot import create_reset_handler

        runner = MagicMock()
        runner.cancel_all.return_value = []

        handler = create_reset_handler(
            session_manager, allowed_user_id=12345, runner=runner
        )

        update = FakeUpdate("/reset", user_id=12345)
        context = FakeContext()
        await handler(update, context)

        reply_text = update.message.reply_text.call_args.args[0]
        assert "cleared" in reply_text.lower()
