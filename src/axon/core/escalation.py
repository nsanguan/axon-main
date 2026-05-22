"""Escalation Engine — severity scoring and 4-tier escalation ladder.

Replaces the simple `_needs_hitl()` boolean with a structured escalation
pipeline: Worker → Manager → Director → Executive.

Each level has a severity score threshold. Events that exceed a threshold
are escalated to the next level. The Executive tier includes HITL interrupt.

Scoring formula:  severity = impact_value × urgency × dept_count × customer_risk
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from axon.core.telemetry import log_event


class EscalationLevel(StrEnum):
    """Four-tier escalation ladder."""

    WORKER = "worker"  # Alert detection, initial scoring
    MANAGER = "manager"  # Within-department resolution
    DIRECTOR = "director"  # Cross-department coordination
    EXECUTIVE = "executive"  # Strategic HITL decision


class EventType(StrEnum):
    """Supply chain disruption event types."""

    PO_DELAY = "po_delay"
    PRODUCTION_BROKEN = "production_broken"
    MACHINE_BROKEN = "machine_broken"
    DEMAND_SPIKE = "demand_spike"
    INVENTORY_SHORTAGE = "inventory_shortage"
    QUALITY_INCIDENT = "quality_incident"
    SUPPLIER_CRISIS = "supplier_crisis"
    CUSTOMER_COMPLAINT = "customer_complaint"
    SAFETY_INCIDENT = "safety_incident"


class RiskLevel(StrEnum):
    """Risk assessment levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(StrEnum):
    """Executive-level action types."""

    HALT = "halt"
    NOTIFY = "notify"
    APPROVE = "approve"
    DEFER = "defer"
    ESCALATE = "escalate"
    INVESTIGATE = "investigate"


# =============================================================================
# Severity thresholds
# =============================================================================

# Score thresholds for escalation
MANAGER_MAX = 2_000  # ≤ 2K → manager handles within department
DIRECTOR_MAX = 10_000  # ≤ 10K → director coordinates cross-department
# > 10K → executive strategic decision + HITL

# Event types that ALWAYS go to Executive regardless of score
ALWAYS_EXECUTIVE: set[EventType] = {
    EventType.PRODUCTION_BROKEN,
    EventType.SAFETY_INCIDENT,
    EventType.SUPPLIER_CRISIS,
}


# =============================================================================
# Models
# =============================================================================


@dataclass
class StrategicAction:
    """A recommended action at the Executive level."""

    action_type: ActionType
    target: str
    description: str
    estimated_impact: str
    reversible: bool
    urgency_hours: int = 0
    responsible_dept: str = "operations"


@dataclass
class EscalationStep:
    """Single step in the escalation audit trail."""

    level: EscalationLevel
    agent: str
    summary: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EscalationState:
    """State accumulated through the escalation ladder."""

    event_type: EventType
    raw_detail: str
    severity_score: float = 0.0
    affected_departments: list[str] = field(default_factory=list)
    steps: list[EscalationStep] = field(default_factory=list)
    human_decision: str = ""
    final_summary: str = ""


class SeverityScorer:
    """Computes severity scores for escalation routing.

    Formula:  score = impact_value × urgency × dept_count × customer_risk

    Each event type has a default impact, urgency, and customer risk.
    Override via constructor for custom scoring per scenario.
    """

    DEFAULT_SCORING: dict[str, dict[str, float]] = {
        "po_delay": {"impact": 80_000, "urgency": 2.5, "customer_risk": 1.2},
        "production_broken": {"impact": 500_000, "urgency": 3.0, "customer_risk": 2.0},
        "machine_broken": {"impact": 50_000, "urgency": 1.5, "customer_risk": 1.0},
        "demand_spike": {"impact": 200_000, "urgency": 2.0, "customer_risk": 1.5},
        "inventory_shortage": {"impact": 100_000, "urgency": 2.0, "customer_risk": 1.3},
        "quality_incident": {"impact": 150_000, "urgency": 2.5, "customer_risk": 1.8},
        "supplier_crisis": {"impact": 300_000, "urgency": 3.0, "customer_risk": 2.0},
        "customer_complaint": {"impact": 30_000, "urgency": 1.5, "customer_risk": 1.0},
        "safety_incident": {"impact": 1_000_000, "urgency": 4.0, "customer_risk": 3.0},
    }

    def __init__(self, custom_scoring: dict[str, dict[str, float]] | None = None):
        self._scoring = {**self.DEFAULT_SCORING, **(custom_scoring or {})}

    def compute(
        self,
        event_type: EventType,
        dept_count: int = 1,
        override_impact: float | None = None,
        override_urgency: float | None = None,
        override_customer_risk: float | None = None,
    ) -> float:
        """Compute severity score.

        Args:
            event_type: Type of disruption event.
            dept_count: Number of affected departments.
            override_impact: Override default impact value.
            override_urgency: Override default urgency multiplier.
            override_customer_risk: Override default customer risk multiplier.

        Returns:
            Severity score (positive float).
        """
        params = self._scoring.get(
            event_type.value, {"impact": 10_000, "urgency": 1.0, "customer_risk": 1.0}
        )
        impact = override_impact if override_impact is not None else params["impact"]
        urgency = override_urgency if override_urgency is not None else params["urgency"]
        cust_risk = (
            override_customer_risk
            if override_customer_risk is not None
            else params["customer_risk"]
        )

        score = impact * urgency * dept_count * cust_risk

        # Hardcoded events always reach Executive
        if event_type in ALWAYS_EXECUTIVE:
            score = max(score, DIRECTOR_MAX + 1)

        return round(score, 2)

    def route(self, score: float, event_type: EventType) -> EscalationLevel:
        """Determine which escalation level should handle this event."""
        if event_type in ALWAYS_EXECUTIVE or score > DIRECTOR_MAX:
            return EscalationLevel.EXECUTIVE
        if score > MANAGER_MAX:
            return EscalationLevel.DIRECTOR
        return EscalationLevel.MANAGER

    def needs_hitl(self, score: float, event_type: EventType, priority: int = 0) -> bool:
        """Determine if this event requires HITL.

        HITL is required when:
        - Severity score > DIRECTOR_MAX (Executive level)
        - Event type is in ALWAYS_EXECUTIVE
        - VIP priority > 80 (mandatory per AGENTS.md spec)
        - VIP priority > 80 and score > MANAGER_MAX (belt-and-suspenders)
        """
        if event_type in ALWAYS_EXECUTIVE:
            return True
        if priority > 80:
            return True
        if score > DIRECTOR_MAX:
            return True
        return bool(score > MANAGER_MAX)


# =============================================================================
# Escalation helper
# =============================================================================


def determine_escalation_level(
    event_type: str,
    severity_score: float,
    priority: int = 0,
) -> EscalationLevel:
    """Quick helper to determine escalation level from event context.

    Used by MasterGraph's approve node to route to the correct level.
    """
    try:
        etype = EventType(event_type)
    except ValueError:
        etype = EventType.PO_DELAY

    scorer = SeverityScorer()
    return scorer.route(severity_score, etype)


def compute_severity_from_state(state: dict[str, Any]) -> float:
    """Compute severity score from a planning state dict.

    Extracts event-type info from the state and computes a severity score
    suitable for escalation routing.
    """
    demands = state.get("demands", []) or state.get("raw_demands", [])
    state.get("supplies", []) or state.get("raw_supplies", [])
    deadlock = state.get("deadlock", False)
    negotiation_rounds = state.get("negotiation_rounds", [])
    state.get("traces", [])

    # Determine event type from context
    event_type = EventType.PO_DELAY
    if deadlock:
        event_type = EventType.PRODUCTION_BROKEN
    elif negotiation_rounds and len(negotiation_rounds) > 2:
        event_type = EventType.SUPPLIER_CRISIS
    elif any(d.get("priority", 0) > 95 for d in demands):
        event_type = EventType.DEMAND_SPIKE

    # Compute factors
    proposals = state.get("agent_proposals", {})
    agent_ids = {p.get("agent_id", "unknown") for p in proposals.values() if isinstance(p, dict)}
    dept_count = max(1, len(agent_ids))
    # If there are no real demands, this is a test/empty cycle — score low
    if not demands:
        return 0.0
    impact = sum(float(d.get("quantity", 0)) * d.get("priority", 50) / 100 for d in demands)

    scorer = SeverityScorer()
    score = scorer.compute(
        event_type,
        dept_count=dept_count,
        override_impact=float(impact),
    )

    log_event(
        "info",
        "severity_computed",
        event_type=event_type.value,
        score=score,
        dept_count=dept_count,
    )

    return score
