"""
core.schema.supply — Universal Supply Model.

ERP-agnostic representation of supply (on-hand stock, POs, MOs, transfers).
Agents reason about AxonSupplyItem objects; MCP adapters translate from Odoo
stock.quant / purchase.order, SAP MM, etc. into this model.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonSupplySource(str, Enum):
    ON_HAND = "on_hand"
    PURCHASE_ORDER = "purchase_order"
    MANUFACTURING_ORDER = "manufacturing_order"
    TRANSFER = "transfer"
    WORK_ORDER = "work_order"
    FORECAST = "forecast"


class AxonSupplyStatus(str, Enum):
    OPEN = "open"
    ALLOCATED = "allocated"
    PARTIAL = "partial"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class AxonSupplyItem(BaseModel):
    """
    A single unit of supply — ERP-agnostic.

    Covers both on-hand stock (immediate) and future supply (incoming POs,
    MOs, transfers). The agent uses supply_date to determine if supply arrives
    before the demand_date it needs to cover.
    """

    id: str = Field(description="Unique supply identifier (ERP-agnostic, prefixed by adapter)")
    source_type: AxonSupplySource = Field(description="Nature of this supply signal")
    source_ref: str = Field(description="ERP-native reference (e.g. 'PO/2026/0099')")
    erp_id: int | None = Field(None, description="Native ERP record ID (adapter-internal)")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Human-readable product name")
    product_sku: str | None = Field(None, description="SKU / internal reference")

    supply_qty: float = Field(description="Total available or incoming quantity")
    available_qty: float = Field(description="Quantity not yet allocated to any demand")
    uom: str = Field("units", description="Unit of measure")

    supply_date: date = Field(description="Date when supply is available (on-hand = today)")
    vendor_ref: str | None = Field(None, description="Vendor or supplier reference")
    location_ref: str | None = Field(None, description="Source location reference")

    unit_cost: float | None = Field(None, description="Unit cost in local currency")
    currency: str | None = Field(None, description="Currency code (ISO 4217)")
    lead_days: int | None = Field(None, description="Lead time in calendar days")

    status: AxonSupplyStatus = Field(AxonSupplyStatus.OPEN, description="Current supply status")

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific extra fields (not used by agents)",
    )

    @property
    def is_immediate(self) -> bool:
        """True if supply is on-hand and available today."""
        return self.source_type == AxonSupplySource.ON_HAND

    @property
    def is_unallocated(self) -> bool:
        return self.available_qty > 0


class AxonSupplyStream(BaseModel):
    """Snapshot of all available and incoming supply for a planning cycle."""

    cycle_id: str
    items: list[AxonSupplyItem] = Field(default_factory=list)
    total_items: int = Field(0)
    source_erp: str = Field(description="ERP system that sourced this supply (e.g. 'odoo', 'sap')")

    @property
    def on_hand(self) -> list[AxonSupplyItem]:
        return [i for i in self.items if i.source_type == AxonSupplySource.ON_HAND]

    @property
    def incoming(self) -> list[AxonSupplyItem]:
        return [i for i in self.items if i.source_type != AxonSupplySource.ON_HAND]

    def available_for_product(self, product_id: str) -> float:
        """Total unallocated quantity for a product across all supply."""
        return sum(i.available_qty for i in self.items if i.product_id == product_id)
