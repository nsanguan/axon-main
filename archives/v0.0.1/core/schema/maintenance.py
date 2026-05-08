"""
core.schema.maintenance — Universal Maintenance & Asset Reliability Models.

ERP-agnostic representation of assets, PM orders, breakdowns, and the
production constraints they impose. Agents reason about these models;
MCP adapters translate from Odoo maintenance.request / maintenance.equipment,
SAP PM, Oracle EAM, etc.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonAssetStatus(str, Enum):
    OPERATIONAL = "operational"
    UNDER_MAINTENANCE = "under_maintenance"
    BROKEN_DOWN = "broken_down"
    DECOMMISSIONED = "decommissioned"


class AxonMaintenanceType(str, Enum):
    PREVENTIVE = "preventive"   # Planned PM
    CORRECTIVE = "corrective"   # Breakdown repair
    PREDICTIVE = "predictive"   # Condition-based


class AxonMaintenancePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AxonAsset(BaseModel):
    """
    A physical asset (machine, equipment, work centre) — ERP-agnostic.
    """

    id: str = Field(description="ERP-agnostic asset identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Asset name")
    code: str | None = Field(None, description="Asset code / tag number")
    category: str | None = Field(None, description="Asset category (e.g. 'CNC Machine')")
    work_centre_id: str | None = Field(
        None, description="Linked AxonWorkCenter.id (if this asset maps to a work centre)"
    )
    location: str | None = Field(None, description="Physical location in the plant")
    status: AxonAssetStatus = Field(
        AxonAssetStatus.OPERATIONAL, description="Current operational status"
    )
    last_maintenance_date: date | None = Field(
        None, description="Date of last completed maintenance"
    )
    next_pm_date: date | None = Field(
        None, description="Next scheduled preventive maintenance date"
    )
    mean_time_between_failures: float | None = Field(
        None, description="MTBF in hours"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonPMOrder(BaseModel):
    """
    A Preventive Maintenance order — ERP-agnostic.
    Scheduled maintenance that the Production Planning Agent must treat as
    a capacity constraint.
    """

    id: str = Field(description="ERP-agnostic PM order identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="PM order reference")
    asset_id: str = Field(description="AxonAsset.id this PM targets")
    asset_name: str = Field(description="Asset display name")
    work_centre_id: str | None = Field(
        None, description="Work centre blocked during this PM"
    )
    maintenance_type: AxonMaintenanceType = Field(
        AxonMaintenanceType.PREVENTIVE, description="Type of maintenance"
    )
    priority: AxonMaintenancePriority = Field(
        AxonMaintenancePriority.NORMAL, description="Maintenance priority"
    )
    scheduled_start: date = Field(description="Planned maintenance start date")
    scheduled_end: date = Field(description="Planned maintenance end date")
    estimated_duration_hours: float = Field(
        description="Estimated duration in hours"
    )
    technician: str | None = Field(None, description="Assigned technician name")
    status: str = Field(
        "planned",
        description="Status: 'planned' | 'in_progress' | 'done' | 'cancelled'",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def capacity_block_days(self) -> int:
        """Number of calendar days this PM blocks the work centre."""
        delta = self.scheduled_end - self.scheduled_start
        return max(1, delta.days + 1)


class AxonBreakdown(BaseModel):
    """
    An unplanned equipment failure (breakdown) event — ERP-agnostic.

    When the Maintenance Agent detects a breakdown, it creates an
    AxonMaintenanceConstraint for the Optimization / Production Planning Agent
    to consume when re-sequencing production.
    """

    id: str = Field(description="ERP-agnostic breakdown identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Breakdown report reference")
    asset_id: str = Field(description="AxonAsset.id of the failed equipment")
    asset_name: str = Field(description="Asset display name")
    work_centre_id: str | None = Field(
        None, description="Work centre blocked by this breakdown"
    )

    failure_description: str = Field(description="What failed and how")
    reported_at: datetime = Field(description="When the breakdown was reported")
    estimated_repair_hours: float | None = Field(
        None, description="Estimated hours to repair"
    )
    estimated_resume_date: date | None = Field(
        None, description="Expected date when the asset returns to service"
    )

    impact_severity: str = Field(
        "high",
        description="Impact level: 'low' | 'medium' | 'high' | 'critical'",
    )
    affected_production_orders: list[str] = Field(
        default_factory=list,
        description="Production order IDs blocked by this breakdown",
    )
    status: str = Field(
        "open",
        description="Status: 'open' | 'in_repair' | 'resolved'",
    )
    resolved_at: datetime | None = Field(None, description="When the breakdown was resolved")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonMaintenanceConstraint(BaseModel):
    """
    The consolidated constraint set produced by the Maintenance Agent.

    This is the single output consumed by the Production Planning / Sequencing
    Agent to re-schedule affected production orders.

    Inter-departmental data flow:
        Maintenance Agent → AxonMaintenanceConstraint
        → Production Planning Agent (reschedule)
        → Sales/Logistics Agent (notify delivery slip)
    """

    cycle_id: str = Field(description="Planning cycle reference")
    generated_at: datetime = Field(description="When this constraint set was generated")

    breakdowns: list[AxonBreakdown] = Field(
        default_factory=list, description="Active breakdown events"
    )
    pm_orders: list[AxonPMOrder] = Field(
        default_factory=list, description="Scheduled PM that blocks capacity"
    )
    blocked_work_centres: list[str] = Field(
        default_factory=list,
        description="Work centre IDs currently or imminently unavailable",
    )
    capacity_loss_hours: float = Field(
        0.0, description="Total planned capacity lost (hours) across all constraints"
    )
    requires_reschedule: bool = Field(
        False,
        description="True when at least one active constraint affects a scheduled production order",
    )
    affected_production_orders: list[str] = Field(
        default_factory=list,
        description="Production order IDs that must be rescheduled",
    )
    notify_sales: bool = Field(
        False,
        description="True when a delivery delay to customers is likely and Sales must be notified",
    )
    delay_notification: str | None = Field(
        None,
        description="Draft message for Sales/Logistics teams about expected delivery slip",
    )
    ai_context: str = Field(
        description="Maintenance Agent reasoning summarising all active constraints"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
