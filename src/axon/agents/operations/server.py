"""FastMCP server for Operations agents (Production, Logistics, Warehouse).

Exposes tools on port 8102 by default.
"""

from __future__ import annotations

from fastmcp import FastMCP

from axon.agents.operations import LogisticsAgent, ProductionAgent, WarehouseAgent
from axon.core.telemetry import log_event

server = FastMCP(
    "axon-agent-operations",
    description="Operations agent MCP server: Production, Logistics, Warehouse",
)


@server.tool()
async def operations_reason(
    agent_id: str,
    planning_context: dict,
    past_insights: list | None = None,
) -> dict:
    """Run an operations agent's reasoning.

    Args:
        agent_id: One of 'production', 'logistics', 'warehouse'
        planning_context: Current planning state (demands, supplies, allocations)
        past_insights: Previous plan insights from long-term memory

    Returns:
        Agent proposal with utility score and justification
    """
    log_event("info", "agent_server_reason", agent_id=agent_id, server="operations")

    agent_map = {
        "production": ProductionAgent,
        "logistics": LogisticsAgent,
        "warehouse": WarehouseAgent,
    }

    agent_cls = agent_map.get(agent_id)
    if not agent_cls:
        return {"error": f"Unknown operations agent: {agent_id}"}

    agent = agent_cls()
    proposal = await agent.propose(
        {"context": planning_context, "insights": past_insights or []}
    )

    return {
        "agent_id": agent_id,
        "domain": "operations",
        "proposal": proposal,
    }


@server.tool()
async def list_operations_agents() -> list[str]:
    """List all available operations agents."""
    return ["production", "logistics", "warehouse"]


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8102)
