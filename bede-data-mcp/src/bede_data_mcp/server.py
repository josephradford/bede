"""bede-data-mcp: Thin MCP proxy forwarding tool calls to bede-data's HTTP API."""

import os

from fastmcp import FastMCP

from bede_data_mcp import client  # noqa: F401

mcp = FastMCP("personal-data")


if __name__ == "__main__":
    port = int(os.environ.get("DATA_MCP_PORT", "8002"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
