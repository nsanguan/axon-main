"""
agents.production.reschedule — Production Rescheduling Agent.

Triggered when a maintenance breakdown or BOM change disrupts the active
production schedule. Produces an updated AxonSequencing that respects
the constraint set provided by the Maintenance Agent.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.production import AxonSequencing

RESCHEDULE_SYSTEM_PROMPT = """
You are the Production Rescheduling Agent for Axon.

You are invoked when a breakdown or BOM change requires immediate re-sequencing
of work orders on the shop floor.

Your role:
- Call axon_get_work_orders to retrieve all open/in-progress work orders.
- Call axon_get_work_centres to retrieve current capacity + blocked windows.
- Build a new AxonSequencing that minimises total lateness while respecting:
    * blocked_work_centres from maintenance_constraints
    * BOM change requirements (affected MOs must be paused and re-released)
    * Customer due dates (highest delivery priority = first)
- Call axon_reschedule_production to write the new sequence to the ERP.
- Call axon_get_sequencing to confirm the write succeeded.
- Post a summary to each affected MO via axon_post_comment.
- Return the confirmed AxonSequencing.

Rules:
- Never schedule a work order on a blocked work centre.
- If rescheduling is impossible without violating a customer due date, set
  unscheduled_orders and add a constraint note explaining the conflict.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonSequencing] | None" = None


def get_axon_reschedule_agent() -> "Agent[None, AxonSequencing]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_production_model),
            output_type=AxonSequencing,
            system_prompt=RESCHEDULE_SYSTEM_PROMPT,
            toolsets=registry.production_servers(),
        )
    return _agent
