"""
agents.planning — Planning Manager Agent.

Analyses universal AxonDemandStream vs AxonSupplyStream and produces a AxonPlanningDecision.
Connects to the ERP via MCP servers — ERP-agnostic by design.

The output AxonPlanningDecision uses core.schema models, not Odoo-specific fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.allocation import AxonAllocationAction, AxonPlanningDecision, AxonShortageItem
from core.schema.allocation import AxonAllocation


# ── Legacy output models (kept for orchestrator compatibility during migration) ─

class AxonAllocationUpdate(BaseModel):
    pegging_id: int = Field(description="ERP pegging record ID to update")
    allocated_qty: float = Field(description="New allocated quantity")
    status: str = Field(description="New pegging status")
    reason: str = Field(description="Why this allocation was chosen")


class AxonShortageItem(BaseModel):
    product_id: int
    product_name: str
    demand_qty: float
    available_qty: float
    shortage_qty: float
    demand_date: str
    pegging_id: int


class AxonPlanningDecision(BaseModel):
    action: str = Field(
        description="'allocate' | 'shortage' | 'hitl_required' | 'no_action'"
    )
    pegging_updates: list[AxonAllocationUpdate] = Field(default_factory=list)
    shortages: list[AxonShortageItem] = Field(
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
You are the Planning Manager Agent for Axon — the AI-Native Supply Chain Planning Engine.

You reason over a universal demand/supply schema that is ERP-agnostic.
Your MCP tools speak to the connected ERP (Odoo, SAP, etc.) on your behalf.

Your role:
- Read the demand stream and pegging ledger via axon_get_ledger,
  axon_sync_demand_stream, and axon_check_shortage.
- If stock is sufficient: call axon_update_allocation and return action='allocate'.
- If shortages exist: return action='shortage' with a populated shortages list.
  The Supervisor will route to the Purchase Cluster.
- If a major exception requires human review: call axon_create_activity and
  return action='hitl_required'.
- Set confidence between 0.0 and 1.0; below 0.7 escalates to Executive Agent.
"""

_planning_agent: "Agent[None, AxonPlanningDecision] | None" = None


def get_axon_planning_agent() -> "Agent[None, AxonPlanningDecision]":
    global _planning_agent
    if _planning_agent is None:
        registry = AxonAdapterRegistry()
        _planning_agent = Agent(
            build_model(settings.llm_planning_model),
            output_type=AxonPlanningDecision,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            toolsets=registry.planning_servers(),
        )
    return _planning_agent


# Backward-compat aliases
def get_axon_planning_manager_agent() -> "Agent[None, AxonPlanningDecision]":
    return get_axon_planning_agent()


def axon_planning_manager_agent_factory():
    return get_axon_planning_agent()
