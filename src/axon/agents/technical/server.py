"""FastMCP server for Technical agents (QA, QC, Maintenance, PD).

Exposes tools on port 8103 by default.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from axon.agents.connector_builder import build_connectors
from axon.agents.technical import MaintenanceAgent, PDAgent, QAAgent, QCAgent
from axon.core.telemetry import log_event

server = FastMCP(
    "axon-agent-technical",
    instructions="Technical agent MCP server: QA, QC, Maintenance, PD",
    host="0.0.0.0",
    port=8103,
)
...
if __name__ == "__main__":
    server.run(transport="sse")
