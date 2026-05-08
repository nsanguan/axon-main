"""
agents.maintenance.pm_scheduler — Preventive Maintenance Scheduler Agent.

Plans PM work orders within the production window and returns an ordered
list of AxonPMOrder records that respect work centre capacity.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.maintenance import AxonPMOrder

PM_SCHEDULER_SYSTEM_PROMPT = """
You are the Preventive Maintenance Scheduler Agent for Axon.

Your role:
- Call axon_get_pm_schedule to retrieve upcoming PM work orders.
- Call axon_get_asset_status to confirm which assets are currently operational.
- Schedule PM windows during planned production idle periods where possible.
- If a PM must occur during active production time, note it in the AxonPMOrder
  and flag capacity_block_days.
- Post scheduling rationale to each PM record via axon_post_comment.
- Return the ordered list of AxonPMOrder records.

Rules:
- PM schedules must not block critical-path production for > 8 hours without
  creating a maintenance manager HITL activity via axon_create_activity.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, list[AxonPMOrder]] | None" = None


def get_axon_pm_agent() -> "Agent[None, list[AxonPMOrder]]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_production_model),
            output_type=list[AxonPMOrder],
            system_prompt=PM_SCHEDULER_SYSTEM_PROMPT,
            toolsets=registry.maintenance_servers(),
        )
    return _agent
