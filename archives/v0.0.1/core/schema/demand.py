"""
core.schema.demand — Universal Demand Model.

This is the ERP-agnostic representation of demand. Agents only speak this
schema, regardless of whether data originates from Odoo, SAP, Oracle, or any
other System of Record.

The MCP adapter layer (adapters/mapping/) translates ERP-native records into
these models before they reach the orchestrator and agents.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonDemandSource(str, Enum):
    SALE_ORDER = "sale_order"
    FORECAST = "forecast"
    MPS = "mps"                    # Master Production Schedule
    MRP = "mrp"                    # Material Requirements Planning
    MANUAL = "manual"
    TRANSFER = "transfer"
    MPS_PRODUCTION = "mps_production"  # Demand created by the MPS Agent for production
    REWORK = "rework"              # Demand created by QC Agent after NG detection


class AxonDemandStatus(str, Enum):
    OPEN = "open"
    PEGGED = "pegged"
    PARTIAL = "partial"
    EXCEPTION = "exception"
    CLOSED = "closed"


class AxonDemandItem(BaseModel):
    """
    A single unit of demand — ERP-agnostic.

    Agents reason about AxonDemandItem objects; MCP adapters translate from
    Odoo sale.order lines, SAP delivery items, etc. into this model.
    """

    id: str = Field(description="Unique demand identifier (ERP-agnostic, prefixed by adapter)")
    source_type: AxonDemandSource = Field(description="Origin of this demand signal")
    source_ref: str = Field(description="ERP-native reference (e.g. 'SO/2026/0042')")
    erp_id: int | None = Field(None, description="Native ERP record ID (adapter-internal)")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Human-readable product name")
    product_sku: str | None = Field(None, description="SKU / internal reference")

    demand_qty: float = Field(description="Gross demand quantity")
    confirmed_qty: float = Field(0.0, description="Quantity already pegged/allocated")
    uom: str = Field("units", description="Unit of measure")

    demand_date: date = Field(description="Date by which demand must be fulfilled")
    creation_date: date | None = Field(None, description="When the demand was created")

    status: AxonDemandStatus = Field(AxonDemandStatus.OPEN, description="Current coverage status")
    priority: int = Field(0, description="Priority rank (higher = more urgent)")

    customer_ref: str | None = Field(None, description="Customer or requester reference")
    location_ref: str | None = Field(None, description="Destination location reference")

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific extra fields (not used by agents)",
    )

    @property
    def open_qty(self) -> float:
        """Quantity not yet covered by any allocation."""
        return max(0.0, self.demand_qty - self.confirmed_qty)

    @property
    def is_covered(self) -> bool:
        return self.confirmed_qty >= self.demand_qty


class AxonDemandStream(BaseModel):
    """Snapshot of all open demand for a planning cycle."""

    cycle_id: str
    items: list[AxonDemandItem] = Field(default_factory=list)
    total_items: int = Field(0)
    source_erp: str = Field(description="ERP system that sourced this demand (e.g. 'odoo', 'sap')")

    @property
    def open_items(self) -> list[AxonDemandItem]:
        return [i for i in self.items if not i.is_covered]

    @property
    def product_ids(self) -> list[str]:
        return list({i.product_id for i in self.items})
