import asyncio
import json
import logging
import os
import signal
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ClaudeResult:
    text: str = ""
    session_id: str | None = None
    stop_reason: str = "end_turn"
    returncode: int = 0
    stderr: str = ""
    timed_out: bool = False
    stale_session: bool = False
    auth_failure: bool = False


def build_command(
    prompt: str,
    model: str,
    session_id: str | None = None,
    mcp_config: str | None = None,
) -> list[str]:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--dangerously-skip-permissions",
        "--output-format",
        "json",
    ]
    if session_id:
        cmd += ["--resume", session_id]
    if mcp_config:
        cmd += ["--mcp-config", mcp_config]
    return cmd


def parse_output(stdout: str) -> ClaudeResult:
    result = ClaudeResult()
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            result.text = obj.get("result", "").strip()
            result.session_id = obj.get("session_id")
            result.stop_reason = obj.get("stop_reason", "end_turn")
    return result


def _run_subprocess(
    cmd: list[str], workdir: str, timeout: int, env: dict | None = None
) -> subprocess.CompletedProcess:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        cwd=workdir,
        text=True,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        raise


_AUTH_KEYWORDS = ("unauthorized", "authentication", "auth", "login")


class ClaudeCli:
    def __init__(
        self,
        workdir: str,
        timeout: int,
        filter_env_keys: list[str] | None = None,
        mcp_config: str | None = None,
    ):
        self._workdir = workdir
        self._timeout = timeout
        self._filter_env_keys = set(filter_env_keys or [])
        self._mcp_config = mcp_config

    def _build_env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k not in self._filter_env_keys}
        return env

    async def run(
        self,
        prompt: str,
        model: str,
        session_id: str | None = None,
        timeout: int | None = None,
    ) -> ClaudeResult:
        cmd = build_command(
            prompt, model, session_id=session_id, mcp_config=self._mcp_config
        )
        env = self._build_env()
        effective_timeout = timeout or self._timeout

        try:
            proc = await asyncio.to_thread(
                _run_subprocess, cmd, self._workdir, effective_timeout, env
            )
        except subprocess.TimeoutExpired:
            log.warning("Claude CLI timed out after %ds", effective_timeout)
            return ClaudeResult(timed_out=True)

        result = parse_output(proc.stdout)
        result.returncode = proc.returncode
        result.stderr = proc.stderr

        if session_id and "no conversation found" in proc.stderr.lower():
            result.stale_session = True

        if proc.returncode != 0 and any(
            kw in proc.stderr.lower() for kw in _AUTH_KEYWORDS
        ):
            result.auth_failure = True

        if not result.text and proc.returncode != 0:
            result.text = (proc.stderr or proc.stdout or "No response.").strip()[:4096]

        return result
