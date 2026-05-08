"""
Experience Ledger Models — Pydantic v2 models for plan recording, outcome tracking,
and step-by-step reasoning audit.

All data flowing through the Experience Ledger uses these types.
The retention strategy is 90 days hot (Postgres, full detail), up to 2 years
warm (summary only), auto-purge after 2 years.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Plan Context — snapshot at plan time
# =============================================================================


class PlanContext(BaseModel):
    """Snapshot of Demand/Supply/Policy at the time the plan was created.

    This is the frozen state that agents reasoned about. It is stored
    alongside the plan so future retrievals can compare demand profiles.
    """

    model_config = ConfigDict(extra="allow")

    demands: list[dict[str, Any]] = Field(default_factory=list)
    supplies: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    business_weights: dict[str, float] = Field(default_factory=dict)
    degradation_level: str = "FULL"
    correlation_id: str = ""


# =============================================================================
# Plan Outcome — populated after execution
# =============================================================================


class PlanOutcome(BaseModel):
    """Outcome of a plan, populated after execution.

    Populated by manual input (via dashboard) or automated ERP reconciliation.
    """

    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    on_time: bool = False
    over_budget: bool = False
    replan_triggered: bool = False
    cost_variance_pct: float | None = None
    delivery_variance_days: int | None = None
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    violations_detected: int = 0
    notes: str = ""


# =============================================================================
# Plan Trace — step-by-step reasoning audit
# =============================================================================


class PlanTrace(BaseModel):
    """A single step in the agent reasoning chain.

    Every agent decision is recorded as an immutable trace step.
    The full chain for a plan is reconstructed by ordering by step_sequence.
    """

    model_config = ConfigDict(extra="allow")

    decision_id: UUID
    step_sequence: int
    trigger_event: str  # violation_detected, demand_spike, capacity_change, etc.
    agent_id: str  # Which agent produced this step
    logic_version: str = ""  # Prompt/model version hash, e.g. "planning_v2.3"
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_ms: int = 0
    model_used: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# Experience Record — the central plan record
# =============================================================================


class ExperienceRecord(BaseModel):
    """A complete plan record in the Experience Ledger.

    Stores the full context (Demand/Supply/Policy snapshot at plan time),
    all negotiation rounds, final plan, and eventual outcome.

    Retention:
        Hot (90d):   Full detail in Postgres
        Warm (2y):   Summary only (context and trace may be pruned)
        Purge (>2y): Removed unless tagged `reference`
    """

    model_config = ConfigDict(extra="allow")

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID = Field(default_factory=uuid4)
    correlation_id: str = ""
    context: PlanContext = Field(default_factory=PlanContext)
    final_plan: list[dict[str, Any]] = Field(default_factory=list)
    negotiations: list[dict[str, Any]] = Field(default_factory=list)
    traces: list[PlanTrace] = Field(default_factory=list)
    outcome: PlanOutcome | None = None
    tags: list[str] = Field(default_factory=list)
    plan_confidence: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    warm_archived: bool = False  # True when moved from hot → warm storage


# =============================================================================
# Lookup helpers
# =============================================================================


def compute_plan_confidence(
    traces: list[PlanTrace],
    negotiation_resolution_factor: float = 1.0,
) -> float:
    """Compute plan-level confidence from per-step confidence.

    Formula: plan_confidence = avg(step.confidence) × negotiation_resolution_factor

    negotiation_resolution_factor:
        1.0 — resolved naturally
        0.7 — deadlock-resolved (weighted-random tiebreaker)
        0.5 — HITL-overridden (human rejected and forced a different outcome)
    """
    if not traces:
        return 0.5 * negotiation_resolution_factor

    avg_step = sum(t.confidence for t in traces) / len(traces)
    return round(avg_step * negotiation_resolution_factor, 4)
