"""Tests for interactive task session features in bot.py and scheduler.py."""

import json
import os
import time

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ALLOWED_USER_ID", "12345")

import pytest


# -- scheduler: _extract_session_id ------------------------------------------

from scheduler import _extract_session_id


def _make_claude_output(result_text="Hello", session_id="sess-abc-123"):
    lines = [
        json.dumps({"type": "assistant", "content": "thinking..."}),
        json.dumps({
            "type": "result",
            "result": result_text,
            "session_id": session_id,
        }),
    ]
    return "\n".join(lines)


def test_extract_session_id_normal():
    stdout = _make_claude_output(session_id="sess-xyz")
    assert _extract_session_id(stdout) == "sess-xyz"


def test_extract_session_id_missing():
    stdout = json.dumps({"type": "result", "result": "hi"})
    assert _extract_session_id(stdout) is None


def test_extract_session_id_empty():
    assert _extract_session_id("") is None


def test_extract_session_id_malformed_json():
    stdout = "not json\n{bad\n"
    assert _extract_session_id(stdout) is None


def test_extract_session_id_multiple_results():
    lines = [
        json.dumps({"type": "result", "result": "first", "session_id": "old"}),
        json.dumps({"type": "result", "result": "second", "session_id": "new"}),
    ]
    stdout = "\n".join(lines)
    assert _extract_session_id(stdout) == "new"


# -- scheduler: _parse_tasks validation --------------------------------------

from scheduler import _parse_tasks


def _write_tasks_file(tmp_path, tasks_yaml):
    md = f"# Tasks\n\n```yaml\n{tasks_yaml}\n```\n"
    tasks_file = tmp_path / "Bede" / "scheduled-tasks.md"
    tasks_file.parent.mkdir(parents=True)
    tasks_file.write_text(md)
    return tasks_file


def test_parse_tasks_rejects_interactive_steps(tmp_path, monkeypatch):
    yaml_content = """\
tasks:
  - name: Bad Task
    schedule: "0 7 * * *"
    interactive: true
    steps:
      - name: Step 1
        prompt: "do something"
    prompt: "ignored"
  - name: Good Task
    schedule: "0 8 * * *"
    interactive: true
    prompt: "this is fine"
"""
    _write_tasks_file(tmp_path, yaml_content)
    monkeypatch.setattr("scheduler.VAULT_PATH", str(tmp_path))
    monkeypatch.setattr("scheduler.TASKS_REL_PATH", "Bede/scheduled-tasks.md")

    tasks = _parse_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Good Task"


def test_parse_tasks_allows_non_interactive_steps(tmp_path, monkeypatch):
    yaml_content = """\
tasks:
  - name: Multi Step
    schedule: "0 7 * * *"
    steps:
      - name: Step 1
        prompt: "do something"
"""
    _write_tasks_file(tmp_path, yaml_content)
    monkeypatch.setattr("scheduler.VAULT_PATH", str(tmp_path))
    monkeypatch.setattr("scheduler.TASKS_REL_PATH", "Bede/scheduled-tasks.md")

    tasks = _parse_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Multi Step"


# -- bot: register + get interactive session ----------------------------------

import bot


def test_register_and_get_interactive_session():
    bot._interactive_session = None
    bot.register_interactive_session("sess-1", "claude-sonnet-4-6")

    now = time.monotonic()
    session = bot._get_interactive_session(now)
    assert session is not None
    assert session["session_id"] == "sess-1"
    assert session["model"] == "claude-sonnet-4-6"

    bot._interactive_session = None


def test_interactive_session_idle_timeout():
    bot._interactive_session = None
    bot.register_interactive_session("sess-1", "claude-sonnet-4-6")

    future = time.monotonic() + bot.INTERACTIVE_IDLE_TIMEOUT_SECS + 1
    session = bot._get_interactive_session(future)
    assert session is None
    assert bot._interactive_session is None


def test_interactive_session_max_age_timeout():
    bot._interactive_session = None
    bot.register_interactive_session("sess-1", "claude-sonnet-4-6")
    bot._interactive_session["ts"] = time.monotonic()

    future = time.monotonic() + bot.INTERACTIVE_MAX_AGE_SECS + 1
    session = bot._get_interactive_session(future)
    assert session is None
    assert bot._interactive_session is None


def test_interactive_session_within_limits():
    bot._interactive_session = None
    bot.register_interactive_session("sess-1", "claude-sonnet-4-6")

    future = time.monotonic() + 60
    session = bot._get_interactive_session(future)
    assert session is not None
    assert session["session_id"] == "sess-1"

    bot._interactive_session = None


def test_get_interactive_session_when_none():
    bot._interactive_session = None
    assert bot._get_interactive_session(time.monotonic()) is None


# -- bot: _append_correction --------------------------------------------------

from bot import _append_correction


def test_append_correction_creates_file(tmp_path, monkeypatch):
    mem_path = str(tmp_path / "Bede" / "reflection-memory.md")
    monkeypatch.setattr("bot.REFLECTION_MEMORY_PATH", mem_path)
    monkeypatch.setattr("bot.VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("TIMEZONE", "UTC")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

    _append_correction("I did go for a run, the GPS was off")

    assert os.path.isfile(mem_path)
    content = open(mem_path).read()
    assert "# Reflection Memory" in content
    assert "## Corrections" in content
    assert "I did go for a run, the GPS was off" in content


def test_append_correction_appends_to_existing(tmp_path, monkeypatch):
    mem_dir = tmp_path / "Bede"
    mem_dir.mkdir()
    mem_path = str(mem_dir / "reflection-memory.md")
    with open(mem_path, "w") as f:
        f.write("# Reflection Memory\n\n## Corrections\n\n- [2026-04-27 20:45] first correction\n")

    monkeypatch.setattr("bot.REFLECTION_MEMORY_PATH", mem_path)
    monkeypatch.setattr("bot.VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("TIMEZONE", "UTC")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

    _append_correction("second correction")

    content = open(mem_path).read()
    assert "first correction" in content
    assert "second correction" in content


def test_append_correction_timestamp_format(tmp_path, monkeypatch):
    mem_dir = tmp_path / "Bede"
    mem_dir.mkdir()
    mem_path = str(mem_dir / "reflection-memory.md")
    with open(mem_path, "w") as f:
        f.write("# Reflection Memory\n\n## Corrections\n\n")

    monkeypatch.setattr("bot.REFLECTION_MEMORY_PATH", mem_path)
    monkeypatch.setattr("bot.VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("TIMEZONE", "UTC")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

    _append_correction("test")

    import re
    content = open(mem_path).read()
    assert re.search(r"- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] test", content)
