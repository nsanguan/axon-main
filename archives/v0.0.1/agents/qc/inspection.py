"""
agents.qc.inspection — QC Inspection & NG Response Agent.

Reads quality inspection results, identifies NG (non-conforming) items,
locks the affected stock, and creates rework or scrap demand in the ERP.

The rework demand is injected back into the planning stream via the Planning
Agent in the next cycle.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.quality import AxonNGItem

QC_SYSTEM_PROMPT = """
You are the QC Inspection Agent for Axon.

Your role:
- Call axon_get_ng_items to find all unresolved NG items.
- For each NG item:
    1. Call axon_lock_stock on the affected stock.quant to quarantine the stock.
    2. Determine the rework_type based on ng_severity:
        - 'minor'    → 'rework'
        - 'major'    → 'rework' or 'return_to_vendor' (based on item origin)
        - 'critical' → 'scrap' or 'return_to_vendor'
    3. Call axon_create_rework_order to inject the corrective demand.
    4. Post Chatter note to the quality check record via axon_post_comment.
    5. If critical severity: create a QC manager activity via axon_create_activity.
- Return the list of AxonNGItem records (now with stock_locked=True and
  rework_order_id populated).

Rules:
- Never release NG stock back to saleable locations without human review.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, list[AxonNGItem]] | None" = None


def get_axon_qc_agent() -> "Agent[None, list[AxonNGItem]]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_quality_model),
            output_type=list[AxonNGItem],
            system_prompt=QC_SYSTEM_PROMPT,
            toolsets=registry.qc_servers(),
        )
    return _agent
