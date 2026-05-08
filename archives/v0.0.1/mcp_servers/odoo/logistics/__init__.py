"""
mcp_servers.odoo.logistics — Axon FastMCP server for Logistics & Distribution (SSE transport).

Exposes delivery route planning, shipment management, and carrier availability
to the Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  stock.picking, delivery.carrier, stock.picking.type, res.partner

Tools:
  axon_get_delivery_routes        — list active delivery routes
  axon_plan_shipment              — create or update a delivery shipment
  axon_check_carrier_availability — check if a carrier can deliver by a date
  axon_get_atp_by_date            — ATP check via logistics view (with transit time)
  axon_get_pending_shipments      — list shipments pending dispatch
  axon_post_comment               — post AI reasoning to Chatter
  axon_create_activity            — create HITL mail.activity
  axon_check_activity_done        — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-logistics",
    instructions=(
        "Logistics & Distribution adapter for Axon. "
        "Tools expose delivery routes, shipment planning, and ATP-with-transit-time "
        "data from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetDeliveryRoutesInput(BaseModel):
    origin_location: str | None = Field(
        None, description="Filter by origin warehouse/location name"
    )
    destination_zone: str | None = Field(
        None, description="Filter by destination zone or country"
    )
    active_only: bool = Field(True, description="Only return active routes")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class PlanShipmentInput(BaseModel):
    sale_order_id: int = Field(
        description="sale.order ID this shipment fulfils"
    )
    carrier_id: int | None = Field(
        None, description="delivery.carrier ID (auto-select if None)"
    )
    scheduled_date: str = Field(
        description="Planned dispatch date (ISO date YYYY-MM-DD)"
    )
    ai_context: str = Field(
        description="Reason why the agent is planning this shipment"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CheckCarrierAvailabilityInput(BaseModel):
    carrier_id: int = Field(description="delivery.carrier ID to check")
    pickup_date: str = Field(
        description="Required pickup date (ISO date YYYY-MM-DD)"
    )
    delivery_date: str = Field(
        description="Required delivery date (ISO date YYYY-MM-DD)"
    )
    weight_kg: float | None = Field(
        None, description="Total shipment weight in kg"
    )
    ai_context: str = Field(description="Reason why the agent is checking availability")


class GetATPByDateInput(BaseModel):
    product_id: int = Field(description="product.product ID to check")
    requested_qty: float = Field(description="Required quantity")
    requested_date: str = Field(
        description="Customer requested delivery date (ISO date YYYY-MM-DD)"
    )
    include_transit: bool = Field(
        True,
        description="If True, deduct carrier transit time from available supply date",
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetPendingShipmentsInput(BaseModel):
    warehouse_id: int | None = Field(
        None, description="Filter by Odoo stock.warehouse ID"
    )
    date_from: str | None = Field(
        None, description="Scheduled date from (ISO date)"
    )
    date_to: str | None = Field(
        None, description="Scheduled date to (ISO date)"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class LogisticsPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'stock.picking')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class LogisticsCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'stock.picking')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary")
    note: str = Field(description="Detailed note for the human reviewer")
    deadline_days: int = Field(2, description="Days from today until activity deadline")
    ai_context: str = Field(description="Reason why the agent is creating this activity")


class LogisticsCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_delivery_routes(params: GetDeliveryRoutesInput) -> list[dict]:
    """
    List active delivery routes from the ERP.
    Returns AxonDeliveryRoute-compatible dicts.

    Implement via: stock.route, delivery.carrier.
    """
    raise NotImplementedError(
        "axon_get_delivery_routes: implement in Phase 6 using AxonLogisticsSkills"
    )


@mcp.tool()
def axon_plan_shipment(params: PlanShipmentInput) -> dict:
    """
    Create or update a delivery shipment in the ERP.
    Returns AxonShipment-compatible dict with the created/updated picking ID.

    Implement via: stock.picking (write) + delivery.carrier.
    """
    raise NotImplementedError(
        "axon_plan_shipment: implement in Phase 6 using AxonLogisticsSkills"
    )


@mcp.tool()
def axon_check_carrier_availability(params: CheckCarrierAvailabilityInput) -> dict:
    """
    Check whether a carrier can fulfil a shipment on the given dates.
    Returns AxonCarrier-compatible dict with available flag and transit_days.

    Implement via: delivery.carrier + carrier-specific API calls.
    """
    raise NotImplementedError(
        "axon_check_carrier_availability: implement in Phase 6 using AxonLogisticsSkills"
    )


@mcp.tool()
def axon_get_atp_by_date(params: GetATPByDateInput) -> dict:
    """
    ATP check that accounts for carrier transit time.
    Returns AxonATPResult-compatible dict.

    Implement via: stock.quant + stock.move (incoming) - transit_days offset.
    """
    raise NotImplementedError(
        "axon_get_atp_by_date: implement in Phase 6 using AxonLogisticsSkills"
    )


@mcp.tool()
def axon_get_pending_shipments(params: GetPendingShipmentsInput) -> list[dict]:
    """
    List shipments pending dispatch.
    Returns AxonShipment-compatible dicts.

    Implement via: stock.picking (state in ('ready', 'waiting', 'confirmed')).
    """
    raise NotImplementedError(
        "axon_get_pending_shipments: implement in Phase 6 using AxonLogisticsSkills"
    )


@mcp.tool()
def axon_post_comment(params: LogisticsPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: LogisticsCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: LogisticsCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_logistics_port)
