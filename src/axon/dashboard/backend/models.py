"""Dashboard API models — request/response schemas for the Control Tower."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from axon.orchestrator.conflict_resolver import BusinessWeights

# ---------------------------------------------------------------------------
# Weight management
# ---------------------------------------------------------------------------


class WeightsResponse(BaseModel):
    weights: BusinessWeights
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WeightsUpdateRequest(BaseModel):
    cost: float | None = None
    delivery: float | None = None
    quality: float | None = None
    sustainability: float | None = None
    flexibility: float | None = None

    def apply_to(self, weights: BusinessWeights) -> BusinessWeights:
        if self.cost is not None:
            weights.cost = self.cost
        if self.delivery is not None:
            weights.delivery = self.delivery
        if self.quality is not None:
            weights.quality = self.quality
        if self.sustainability is not None:
            weights.sustainability = self.sustainability
        if self.flexibility is not None:
            weights.flexibility = self.flexibility
        return weights


# ---------------------------------------------------------------------------
# Plan listing
# ---------------------------------------------------------------------------


class PlanSummary(BaseModel):
    plan_id: UUID
    created_at: datetime
    tags: list[str] = Field(default_factory=list)
    plan_confidence: float | None = None
    allocation_count: int = 0
    deadlock: bool = False
    approved: bool = False


class PlanListResponse(BaseModel):
    plans: list[PlanSummary]
    total: int
    offset: int = 0
    limit: int = 20


class PlanDetailResponse(BaseModel):
    plan_id: UUID
    context: dict[str, Any] = Field(default_factory=dict)
    final_plan: list[dict[str, Any]] = Field(default_factory=list)
    negotiations: list[dict[str, Any]] = Field(default_factory=list)
    traces: list[dict[str, Any]] = Field(default_factory=list)
    outcome: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    plan_confidence: float | None = None
    created_at: datetime | None = None
    approved: bool = False
    approval_note: str = ""


# ---------------------------------------------------------------------------
# HITL approval
# ---------------------------------------------------------------------------


class PendingApproval(BaseModel):
    plan_id: UUID
    context_summary: str
    deadlock: bool = False
    demand_count: int = 0
    supply_count: int = 0
    agent_proposals: int = 0
    negotiation_rounds: int = 0
    global_utility: float | None = None
    created_at: datetime | None = None
    requires_approval: bool = True


class ApprovalAction(BaseModel):
    plan_id: UUID
    approved: bool
    note: str = ""


# ---------------------------------------------------------------------------
# Agent overview
# ---------------------------------------------------------------------------


class AgentInfo(BaseModel):
    agent_id: str
    domain: str
    tool_count: int
    tool_names: list[str] = Field(default_factory=list)


class SystemHealth(BaseModel):
    degradation_level: str
    healthy_servers: list[str]
    unhealthy_servers: list[str]
    total_plans: int
    pending_approvals: int


# ---------------------------------------------------------------------------
# Engine monitoring
# ---------------------------------------------------------------------------


class ThreadInfo(BaseModel):
    """Status of a single LangGraph orchestration thread."""

    thread_id: str
    event_type: str
    status: str  # running | waiting_for_approval | completed | error
    progress: float = 0.0  # 0.0 – 1.0
    severity_score: float = 0.0
    escalation_level: str = "worker"
    affected_departments: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: str = ""
    updated_at: str = ""


class EngineSummary(BaseModel):
    """Aggregate engine monitoring statistics."""

    total_threads: int = 0
    running: int = 0
    waiting_for_approval: int = 0
    completed: int = 0
    error: int = 0
    avg_severity: float = 0.0
    top_escalation_level: str = "none"
