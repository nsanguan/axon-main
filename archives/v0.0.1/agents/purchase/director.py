"""
agents.purchase.director — Purchase Director Agent.

Final procurement decision authority. Confirms POs or creates HITL gates
for critical cost/time deviations. ERP-agnostic via MCP.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model


# ── Output model ────────────────────────────────────────────────────────────

class AxonDirectorDecision(BaseModel):
    action: str = Field(
        description=(
            "Final outcome: 'confirmed' | 'hitl_pending' | 'partial_confirm' | 'rejected'"
        )
    )
    confirmed_po_ids: list[int] = Field(
        default_factory=list,
        description="PO IDs that were confirmed by the Director",
    )
    hitl_activity_ids: list[int] = Field(
        default_factory=list,
        description="mail.activity IDs created for human Director approval",
    )
    pending_po_ids: list[int] = Field(
        default_factory=list,
        description="PO IDs awaiting human approval (HITL pending)",
    )
    rejected_po_ids: list[int] = Field(
        default_factory=list,
        description="PO IDs rejected by the Director",
    )
    summary: str = Field(description="Plain-language summary of the Director's decision")
    director_reasoning: str = Field(
        description="Full reasoning trail — stored in purchase_analysis_logs and posted to Chatter"
    )
    cycle_id: str | None = Field(None)


# ── Agent definition ─────────────────────────────────────────────────────────

DIRECTOR_SYSTEM_PROMPT = """
You are the Purchase Director Agent for Axon — the final decision authority
for procurement actions in the AI-Native Supply Chain Planning Engine.

Decision rules (strictly follow these):
1. If AxonManagerAnalysis.hitl_required is True:
   - Call axon_create_activity on the PO record with:
       model        = "purchase.order"
       summary      = "Director approval required: price impact > 10%"
       note         = (include price_delta_pct, cost_delta, vendor name)
       deadline     = today + 2 days (ISO format YYYY-MM-DD)
       ai_context   = your full reasoning
   - Add the activity_id to hitl_activity_ids.
   - Do NOT call axon_confirm_po — set action = 'hitl_pending'.

2. If all lines are 'acceptable':
   - Call axon_confirm_po for each PO.
   - Set action = 'confirmed'.

3. If mixed (some 'warning', no 'critical'):
   - Call axon_confirm_po for acceptable lines.
   - Post a warning comment on warning-line POs via axon_post_comment.
   - Use your judgment: if policy allows, confirm with note; otherwise HITL.
   - Set action = 'partial_confirm' or 'hitl_pending' as appropriate.

4. Always call axon_post_comment after each confirmation or HITL creation to
   record your reasoning in the Odoo Chatter.

5. Include your full reasoning in director_reasoning.  This will be stored in
   AxonState.purchase_analysis_logs for auditability.
"""

_director_agent: "Agent[None, AxonDirectorDecision] | None" = None


def get_axon_purchase_director_agent() -> "Agent[None, AxonDirectorDecision]":
    global _director_agent
    if _director_agent is None:
        registry = AxonAdapterRegistry()
        _director_agent = Agent(
            build_model(settings.llm_executive_model),
            output_type=AxonDirectorDecision,
            system_prompt=DIRECTOR_SYSTEM_PROMPT,
            toolsets=registry.procurement_servers(),
        )
    return _director_agent
