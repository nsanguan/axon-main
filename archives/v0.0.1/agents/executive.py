"""
agents.executive — Executive Agent.

Serves two roles in the Axon ASCP workflow:

1. **Entry Point** (``get_axon_executive_entry_agent``):
   Called at the start of every planning cycle to interpret the user's
   strategy & policy and produce an ``AxonExecutiveDirective`` that guides
   the Planning Manager and Purchase Cluster.

2. **Escalation Authority** (``get_axon_executive_agent``):
   Called when the Planning Manager's confidence < 0.7 or an unresolvable
   exception occurs.  Returns an ``AxonExecutiveSummary`` with a corrective
   recommendation.

Both agents are ERP-agnostic — they connect to all enabled MCP servers via
``AxonAdapterRegistry``, so adding a new ERP (SAP, NetSuite, …) requires no
change here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model


# ── Output models ────────────────────────────────────────────────────────────

class AxonExecutiveDirective(BaseModel):
    """
    Produced at cycle start: the Executive's interpretation of the user's
    strategy.  The Planning Manager and Supervisor read this to prioritise
    allocations and set thresholds.
    """

    cycle_objective: str = Field(
        description=(
            "Primary goal for this planning cycle: "
            "'maximise_service_level' | 'minimise_cost' | 'balance' | 'custom'"
        )
    )
    priority_products: list[int] = Field(
        default_factory=list,
        description="Product IDs that must be allocated first (strategic items)",
    )
    cost_tolerance_pct: float = Field(
        default=10.0,
        description=(
            "Maximum acceptable cost increase % before HITL is required. "
            "Overrides the Manager Agent's default 10 % threshold."
        ),
    )
    lead_tolerance_days: int = Field(
        default=14,
        description=(
            "Maximum acceptable extra lead days before HITL is required. "
            "Overrides the Manager Agent's default 14-day threshold."
        ),
    )
    notes: str = Field(
        default="",
        description="Free-text executive notes propagated into the audit trail",
    )
    confidence: float = Field(
        default=1.0,
        description="Executive's confidence in the directive (0.0–1.0)",
    )


class AxonExecutiveSummary(BaseModel):
    """Produced on escalation: corrective recommendation after low-confidence planning."""

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


# ── System prompts ────────────────────────────────────────────────────────────

EXECUTIVE_ENTRY_SYSTEM_PROMPT = """
You are the Executive Agent for Axon — the strategic entry point for every
AI-Native Supply Chain Planning cycle.

You receive the user's strategy & policy statement and the current context
(cycle ID, open shortages, pending activities) from the planning MCP server.
Produce an AxonExecutiveDirective that guides the Planning Manager and Purchase
Cluster for this cycle.

Guidelines:
- Use axon_get_ledger and axon_check_shortage to understand the current state.
- Translate the user's business objective into concrete thresholds
  (cost_tolerance_pct, lead_tolerance_days).
- Identify priority_products from the user's policy (e.g. strategic SKUs,
  shortage alerts, customer commitments).
- Set cycle_objective to one of: 'maximise_service_level', 'minimise_cost',
  'balance', or 'custom' (with explanation in notes).
- Be concise — the Planning Manager will act on your directive immediately.
"""

EXECUTIVE_ESCALATION_SYSTEM_PROMPT = """
You are the Executive Agent for Axon — the final escalation authority in the
AI-Native Supply Chain Planning Engine.

You are invoked when the Planning Manager's confidence is below 0.7 or when
an unresolvable exception occurs.  Use all available MCP tools to gather
context, then return an AxonExecutiveSummary with a clear recommendation.

When human approval is required, call axon_create_activity with
activity_type_xmlid='mail.mail_activity_data_warning'.
"""


# ── Agent factories (lazy singletons) ────────────────────────────────────────

_executive_entry_agent: "Agent[None, AxonExecutiveDirective] | None" = None
_executive_agent: "Agent[None, AxonExecutiveSummary] | None" = None


def get_axon_executive_entry_agent() -> "Agent[None, AxonExecutiveDirective]":
    """Entry-point Executive Agent — interprets user strategy at cycle start."""
    global _executive_entry_agent
    if _executive_entry_agent is None:
        registry = AxonAdapterRegistry()
        _executive_entry_agent = Agent(
            build_model(settings.llm_executive_model),
            output_type=AxonExecutiveDirective,
            system_prompt=EXECUTIVE_ENTRY_SYSTEM_PROMPT,
            toolsets=registry.all_servers(),
        )
    return _executive_entry_agent


def get_axon_executive_agent() -> "Agent[None, AxonExecutiveSummary]":
    """Escalation Executive Agent — handles low-confidence or exception cases."""
    global _executive_agent
    if _executive_agent is None:
        registry = AxonAdapterRegistry()
        _executive_agent = Agent(
            build_model(settings.llm_executive_model),
            output_type=AxonExecutiveSummary,
            system_prompt=EXECUTIVE_ESCALATION_SYSTEM_PROMPT,
            toolsets=registry.all_servers(),
        )
    return _executive_agent
