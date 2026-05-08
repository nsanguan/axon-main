"""
mcp-ascp-planning — Axon FastMCP server for Planning (SSE transport).

This MCP server exposes Odoo ASCP planning data to the Axon reasoning layer.
Swap or extend with adapters for other ERPs (SAP, Oracle) without changing agents.

Tools:
  axon_get_ledger           — query era.ascp.pegging.ledger (read-only)
  axon_update_allocation    — write allocated_qty + status (auto-chatter)
  axon_create_exception     — set status=exception on a pegging record (auto-chatter)
  axon_check_shortage       — compare open demand vs on-hand stock
  axon_sync_demand_stream   — pull confirmed SOs → era.ascp.demand.stream (auto-chatter)
  axon_get_supply_stream    — query era.ascp.supply.stream (read-only)
  axon_post_comment         — post AI reasoning to any record's Chatter
  axon_create_activity      — create mail.activity for human approval (HITL)
  axon_check_activity_done  — poll whether a mail.activity has been completed
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.skills.communication_skills import AxonCommunicationSkills
from core.skills.planning_skills import AxonPlanningSkills

mcp = FastMCP("axon-planning")

_planning = AxonPlanningSkills()
_comms = AxonCommunicationSkills()


# ── Input models ──────────────────────────────────────────────────────────────

class GetLedgerInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    status_filter: list[str] | None = Field(
        None, description="Filter by status values, e.g. ['draft','firm','exception']"
    )
    demand_date_from: str | None = Field(
        None, description="Filter: demand_date >= this ISO date"
    )
    demand_date_to: str | None = Field(
        None, description="Filter: demand_date <= this ISO date"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class UpdateAllocationInput(BaseModel):
    pegging_id: int = Field(description="era.ascp.pegging.ledger record ID to update")
    allocated_qty: float = Field(description="New allocated quantity")
    status: str = Field(
        description="New status: 'draft' | 'firm' | 'released' | 'partial' | 'exception'"
    )
    ai_context: str = Field(description="Reason why the agent is making this change")
    cycle_id: str | None = Field(None, description="Planning cycle reference")
    confidence: float | None = Field(
        None, description="Agent confidence 0.0–1.0 (logged in Chatter)"
    )


class CreateExceptionInput(BaseModel):
    pegging_id: int = Field(description="era.ascp.pegging.ledger record ID")
    ai_context: str = Field(description="Full explanation of why this is an exception")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CheckShortageInput(BaseModel):
    product_ids: list[int] | None = Field(
        None, description="Limit check to these product.product IDs (None = all open demand)"
    )
    demand_date_from: str | None = Field(
        None, description="Only consider demand from this ISO date"
    )
    demand_date_to: str | None = Field(
        None, description="Only consider demand up to this ISO date"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class SyncDemandStreamInput(BaseModel):
    ai_context: str = Field(description="Reason why the agent is triggering a demand sync")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetSupplyStreamInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    supply_date_from: str | None = Field(
        None, description="Filter: supply_date >= this ISO date"
    )
    supply_date_to: str | None = Field(
        None, description="Filter: supply_date <= this ISO date"
    )
    limit: int = Field(80, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class PostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name, e.g. era.ascp.pegging.ledger")
    record_id: int = Field(description="Record ID to post the Chatter note on")
    action_taken: str = Field(description="What the AI did")
    ai_context: str = Field(description="Full reasoning behind the action")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name")
    record_id: int = Field(description="Record to attach the activity to")
    summary: str = Field(description="Activity title shown to the planner")
    note: str = Field(description="Full reasoning for the human to read")
    deadline: str = Field(description="ISO date deadline for human response")
    ai_context: str = Field(description="Why the AI is requesting this approval")


class CheckActivityDoneInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is polling this activity")


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_ledger(input: GetLedgerInput) -> list[dict]:
    """Query era.ascp.pegging.ledger — read-only, no Chatter post."""
    return _planning.get_ledger(
        product_id=input.product_id,
        status_filter=input.status_filter,
        demand_date_from=input.demand_date_from,
        demand_date_to=input.demand_date_to,
        limit=input.limit,
    )


@mcp.tool()
def axon_update_allocation(input: UpdateAllocationInput) -> dict:
    """
    Update allocated_qty and status on a pegging ledger record.
    Chatter note auto-posted with full change audit trail.
    """
    return _planning.update_allocation(
        pegging_id=input.pegging_id,
        allocated_qty=input.allocated_qty,
        status=input.status,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
        confidence=input.confidence,
    )


@mcp.tool()
def axon_create_exception(input: CreateExceptionInput) -> dict:
    """
    Flag a pegging ledger record as an exception.
    Sets status='exception' and posts Chatter note with AI reasoning.
    """
    return _planning.create_exception(
        pegging_id=input.pegging_id,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def axon_check_shortage(input: CheckShortageInput) -> list[dict]:
    """
    Compare open demand stream records against on-hand stock (stock.quant).
    Returns a list of shortage dicts for products where demand > available stock.
    Read-only — no Chatter post.
    """
    return _planning.check_shortage(
        product_ids=input.product_ids,
        demand_date_from=input.demand_date_from,
        demand_date_to=input.demand_date_to,
    )


@mcp.tool()
def axon_sync_demand_stream(input: SyncDemandStreamInput) -> dict:
    """
    Pull all confirmed sale.order lines from Odoo and upsert them into
    era.ascp.demand.stream.  Returns {created, updated, total_lines}.
    Write operation — Chatter posted on new/updated records via planning_skills.
    """
    return _planning.sync_demand_from_so(
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def axon_get_supply_stream(input: GetSupplyStreamInput) -> list[dict]:
    """Query era.ascp.supply.stream — read-only, no Chatter post."""
    return _planning.get_supply_stream(
        product_id=input.product_id,
        supply_date_from=input.supply_date_from,
        supply_date_to=input.supply_date_to,
        limit=input.limit,
    )


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
        port=settings.mcp_planning_port,
    )
