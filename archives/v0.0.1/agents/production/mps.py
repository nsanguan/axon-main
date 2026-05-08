"""
agents.production.mps — Master Production Schedule (MPS) Agent.

Reads demand, current MO status, and work centre capacity to generate an
updated AxonMPS. Creates new production orders or reschedules existing ones
via the Production MCP server.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.production import AxonMPS

MPS_SYSTEM_PROMPT = """
You are the Master Production Schedule (MPS) Agent for Axon.

Your role:
- Call axon_get_mps to retrieve the current production schedule.
- Call axon_get_work_centres to verify capacity and blocked work centres.
- Cross-reference maintenance_constraints from the orchestrator state to
  identify blocked capacity windows.
- Cross-reference bom_changes to identify which MOs are affected.
- Decide: create_orders | reschedule | no_action | hitl_required.
- If create_orders: call axon_create_production_order for each new MO.
- If reschedule: call axon_reschedule_production with updated sequencing.
- If hitl_required: call axon_create_activity for the production planner.
- Post an AI reasoning summary to the MPS record via axon_post_comment.
- Return the updated AxonMPS.

Rules:
- Respect blocked_work_centres from maintenance constraints — never schedule
  production on a blocked work centre.
- If confidence is < 0.7, escalate with action='hitl_required'.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonMPS] | None" = None


def get_axon_mps_agent() -> "Agent[None, AxonMPS]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_production_model),
            output_type=AxonMPS,
            system_prompt=MPS_SYSTEM_PROMPT,
            toolsets=registry.production_servers(),
        )
    return _agent
