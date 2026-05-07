"""
PurchaseManagerAgent — analyses cost/time impact of the Buyer's proposals.

Responsibilities:
  1. Receive BuyerDecision (proposed_lines with price_unit, lead_days).
  2. Call ascp_analyse_rfq_impact to compare each line against Odoo baseline.
  3. Interpret the ImpactResult list:
       - 'acceptable' → recommend confirming
       - 'warning'    → flag for Director review with justification
       - 'critical'   → flag for HITL via ascp_create_activity
  4. Post analysis summary to Chatter via ascp_post_comment on each PO.
  5. Return ManagerAnalysis with classification and routing recommendation.

The Manager does NOT create or confirm any Odoo records — it is purely
a reasoning + analysis agent.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from core.config import settings
from core.model_factory import build_model


# ── Output model ────────────────────────────────────────────────────────────

class LineAnalysis(BaseModel):
    """Impact analysis result for a single proposed purchase line."""
    product_id: int
    product_name: str
    rfq_id: int | None = None
    price_delta_pct: float = Field(description="% change vs. baseline price (positive = costlier)")
    lead_delta_days: int = Field(description="Extra lead days vs. baseline")
    cost_delta: float = Field(description="Absolute cost delta (currency)")
    classification: str = Field(description="'acceptable' | 'warning' | 'critical'")
    breach_reasons: list[str] = Field(default_factory=list)
    manager_note: str = Field(description="Manager's own commentary on this line")


class ManagerAnalysis(BaseModel):
    overall_classification: str = Field(
        description="'acceptable' | 'warning' | 'critical' — worst across all lines"
    )
    total_cost_delta: float = Field(description="Sum of all cost deltas")
    overall_price_delta_pct: float = Field(description="Blended price change %")
    line_analyses: list[LineAnalysis] = Field(default_factory=list)
    recommendation: str = Field(
        description=(
            "Director action recommendation: "
            "'confirm_all' | 'confirm_acceptable_only' | 'require_hitl' | 'reject_all'"
        )
    )
    hitl_required: bool = Field(
        description="True if any line is 'critical' (Director must trigger HITL)"
    )
    summary: str = Field(description="Plain-language manager summary for the Director")
    cycle_id: str | None = Field(None)
    purchase_analysis_log: str = Field(
        description=(
            "Formatted log entry to be stored in ASCPState.purchase_analysis_logs "
            "and posted to Chatter by the workflow node"
        )
    )


# ── Agent definition ─────────────────────────────────────────────────────────

MANAGER_SYSTEM_PROMPT = """
You are the Purchase Manager Agent for EraOwl ASCP.

Your role:
- You receive the Buyer's proposed purchase lines (from BuyerDecision).
- For each group of lines belonging to the same RFQ, call ascp_analyse_rfq_impact
  to get a structured ImpactResult list from Odoo baseline data.
- Interpret each ImpactResult:
    - price_delta_pct > 10 %  OR  lead_delta_days > 14  → classification = 'critical' → hitl_required = True
    - price_delta_pct > 5 %   OR  lead_delta_days > 7   → classification = 'warning'
    - otherwise                                          → classification = 'acceptable'
- Post your analysis summary to each RFQ's Chatter using ascp_post_comment.
  Always include price_delta_pct, cost_delta, and classification in the comment.
- Set recommendation:
    - All lines acceptable   → 'confirm_all'
    - Mixed acceptable/warn  → 'confirm_acceptable_only'
    - Any critical line      → 'require_hitl'
    - Analysis error / zero  → 'reject_all'
- Always include your full reasoning chain in purchase_analysis_log so the
  Director and humans can audit the decision trail.

You do NOT create or confirm Odoo records.  Only analyse and post comments.
"""

_manager_agent: "Agent[None, ManagerAnalysis] | None" = None


def get_purchase_manager_agent() -> "Agent[None, ManagerAnalysis]":
    global _manager_agent
    if _manager_agent is None:
        mcp_procurement = MCPServerSSE(
            f"http://localhost:{settings.mcp_procurement_port}/sse"
        )
        _manager_agent = Agent(
            build_model(settings.llm_buyer_model),
            output_type=ManagerAnalysis,
            system_prompt=MANAGER_SYSTEM_PROMPT,
            toolsets=[mcp_procurement],
        )
    return _manager_agent


# Legacy name kept for import compat
purchase_manager_agent = property(lambda self: get_purchase_manager_agent())
