"""
core.schema.quality — Universal Quality Assurance & Quality Control Models.

ERP-agnostic representation of inspections, NG (non-conformance) items,
compliance checks, compliance decisions, and rework orders.

Agents reason about these models; MCP adapters translate from Odoo
quality.check / quality.alert, SAP QM, Oracle Quality, etc.

Inter-departmental data flows:
    QC → Warehouse:   AxonNGItem triggers stock lock + AxonReworkOrder
    QA → All Depts:   AxonComplianceDecision acts as guardrail before every ERP write
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────

class AxonInspectionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"  # Passed with deviations


class AxonNGSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class AxonComplianceOutcome(str, Enum):
    COMPLIANT = "compliant"
    VIOLATION_FOUND = "violation_found"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AxonReworkType(str, Enum):
    REWORK = "rework"           # Fix and re-inspect
    SCRAP = "scrap"             # Destroy and re-produce
    RETURN_TO_VENDOR = "return_to_vendor"
    CONDITIONAL_RELEASE = "conditional_release"  # Release with deviation permit


# ── QC Models ─────────────────────────────────────────────────────────────────

class AxonInspection(BaseModel):
    """A quality inspection event — ERP-agnostic."""

    id: str = Field(description="ERP-agnostic inspection identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Inspection reference")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Product display name")
    product_sku: str | None = Field(None, description="SKU / internal reference")

    lot_id: str | None = Field(None, description="Lot / serial number inspected")
    location_id: str | None = Field(None, description="Warehouse location")

    qty_inspected: float = Field(description="Quantity put through inspection")
    qty_passed: float = Field(0.0, description="Quantity that passed")
    qty_failed: float = Field(0.0, description="Quantity that failed (NG)")
    uom: str = Field("units", description="Unit of measure")

    inspection_date: date = Field(description="Date inspection was performed")
    status: AxonInspectionStatus = Field(
        AxonInspectionStatus.PENDING, description="Inspection status"
    )
    inspector: str | None = Field(None, description="Name of QC inspector")

    failure_reason: str | None = Field(
        None, description="Root cause or description of failure"
    )
    production_order_id: str | None = Field(
        None, description="Linked production order if this is an in-process inspection"
    )
    purchase_order_id: str | None = Field(
        None, description="Linked purchase order if this is an incoming inspection"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if self.qty_inspected == 0:
            return 0.0
        return self.qty_passed / self.qty_inspected


class AxonNGItem(BaseModel):
    """
    A non-conformance (NG) item detected by QC.

    Inter-departmental trigger:
        AxonNGItem → QC Agent → lock stock + create AxonReworkOrder
        → Planning Agent re-computes shortages
    """

    id: str = Field(description="ERP-agnostic NG record identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    inspection_id: str = Field(description="Source AxonInspection.id")

    product_id: str = Field(description="ERP-agnostic product identifier")
    product_name: str = Field(description="Product display name")

    qty_ng: float = Field(description="Non-conforming quantity")
    uom: str = Field("units", description="Unit of measure")

    lot_id: str | None = Field(None, description="Lot / serial number of the NG item")
    location_id: str | None = Field(None, description="Warehouse location of the NG stock")
    stock_quant_id: str | None = Field(
        None, description="ERP stock.quant ID to lock (Odoo-specific, populated by adapter)"
    )

    severity: AxonNGSeverity = Field(
        AxonNGSeverity.MAJOR, description="NG severity level"
    )
    failure_description: str = Field(description="What is wrong with the item")
    detected_at: datetime = Field(description="When the NG was detected")

    stock_locked: bool = Field(
        False, description="True when the stock has been locked in the ERP"
    )
    rework_order_id: str | None = Field(
        None, description="Linked AxonReworkOrder.id created for this NG"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonReworkOrder(BaseModel):
    """
    A rework or scrap instruction produced by the QC Agent.

    Created automatically when AxonNGItem is detected.
    Injected back into the Planning demand stream as a new demand item.
    """

    id: str = Field(description="ERP-agnostic rework order identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Rework order reference")
    ng_item_id: str = Field(description="Source AxonNGItem.id")

    product_id: str = Field(description="Product to be reworked or replaced")
    product_name: str = Field(description="Product display name")

    qty_rework: float = Field(description="Quantity to rework or replace")
    uom: str = Field("units", description="Unit of measure")

    rework_type: AxonReworkType = Field(
        AxonReworkType.REWORK, description="How to handle the NG stock"
    )
    required_by: date = Field(
        description="Date by which reworked / replacement stock is needed"
    )
    production_order_id: str | None = Field(
        None, description="New production order created for rework (if rework_type=REWORK)"
    )
    demand_item_id: str | None = Field(
        None, description="New AxonDemandItem.id injected for replacement demand"
    )

    ai_context: str = Field(
        description="QC Agent reasoning for this rework decision"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── QA Models ─────────────────────────────────────────────────────────────────

class AxonComplianceRule(BaseModel):
    """A single compliance rule or regulatory requirement."""

    id: str = Field(description="ERP-agnostic rule identifier")
    code: str = Field(description="Rule code (e.g. 'ISO-9001-4.1')")
    description: str = Field(description="Plain-language rule description")
    department: str = Field(
        description="Department this rule applies to (e.g. 'procurement', 'production', 'all')"
    )
    severity: str = Field(
        "major",
        description="Violation severity: 'minor' | 'major' | 'critical'",
    )
    requires_human_review: bool = Field(
        False,
        description="If True, any violation must be reviewed by a human before proceeding",
    )


class AxonComplianceViolation(BaseModel):
    """A single detected compliance violation."""

    rule_id: str = Field(description="Violated AxonComplianceRule.id")
    rule_code: str = Field(description="Rule code for quick reference")
    description: str = Field(description="What was violated and how")
    severity: str = Field(description="Violation severity: 'minor' | 'major' | 'critical'")
    affected_entity: str = Field(
        description="Entity type being checked (e.g. 'purchase.order', 'mrp.production')"
    )
    affected_entity_id: str = Field(description="ID of the entity that violated the rule")
    remediation: str | None = Field(
        None, description="Suggested remediation action"
    )


class AxonComplianceCheck(BaseModel):
    """
    Input to the QA Compliance Guardrail Agent.

    Carries the proposed action and enough context for the QA Agent to
    evaluate it against compliance rules.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    action_type: str = Field(
        description="Type of action being checked (e.g. 'confirm_po', 'release_production', 'ship_goods')"
    )
    action_description: str = Field(
        description="Plain-language description of the proposed action"
    )
    entity_type: str = Field(
        description="ERP entity type involved (e.g. 'purchase.order', 'mrp.production')"
    )
    entity_id: str = Field(description="ERP entity ID")
    department: str = Field(
        description="Department initiating the action (e.g. 'procurement', 'production')"
    )
    ai_context: str = Field(
        description="Agent reasoning context — why this action is being proposed"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonComplianceDecision(BaseModel):
    """
    Output of the QA Compliance Guardrail Agent.

    If outcome == VIOLATION_FOUND and any violation has requires_human_review=True,
    the orchestrator fires a LangGraph interrupt checkpoint for human sign-off.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    check_id: str = Field(description="Identifier for this compliance check instance")
    outcome: AxonComplianceOutcome = Field(description="Overall compliance verdict")

    violations: list[AxonComplianceViolation] = Field(
        default_factory=list,
        description="List of detected violations (empty if compliant)",
    )
    rules_checked: int = Field(
        0, description="Number of compliance rules evaluated"
    )
    requires_human_review: bool = Field(
        False,
        description="True when at least one violation mandates human sign-off before proceeding",
    )
    human_review_activity_id: int | None = Field(
        None,
        description="ERP HITL activity ID created for human review (if requires_human_review=True)",
    )

    recommendation: str = Field(
        description=(
            "QA recommendation: 'proceed' | 'proceed_with_conditions' | "
            "'block_pending_review' | 'block_and_escalate'"
        )
    )
    ai_context: str = Field(
        description="QA Agent reasoning for this compliance decision"
    )
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    checked_at: datetime = Field(description="When the compliance check was performed")
    metadata: dict[str, Any] = Field(default_factory=dict)
