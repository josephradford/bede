import asyncio

import pytest
from fastmcp import FastMCP
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelResponse, SystemPromptPart, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from bede_core.agent_runner import AgentRunner
from bede_core.vault_tools import Vault, build_vault_tools


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("hello World\nsecond line\n")
    return Vault(str(root))


@pytest.fixture
def persona(tmp_path):
    path = tmp_path / "CLAUDE.md"
    path.write_text("You are Bede.")
    return str(path)


def make_runner(persona, vault, toolsets=None, **kwargs):
    return AgentRunner(
        persona,
        build_vault_tools(vault),
        toolsets or {},
        retry_delay=0,
        **kwargs,
    )


def text_model(text):
    def fn(messages, info):
        return ModelResponse(parts=[TextPart(text)])

    return FunctionModel(fn)


def failing_model(status, calls=None):
    def fn(messages, info):
        if calls is not None:
            calls.append(status)
        raise ModelHTTPError(status, "m", None)

    return FunctionModel(fn)


async def test_success_uses_persona_as_system_prompt(persona, vault):
    seen = {}

    def fn(messages, info):
        seen["system"] = [
            p.content
            for m in messages
            for p in m.parts
            if isinstance(p, SystemPromptPart)
        ]
        return ModelResponse(parts=[TextPart("done")])

    result = await make_runner(persona, vault).run("hi", FunctionModel(fn))
    assert result.text == "done"
    assert result.steps == 1
    assert not result.timed_out
    assert seen["system"] == ["You are Bede."]


async def test_session_id_is_ignored(persona, vault):
    result = await make_runner(persona, vault).run(
        "hi", text_model("ok"), session_id="old-session"
    )
    assert result.text == "ok"
    assert result.session_id is None


async def test_model_can_call_vault_tools(persona, vault):
    def fn(messages, info):
        if len(messages) == 1:
            return ModelResponse(parts=[ToolCallPart("read_file", {"path": "note.md"})])
        first_line = messages[-1].parts[0].content.splitlines()[0]
        return ModelResponse(parts=[TextPart(f"saw: {first_line}")])

    result = await make_runner(persona, vault).run("go", FunctionModel(fn))
    assert result.text == "saw: hello World"
    assert result.steps == 2


async def test_step_cap_stops_a_looping_model(persona, vault):
    def fn(messages, info):
        return ModelResponse(parts=[ToolCallPart("list_dir", {})])

    result = await make_runner(persona, vault, max_steps=3).run("go", FunctionModel(fn))
    assert result.stop_reason == "max_steps"
    assert "3 steps" in result.text
    assert result.returncode == 1


async def test_timeout_sets_timed_out(persona, vault):
    async def fn(messages, info):
        await asyncio.sleep(1)
        return ModelResponse(parts=[TextPart("late")])

    result = await make_runner(persona, vault).run(
        "go", FunctionModel(fn), timeout=0.05
    )
    assert result.timed_out


@pytest.mark.parametrize("status", [401, 403])
async def test_rejected_key_sets_auth_failure(persona, vault, status):
    calls = []
    result = await make_runner(persona, vault).run("go", failing_model(status, calls))
    assert result.auth_failure
    assert "API key" in result.text
    assert len(calls) == 1


async def test_transient_error_is_retried_once(persona, vault):
    calls = []

    def fn(messages, info):
        calls.append(1)
        if len(calls) == 1:
            raise ModelHTTPError(503, "m", None)
        return ModelResponse(parts=[TextPart("ok")])

    result = await make_runner(persona, vault).run("go", FunctionModel(fn))
    assert result.text == "ok"
    assert len(calls) == 2


async def test_persistent_transient_error_fails_after_one_retry(persona, vault):
    calls = []
    result = await make_runner(persona, vault).run("go", failing_model(503, calls))
    assert "HTTP 503" in result.text
    assert result.returncode == 1
    assert len(calls) == 2


async def test_client_error_is_not_retried(persona, vault):
    calls = []
    result = await make_runner(persona, vault).run("go", failing_model(400, calls))
    assert "HTTP 400" in result.text
    assert len(calls) == 1


async def test_unreachable_mcp_is_reported_not_fatal(persona, vault):
    server = FastMCP("t")

    @server.tool
    def ping() -> str:
        return "pong"

    toolsets = {"good": MCPToolset(server), "bad": MCPToolset("http://127.0.0.1:9/mcp")}
    result = await make_runner(persona, vault, toolsets).run("go", TestModel())
    assert result.tools_unavailable == ["bad"]
    assert result.text.endswith("Unavailable tools this run: bad.")
    assert "pong" in result.text


async def test_concurrent_runs_share_toolsets(persona, vault):
    server = FastMCP("t")

    @server.tool
    def ping() -> str:
        return "pong"

    runner = make_runner(persona, vault, {"good": MCPToolset(server)})
    a, b = await asyncio.gather(
        runner.run("one", TestModel()), runner.run("two", TestModel())
    )
    assert "pong" in a.text
    assert "pong" in b.text


async def test_missing_persona_is_a_failed_result(tmp_path, vault):
    runner = AgentRunner(str(tmp_path / "nope.md"), [], {})
    result = await runner.run("go", TestModel())
    assert result.returncode == 1
    assert "Persona file unreadable" in result.text


async def test_empty_model_output_is_reported(persona, vault):
    result = await make_runner(persona, vault).run("go", text_model(""))
    assert result.returncode == 1
    assert "did not return a usable answer" in result.text


async def test_old_style_model_name_falls_back_to_default_model(persona, vault):
    runner = AgentRunner(
        persona,
        build_vault_tools(vault),
        {},
        retry_delay=0,
        default_model=text_model("from default"),
    )
    result = await runner.run("go", "sonnet")
    assert result.text == "from default"


async def test_provider_error_after_a_tool_ran_is_not_retried(persona, vault):
    calls = []

    def fn(messages, info):
        calls.append(1)
        if len(calls) == 1:
            return ModelResponse(
                parts=[ToolCallPart("write_file", {"path": "a.md", "content": "x"})]
            )
        raise ModelHTTPError(503, "m", None)

    result = await make_runner(persona, vault).run("go", FunctionModel(fn))
    assert "HTTP 503" in result.text
    assert result.returncode == 1
    assert len(calls) == 2


async def test_denies_data_collection_by_default(persona, vault):
    seen = {}

    def fn(messages, info):
        seen["settings"] = info.model_settings
        return ModelResponse(parts=[TextPart("ok")])

    runner = make_runner(persona, vault)
    result = await runner.run("hi", FunctionModel(fn))

    assert result.text == "ok"
    assert seen["settings"]["openrouter_provider"] == {"data_collection": "deny"}


async def test_data_collection_policy_can_be_switched_off(persona, vault):
    seen = {}

    def fn(messages, info):
        seen["settings"] = info.model_settings
        return ModelResponse(parts=[TextPart("ok")])

    runner = make_runner(persona, vault, deny_data_collection=False)
    await runner.run("hi", FunctionModel(fn))

    assert "openrouter_provider" not in (seen["settings"] or {})
