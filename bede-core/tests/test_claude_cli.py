import json
import subprocess
from unittest.mock import patch


from bede_core.claude_cli import ClaudeCli, build_command, parse_output


class TestBuildCommand:
    def test_basic_command(self):
        cmd = build_command("hello", model="claude-sonnet-4-5-20250514")
        assert cmd[:2] == ["claude", "-p"]
        assert "hello" in cmd
        assert "--model" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd

    def test_with_session_resume(self):
        cmd = build_command(
            "hello", model="claude-sonnet-4-5-20250514", session_id="abc-123"
        )
        assert "--resume" in cmd
        idx = cmd.index("--resume")
        assert cmd[idx + 1] == "abc-123"

    def test_without_session(self):
        cmd = build_command("hello", model="claude-sonnet-4-5-20250514")
        assert "--resume" not in cmd

    def test_mcp_config(self):
        cmd = build_command(
            "hello", model="claude-sonnet-4-5-20250514", mcp_config="/path/mcp.json"
        )
        assert "--mcp-config" in cmd
        idx = cmd.index("--mcp-config")
        assert cmd[idx + 1] == "/path/mcp.json"


class TestParseOutput:
    def test_extracts_result(self):
        stdout = json.dumps(
            {
                "type": "result",
                "result": "hello world",
                "session_id": "sess-1",
                "stop_reason": "end_turn",
            }
        )
        r = parse_output(stdout)
        assert r.text == "hello world"
        assert r.session_id == "sess-1"
        assert r.stop_reason == "end_turn"

    def test_multiple_lines(self):
        lines = [
            json.dumps({"type": "assistant", "content": "thinking..."}),
            json.dumps(
                {
                    "type": "result",
                    "result": "final answer",
                    "session_id": "s2",
                    "stop_reason": "end_turn",
                }
            ),
        ]
        r = parse_output("\n".join(lines))
        assert r.text == "final answer"
        assert r.session_id == "s2"

    def test_empty_stdout(self):
        r = parse_output("")
        assert r.text == ""
        assert r.session_id is None

    def test_max_tokens(self):
        stdout = json.dumps(
            {
                "type": "result",
                "result": "truncated",
                "session_id": "s3",
                "stop_reason": "max_tokens",
            }
        )
        r = parse_output(stdout)
        assert r.stop_reason == "max_tokens"

    def test_invalid_json_lines_skipped(self):
        lines = [
            "not json",
            json.dumps(
                {
                    "type": "result",
                    "result": "ok",
                    "session_id": "s4",
                    "stop_reason": "end_turn",
                }
            ),
        ]
        r = parse_output("\n".join(lines))
        assert r.text == "ok"


class TestClaudeCli:
    async def test_run_success(self):
        mock_result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "result": "hi",
                    "session_id": "s1",
                    "stop_reason": "end_turn",
                }
            ),
            stderr="",
        )
        cli = ClaudeCli(workdir="/app", timeout=300)
        with patch("bede_core.claude_cli._run_subprocess", return_value=mock_result):
            r = await cli.run("hello", model="claude-sonnet-4-5-20250514")
        assert r.text == "hi"
        assert r.session_id == "s1"
        assert r.returncode == 0

    async def test_run_timeout(self):
        cli = ClaudeCli(workdir="/app", timeout=1)
        with patch(
            "bede_core.claude_cli._run_subprocess",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=1),
        ):
            r = await cli.run("hello", model="claude-sonnet-4-5-20250514")
        assert r.timed_out is True
        assert r.text == ""

    async def test_run_stale_session_detected(self):
        mock_result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Error: no conversation found for session abc",
        )
        cli = ClaudeCli(workdir="/app", timeout=300)
        with patch("bede_core.claude_cli._run_subprocess", return_value=mock_result):
            r = await cli.run(
                "hello", model="claude-sonnet-4-5-20250514", session_id="abc"
            )
        assert r.stale_session is True

    async def test_run_auth_failure_detected(self):
        mock_result = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Authentication failed: unauthorized",
        )
        cli = ClaudeCli(workdir="/app", timeout=300)
        with patch("bede_core.claude_cli._run_subprocess", return_value=mock_result):
            r = await cli.run("hello", model="claude-sonnet-4-5-20250514")
        assert r.auth_failure is True

    async def test_env_filtering(self):
        cli = ClaudeCli(workdir="/app", timeout=300, filter_env_keys=["SECRET_TOKEN"])
        captured_env = {}

        def fake_run(cmd, workdir, timeout, env=None):
            if env:
                captured_env.update(env)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=json.dumps(
                    {
                        "type": "result",
                        "result": "ok",
                        "session_id": "s1",
                        "stop_reason": "end_turn",
                    }
                ),
                stderr="",
            )

        with patch("bede_core.claude_cli._run_subprocess", side_effect=fake_run):
            with patch.dict(
                "os.environ", {"SECRET_TOKEN": "secret", "SAFE_VAR": "ok"}, clear=True
            ):
                await cli.run("hello", model="claude-sonnet-4-5-20250514")
        assert "SECRET_TOKEN" not in captured_env
        assert captured_env.get("SAFE_VAR") == "ok"
