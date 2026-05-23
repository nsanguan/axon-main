"""
Experience Ledger Schema — Pydantic models for plan recording, retrieval, and audit.

Mirrors the database tables defined in `schema/migrate.py` (experience_records,
plan_traces) and provides the typed Python interface for the Learning module.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PlanTrace(BaseModel):
    """A single step in an agent's reasoning chain during a planning cycle.

    Every agent decision is recorded as an immutable trace step.
    The full chain for a plan is reconstructed by ordering by step_sequence.
    """

    model_config = ConfigDict(extra="allow")

    decision_id: UUID
    step_sequence: int
    trigger_event: str
    agent_id: str
    logic_version: str | None = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    duration_ms: int = 0
    model_used: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlanContext(BaseModel):
    """Snapshot of the full planning environment when a plan was created."""

    model_config = ConfigDict(extra="allow")

    demands: list[dict[str, Any]] = Field(default_factory=list)
    supplies: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    business_weights: dict[str, float] = Field(default_factory=dict)
    degradation_level: str = "FULL"
    correlation_id: str = ""


class PlanOutcome(BaseModel):
    """Result of executing a plan, populated later when actuals are known.

    Combines financial, delivery, and quality outcome tracking.
    """

    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    on_time: bool | None = None
    on_budget: bool | None = None
    over_budget: bool = False
    replan_triggered: bool = False
    total_demand_fulfilled_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    actual_cost: float | None = None
    cost_variance_pct: float | None = None
    days_late: int = 0
    delivery_variance_days: int | None = None
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    violations_detected: int = 0
    notes: str = ""
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
    plan_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    warm_archived: bool = False
    is_reference: bool = False


class SimilarPlanResult(BaseModel):
    """One result from retrieve_similar()."""

    plan: ExperienceRecord
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str] = Field(default_factory=list)


class LedgerQuery(BaseModel):
    """Query parameters for retrieving plans from the ledger."""

    plan_id: UUID | None = None
    tags: list[str] | None = None
    agent_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 20
    offset: int = 0
    include_outcomes: bool = False


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
