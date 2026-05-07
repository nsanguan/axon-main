"""
ExecutiveAgent — handles low-confidence escalations and unresolvable exceptions.

Phase 3 implementation: connected to all three MCP servers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from core.config import settings
from core.model_factory import build_model


class ExecutiveSummary(BaseModel):
    recommended_action: str = Field(
        description="'approve_plan' | 'override' | 'escalate_to_human' | 'defer'"
    )
    rationale: str = Field(description="Full reasoning from the Executive Agent")
    override_updates: list[dict] = Field(
        default_factory=list,
        description="If action='override': pegging updates to apply",
    )
    hitl_activity_ids: list[int] = Field(default_factory=list)
    confidence: float = Field(description="Executive's confidence in the recommendation")


EXECUTIVE_SYSTEM_PROMPT = """
You are the Executive Agent for EraOwl ASCP — the final escalation authority.

You are invoked when the Planning Manager's confidence is below 0.7 or when
an unresolvable exception occurs.  Use all available MCP tools to gather
context, then return an ExecutiveSummary with a clear recommendation.

When human approval is required, call ascp_create_activity with
activity_type_xmlid='mail.mail_activity_data_warning'.
"""

_executive_agent: "Agent[None, ExecutiveSummary] | None" = None


def get_executive_agent() -> "Agent[None, ExecutiveSummary]":
    global _executive_agent
    if _executive_agent is None:
        mcp_planning = MCPServerSSE(
            f"http://localhost:{settings.mcp_planning_port}/sse"
        )
        mcp_procurement = MCPServerSSE(
            f"http://localhost:{settings.mcp_procurement_port}/sse"
        )
        mcp_inventory = MCPServerSSE(
            f"http://localhost:{settings.mcp_inventory_port}/sse"
        )
        _executive_agent = Agent(
            build_model(settings.llm_executive_model),
            output_type=ExecutiveSummary,
            system_prompt=EXECUTIVE_SYSTEM_PROMPT,
            toolsets=[mcp_planning, mcp_procurement, mcp_inventory],
        )
    return _executive_agent
