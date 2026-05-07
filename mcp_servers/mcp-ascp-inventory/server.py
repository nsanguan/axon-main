"""
mcp-ascp-inventory — FastMCP server (SSE transport).

Tools:
  ascp_get_stock_quant      — query on-hand stock (stock.quant, read-only)
  ascp_get_incoming_moves   — incoming stock moves by date/product (read-only)
  ascp_get_outgoing_demand  — outgoing stock moves vs demand (read-only)
  ascp_reserve_stock        — call action_assign on a picking (auto-chatter)
  ascp_post_comment         — post AI reasoning to any record's Chatter
  ascp_create_activity      — create mail.activity for human approval (HITL)
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from core.skills.communication_skills import CommunicationSkills
from core.skills.inventory_skills import InventorySkills

mcp = FastMCP("mcp-ascp-inventory")

_inventory = InventorySkills()
_comms = CommunicationSkills()


# ── Input models ──────────────────────────────────────────────────────────────

class GetStockQuantInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    location_id: int | None = Field(
        None, description="Filter by specific stock.location ID"
    )
    limit: int = Field(80, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetIncomingMovesInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    date_from: str | None = Field(
        None, description="Filter: move date >= this ISO datetime"
    )
    date_to: str | None = Field(
        None, description="Filter: move date <= this ISO datetime"
    )
    limit: int = Field(80, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetOutgoingDemandInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    date_from: str | None = Field(
        None, description="Filter: move date >= this ISO datetime"
    )
    date_to: str | None = Field(
        None, description="Filter: move date <= this ISO datetime"
    )
    limit: int = Field(80, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class ReserveStockInput(BaseModel):
    picking_id: int = Field(description="stock.picking ID to reserve stock for")
    ai_context: str = Field(
        description="Reason why the agent is reserving stock for this picking"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class PostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name, e.g. stock.picking")
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


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def ascp_get_stock_quant(input: GetStockQuantInput) -> list[dict]:
    """
    Query on-hand stock quantities from stock.quant.
    Returns available_quantity per product/location — read-only.
    """
    return _inventory.get_stock_quant(
        product_id=input.product_id,
        location_id=input.location_id,
        limit=input.limit,
    )


@mcp.tool()
def ascp_get_incoming_moves(input: GetIncomingMovesInput) -> list[dict]:
    """
    List incoming stock moves (confirmed/assigned) arriving at internal locations.
    Useful for calculating projected available stock — read-only.
    """
    return _inventory.get_incoming_moves(
        product_id=input.product_id,
        date_from=input.date_from,
        date_to=input.date_to,
        limit=input.limit,
    )


@mcp.tool()
def ascp_get_outgoing_demand(input: GetOutgoingDemandInput) -> list[dict]:
    """
    List outgoing stock moves (confirmed/assigned) leaving internal locations.
    Useful for comparing committed demand against available stock — read-only.
    """
    return _inventory.get_outgoing_demand(
        product_id=input.product_id,
        date_from=input.date_from,
        date_to=input.date_to,
        limit=input.limit,
    )


@mcp.tool()
def ascp_reserve_stock(input: ReserveStockInput) -> dict:
    """
    Reserve stock for a delivery order by calling action_assign on stock.picking.
    Chatter note auto-posted with AI reasoning after reservation.
    """
    return _inventory.reserve_stock(
        picking_id=input.picking_id,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def ascp_post_comment(input: PostCommentInput) -> dict:
    """Post AI reasoning as a Chatter note on any Odoo record."""
    return _comms.post_ai_reasoning(
        model=input.model,
        record_id=input.record_id,
        action_taken=input.action_taken,
        ai_context=input.ai_context,
        cycle_id=input.cycle_id,
    )


@mcp.tool()
def ascp_create_activity(input: CreateActivityInput) -> dict:
    """Create a mail.activity on a record to request human approval (HITL gate)."""
    return _comms.create_activity(
        model=input.model,
        record_id=input.record_id,
        summary=input.summary,
        note=input.note,
        deadline=input.deadline,
    )


if __name__ == "__main__":
    from core.config import settings

    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=settings.mcp_inventory_port,
    )
