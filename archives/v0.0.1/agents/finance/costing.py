"""
agents.finance.costing — Supply Chain Costing Agent.

Tracks cost impact of procurement and production decisions within a planning
cycle. Produces an AxonCostRecord summarising actual vs standard cost
for the cycle.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.finance import AxonCostRecord

COSTING_SYSTEM_PROMPT = """
You are the Supply Chain Costing Agent for Axon.

Your role:
- Call axon_get_cost_records for the current planning cycle.
- Call axon_get_product_cost for each product in the cycle to compare
  actual vs standard costs.
- Identify cost overruns (actual > standard by > 10 %).
- Post a Chatter summary to each overrunning PO or MO via axon_post_comment.
- Return a consolidated AxonCostRecord for the cycle.

Rules:
- Cost data is read-only — do NOT post journal entries.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonCostRecord] | None" = None


def get_axon_costing_agent() -> "Agent[None, AxonCostRecord]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_finance_model),
            output_type=AxonCostRecord,
            system_prompt=COSTING_SYSTEM_PROMPT,
            toolsets=registry.finance_servers(),
        )
    return _agent
