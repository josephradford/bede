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
