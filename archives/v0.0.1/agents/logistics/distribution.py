"""
agents.logistics.distribution — Distribution Planning Agent.

Plans and validates outbound shipments against ATP commitments, carrier
availability, and route capacity. Produces a list of AxonShipment records
ready to be committed to the ERP (or escalated for HITL if constraints exist).

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.logistics import AxonShipment

DISTRIBUTION_SYSTEM_PROMPT = """
You are the Distribution Planning Agent for Axon — the AI-Native Supply Chain Engine.

Your role:
- Call axon_get_pending_shipments to fetch open delivery orders.
- Call axon_get_delivery_routes to retrieve available routes.
- Call axon_check_carrier_availability to confirm carrier capacity.
- Call axon_plan_shipment for each confirmed delivery order.
- Return the list of planned AxonShipment records.

Constraints:
- Never plan a shipment where ATP has not been confirmed (atp_confirmed must be True).
- If a carrier is unavailable, post a comment via axon_post_comment and
  create an activity via axon_create_activity for the logistics manager.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, list[AxonShipment]] | None" = None


def get_axon_distribution_agent() -> "Agent[None, list[AxonShipment]]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_logistics_model),
            output_type=list[AxonShipment],
            system_prompt=DISTRIBUTION_SYSTEM_PROMPT,
            toolsets=registry.logistics_servers(),
        )
    return _agent
