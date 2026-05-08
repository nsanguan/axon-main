"""FastMCP server for Technical agents (QA, QC, Maintenance, PD).

Exposes tools on port 8103 by default.
"""

from __future__ import annotations

from fastmcp import FastMCP

from axon.agents.technical import MaintenanceAgent, PDAgent, QAAgent, QCAgent
from axon.core.telemetry import log_event

server = FastMCP(
    "axon-agent-technical",
    description="Technical agent MCP server: QA, QC, Maintenance, PD",
)


@server.tool()
async def technical_reason(
    agent_id: str,
    planning_context: dict,
    past_insights: list | None = None,
) -> dict:
    """Run a technical agent's reasoning.

    Args:
        agent_id: One of 'qa', 'qc', 'maintenance', 'pd'
        planning_context: Current planning state (demands, supplies, allocations)
        past_insights: Previous plan insights from long-term memory

    Returns:
        Agent proposal with utility score and justification
    """
    log_event("info", "agent_server_reason", agent_id=agent_id, server="technical")

    agent_map = {
        "qa": QAAgent,
        "qc": QCAgent,
        "maintenance": MaintenanceAgent,
        "pd": PDAgent,
    }

    agent_cls = agent_map.get(agent_id)
    if not agent_cls:
        return {"error": f"Unknown technical agent: {agent_id}"}

    agent = agent_cls()
    proposal = await agent.propose(
        {"context": planning_context, "insights": past_insights or []}
    )

    return {
        "agent_id": agent_id,
        "domain": "technical",
        "proposal": proposal,
    }


@server.tool()
async def list_technical_agents() -> list[str]:
    """List all available technical agents."""
    return ["qa", "qc", "maintenance", "pd"]


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8103)
