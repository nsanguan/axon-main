"""FastMCP server for Commercial agents (Sales, Procurement, Finance).

Registers each commercial agent's reasoning capability as an MCP tool.
The orchestrator discovers and calls these tools during the REASON phase.

Exposes tools on port 8101 by default.
"""

from __future__ import annotations

from fastmcp import FastMCP

from axon.agents.commercial import FinanceAgent, ProcurementAgent, SalesAgent
from axon.core.telemetry import log_event

server = FastMCP(
    "axon-agent-commercial",
    description="Commercial agent MCP server: Sales, Procurement, Finance",
)


@server.tool()
async def commercial_reason(
    agent_id: str,
    planning_context: dict,
    past_insights: list | None = None,
) -> dict:
    """Run a commercial agent's reasoning.

    Args:
        agent_id: One of 'sales', 'procurement', 'finance'
        planning_context: Current planning state (demands, supplies, allocations)
        past_insights: Previous plan insights from long-term memory

    Returns:
        Agent proposal with utility score and justification
    """
    log_event("info", "agent_server_reason", agent_id=agent_id, server="commercial")

    agent_map = {
        "sales": SalesAgent,
        "procurement": ProcurementAgent,
        "finance": FinanceAgent,
    }

    agent_cls = agent_map.get(agent_id)
    if not agent_cls:
        return {"error": f"Unknown commercial agent: {agent_id}"}

    agent = agent_cls()
    proposal = await agent.propose(
        {"context": planning_context, "insights": past_insights or []}
    )

    return {
        "agent_id": agent_id,
        "domain": "commercial",
        "proposal": proposal,
    }


@server.tool()
async def list_commercial_agents() -> list[str]:
    """List all available commercial agents."""
    return ["sales", "procurement", "finance"]


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8101)
