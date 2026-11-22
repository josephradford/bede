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
