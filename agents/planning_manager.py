"""
PlanningManagerAgent — analyse demand vs supply and produce a PlanningDecision.

Phase 3 implementation: connected to mcp-ascp-planning MCP server (SSE).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from core.config import settings
from core.model_factory import build_model


# ── Output models ─────────────────────────────────────────────────────────────

class AllocationUpdate(BaseModel):
    pegging_id: int = Field(description="era.ascp.pegging.ledger record ID")
    allocated_qty: float = Field(description="New allocated quantity")
    status: str = Field(description="New pegging status")
    reason: str = Field(description="Why this allocation was chosen")


class ShortageItem(BaseModel):
    product_id: int
    product_name: str
    demand_qty: float
    available_qty: float
    shortage_qty: float
    demand_date: str
    pegging_id: int


class PlanningDecision(BaseModel):
    action: str = Field(
        description="'allocate' | 'shortage' | 'hitl_required' | 'no_action'"
    )
    pegging_updates: list[AllocationUpdate] = Field(default_factory=list)
    shortages: list[ShortageItem] = Field(
        default_factory=list,
        description="Populated when action='shortage'",
    )
    hitl_activity_ids: list[int] = Field(
        default_factory=list,
        description="Odoo mail.activity IDs awaiting human response",
    )
    summary: str
    confidence: float = Field(
        default=1.0,
        description="0.0–1.0; < 0.7 triggers escalation to Executive Agent",
    )


# ── Agent ─────────────────────────────────────────────────────────────────────

PLANNING_SYSTEM_PROMPT = """
You are the Planning Manager Agent for EraOwl ASCP.

Your role:
- Read the demand stream and pegging ledger from Odoo via ascp_get_ledger,
  ascp_sync_demand_stream, and ascp_check_shortage.
- If stock is sufficient: call ascp_update_allocation and return action='allocate'.
- If shortages exist: return action='shortage' with a populated shortages list.
  The Supervisor will route to the Purchase Cluster.
- If a major exception requires human review: call ascp_create_activity and
  return action='hitl_required'.
- Set confidence between 0.0 and 1.0; below 0.7 escalates to Executive Agent.
"""

_planning_agent: "Agent[None, PlanningDecision] | None" = None


def get_planning_manager_agent() -> "Agent[None, PlanningDecision]":
    global _planning_agent
    if _planning_agent is None:
        mcp_planning = MCPServerSSE(
            f"http://localhost:{settings.mcp_planning_port}/sse"
        )
        _planning_agent = Agent(
            build_model(settings.llm_planning_model),
            output_type=PlanningDecision,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            toolsets=[mcp_planning],
        )
    return _planning_agent


# Legacy alias
def planning_manager_agent_factory():
    return get_planning_manager_agent()
