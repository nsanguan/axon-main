"""FastMCP server for Operations agents (Production, Logistics, Warehouse).

Exposes tools on port 8102 by default.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    "axon-agent-operations",
    instructions="Operations agent MCP server: Production, Logistics, Warehouse",
    host="0.0.0.0",
    port=8102,
)
...
if __name__ == "__main__":
    server.run(transport="sse")
