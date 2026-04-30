from bede_data_mcp.server import mcp

import os

port = int(os.environ.get("DATA_MCP_PORT", "8002"))
mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
