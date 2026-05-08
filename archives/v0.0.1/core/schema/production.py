"""
core.schema.production — Universal Production & MPS Models.

ERP-agnostic representation of production orders, master production schedules,
BOM changes, work centres, and sequencing. Agents reason about these models;
MCP adapters translate from Odoo mrp.production, SAP PP, Oracle WIP, etc.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonProductionStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class AxonProductionPriority(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"
    CRITICAL = "critical"


class AxonWorkCenter(BaseModel):
    """A machine or work centre that performs production operations."""

    id: str = Field(description="ERP-agnostic work centre identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Work centre name")
    code: str | None = Field(None, description="Work centre code")
    capacity: float = Field(1.0, description="Available capacity ratio (0.0–1.0)")
    time_efficiency: float = Field(
        1.0, description="Time efficiency ratio (1.0 = 100%)"
    )
    available_from: date | None = Field(
        None, description="Date from which this work centre is operational"
    )
    is_blocked: bool = Field(
        False, description="True when blocked by maintenance or breakdown"
    )
    blocked_reason: str | None = Field(
        None, description="Reason for blockage (e.g. 'Breakdown WO-001')"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonRoutingStep(BaseModel):
    """A single operation step in a production routing."""

    id: str = Field(description="ERP-agnostic routing step identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    sequence: int = Field(description="Step sequence number")
    name: str = Field(description="Operation name")
    work_centre_id: str = Field(description="Assigned AxonWorkCenter.id")
    work_centre_name: str = Field(description="Work centre display name")
    duration_expected: float = Field(
        description="Expected duration in minutes"
    )
    workcenter_time: float = Field(
        0.0, description="Actual workcenter time consumed (minutes)"
    )


class AxonProductionOrder(BaseModel):
    """
    A single manufacturing / production order — ERP-agnostic.

    Covers Odoo mrp.production, SAP Production Order, Oracle WIP Job, etc.
    """

    id: str = Field(description="ERP-agnostic production order identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Production order reference (e.g. 'MO/2026/0042')")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Human-readable product name")
    product_sku: str | None = Field(None, description="SKU / internal reference")

    qty_planned: float = Field(description="Planned production quantity")
    qty_produced: float = Field(0.0, description="Quantity already produced")
    uom: str = Field("units", description="Unit of measure")

    scheduled_start: date = Field(description="Planned production start date")
    scheduled_end: date = Field(description="Planned production end date")
    actual_start: date | None = Field(None, description="Actual start date")

    status: AxonProductionStatus = Field(
        AxonProductionStatus.DRAFT, description="Current production order status"
    )
    priority: AxonProductionPriority = Field(
        AxonProductionPriority.NORMAL, description="Production priority"
    )

    work_centre_id: str | None = Field(
        None, description="Primary work centre identifier"
    )
    routing_steps: list[AxonRoutingStep] = Field(
        default_factory=list, description="Ordered routing operations"
    )

    bom_id: str | None = Field(None, description="Active BOM identifier")
    bom_version: str | None = Field(None, description="BOM version in use")

    demand_id: str | None = Field(
        None, description="Linked AxonDemandItem.id this order fulfils"
    )
    sale_ref: str | None = Field(None, description="Linked sale order reference")

    ai_context: str | None = Field(
        None, description="Agent reasoning attached to this order"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def qty_remaining(self) -> float:
        return max(0.0, self.qty_planned - self.qty_produced)

    @property
    def is_behind_schedule(self) -> bool:
        from datetime import date as _date
        return self.scheduled_end < _date.today() and self.status not in (
            AxonProductionStatus.DONE, AxonProductionStatus.CANCELLED
        )


class AxonBOMLine(BaseModel):
    """A single line in a Bill of Materials."""

    id: str = Field(description="ERP-agnostic BOM line identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    product_id: str = Field(description="Component product identifier")
    product_name: str = Field(description="Component product name")
    qty: float = Field(description="Component quantity per finished unit")
    uom: str = Field("units", description="Unit of measure")
    operation_id: str | None = Field(
        None, description="Routing step where this component is consumed"
    )


class AxonBOMChange(BaseModel):
    """
    A BOM change event produced by the PD Agent.

    Captures a delta between the previous and new BOM version so the
    Production Planning Agent can re-compute affected manufacturing orders.
    """

    id: str = Field(description="ERP-agnostic change record identifier")
    bom_id: str = Field(description="BOM record identifier")
    bom_name: str = Field(description="BOM display name")
    product_id: str = Field(description="Finished product this BOM produces")
    product_name: str = Field(description="Finished product name")

    previous_version: str | None = Field(None, description="Previous BOM version tag")
    new_version: str = Field(description="New BOM version tag after change")

    changed_lines: list[AxonBOMLine] = Field(
        default_factory=list,
        description="BOM lines that were added, removed, or modified",
    )
    change_type: str = Field(
        description="Type of change: 'add_component' | 'remove_component' | 'qty_change' | 'routing_change' | 'full_revision'"
    )
    affected_mo_ids: list[str] = Field(
        default_factory=list,
        description="Production order IDs that must be re-planned due to this BOM change",
    )

    changed_by: str | None = Field(None, description="User or agent that made the change")
    changed_at: datetime | None = Field(None, description="When the change was recorded")

    ai_context: str = Field(
        description="Agent reasoning explaining the impact of this BOM change"
    )
    requires_replan: bool = Field(
        True,
        description="Whether this change necessitates re-computing the production schedule",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonSequencingEntry(BaseModel):
    """One job in the sequenced production schedule."""

    production_order_id: str = Field(
        description="AxonProductionOrder.id being scheduled"
    )
    production_order_name: str = Field(description="Production order reference")
    product_id: str = Field(description="Product being manufactured")
    product_name: str = Field(description="Product display name")
    work_centre_id: str = Field(description="AxonWorkCenter.id this job runs on")
    work_centre_name: str = Field(description="Work centre display name")
    scheduled_start: datetime = Field(description="Planned start datetime")
    scheduled_end: datetime = Field(description="Planned end datetime")
    sequence_rank: int = Field(description="Position in the work centre queue (1 = first)")
    priority: AxonProductionPriority = Field(AxonProductionPriority.NORMAL)


class AxonSequencing(BaseModel):
    """
    The full sequenced production schedule output by the Production Planning Agent.

    This is the 'master schedule' — it tells the shop floor which job runs
    on which machine in which order, taking all constraints into account.
    """

    cycle_id: str = Field(description="Planning cycle this schedule belongs to")
    generated_at: datetime = Field(description="When this schedule was generated")
    entries: list[AxonSequencingEntry] = Field(
        default_factory=list, description="Ordered list of scheduled jobs"
    )
    unscheduled_orders: list[str] = Field(
        default_factory=list,
        description="Production order IDs that could not be scheduled (capacity/constraint conflict)",
    )
    constraint_notes: list[str] = Field(
        default_factory=list,
        description="Human-readable constraint explanations (maintenance blocks, BOM changes, etc.)",
    )
    confidence: float = Field(
        1.0, description="Agent confidence in this schedule (0.0–1.0)"
    )
    ai_context: str = Field(description="Agent reasoning for this scheduling decision")


class AxonMPS(BaseModel):
    """
    Master Production Schedule — high-level demand-driven production plan.

    The MPS Agent creates this from AxonDemandStream + AxonSupplyStream.
    The Sequencing Agent then translates it into AxonSequencing (shop-floor ops).
    """

    cycle_id: str = Field(description="Planning cycle reference")
    period_start: date = Field(description="MPS planning horizon start")
    period_end: date = Field(description="MPS planning horizon end")

    production_orders: list[AxonProductionOrder] = Field(
        default_factory=list,
        description="Production orders to create or adjust in this MPS run",
    )
    total_planned_qty: float = Field(
        0.0, description="Total planned production quantity across all orders"
    )
    capacity_utilisation: float = Field(
        0.0, description="Estimated overall capacity utilisation (0.0–1.0)"
    )
    action: str = Field(
        description="'create_orders' | 'reschedule' | 'no_action' | 'hitl_required'"
    )
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    ai_context: str = Field(description="Agent reasoning for this MPS decision")
    metadata: dict[str, Any] = Field(default_factory=dict)
