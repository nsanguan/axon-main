"""
Experience Ledger Schema — Pydantic models for plan recording, retrieval, and audit.

Mirrors the database tables defined in `schema/migrate.py` (experience_records,
plan_traces) and provides the typed Python interface for the Learning module.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PlanTrace(BaseModel):
    """A single step in an agent's reasoning chain during a planning cycle."""

    decision_id: UUID
    step_sequence: int
    trigger_event: str
    agent_id: str
    logic_version: str | None = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    duration_ms: int = 0
    model_used: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlanContext(BaseModel):
    """Snapshot of the full planning environment when a plan was created."""

    demands: list[dict[str, Any]] = Field(default_factory=list)
    supplies: list[dict[str, Any]] = Field(default_factory=list)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    business_weights: dict[str, float] = Field(default_factory=dict)
    degradation_level: str = "FULL"
    correlation_id: str = ""


class PlanOutcome(BaseModel):
    """Result of executing a plan, populated later when actuals are known."""

    on_time: bool | None = None
    on_budget: bool | None = None
    total_demand_fulfilled_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    actual_cost: float | None = None
    days_late: int = 0
    replan_triggered: bool = False
    notes: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExperienceRecord(BaseModel):
    """Complete record of a planning cycle, stored in the Experience Ledger.

    Hot storage (Postgres, full detail): last 90 days.
    Warm storage (summary only): 91 days - 2 years.
    Auto-purge after 2 years unless tagged 'reference'.
    """

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

    id: UUID | None = None
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
