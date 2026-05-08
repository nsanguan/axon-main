"""
core.schema.allocation — Universal AxonAllocation (Pegging) Model.

The allocation schema is the core output of Axon's planning logic.
It links a demand item to one or more supply items — this is "pegging".

Agents produce AxonAllocation objects; the MCP adapter layer writes them back
to the ERP's pegging/allocation store (Odoo, SAP, legacy DB, etc.).
The specific target model is an Odoo detail — the orchestrator never sees it.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonAllocationStatus(str, Enum):
    DRAFT = "draft"
    FIRM = "firm"
    RELEASED = "released"
    PARTIAL = "partial"
    EXCEPTION = "exception"
    CANCELLED = "cancelled"


class AxonAllocationAction(str, Enum):
    ALLOCATE = "allocate"
    SHORTAGE = "shortage"
    EXCEPTION = "exception"
    HITL_REQUIRED = "hitl_required"
    NO_ACTION = "no_action"


class AxonAllocation(BaseModel):
    """
    A pegging record that links one demand item to one supply item — ERP-agnostic.

    This is the primary write output of the Planning Manager Agent.
    The orchestrator persists it back to the ERP via the appropriate MCP adapter.
    """

    id: str | None = Field(None, description="Axon-assigned allocation ID (set after ERP write)")
    erp_id: int | None = Field(None, description="Native ERP record ID after write-back")

    demand_id: str = Field(description="AxonDemandItem.id this allocation covers")
    supply_id: str = Field(description="AxonSupplyItem.id providing the supply")

    demand_ref: str = Field(description="Human-readable demand reference (e.g. SO/2026/0042)")
    supply_ref: str = Field(description="Human-readable supply reference (e.g. PO/2026/0099)")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Human-readable product name")

    allocated_qty: float = Field(description="Quantity allocated from supply to demand")
    uom: str = Field("units", description="Unit of measure")

    demand_date: date = Field(description="Required-by date from the demand item")
    plan_date: date = Field(description="Planned fulfillment date")

    status: AxonAllocationStatus = Field(AxonAllocationStatus.DRAFT, description="AxonAllocation status")
    confidence: float = Field(1.0, description="Agent confidence 0.0–1.0")

    ai_context: str = Field(description="Agent reasoning for this allocation decision")
    cycle_id: str | None = Field(None, description="Planning cycle reference")

    created_at: datetime | None = Field(None, description="When this allocation was created")
    updated_at: datetime | None = Field(None, description="When this allocation was last updated")

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific extra fields for ERP write-back",
    )


class AxonShortageItem(BaseModel):
    """Represents an unresolvable demand gap — output when supply is insufficient."""

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Human-readable product name")
    product_sku: str | None = None

    demand_qty: float = Field(description="Total demand quantity required")
    available_qty: float = Field(description="Total supply available (may be zero)")
    shortage_qty: float = Field(description="Unmet quantity (demand_qty - available_qty)")

    demand_date: str = Field(description="ISO date by which this was needed")
    demand_id: str = Field(description="AxonDemandItem.id with the shortage")
    demand_ref: str = Field(description="Human-readable demand reference")

    pegging_id: str | None = Field(None, description="AxonAllocation record ID (if partially covered)")
    erp_pegging_id: int | None = Field(None, description="Native ERP pegging record ID")


class AxonPlanningDecision(BaseModel):
    """
    The top-level output of the Planning Manager Agent for one planning cycle.

    This is the universal planning result — ERP-agnostic.
    The orchestrator routes based on `action`.
    """

    cycle_id: str
    action: AxonAllocationAction = Field(
        description="'allocate' | 'shortage' | 'hitl_required' | 'exception' | 'no_action'"
    )

    allocations: list[AxonAllocation] = Field(
        default_factory=list,
        description="Pegging records to write back to the ERP",
    )
    shortages: list[AxonShortageItem] = Field(
        default_factory=list,
        description="Products with insufficient supply — routes to Purchase Cluster",
    )
    hitl_activity_ids: list[int] = Field(
        default_factory=list,
        description="ERP activity IDs awaiting human response",
    )

    summary: str = Field(description="Plain-language summary of the planning decision")
    confidence: float = Field(
        1.0,
        description="Overall confidence 0.0–1.0; below 0.7 escalates to Executive Agent",
    )

    source_erp: str = Field(
        "unknown",
        description="Which ERP this planning cycle ran against",
    )
