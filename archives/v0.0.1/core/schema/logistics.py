"""
core.schema.logistics — Universal Logistics & Distribution Models.

ERP-agnostic representation of shipments, delivery routes, carriers,
and Available-to-Promise (ATP) checks. Agents reason about these models;
MCP adapters translate from Odoo stock.picking / delivery.carrier,
SAP TM, Oracle Shipping, etc.

Inter-departmental data flow:
    Maintenance → Logistics: breakdown delays trigger notify_sales in AxonMaintenanceConstraint
    Logistics Agent → Sales Agent: ATP dates updated after reschedule
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonShipmentStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class AxonCarrier(BaseModel):
    """A logistics carrier / shipping provider — ERP-agnostic."""

    id: str = Field(description="ERP-agnostic carrier identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Carrier display name")
    code: str | None = Field(None, description="Carrier code (e.g. 'FDX', 'DHL')")
    transit_days: int = Field(
        1, description="Standard transit time in calendar days"
    )
    max_weight_kg: float | None = Field(
        None, description="Maximum shipment weight in kg"
    )
    cost_per_kg: float | None = Field(
        None, description="Standard shipping cost per kg"
    )
    currency: str | None = Field("USD", description="Currency for cost fields")
    available: bool = Field(True, description="Whether carrier is currently available")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonDeliveryRoute(BaseModel):
    """A configured delivery route from origin to destination."""

    id: str = Field(description="ERP-agnostic route identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Route display name")
    origin_location: str = Field(description="Source warehouse / location name")
    destination_location: str = Field(description="Destination address or zone")
    carrier_id: str | None = Field(None, description="Default AxonCarrier.id for this route")
    carrier_name: str | None = Field(None, description="Carrier display name")
    transit_days: int = Field(1, description="Standard transit days on this route")
    is_active: bool = Field(True, description="Whether this route is active")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonShipmentLine(BaseModel):
    """A single product line within a shipment."""

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Product display name")
    qty: float = Field(description="Quantity being shipped")
    uom: str = Field("units", description="Unit of measure")
    weight_kg: float | None = Field(None, description="Line weight in kg")
    lot_id: str | None = Field(None, description="Lot / serial number")
    demand_id: str | None = Field(None, description="Linked AxonDemandItem.id")


class AxonShipment(BaseModel):
    """
    A delivery / shipment record — ERP-agnostic.

    Covers Odoo stock.picking (outgoing), SAP delivery, Oracle shipping txn, etc.
    """

    id: str = Field(description="ERP-agnostic shipment identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Shipment reference (e.g. 'OUT/2026/0042')")

    customer_ref: str | None = Field(None, description="Customer name or reference")
    sale_order_ref: str | None = Field(None, description="Source sale order reference")

    origin_location: str = Field(description="Source warehouse / location")
    destination_address: str = Field(description="Delivery destination address")

    lines: list[AxonShipmentLine] = Field(
        default_factory=list, description="Product lines in this shipment"
    )

    carrier_id: str | None = Field(None, description="AxonCarrier.id assigned")
    carrier_name: str | None = Field(None, description="Carrier display name")
    route_id: str | None = Field(None, description="AxonDeliveryRoute.id used")

    scheduled_date: date = Field(description="Planned shipment / dispatch date")
    expected_delivery_date: date = Field(description="Expected delivery date at customer")
    actual_delivery_date: date | None = Field(None, description="Actual delivery date")

    status: AxonShipmentStatus = Field(
        AxonShipmentStatus.DRAFT, description="Current shipment status"
    )
    is_delayed: bool = Field(False, description="True when shipment is behind schedule")
    delay_reason: str | None = Field(None, description="Reason for delay if is_delayed")

    ai_context: str | None = Field(None, description="Agent reasoning attached to this shipment")
    cycle_id: str | None = Field(None, description="Planning cycle reference")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_weight_kg(self) -> float:
        return sum(ln.weight_kg or 0.0 for ln in self.lines)


class AxonATPResult(BaseModel):
    """ATP result for a single product + requested date combination."""

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Product display name")
    requested_qty: float = Field(description="Quantity the customer requested")
    requested_date: date = Field(description="Customer's requested delivery date")
    available_qty: float = Field(
        description="Quantity that can be promised by the requested date"
    )
    promised_date: date | None = Field(
        None,
        description="Earliest date full quantity can be delivered (None = cannot promise)",
    )
    can_fulfill: bool = Field(
        description="True when full qty can be delivered by or before requested_date"
    )
    partial_qty: float = Field(
        0.0,
        description="Partial quantity available by requested_date (0 if can_fulfill=True)",
    )
    shortage_qty: float = Field(
        0.0, description="Quantity that cannot be promised (0 if can_fulfill=True)"
    )
    supply_plan: str | None = Field(
        None,
        description="Brief summary of the supply plan covering this demand",
    )


class AxonATP(BaseModel):
    """
    Available-to-Promise response — produced by the Logistics / Sales Agent.

    Used by the Sales team to confirm delivery dates to customers.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    requested_at: datetime = Field(description="When the ATP check was requested")
    results: list[AxonATPResult] = Field(
        default_factory=list, description="ATP results per product"
    )
    overall_fulfillable: bool = Field(
        description="True when ALL requested lines can be fulfilled"
    )
    ai_context: str = Field(description="Agent reasoning for the ATP decision")
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    metadata: dict[str, Any] = Field(default_factory=dict)
