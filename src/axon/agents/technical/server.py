"""FastMCP server for Technical agents (QA, QC, Maintenance, PD).

Exposes tools on port 8103 by default.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    "axon-agent-technical",
    instructions="Technical agent MCP server: QA, QC, Maintenance, PD",
    host="0.0.0.0",
    port=8103,
)
...
if __name__ == "__main__":
    server.run(transport="sse")
