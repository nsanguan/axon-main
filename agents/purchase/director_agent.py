"""
PurchaseDirectorAgent — final procurement decision authority.

Responsibilities:
  1. Receive ManagerAnalysis with line-level impact classifications.
  2. For lines classified 'acceptable' → call ascp_confirm_po immediately.
  3. For lines classified 'warning'    → confirm if within policy; otherwise HITL.
  4. For lines classified 'critical'   → ALWAYS call ascp_create_activity to create
     a Human Director approval task in Odoo before confirming the PO.
  5. Post the final decision summary to each PO's Chatter via ascp_post_comment.
  6. Return DirectorDecision with full audit trail.

HITL rule (non-negotiable):
  If the ManagerAnalysis.hitl_required is True, the Director MUST call
  ascp_create_activity with:
    - activity_type_xmlid = "mail.mail_activity_data_warning"
    - summary  = "Director approval required: price impact > 10 %"
    - deadline = today + 2 business days
  and must NOT call ascp_confirm_po until the activity is resolved.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from core.config import settings
from core.model_factory import build_model


# ── Output model ────────────────────────────────────────────────────────────

class DirectorDecision(BaseModel):
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
You are the Purchase Director Agent for EraOwl ASCP — the final decision authority
for procurement actions.

Decision rules (strictly follow these):
1. If ManagerAnalysis.hitl_required is True:
   - Call ascp_create_activity on the PO record with:
       model        = "purchase.order"
       summary      = "Director approval required: price impact > 10%"
       note         = (include price_delta_pct, cost_delta, vendor name)
       deadline     = today + 2 days (ISO format YYYY-MM-DD)
       ai_context   = your full reasoning
   - Add the activity_id to hitl_activity_ids.
   - Do NOT call ascp_confirm_po — set action = 'hitl_pending'.

2. If all lines are 'acceptable':
   - Call ascp_confirm_po for each PO.
   - Set action = 'confirmed'.

3. If mixed (some 'warning', no 'critical'):
   - Call ascp_confirm_po for acceptable lines.
   - Post a warning comment on warning-line POs via ascp_post_comment.
   - Use your judgment: if policy allows, confirm with note; otherwise HITL.
   - Set action = 'partial_confirm' or 'hitl_pending' as appropriate.

4. Always call ascp_post_comment after each confirmation or HITL creation to
   record your reasoning in the Odoo Chatter.

5. Include your full reasoning in director_reasoning.  This will be stored in
   ASCPState.purchase_analysis_logs for auditability.
"""

_director_agent: "Agent[None, DirectorDecision] | None" = None


def get_purchase_director_agent() -> "Agent[None, DirectorDecision]":
    global _director_agent
    if _director_agent is None:
        mcp_procurement = MCPServerSSE(
            f"http://localhost:{settings.mcp_procurement_port}/sse"
        )
        _director_agent = Agent(
            build_model(settings.llm_executive_model),
            output_type=DirectorDecision,
            system_prompt=DIRECTOR_SYSTEM_PROMPT,
            toolsets=[mcp_procurement],
        )
    return _director_agent
