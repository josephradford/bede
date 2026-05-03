import json

import pytest
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from bede_core.claude_cli import ClaudeResult
from bede_core.scheduler import TaskRunner, load_schedules


TZ = ZoneInfo("Australia/Sydney")


@pytest.fixture
def data_client():
    return AsyncMock()


@pytest.fixture
def session_manager():
    sm = AsyncMock()
    sm.send_task.return_value = ClaudeResult(
        text="Task done!", session_id="task-sess-1"
    )
    return sm


@pytest.fixture
def send_fn():
    return AsyncMock()


@pytest.fixture
def runner(data_client, session_manager, send_fn):
    return TaskRunner(
        data_client=data_client,
        session_manager=session_manager,
        send_fn=send_fn,
        timezone="Australia/Sydney",
        quiet_hours_start=0,
        quiet_hours_end=0,
    )


class TestLoadSchedules:
    async def test_loads_enabled_schedules(self, data_client):
        data_client.get.return_value = {
            "schedules": [
                {
                    "id": 1,
                    "task_name": "Morning Briefing",
                    "cron_expression": "0 8 * * 1-5",
                    "prompt": "Give me a briefing",
                    "model": None,
                    "timeout_seconds": 300,
                    "interactive": False,
                    "enabled": True,
                },
                {
                    "id": 2,
                    "task_name": "Disabled Task",
                    "cron_expression": "0 9 * * *",
                    "prompt": "test",
                    "model": None,
                    "timeout_seconds": 300,
                    "interactive": False,
                    "enabled": False,
                },
            ]
        }
        schedules = await load_schedules(data_client)
        assert len(schedules) == 1
        assert schedules[0]["task_name"] == "Morning Briefing"

    async def test_handles_api_error(self, data_client):
        data_client.get.return_value = {"error": "bede-data unavailable"}
        schedules = await load_schedules(data_client)
        assert schedules == []


class TestTaskRunner:
    async def test_run_task_success(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "id": 1,
            "task_name": "Morning Briefing",
            "cron_expression": "0 8 * * 1-5",
            "prompt": "Give me a morning briefing",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        data_client.post.return_value = {
            "id": 1,
            "task_name": "Morning Briefing",
            "status": "running",
        }
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        session_manager.send_task.assert_called_once()
        assert send_fn.call_count >= 1
        # Task log should be created and updated
        assert data_client.post.call_count >= 1
        assert data_client.put.call_count >= 1

    async def test_run_task_timeout(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "id": 1,
            "task_name": "Slow Task",
            "cron_expression": "0 8 * * *",
            "prompt": "Do something slow",
            "model": None,
            "timeout_seconds": 60,
            "interactive": False,
        }
        session_manager.send_task.return_value = ClaudeResult(timed_out=True)
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "timeout"}

        await runner.run_task(task)

        send_fn.assert_called()
        last_call_text = send_fn.call_args.args[0] if send_fn.call_args.args else ""
        assert (
            "timed out" in last_call_text.lower() or "timeout" in last_call_text.lower()
        )

    async def test_run_task_prevents_duplicate(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "id": 1,
            "task_name": "Morning Briefing",
            "cron_expression": "0 8 * * *",
            "prompt": "test",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        runner._running.add("Morning Briefing")

        await runner.run_task(task)

        session_manager.send_task.assert_not_called()


class TestInteractiveHandoff:
    async def test_interactive_task_registers_session(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "task_name": "Evening Reflection",
            "cron_expression": "0 21 * * *",
            "prompt": "Write the evening reflection",
            "model": "claude-sonnet-4-5-20250514",
            "timeout_seconds": 300,
            "interactive": True,
        }
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        session_manager.register_interactive.assert_called_once_with(
            "claude-sonnet-4-5-20250514"
        )

    async def test_non_interactive_task_does_not_register(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "task_name": "Morning Briefing",
            "cron_expression": "0 8 * * 1-5",
            "prompt": "Give me a briefing",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        session_manager.register_interactive.assert_not_called()

    async def test_interactive_not_registered_on_timeout(
        self, runner, data_client, session_manager, send_fn
    ):
        task = {
            "task_name": "Evening Reflection",
            "cron_expression": "0 21 * * *",
            "prompt": "Write the evening reflection",
            "model": "claude-sonnet-4-5-20250514",
            "timeout_seconds": 60,
            "interactive": True,
        }
        session_manager.send_task.return_value = ClaudeResult(timed_out=True)
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "timeout"}

        await runner.run_task(task)

        session_manager.register_interactive.assert_not_called()


class TestCancelTasks:
    def test_cancel_all_returns_running_names(self, runner):
        runner._running.add("Morning Briefing")
        runner._running.add("Deal Scout")

        cancelled = runner.cancel_all()

        assert set(cancelled) == {"Morning Briefing", "Deal Scout"}
        assert len(runner._running) == 0

    def test_cancel_all_empty_when_nothing_running(self, runner):
        cancelled = runner.cancel_all()
        assert cancelled == []


class TestTypingIndicator:
    async def test_typing_called_during_task(
        self, data_client, session_manager, send_fn
    ):
        typing_fn = AsyncMock()
        runner = TaskRunner(
            data_client=data_client,
            session_manager=session_manager,
            send_fn=send_fn,
            timezone="Australia/Sydney",
            quiet_hours_start=0,
            quiet_hours_end=0,
            typing_fn=typing_fn,
        )
        task = {
            "task_name": "Test Task",
            "cron_expression": "0 8 * * *",
            "prompt": "Do something",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        typing_fn.assert_called()


class TestMultiStepTasks:
    def _make_task(self, steps, parallel=False, preamble="Context for all steps"):
        config = {"steps": steps}
        if parallel:
            config["parallel"] = True
        return {
            "task_name": "Multi Step",
            "cron_expression": "0 14 * * 0",
            "prompt": preamble,
            "model": "claude-sonnet-4-5-20250514",
            "timeout_seconds": 600,
            "interactive": False,
            "task_config": json.dumps(config),
        }

    async def test_sequential_steps(self, data_client, session_manager, send_fn):
        runner = TaskRunner(
            data_client=data_client,
            session_manager=session_manager,
            send_fn=send_fn,
            timezone="Australia/Sydney",
            quiet_hours_start=0,
            quiet_hours_end=0,
        )
        session_manager.send_task.side_effect = [
            ClaudeResult(text="Step 1 result", session_id="s1"),
            ClaudeResult(text="Step 2 result", session_id="s2"),
        ]
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        task = self._make_task(
            [
                {"name": "Step 1", "prompt": "Do step 1"},
                {"name": "Step 2", "prompt": "Do step 2"},
            ]
        )

        await runner.run_task(task)

        assert session_manager.send_task.call_count == 2
        calls = [
            c.kwargs.get("prompt", c.args[0] if c.args else "")
            for c in session_manager.send_task.call_args_list
        ]
        assert any("step 1" in c.lower() for c in calls)
        assert any("step 2" in c.lower() for c in calls)

    async def test_parallel_steps(self, data_client, session_manager, send_fn):
        runner = TaskRunner(
            data_client=data_client,
            session_manager=session_manager,
            send_fn=send_fn,
            timezone="Australia/Sydney",
            quiet_hours_start=0,
            quiet_hours_end=0,
        )
        session_manager.send_task.return_value = ClaudeResult(
            text="Result", session_id="s1"
        )
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        task = self._make_task(
            [
                {"name": "Cat 1", "prompt": "Check cat 1"},
                {"name": "Cat 2", "prompt": "Check cat 2"},
            ],
            parallel=True,
        )

        await runner.run_task(task)

        assert session_manager.send_task.call_count == 2

    async def test_silent_step_not_sent_to_telegram(
        self, data_client, session_manager, send_fn
    ):
        runner = TaskRunner(
            data_client=data_client,
            session_manager=session_manager,
            send_fn=send_fn,
            timezone="Australia/Sydney",
            quiet_hours_start=0,
            quiet_hours_end=0,
        )
        session_manager.send_task.side_effect = [
            ClaudeResult(text="Visible result", session_id="s1"),
            ClaudeResult(text="Silent result", session_id="s2"),
        ]
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        task = self._make_task(
            [
                {"name": "Visible", "prompt": "Show this"},
                {"name": "Silent", "prompt": "Hide this", "silent": True},
            ]
        )

        await runner.run_task(task)

        sent_texts = " ".join(str(c) for c in send_fn.call_args_list)
        assert "Visible result" in sent_texts
        assert "Silent result" not in sent_texts

    async def test_preamble_injected_into_steps(
        self, data_client, session_manager, send_fn
    ):
        runner = TaskRunner(
            data_client=data_client,
            session_manager=session_manager,
            send_fn=send_fn,
            timezone="Australia/Sydney",
            quiet_hours_start=0,
            quiet_hours_end=0,
        )
        session_manager.send_task.return_value = ClaudeResult(
            text="Done", session_id="s1"
        )
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        task = self._make_task(
            [{"name": "S1", "prompt": "Do the thing"}],
            preamble="You are a deal scout",
        )

        await runner.run_task(task)

        prompt = session_manager.send_task.call_args.kwargs.get(
            "prompt", session_manager.send_task.call_args.args[0]
        )
        assert "deal scout" in prompt.lower()

    async def test_no_task_config_runs_single_step(
        self, runner, data_client, session_manager, send_fn
    ):
        """Tasks without task_config still work as single-step (backward compat)."""
        task = {
            "task_name": "Simple Task",
            "cron_expression": "0 8 * * *",
            "prompt": "Do something",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        data_client.post.return_value = {"id": 1, "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        session_manager.send_task.assert_called_once()
