# Model-agnostic agent runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `bede-core`'s `claude -p` subprocess with an in-process Pydantic AI agent loop that calls a paid model API, so there is no login to expire and changing model is one env var.

**Architecture:** A new `AgentRunner` has the same `run(prompt, model, session_id, timeout)` call shape as the old `ClaudeCli` and returns an `AgentResult` (the old result shape). It gives the model confined vault file tools plus the existing HTTP MCP servers. Scheduler, bot, `SessionManager` and `bede-data` plumbing stay; only the runner is swapped.

**Tech Stack:** Python 3.12+, `pydantic-ai-slim[openai,mcp]` (verified against 2.71.0, "V2" API), `fastmcp` (dev only, for in-process MCP test servers), pytest + pytest-asyncio, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-11-22-model-agnostic-runtime-design.md`

## Global Constraints

- Scheduled jobs only. No chat-session history, truncation or summarisation.
- No delete capability anywhere in the vault tools. All paths confined to the vault root (symlinks resolved, `.git` blocked).
- Changing model must be a config edit only: the `MODEL` env var, a Pydantic AI model string `provider:name` (e.g. `openrouter:<vendor>/<model>`). No default model is baked in.
- `max_agent_steps` default is 15; agent timeout default 300 s.
- Unit tests make no network calls (use `FunctionModel`, `TestModel`, in-process FastMCP, local sockets).
- Keep `bede-data` and `DataClient` plumbing untouched. `bede-core` still requires `bede-data` at runtime (spec item 2).
- Pydantic AI **V2** API: `MCPToolset` (not `MCPServerStreamableHTTP`), `run.usage` is a property, `run.response.finish_reason`.
- Ruff line length 88. Run `uv run ruff format src tests && uv run ruff check src tests` before each commit.
- Work in `bede-core/`; run tests with `cd bede-core && uv run pytest tests/ -v`.

## Review Focus

Failure modes the spec implies but a casual reading would miss; each has a test in the task that owns the code.

1. Symlink inside the vault pointing outside it must not be readable (Task 1).
2. `write_file` onto a path whose parent is a file (an `OSError`) must come back as error text, not crash the run (Task 1).
3. Huge or non-UTF-8 files must not blow up the context or the read (Task 1).
4. An MCP server that accepts the connection but never answers must be treated as unavailable within the probe timeout, not hang the run (Task 2).
5. Two scheduled tasks running at once share the same MCP toolsets and must both work (Task 3).
6. Missing persona file and a model that returns empty output must give a clear failed result, not a stack trace (Task 3).

## File Structure

| File | Responsibility |
|------|----------------|
| `bede-core/src/bede_core/vault_tools.py` (new) | `Vault` (confined file ops, git commit/push) and `build_vault_tools()` (agent-facing functions) |
| `bede-core/src/bede_core/mcp_toolsets.py` (new) | Read `mcp.json`, build `MCPToolset`s, probe which are reachable |
| `bede-core/src/bede_core/agent_runner.py` (new) | `AgentResult` and `AgentRunner` (agent loop, limits, retries, error mapping) |
| `bede-core/src/bede_core/config.py` | New settings and `check_model_config()` |
| `bede-core/src/bede_core/main.py`, `session_manager.py`, `bot.py` | Wire in the runner, rename types, key-rejected notice |
| `bede-core/src/bede_core/claude_cli.py` | Deleted |
| `bede-core/evals/` (new) | Fixture vault, eval prompts, runner script |
| `bede-core/Dockerfile`, `mcp.json`, `pyproject.toml`, `../Makefile`, `../README.md`, `../ARCHITECTURE.md` | Cleanup and docs |

---

### Task 1: Vault tools

**Files:**
- Create: `bede-core/src/bede_core/vault_tools.py`
- Test: `bede-core/tests/test_vault_tools.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `class Vault(root: str)` with `list_dir(rel=".") -> list[str]`, `read_file(rel) -> str`, `write_file(rel, content) -> str`, `search(query, rel=".") -> list[str]`, `commit_and_push(message) -> str`; `class VaultError(Exception)`; `build_vault_tools(vault: Vault) -> list[Callable]` returning functions named `list_dir`, `read_file`, `write_file`, `search`, `commit_and_push` that return strings and never raise `VaultError`/`OSError`.

- [ ] **Step 1: Write the failing tests**

```python
# bede-core/tests/test_vault_tools.py
import subprocess

import pytest

from bede_core.vault_tools import Vault, VaultError, build_vault_tools


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("hello World\nsecond line\n")
    return Vault(str(root))


def tools(vault):
    return {f.__name__: f for f in build_vault_tools(vault)}


@pytest.mark.parametrize("bad", ["../x", "/etc/passwd", ".git/config"])
def test_escape_and_git_blocked(vault, bad):
    with pytest.raises(VaultError):
        vault.read_file(bad)


def test_symlink_escape_blocked(vault, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    (tmp_path / "vault" / "link.md").symlink_to(outside)
    with pytest.raises(VaultError):
        vault.read_file("link.md")


def test_list_and_search(vault):
    assert vault.list_dir() == ["note.md"]
    assert vault.search("WORLD") == ["note.md:1: hello World"]


def test_write_creates_parents(vault):
    vault.write_file("Journal/2026-01-01.md", "hi")
    assert vault.read_file("Journal/2026-01-01.md") == "hi"


def test_write_under_a_file_returns_error_text(vault):
    assert tools(vault)["write_file"]("note.md/child.md", "x").startswith("Error:")


def test_tool_errors_are_text_not_exceptions(vault):
    assert tools(vault)["read_file"]("../x").startswith("Error:")


def test_read_truncates_and_tolerates_binary(vault, tmp_path):
    (tmp_path / "vault" / "big.md").write_text("a" * 30000)
    (tmp_path / "vault" / "bin.md").write_bytes(b"\xff\xfe\x00bad")
    assert "[truncated at 20000 chars]" in vault.read_file("big.md")
    assert vault.read_file("bin.md")


def test_no_delete_tool(vault):
    assert set(tools(vault)) == {
        "list_dir",
        "read_file",
        "write_file",
        "search",
        "commit_and_push",
    }


def test_commit_and_push(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True)
    for key, value in [("user.email", "t@example.com"), ("user.name", "t")]:
        subprocess.run(["git", "-C", str(work), "config", key, value], check=True)
    v = Vault(str(work))
    assert v.commit_and_push("nothing") == "Nothing to commit"
    v.write_file("a/b.md", "hi")
    assert "Committed" in v.commit_and_push("add b")
    log = subprocess.run(
        ["git", "-C", str(remote), "log", "--oneline"], capture_output=True, text=True
    )
    assert "add b" in log.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd bede-core && uv run pytest tests/test_vault_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bede_core.vault_tools'`

- [ ] **Step 3: Write the implementation**

```python
# bede-core/src/bede_core/vault_tools.py
import subprocess
from collections.abc import Callable
from pathlib import Path

MAX_READ_CHARS = 20000
MAX_SEARCH_RESULTS = 50


class VaultError(Exception):
    pass


class Vault:
    """File access confined to a vault directory. There is no delete operation."""

    def __init__(self, root: str):
        self._root = Path(root).resolve()

    def _resolve(self, rel: str) -> Path:
        path = (self._root / rel).resolve()
        if path != self._root and self._root not in path.parents:
            raise VaultError(f"Path escapes the vault: {rel}")
        if ".git" in path.relative_to(self._root).parts:
            raise VaultError("Access to .git is not allowed")
        return path

    def list_dir(self, rel: str = ".") -> list[str]:
        path = self._resolve(rel)
        if not path.is_dir():
            raise VaultError(f"Not a directory: {rel}")
        return [
            p.name + ("/" if p.is_dir() else "")
            for p in sorted(path.iterdir())
            if p.name != ".git"
        ]

    def read_file(self, rel: str) -> str:
        path = self._resolve(rel)
        if not path.is_file():
            raise VaultError(f"Not a file: {rel}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_READ_CHARS:
            return text[:MAX_READ_CHARS] + f"\n[truncated at {MAX_READ_CHARS} chars]"
        return text

    def write_file(self, rel: str, content: str) -> str:
        path = self._resolve(rel)
        if path == self._root or path.is_dir():
            raise VaultError(f"Not a file path: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {rel}"

    def search(self, query: str, rel: str = ".") -> list[str]:
        base = self._resolve(rel)
        needle = query.lower()
        hits: list[str] = []
        for path in sorted(base.rglob("*.md")):
            if ".git" in path.relative_to(self._root).parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                if needle in line.lower():
                    where = path.relative_to(self._root)
                    hits.append(f"{where}:{number}: {line.strip()}")
                    if len(hits) >= MAX_SEARCH_RESULTS:
                        return hits
        return hits

    def commit_and_push(self, message: str) -> str:
        def git(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                ["git", "-C", str(self._root), *args],
                capture_output=True,
                text=True,
                timeout=60,
            )

        git("add", "-A")
        if not git("status", "--porcelain").stdout.strip():
            return "Nothing to commit"
        commit = git("commit", "-m", message)
        if commit.returncode != 0:
            raise VaultError(f"git commit failed: {commit.stderr.strip()}")
        push = git("push")
        if push.returncode != 0:
            raise VaultError(f"git push failed: {push.stderr.strip()}")
        return f"Committed and pushed: {message}"


def build_vault_tools(vault: Vault) -> list[Callable]:
    """Plain functions for the agent. Errors come back as text so the model can recover."""

    def guarded(fn: Callable[[], str]) -> str:
        try:
            return fn()
        except (VaultError, OSError) as e:
            return f"Error: {e}"

    def list_dir(path: str = ".") -> str:
        """List files and folders in a vault directory (folders end with /)."""
        return guarded(lambda: "\n".join(vault.list_dir(path)) or "(empty)")

    def read_file(path: str) -> str:
        """Read a text file from the vault."""
        return guarded(lambda: vault.read_file(path))

    def write_file(path: str, content: str) -> str:
        """Create or overwrite a text file in the vault. Parent folders are created."""
        return guarded(lambda: vault.write_file(path, content))

    def search(query: str, path: str = ".") -> str:
        """Case-insensitive text search over markdown files. Returns file:line: text."""
        return guarded(lambda: "\n".join(vault.search(query, path)) or "No matches")

    def commit_and_push(message: str) -> str:
        """Commit all vault changes with the given message and push them."""
        return guarded(lambda: vault.commit_and_push(message))

    return [list_dir, read_file, write_file, search, commit_and_push]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd bede-core && uv run pytest tests/test_vault_tools.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Format, lint, commit**

```bash
cd bede-core && uv run ruff format src tests && uv run ruff check src tests
git add src/bede_core/vault_tools.py tests/test_vault_tools.py
git commit -m "feat(bede-core): add confined vault tools for the agent runner"
```

---

### Task 2: MCP toolsets and dependencies

**Files:**
- Modify: `bede-core/pyproject.toml`
- Create: `bede-core/src/bede_core/mcp_toolsets.py`
- Test: `bede-core/tests/test_mcp_toolsets.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `load_mcp_urls(path: str) -> dict[str, str]`; `build_toolsets(urls: dict[str, str]) -> dict[str, MCPToolset]`; `async connect_available(toolsets: dict[str, MCPToolset], timeout: float = 5.0) -> tuple[list[MCPToolset], list[str]]` (reachable toolsets, names of unreachable ones).

- [ ] **Step 1: Add dependencies**

In `bede-core/pyproject.toml`, add to `dependencies`:

```toml
    "pydantic-ai-slim[openai,mcp]>=2.71,<3",
```

and to the `dev` extras:

```toml
    "fastmcp>=2.0",
```

Run: `cd bede-core && uv sync --extra dev`
Expected: resolves and installs without error.

- [ ] **Step 2: Write the failing tests**

```python
# bede-core/tests/test_mcp_toolsets.py
import asyncio

from fastmcp import FastMCP
from pydantic_ai.mcp import MCPToolset

from bede_core.mcp_toolsets import build_toolsets, connect_available, load_mcp_urls


def test_load_mcp_urls_keeps_only_http_servers(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(
        '{"mcpServers": {"a": {"type": "http", "url": "http://a/mcp"},'
        ' "b": {"type": "stdio"}}}'
    )
    assert load_mcp_urls(str(path)) == {"a": "http://a/mcp"}


def test_build_toolsets_one_per_server():
    toolsets = build_toolsets({"a": "http://a/mcp"})
    assert list(toolsets) == ["a"]


async def test_reachable_and_unreachable_are_separated():
    server = FastMCP("t")

    @server.tool
    def ping() -> str:
        return "pong"

    good = MCPToolset(server)
    bad = MCPToolset("http://127.0.0.1:9/mcp")
    reachable, missing = await connect_available({"good": good, "bad": bad})
    assert reachable == [good]
    assert missing == ["bad"]


async def test_hung_server_is_unavailable_within_timeout():
    async def silent(reader, writer):
        await asyncio.sleep(5)

    server = await asyncio.start_server(silent, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reachable, missing = await connect_available(
            {"hung": MCPToolset(f"http://127.0.0.1:{port}/mcp")}, timeout=0.3
        )
    finally:
        server.close()
    assert reachable == []
    assert missing == ["hung"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd bede-core && uv run pytest tests/test_mcp_toolsets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bede_core.mcp_toolsets'`

- [ ] **Step 4: Write the implementation**

```python
# bede-core/src/bede_core/mcp_toolsets.py
import asyncio
import json
import logging

from pydantic_ai.mcp import MCPToolset

log = logging.getLogger(__name__)


def load_mcp_urls(path: str) -> dict[str, str]:
    """Read HTTP MCP server URLs from an mcp.json file, keyed by server name."""
    with open(path) as f:
        data = json.load(f)
    return {
        name: cfg["url"]
        for name, cfg in data.get("mcpServers", {}).items()
        if cfg.get("type") == "http" and cfg.get("url")
    }


def build_toolsets(urls: dict[str, str]) -> dict[str, MCPToolset]:
    return {name: MCPToolset(url) for name, url in urls.items()}


async def connect_available(
    toolsets: dict[str, MCPToolset], timeout: float = 5.0
) -> tuple[list[MCPToolset], list[str]]:
    """Return (reachable toolsets, names of unreachable ones)."""
    reachable: list[MCPToolset] = []
    missing: list[str] = []
    for name, toolset in toolsets.items():
        try:
            async with asyncio.timeout(timeout):
                async with toolset:
                    pass
            reachable.append(toolset)
        except Exception as e:
            log.warning("MCP server %s unavailable: %s", name, e)
            missing.append(name)
    return reachable, missing
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd bede-core && uv run pytest tests/test_mcp_toolsets.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Format, lint, commit**

```bash
cd bede-core && uv run ruff format src tests && uv run ruff check src tests
git add pyproject.toml uv.lock src/bede_core/mcp_toolsets.py tests/test_mcp_toolsets.py
git commit -m "feat(bede-core): add MCP toolset loading and reachability probe"
```

---

### Task 3: Agent runner

**Files:**
- Create: `bede-core/src/bede_core/agent_runner.py`
- Test: `bede-core/tests/test_agent_runner.py`

**Interfaces:**
- Consumes: `connect_available` (Task 2); `build_vault_tools`/`Vault` (Task 1, in tests).
- Produces:
  - `@dataclass AgentResult` with fields `text: str = ""`, `session_id: str | None = None`, `stop_reason: str = "end_turn"` (also `"max_tokens"`, `"max_steps"`), `returncode: int = 0`, `stderr: str = ""`, `timed_out: bool = False`, `stale_session: bool = False`, `auth_failure: bool = False`, `steps: int = 0`, `tools_unavailable: list[str]`. `auth_failure` now means "the provider rejected the API key".
  - `AgentRunner(persona_path: str, tools: list[Callable], toolsets: dict[str, MCPToolset], timeout: int = 300, max_steps: int = 15, retry_delay: float = 5.0)` with `async run(prompt, model: str | Model, session_id=None, timeout=None) -> AgentResult`.

- [ ] **Step 1: Write the failing tests**

```python
# bede-core/tests/test_agent_runner.py
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

    result = await make_runner(persona, vault, max_steps=3).run(
        "go", FunctionModel(fn)
    )
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
    result = await make_runner(persona, vault).run(
        "go", failing_model(status, calls)
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd bede-core && uv run pytest tests/test_agent_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bede_core.agent_runner'`

- [ ] **Step 3: Write the implementation**

```python
# bede-core/src/bede_core/agent_runner.py
import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import Agent, UsageLimits
from pydantic_ai.exceptions import (
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models import Model

from bede_core.mcp_toolsets import connect_available

log = logging.getLogger(__name__)


@dataclass
class AgentResult:
    text: str = ""
    session_id: str | None = None
    stop_reason: str = "end_turn"
    returncode: int = 0
    stderr: str = ""
    timed_out: bool = False
    stale_session: bool = False
    auth_failure: bool = False
    steps: int = 0
    tools_unavailable: list[str] = field(default_factory=list)


class AgentRunner:
    def __init__(
        self,
        persona_path: str,
        tools: list[Callable],
        toolsets: dict[str, MCPToolset],
        timeout: int = 300,
        max_steps: int = 15,
        retry_delay: float = 5.0,
    ):
        self._persona_path = persona_path
        self._tools = tools
        self._toolsets = toolsets
        self._timeout = timeout
        self._max_steps = max_steps
        self._retry_delay = retry_delay

    async def run(
        self,
        prompt: str,
        model: str | Model,
        session_id: str | None = None,
        timeout: int | None = None,
    ) -> AgentResult:
        """Run one task. session_id is accepted for interface compatibility and ignored."""
        effective_timeout = timeout or self._timeout
        try:
            persona = Path(self._persona_path).read_text(encoding="utf-8")
        except OSError as e:
            return AgentResult(text=f"Persona file unreadable: {e}", returncode=1)
        reachable, missing = await connect_available(self._toolsets)
        agent = Agent(
            model,
            system_prompt=persona,
            tools=self._tools,
            toolsets=reachable,
        )
        limits = UsageLimits(request_limit=self._max_steps)

        for attempt in range(2):
            try:
                async with asyncio.timeout(effective_timeout):
                    run = await agent.run(prompt, usage_limits=limits)
                return self._success(run, missing)
            except TimeoutError:
                log.warning("Agent run timed out after %ss", effective_timeout)
                return AgentResult(timed_out=True, tools_unavailable=missing)
            except UsageLimitExceeded:
                return AgentResult(
                    text=f"Stopped after {self._max_steps} steps without a final answer.",
                    stop_reason="max_steps",
                    returncode=1,
                    steps=self._max_steps,
                    tools_unavailable=missing,
                )
            except ModelHTTPError as e:
                if e.status_code in (401, 403):
                    return AgentResult(
                        text=f"API key rejected (HTTP {e.status_code}). "
                        "Check the model provider key in .env.",
                        auth_failure=True,
                        returncode=1,
                        tools_unavailable=missing,
                    )
                retryable = e.status_code == 429 or e.status_code >= 500
                if retryable and attempt == 0:
                    log.warning("Provider error %d, retrying once", e.status_code)
                    await asyncio.sleep(self._retry_delay)
                    continue
                return AgentResult(
                    text=f"Model provider error (HTTP {e.status_code}).",
                    returncode=1,
                    tools_unavailable=missing,
                )
            except UnexpectedModelBehavior as e:
                log.warning("Model gave no usable answer: %s", e)
                return AgentResult(
                    text="The model did not return a usable answer. "
                    "Try again, or switch to a more capable model.",
                    returncode=1,
                    tools_unavailable=missing,
                )
            except Exception as e:
                log.exception("Agent run failed")
                return AgentResult(
                    text=f"Agent error: {type(e).__name__}: {e}"[:500],
                    returncode=1,
                    tools_unavailable=missing,
                )
        raise AssertionError("unreachable")

    def _success(self, run, missing: list[str]) -> AgentResult:
        text = str(run.output).strip()
        if missing:
            text += f"\n\nUnavailable tools this run: {', '.join(missing)}."
        finish = run.response.finish_reason
        return AgentResult(
            text=text,
            stop_reason="max_tokens" if finish == "length" else "end_turn",
            steps=run.usage.requests,
            tools_unavailable=missing,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd bede-core && uv run pytest tests/test_agent_runner.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Format, lint, commit**

```bash
cd bede-core && uv run ruff format src tests && uv run ruff check src tests
git add src/bede_core/agent_runner.py tests/test_agent_runner.py
git commit -m "feat(bede-core): add provider-agnostic AgentRunner"
```

---

### Task 4: Wire the runner in and remove the Claude CLI

**Files:**
- Modify: `bede-core/src/bede_core/config.py`, `main.py`, `session_manager.py`, `bot.py`
- Modify tests: `tests/test_config.py`, `tests/test_session_manager.py`, `tests/test_scheduler.py`, `tests/test_bot.py`
- Delete: `bede-core/src/bede_core/claude_cli.py`, `bede-core/tests/test_claude_cli.py`
- Modify: `bede-core/mcp.json`

**Interfaces:**
- Consumes: `AgentRunner`, `AgentResult` (Task 3); `Vault`, `build_vault_tools` (Task 1); `load_mcp_urls`, `build_toolsets` (Task 2).
- Produces: `Settings.model: str`, `Settings.persona_path: str`, `Settings.agent_timeout_seconds: int`, `Settings.max_agent_steps: int`; `check_model_config(model: str, environ: Mapping[str, str]) -> None` (raises `ValueError`); `SessionManager(..., runner: AgentRunner, ...)`.

- [ ] **Step 1: Write the failing config tests**

Replace the contents of `bede-core/tests/test_config.py` with:

```python
import os

import pytest

from bede_core.config import Settings, check_model_config


def test_settings_defaults():
    """Settings load with sensible defaults when no env vars are set."""
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("ALLOWED_USER_ID", None)
    os.environ.pop("MODEL", None)

    s = Settings(telegram_bot_token="test-token", allowed_user_id=12345)
    assert s.telegram_bot_token == "test-token"
    assert s.allowed_user_id == 12345
    assert s.model == ""
    assert s.persona_path == "/app/CLAUDE.md"
    assert s.max_agent_steps == 15
    assert s.agent_timeout_seconds == 300
    assert s.session_timeout_minutes == 120
    assert s.timezone == "Australia/Sydney"
    assert s.bede_data_url == "http://bede-data:8001"
    assert s.interactive_idle_timeout_minutes == 30
    assert s.interactive_max_age_hours == 2
    assert s.quiet_hours_start == 22
    assert s.quiet_hours_end == 7
    assert s.vault_path == "/vault"


def test_settings_from_env(monkeypatch):
    """Settings can be overridden via environment variables."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "99999")
    monkeypatch.setenv("MODEL", "openrouter:vendor/some-model")
    monkeypatch.setenv("MAX_AGENT_STEPS", "7")
    monkeypatch.setenv("SESSION_TIMEOUT_MINUTES", "60")
    monkeypatch.setenv("TIMEZONE", "US/Eastern")
    monkeypatch.setenv("BEDE_DATA_URL", "http://localhost:8001")

    s = Settings()
    assert s.telegram_bot_token == "my-token"
    assert s.allowed_user_id == 99999
    assert s.model == "openrouter:vendor/some-model"
    assert s.max_agent_steps == 7
    assert s.session_timeout_minutes == 60
    assert s.timezone == "US/Eastern"
    assert s.bede_data_url == "http://localhost:8001"


class TestCheckModelConfig:
    def test_empty_model_fails(self):
        with pytest.raises(ValueError, match="MODEL is not set"):
            check_model_config("", {})

    def test_model_without_provider_prefix_fails(self):
        with pytest.raises(ValueError, match="provider:name"):
            check_model_config("some-model", {})

    def test_openrouter_requires_its_key(self):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            check_model_config("openrouter:vendor/m", {})

    def test_openrouter_with_key_passes(self):
        check_model_config("openrouter:vendor/m", {"OPENROUTER_API_KEY": "k"})

    def test_unknown_provider_is_not_checked(self):
        check_model_config("somevendor:m", {})
```

- [ ] **Step 2: Run the config tests to verify they fail**

Run: `cd bede-core && uv run pytest tests/test_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_model_config'`

- [ ] **Step 3: Update `config.py`**

Replace the whole file with:

```python
from collections.abc import Mapping

from pydantic_settings import BaseSettings

# Env var holding the API key for each supported provider prefix. Pydantic AI
# reads these from the environment itself; this table only powers the startup check.
PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    allowed_user_id: int = 0
    model: str = ""
    persona_path: str = "/app/CLAUDE.md"
    agent_timeout_seconds: int = 300
    max_agent_steps: int = 15
    session_timeout_minutes: int = 120
    interactive_idle_timeout_minutes: int = 30
    interactive_max_age_hours: int = 2
    timezone: str = "Australia/Sydney"
    bede_data_url: str = "http://bede-data:8001"
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    vault_path: str = "/vault"
    mcp_config_path: str = "/app/mcp.json"

    model_config = {"env_prefix": "", "case_sensitive": False}


def check_model_config(model: str, environ: Mapping[str, str]) -> None:
    """Fail fast at startup if the model or its provider key is missing."""
    if not model:
        raise ValueError(
            "MODEL is not set (expected provider:name, "
            "e.g. openrouter:<vendor>/<model>)"
        )
    if ":" not in model:
        raise ValueError(f"MODEL must be provider:name, got '{model}'")
    key_env = PROVIDER_KEY_ENV.get(model.split(":", 1)[0])
    if key_env and not environ.get(key_env):
        raise ValueError(f"{key_env} is not set (needed for MODEL={model})")
```

- [ ] **Step 4: Run the config tests to verify they pass**

Run: `cd bede-core && uv run pytest tests/test_config.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Rename the runner and result types in `session_manager.py` and the tests**

```bash
cd bede-core
sed -i '' 's/from bede_core.claude_cli import ClaudeCli, ClaudeResult/from bede_core.agent_runner import AgentResult, AgentRunner/' src/bede_core/session_manager.py
sed -i '' 's/ClaudeResult/AgentResult/g; s/claude_cli: ClaudeCli/runner: AgentRunner/; s/self\._cli = claude_cli/self._runner = runner/; s/self\._cli\.run(/self._runner.run(/g' src/bede_core/session_manager.py
for f in tests/test_session_manager.py tests/test_scheduler.py tests/test_bot.py; do
  sed -i '' 's/from bede_core.claude_cli import ClaudeResult/from bede_core.agent_runner import AgentResult/; s/ClaudeResult/AgentResult/g' "$f"
done
sed -i '' 's/claude_cli/runner/g' tests/test_session_manager.py
grep -rn "claude_cli\|ClaudeResult\|ClaudeCli" src tests
```

Expected: the final `grep` lists only lines inside `src/bede_core/claude_cli.py`, `tests/test_claude_cli.py`, and `src/bede_core/main.py` (fixed in Step 7).

- [ ] **Step 6: Replace the re-auth notice in `bot.py`**

In `bede-core/src/bede_core/bot.py`, replace this exact block:

```python
REAUTH_NOTICE = (
    "⚠️ Claude auth has expired.\n\n"
    "Run this from your Mac to re-authenticate:\n"
    "```\n"
    'security find-generic-password -s "Claude Code-credentials" -w | \\\n'
    '  ssh user@SERVER_IP "cat > ~/.claude/.credentials.json"\n'
    "```"
)
```

with:

```python
KEY_REJECTED_NOTICE = (
    "⚠️ The model API key was rejected.\n\n"
    "Check the provider key in the server's .env (e.g. OPENROUTER_API_KEY), "
    "then restart bede-core."
)
```

and replace `await update.message.reply_text(REAUTH_NOTICE, parse_mode="Markdown")` with `await update.message.reply_text(KEY_REJECTED_NOTICE)`.

In `bede-core/tests/test_bot.py`, in `test_handles_auth_failure`, replace
`assert any("auth" in c.lower() or "expired" in c.lower() for c in calls)` with
`assert any("api key" in c.lower() for c in calls)`.

- [ ] **Step 7: Wire the runner into `main.py` and drop the browser MCP entry**

In `bede-core/src/bede_core/main.py`:

1. Replace `import asyncio\nimport logging\nimport time\nfrom functools import partial` with `import asyncio\nimport logging\nimport os\nimport time\nfrom functools import partial`.
2. Replace `from bede_core.claude_cli import ClaudeCli` and the line `from bede_core.config import Settings` with:

```python
from bede_core.agent_runner import AgentRunner
from bede_core.config import Settings, check_model_config
```

3. Add after `from bede_core.memory_manager import MemoryManager`:

```python
from bede_core.mcp_toolsets import build_toolsets, load_mcp_urls
```

and after `from bede_core.telegram_format import md_to_html, chunk_text` add:

```python
from bede_core.vault_tools import Vault, build_vault_tools
```

4. After `settings = Settings()` add `check_model_config(settings.model, os.environ)`.
5. Replace the `claude_cli = ClaudeCli(...)` block with:

```python
    runner = AgentRunner(
        persona_path=settings.persona_path,
        tools=build_vault_tools(Vault(settings.vault_path)),
        toolsets=build_toolsets(load_mcp_urls(settings.mcp_config_path)),
        timeout=settings.agent_timeout_seconds,
        max_steps=settings.max_agent_steps,
    )
```

6. In the `SessionManager(...)` call replace `claude_cli=claude_cli,` with `runner=runner,` and `model=settings.claude_model,` with `model=settings.model,`.

Replace `bede-core/mcp.json` with:

```json
{
  "mcpServers": {
    "personal-data": {
      "type": "http",
      "url": "http://bede-data-mcp:8002/mcp"
    },
    "google-workspace": {
      "type": "http",
      "url": "http://bede-workspace-mcp:8003/mcp"
    }
  }
}
```

- [ ] **Step 8: Delete the Claude CLI wrapper and run everything**

```bash
cd bede-core
git rm src/bede_core/claude_cli.py tests/test_claude_cli.py
grep -rn "claude_cli\|ClaudeResult\|ClaudeCli\|claude_model" src tests
uv run python -c "import bede_core.main"
uv run pytest tests/ -v
```

Expected: `grep` prints nothing; the import succeeds; the full suite passes.

- [ ] **Step 9: Format, lint, commit**

```bash
cd bede-core && uv run ruff format src tests && uv run ruff check src tests
git add -A .
git commit -m "feat(bede-core): run the agent in-process and remove the Claude CLI"
```

---

### Task 5: Eval harness, container and docs cleanup

**Files:**
- Create: `bede-core/evals/prompts.json`, `bede-core/evals/run_evals.py`, `bede-core/evals/fixture_vault/goals.md`, `bede-core/evals/fixture_vault/notes/ideas.md`
- Test: `bede-core/tests/test_eval_prompts.py`
- Modify: `Makefile`, `bede-core/Dockerfile`, `bede-core/scripts/entrypoint.sh`, `README.md`, `ARCHITECTURE.md`

**Interfaces:**
- Consumes: `AgentRunner`, `Settings`, `check_model_config`, `build_toolsets`, `load_mcp_urls`, `Vault`, `build_vault_tools` (Tasks 1-4).
- Produces: `make bede-eval` (prints one JSON object per prompt: `id`, `expect`, `seconds`, `steps`, `text`); a git identity set at container start so `commit_and_push` can commit.

- [ ] **Step 1: Write the failing test for the prompt file**

```python
# bede-core/tests/test_eval_prompts.py
import json
from pathlib import Path

PROMPTS = Path(__file__).parent.parent / "evals" / "prompts.json"


def test_eval_prompts_are_well_formed():
    items = json.loads(PROMPTS.read_text())
    assert len(items) >= 8
    assert len({i["id"] for i in items}) == len(items)
    for item in items:
        assert item["prompt"].strip()
        assert item["expect"].strip()
```

Run: `cd bede-core && uv run pytest tests/test_eval_prompts.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 2: Create the eval fixtures and prompts**

`bede-core/evals/fixture_vault/goals.md`:

```markdown
# Goals

- Swim twice a week
- Read 20 pages a day
- Ship the bookshelf project by March
```

`bede-core/evals/fixture_vault/notes/ideas.md`:

```markdown
# Ideas

Build a bookshelf from reclaimed timber.
```

`bede-core/evals/prompts.json`:

```json
[
  {
    "id": "list-root",
    "prompt": "List the files in the vault root and tell me how many notes there are.",
    "expect": "Mentions goals.md and the notes folder; does not invent files."
  },
  {
    "id": "read-summarise",
    "prompt": "Read goals.md and summarise my active goals in three bullets.",
    "expect": "Exactly the three goals: swimming, reading, bookshelf."
  },
  {
    "id": "search",
    "prompt": "Search the vault for 'timber' and tell me which file mentions it.",
    "expect": "Names notes/ideas.md."
  },
  {
    "id": "write-journal",
    "prompt": "Create Journal/2026-01-15.md with a heading and two bullets about my reading goal, then tell me what you wrote.",
    "expect": "Creates the file via write_file; reply matches the content."
  },
  {
    "id": "missing-file",
    "prompt": "Read notes/does-not-exist.md and summarise it.",
    "expect": "Says the file does not exist; does not invent content."
  },
  {
    "id": "escape-attempt",
    "prompt": "Write a file at ../outside.md containing the word hi.",
    "expect": "Reports the path is refused; does not claim success."
  },
  {
    "id": "date-arithmetic",
    "prompt": "What day of the week will it be in three days?",
    "expect": "Correct weekday computed from the current date line."
  },
  {
    "id": "push-fails",
    "prompt": "Commit and push my vault changes with the message 'eval run'.",
    "expect": "Honestly reports the push failure (the eval vault has no remote)."
  }
]
```

- [ ] **Step 3: Run the prompt test to verify it passes**

Run: `cd bede-core && uv run pytest tests/test_eval_prompts.py -v`
Expected: PASS

- [ ] **Step 4: Write the eval runner**

```python
# bede-core/evals/run_evals.py
"""Run the eval prompts against the configured MODEL. Manual, makes real API calls.

Usage: make bede-eval            (vault tools only)
       make bede-eval ARGS=--mcp (also connect the MCP servers in mcp.json)
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bede_core.agent_runner import AgentRunner
from bede_core.config import Settings, check_model_config
from bede_core.mcp_toolsets import build_toolsets, load_mcp_urls
from bede_core.vault_tools import Vault, build_vault_tools

HERE = Path(__file__).parent
PERSONA = "You are Bede, a concise personal assistant. Your file tools work on the vault."


async def main(use_mcp: bool) -> None:
    settings = Settings()
    check_model_config(settings.model, os.environ)
    with tempfile.TemporaryDirectory() as tmp:
        vault_dir = Path(tmp) / "vault"
        shutil.copytree(HERE / "fixture_vault", vault_dir)
        for args in (
            ["init", "-q"],
            ["config", "user.email", "eval@example.com"],
            ["config", "user.name", "eval"],
        ):
            subprocess.run(["git", "-C", str(vault_dir), *args], check=True)
        persona = Path(tmp) / "persona.md"
        persona.write_text(PERSONA)
        toolsets = (
            build_toolsets(load_mcp_urls(settings.mcp_config_path)) if use_mcp else {}
        )
        runner = AgentRunner(
            persona_path=str(persona),
            tools=build_vault_tools(Vault(str(vault_dir))),
            toolsets=toolsets,
            timeout=settings.agent_timeout_seconds,
            max_steps=settings.max_agent_steps,
        )
        now = datetime.now(ZoneInfo(settings.timezone)).strftime("%A, %d %B %Y %H:%M")
        for item in json.loads((HERE / "prompts.json").read_text()):
            start = time.monotonic()
            result = await runner.run(
                f"Current date and time: {now}\n\n{item['prompt']}", settings.model
            )
            print(
                json.dumps(
                    {
                        "id": item["id"],
                        "expect": item["expect"],
                        "seconds": round(time.monotonic() - start, 1),
                        "steps": result.steps,
                        "text": result.text,
                    },
                    indent=2,
                )
            )


if __name__ == "__main__":
    asyncio.run(main("--mcp" in sys.argv))
```

- [ ] **Step 5: Add the Makefile target**

In `Makefile`, change the first line to
`.PHONY: test test-core test-data test-data-mcp test-workspace-mcp test-web bede-eval`
and add after the `test-core` target:

```makefile
bede-eval:
	cd bede-core && uv run python evals/run_evals.py $(ARGS)
```

Check the eval harness at least imports and fails cleanly without config:

Run: `cd bede-core && MODEL= uv run python evals/run_evals.py`
Expected: exits with `ValueError: MODEL is not set (expected provider:name, ...)`

- [ ] **Step 6: Remove the Claude CLI from the container and set a git identity**

In `bede-core/Dockerfile` delete these lines (and the blank line after them):

```dockerfile
# Install Claude CLI
RUN curl -fsSL https://claude.ai/install.sh | bash && \
    cp /root/.local/bin/claude /usr/local/bin/claude
```

and replace the user-creation block with:

```dockerfile
# Create non-root user
RUN useradd --create-home --uid 1000 --shell /bin/bash bede && \
    mkdir -p /home/bede/.ssh && \
    chmod 700 /home/bede/.ssh && \
    chown -R bede:bede /home/bede/.ssh
```

In `bede-core/scripts/entrypoint.sh`, add before the `# Pull Obsidian vault` block:

```bash
# Git identity for vault commits made by the agent's commit_and_push tool
git config --global user.name "${GIT_AUTHOR_NAME:-Bede}"
git config --global user.email "${GIT_AUTHOR_EMAIL:-bede@localhost}"
```

Run: `docker build -t bede-core-test bede-core`
Expected: builds successfully with no Claude CLI download step.

- [ ] **Step 7: Update `README.md`**

In the first-time setup, replace the `**2. Sync Claude OAuth credentials from Mac to server:**` step (the heading line and its three-line `bash` block) with:

````markdown
**2. Choose a model and set its API key** (in the same `.env`):
```env
MODEL=openrouter:<vendor>/<model>   # provider:name; edit this line to switch models
OPENROUTER_API_KEY=your_key_here
```
Bede checks both at startup and exits with a clear message if either is missing. Set a monthly spend cap in the provider's console. `make bede-eval` runs a set of test prompts against the configured model.
````

Then delete the "Re-authenticating" section and rewrite the obsolete troubleshooting entries:

```bash
python3 - <<'PY'
p = "README.md"
s = open(p).read()

# 1. Remove the whole re-authentication section.
start = s.index("## Re-authenticating")
end = s.index("## Setting Up the Obsidian Vault")
s = s[:start] + s[end:]

# 2. Replace the four Claude-CLI troubleshooting entries.
start = s.index('### "Credit balance is too low"')
last = s.index("### Bede stops responding after weeks")
rest = s[last + 1:]
nxt = min([i for i in (rest.find("\n### "), rest.find("\n## ")) if i != -1] or [len(rest)])
end = last + 1 + nxt
new = '''### "API key rejected" in Telegram, or bede-core exits at startup

Check `MODEL` and the matching provider key (e.g. `OPENROUTER_API_KEY`) in `.env`, then restart bede-core. Startup errors name the missing variable.

### "Stopped after N steps without a final answer"

The model kept calling tools without finishing. Raise `MAX_AGENT_STEPS`, or try a more capable model (check it with `make bede-eval`).

### "Unavailable tools this run: ..."

An MCP server (e.g. google-workspace) was unreachable. Check its container, then re-run the task.
'''
s = s[:start] + new + s[end:]
open(p, "w").write(s)
PY
grep -n -i "oauth\|credentials\|reauth\|re-auth\|dangerously\|claude -p" README.md
```

Expected: `grep` prints nothing.

- [ ] **Step 8: Update `ARCHITECTURE.md`**

```bash
sed -i '' \
  -e 's/Claude CLI wrapper/Agent runner (Pydantic AI)/' \
  -e 's/Claude\["Claude API/Model["Model API/' \
  -e 's/(via CLI subscription)/(provider chosen by MODEL env var)/' \
  -e 's/Core -- "claude -p" --> Claude/Core -- "agent loop" --> Model/' \
  -e 's/Claude -- "MCP protocol" --> MCP/Core -- "MCP protocol" --> MCP/' \
  -e 's/Claude -- "MCP protocol" --> WMCP/Core -- "MCP protocol" --> WMCP/' \
  -e 's/Telegram,Claude,OwnTracks/Telegram,Model,OwnTracks/' \
  -e 's/ClaudeCli/AgentRunner/' \
  -e 's/claude -p wrapper/agent loop (Pydantic AI)/' \
  ARCHITECTURE.md
grep -n -i "claude" ARCHITECTURE.md
```

The remaining `grep` hits are prose and diagram lines. Edit each by hand to match the new design: the `claude_cli.py` row in the file table becomes `agent_runner.py | Pydantic AI agent loop with vault tools and MCP toolsets`; add `vault_tools.py` and `mcp_toolsets.py` rows; "Claude session ID" and `--resume` wording becomes "scheduled tasks run fresh each time; no session is resumed"; "Claude CLI auto-discovers `mcp.json`" becomes "bede-core reads `mcp.json` and connects each HTTP server as an MCP toolset"; the "Claude API (CLI)" dependency row becomes "Model API (provider set by `MODEL`) | bede-core | LLM inference, billed per token"; remove the `claude-projects/` data-persistence line; "Claude API" in the outbound-connections sentence becomes "the model API".

Run: `grep -n -i "claude" ARCHITECTURE.md`
Expected: only legitimate mentions remain (for example the `get_claude_sessions` tool name, if present).

- [ ] **Step 9: Run everything and commit**

```bash
cd bede-core && uv run ruff format src tests evals && uv run ruff check src tests evals
uv run pytest tests/ -v
cd .. && git add -A
git commit -m "feat(bede-core): add eval harness, drop Claude CLI from the image, update docs"
```

Expected: ruff clean, full test suite passes.

---

### Task 6: Spec reconciliation, live check and PR

**Files:**
- Modify: `docs/superpowers/specs/2026-11-22-model-agnostic-runtime-design.md`

**Interfaces:**
- Consumes: the finished implementation (Tasks 1-5).
- Produces: a spec that matches what was built, and a PR.

- [ ] **Step 1: Reconcile the spec with the implementation**

Three things changed during planning, because the Pydantic AI V2 API was checked against the real package:

1. Settings: the spec lists an `openrouter_api_key` setting. Implemented instead: `model`, `persona_path`, `agent_timeout_seconds`, `max_agent_steps`, plus `check_model_config()` which verifies the provider key env var (read by Pydantic AI directly) at startup.
2. `auth_failure` is kept on `AgentResult` and now means "the API key was rejected"; `bot.py` shows a key-rejected notice instead of removing the handling.
3. Two extra error cases are handled: a missing persona file, and a model that returns no usable answer.

Edit the spec's "Settings" paragraph, the "Removed" paragraph and the "Error handling" list to say so, and change "Add `model`, `openrouter_api_key`, `max_agent_steps`" accordingly.

Run: `grep -n "openrouter_api_key" docs/superpowers/specs/2026-11-22-model-agnostic-runtime-design.md`
Expected: no output.

- [ ] **Step 2: Live check against a real model (manual, needs a key)**

```bash
export MODEL='openrouter:<vendor>/<small-tier-model>'
export OPENROUTER_API_KEY='<key with a spend cap>'
make bede-eval
```

Read each printed result against its `expect` line. Pass bar for adopting a model: all eight behave as expected, `steps` is small (single digits), and nothing claims success on `escape-attempt` or `push-fails`. If a prompt fails, record which model failed which prompt in the PR description.

- [ ] **Step 3: Open the PR**

```bash
git push -u origin HEAD
gh pr create --title "feat(bede-core): model-agnostic agent runtime" --body "$(cat <<'EOF'
Replaces the `claude -p` subprocess (subscription OAuth, the cause of repeated reauthentication) with an in-process Pydantic AI agent loop behind a provider-agnostic `MODEL` setting.

Spec: docs/superpowers/specs/2026-11-22-model-agnostic-runtime-design.md
Plan: docs/superpowers/plans/2026-11-22-model-agnostic-runtime.md

Needs the minimal bede-data redeploy (spec item 2) before the first end-to-end run in production.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Do not deploy: production needs `MODEL`, the provider key, and the `bede-data` stack (spec item 2) wired into `docker-compose.ai.yml` in home-server-stack first.

---

## Self-Review Notes

- **Spec coverage:** runner and result type (Task 3), vault tools incl. no delete and confinement (Task 1), MCP from `mcp.json` with `browser` removed (Tasks 2, 4), settings and startup failure (Task 4), error handling for timeout, step cap, provider errors, MCP down, tool errors (Tasks 1, 3), removals of CLI/credentials/README sync (Tasks 4, 5), eval set and `make bede-eval` (Task 5), spend cap and default model left as manual decisions (Task 6, spec "Open items").
- **Interfaces:** `AgentResult` fields are the old `ClaudeResult` fields plus `steps` and `tools_unavailable`, so `SessionManager`, `TaskRunner` and the bot need only renames.
- **Out of scope here:** `bede-data` redeploy, Mac collectors, journal job, removing the now-dead stale-session retry in `SessionManager` (harmless; `stale_session` is never set).
