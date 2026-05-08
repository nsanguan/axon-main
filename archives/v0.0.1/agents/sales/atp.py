"""
agents.sales.atp — Available-To-Promise (ATP) Agent.

Evaluates whether confirmed sales orders can be fulfilled on time given
current inventory, planned production, and logistics capacity.
Returns an AxonATP decision that the Logistics Agent uses for shipment planning.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.logistics import AxonATP

ATP_SYSTEM_PROMPT = """
You are the ATP (Available-To-Promise) Agent for Axon.

Your role:
- Call axon_get_confirmed_orders to fetch demand lines needing ATP confirmation.
- Call axon_atp_check for each order line to determine if it can be fulfilled.
- Build an AxonATP result with a per-line AxonATPResult list.
- For any line that cannot be fully fulfilled, set partial_qty and promised_date
  to the best available date (when planned production / PO will complete).
- If overall_fulfillable=False, post a comment on the affected sales order
  via axon_post_comment explaining the shortfall.

Rules:
- Do NOT promise dates you cannot confirm from MCP data.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonATP] | None" = None


def get_axon_atp_agent() -> "Agent[None, AxonATP]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_sales_model),
            output_type=AxonATP,
            system_prompt=ATP_SYSTEM_PROMPT,
            toolsets=registry.sales_servers(),
        )
    return _agent
