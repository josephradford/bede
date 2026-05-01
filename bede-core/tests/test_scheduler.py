import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
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
    sm.send_task.return_value = ClaudeResult(text="Task done!", session_id="task-sess-1")
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
                {"id": 1, "task_name": "Morning Briefing", "cron_expression": "0 8 * * 1-5",
                 "prompt": "Give me a briefing", "model": None, "timeout_seconds": 300,
                 "interactive": False, "enabled": True},
                {"id": 2, "task_name": "Disabled Task", "cron_expression": "0 9 * * *",
                 "prompt": "test", "model": None, "timeout_seconds": 300,
                 "interactive": False, "enabled": False},
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
    async def test_run_task_success(self, runner, data_client, session_manager, send_fn):
        task = {
            "id": 1,
            "task_name": "Morning Briefing",
            "cron_expression": "0 8 * * 1-5",
            "prompt": "Give me a morning briefing",
            "model": None,
            "timeout_seconds": 300,
            "interactive": False,
        }
        data_client.post.return_value = {"id": 1, "task_name": "Morning Briefing", "status": "running"}
        data_client.put.return_value = {"id": 1, "status": "success"}

        await runner.run_task(task)

        session_manager.send_task.assert_called_once()
        assert send_fn.call_count >= 1
        # Task log should be created and updated
        assert data_client.post.call_count >= 1
        assert data_client.put.call_count >= 1

    async def test_run_task_timeout(self, runner, data_client, session_manager, send_fn):
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
        assert "timed out" in last_call_text.lower() or "timeout" in last_call_text.lower()

    async def test_run_task_prevents_duplicate(self, runner, data_client, session_manager, send_fn):
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
