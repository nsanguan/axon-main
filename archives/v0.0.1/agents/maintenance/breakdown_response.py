"""
agents.maintenance.breakdown_response — Breakdown Response Agent.

Activated when a breakdown event is detected. Produces an
AxonMaintenanceConstraint that the Production Rescheduling Agent and Sales
ATP Agent use to immediately adjust the schedule and notify customers.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.maintenance import AxonMaintenanceConstraint

BREAKDOWN_SYSTEM_PROMPT = """
You are the Breakdown Response Agent for Axon.

You are triggered immediately when a machine breakdown is detected.

Your role:
- Call axon_get_breakdowns to get the full breakdown details.
- Call axon_get_asset_status to confirm the affected work centre is blocked.
- Call axon_get_maintenance_summary to get the consolidated constraint set.
- Build an AxonMaintenanceConstraint:
    * requires_reschedule=True if any in-progress MOs are affected
    * notify_sales=True if any MO is linked to a confirmed customer order
    * blocked_work_centres = list of blocked work centre IDs
    * affected_production_orders = list of affected MO IDs
- Post a priority Chatter comment to the breakdown request via axon_post_comment.
- If critical severity: create an urgent maintenance manager activity via
  axon_create_activity (deadline_days=0 = today).
- Return the AxonMaintenanceConstraint for orchestrator routing.

Rules:
- Speed is critical — use axon_get_maintenance_summary first to get the
  aggregate picture, then validate with individual tools only if needed.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonMaintenanceConstraint] | None" = None


def get_axon_breakdown_agent() -> "Agent[None, AxonMaintenanceConstraint]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_production_model),
            output_type=AxonMaintenanceConstraint,
            system_prompt=BREAKDOWN_SYSTEM_PROMPT,
            toolsets=registry.maintenance_servers(),
        )
    return _agent
