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
PERSONA = (
    "You are Bede, a concise personal assistant. Your file tools work on the vault."
)


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
