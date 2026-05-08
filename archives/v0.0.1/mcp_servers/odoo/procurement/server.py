"""
mcp-ascp-procurement — Axon FastMCP server for Procurement (SSE transport).

This MCP server exposes Odoo procurement data to the Axon reasoning layer.
Swap or extend with adapters for other ERPs (SAP, Oracle) without changing agents.

Tools:
  axon_get_rfq_list         — list draft/sent purchase orders
  axon_create_rfq           — create a new RFQ with lines (auto-chatter)
  axon_confirm_po           — confirm a PO (auto-chatter)
  axon_get_vendor_lead_time — get supplier lead times for a product
  axon_analyse_rfq_impact   — impact analysis: cost/time delta vs. Odoo baseline
  axon_post_comment         — post AI reasoning to any record's Chatter
  axon_create_activity      — create a mail.activity for human approval (HITL)
  axon_check_activity_done  — poll whether a mail.activity has been completed
"""

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.skills.communication_skills import AxonCommunicationSkills
from core.skills.impact_analysis_skill import AxonImpactAnalysisSkill
from core.skills.procurement_skills import AxonProcurementSkills

mcp = FastMCP("axon-procurement")

_procurement = AxonProcurementSkills()
_impact = AxonImpactAnalysisSkill()
_comms = AxonCommunicationSkills()


# ── Input models ──────────────────────────────────────────────────────────────

class GetRfqListInput(BaseModel):
    partner_id: int | None = Field(None, description="Filter by vendor res.partner ID")
    state_filter: list[str] | None = Field(
        None, description="PO states to include, e.g. ['draft','sent']"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class ProposedLineInput(BaseModel):
    product_id: int = Field(description="product.product ID")
    product_qty: float = Field(description="Quantity to purchase")
    price_unit: float = Field(description="Proposed unit price")
    date_planned: str | None = Field(None, description="Expected delivery date (ISO)")
    lead_days: int | None = Field(None, description="Vendor lead time in days (for impact analysis)")


class CreateRfqInput(BaseModel):
    partner_id: int = Field(description="Vendor res.partner ID")
    lines: list[ProposedLineInput] = Field(description="Purchase order lines")
    ai_context: str = Field(description="Reason why the agent is creating this RFQ")
    cycle_id: str | None = Field(None, description="Planning cycle reference")
    notes: str | None = Field(None, description="Internal notes on the PO")


class ConfirmPoInput(BaseModel):
    po_id: int = Field(description="purchase.order ID to confirm")
    ai_context: str = Field(description="Reason why the agent is confirming this PO")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetVendorLeadTimeInput(BaseModel):
    product_id: int = Field(description="product.product ID to query supplier info for")
    limit: int = Field(10, description="Maximum vendor records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class AnalyseRfqImpactInput(BaseModel):
    partner_id: int = Field(description="Vendor res.partner ID")
    proposed_lines: list[ProposedLineInput] = Field(
        description="Proposed purchase lines with price_unit and lead_days"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class AnalysePoForApprovalInput(BaseModel):
    po_id: int = Field(description="purchase.order ID already in Odoo to re-analyse")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class PostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name, e.g. purchase.order")
    record_id: int = Field(description="Record ID to post the Chatter note on")
    action_taken: str = Field(description="What the AI did")
    ai_context: str = Field(description="Full reasoning behind the action")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name")
    record_id: int = Field(description="Record to attach the activity to")
    summary: str = Field(description="Activity title shown to the user")
    note: str = Field(description="Full reasoning for the human to read")
    deadline: str = Field(description="ISO date deadline for human response")
    ai_context: str = Field(description="Why the AI is requesting this approval")


class CheckActivityDoneInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is polling this activity")


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_rfq_list(input: GetRfqListInput) -> list[dict]:
    """List draft/sent purchase orders (RFQs) — read-only."""
    return _procurement.get_rfq_list(
        partner_id=input.partner_id,
        state_filter=input.state_filter,
        limit=input.limit,
    )


@mcp.tool()
def axon_create_rfq(input: CreateRfqInput) -> dict:
    """Create a new RFQ with purchase lines.  Chatter auto-posted."""
    lines = [line.model_dump(exclude_none=True) for line in input.lines]
    return _procurement.create_rfq(
        partner_id=input.partner_id,
        lines=lines,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
        notes=input.notes,
    )


@mcp.tool()
def axon_confirm_po(input: ConfirmPoInput) -> dict:
    """Confirm a purchase order (RFQ → PO).  Chatter auto-posted."""
    return _procurement.confirm_po(
        po_id=input.po_id,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def axon_get_vendor_lead_time(input: GetVendorLeadTimeInput) -> list[dict]:
    """Return vendor price and lead-time from product.supplierinfo — read-only."""
    return _procurement.get_vendor_lead_time(
        product_id=input.product_id,
        limit=input.limit,
    )


@mcp.tool()
def axon_analyse_rfq_impact(input: AnalyseRfqImpactInput) -> list[dict]:
    """
    Compare proposed RFQ lines against Odoo baseline (product.supplierinfo).

    Returns per-line ImpactResult dicts plus a ``_summary`` aggregate.
    Classification thresholds:
      - price > 10%  OR  lead > 14 days  → 'critical'  (hitl_required=True)
      - price > 5%   OR  lead > 7 days   → 'warning'
      - otherwise                         → 'acceptable'
    Read-only — no Odoo writes.
    """
    lines = [line.model_dump(exclude_none=True) for line in input.proposed_lines]
    return _impact.analyse_rfq_lines(
        partner_id=input.partner_id,
        proposed_lines=lines,
    )


@mcp.tool()
def axon_analyse_po_for_approval(input: AnalysePoForApprovalInput) -> dict:
    """Re-analyse an existing PO in Odoo against baseline — for Director pre-approval check."""
    return _impact.analyse_po_for_approval(po_id=input.po_id)


@mcp.tool()
def axon_post_comment(input: PostCommentInput) -> dict:
    """Post AI reasoning as a Chatter note on any Odoo record."""
    return _comms.post_ai_reasoning(
        model=input.model,
        record_id=input.record_id,
        action_taken=input.action_taken,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def axon_create_activity(input: CreateActivityInput) -> dict:
    """Create a mail.activity on a record to request human approval (HITL gate)."""
    return _comms.create_activity(
        model=input.model,
        record_id=input.record_id,
        summary=input.summary,
        note=input.note,
        deadline=input.deadline,
    )


@mcp.tool()
def axon_check_activity_done(input: CheckActivityDoneInput) -> dict:
    """Poll whether a mail.activity has been completed by a human."""
    return _comms.check_activity_done(activity_id=input.activity_id)


if __name__ == "__main__":
    from core.config import settings

    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=settings.mcp_procurement_port,
    )
