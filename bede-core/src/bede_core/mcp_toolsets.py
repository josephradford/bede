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
