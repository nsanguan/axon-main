"""
agents.pd.bom_impact — BOM Impact Analysis Agent.

Detects Bill of Materials changes since the last planning cycle and evaluates
their impact on active production orders. Triggers re-planning if required.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.production import AxonBOMChange

BOM_IMPACT_SYSTEM_PROMPT = """
You are the BOM Impact Analysis Agent for Axon — the Product Development interface.

Your role:
- Call axon_get_bom_changes to detect any BOM changes since the last cycle.
- For each change, call axon_get_bom to read the updated BOM structure.
- Identify which active production orders (affected_mo_ids) are impacted.
- Determine whether requires_replan=True (i.e. component substitution, yield
  change, or routing step modification that affects capacity).
- If requires_replan=True, call axon_notify_bom_updated to:
    * Record the change in the ERP
    * Post Chatter note to all affected MOs
- Return the AxonBOMChange with the full impact assessment.

Rules:
- If no BOM changes exist, return an AxonBOMChange with requires_replan=False
  and an empty affected_mo_ids list.
- Never modify BOM records directly — PD Engineers own BOM edits.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonBOMChange] | None" = None


def get_axon_bom_impact_agent() -> "Agent[None, AxonBOMChange]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_production_model),
            output_type=AxonBOMChange,
            system_prompt=BOM_IMPACT_SYSTEM_PROMPT,
            toolsets=registry.pd_servers(),
        )
    return _agent
