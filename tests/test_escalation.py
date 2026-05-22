"""Tests for escalation engine, supervisor pattern, and HITL approval API."""

from __future__ import annotations

from axon.core.escalation import (
    EventType,
    SeverityScorer,
    compute_severity_from_state,
    determine_escalation_level,
)
from axon.orchestrator.supervisor import classify_agents_needed, supervisor_dispatch

# =============================================================================
# SeverityScorer Tests
# =============================================================================


class TestSeverityScorer:
    def test_compute_defaults(self):
        scorer = SeverityScorer()
        score = scorer.compute(EventType.PO_DELAY, dept_count=2)
        assert score > 100_000  # 80K × 2.5 × 2 × 1.2 = 480K

    def test_compute_machine_broken(self):
        scorer = SeverityScorer()
        score = scorer.compute(EventType.MACHINE_BROKEN, dept_count=1)
        assert 50_000 < score < 200_000  # 50K × 1.5 × 1 × 1.0 = 75K

    def test_compute_production_broken_always_executive(self):
        scorer = SeverityScorer()
        score = scorer.compute(EventType.PRODUCTION_BROKEN, dept_count=1)
        assert score > 10_000  # Always pushed to executive

    def test_route_manager(self):
        scorer = SeverityScorer()
        level = scorer.route(500, EventType.PO_DELAY)
        assert level.value == "manager"

    def test_route_director(self):
        scorer = SeverityScorer()
        level = scorer.route(5_000, EventType.PO_DELAY)
        assert level.value == "director"

    def test_route_executive(self):
        scorer = SeverityScorer()
        level = scorer.route(50_000, EventType.PO_DELAY)
        assert level.value == "executive"

    def test_needs_hitl_vip_order(self):
        scorer = SeverityScorer()
        result = scorer.needs_hitl(5_000, EventType.PO_DELAY, priority=90)
        assert result is True  # VIP + score > MANAGER_MAX

    def test_needs_hitl_low_priority(self):
        scorer = SeverityScorer()
        result = scorer.needs_hitl(500, EventType.PO_DELAY, priority=50)
        assert result is False

    def test_needs_hitl_high_score(self):
        scorer = SeverityScorer()
        result = scorer.needs_hitl(50_000, EventType.PO_DELAY)
        assert result is True

    def test_needs_hitl_always_executive(self):
        scorer = SeverityScorer()
        result = scorer.needs_hitl(100, EventType.PRODUCTION_BROKEN)
        assert result is True

    def test_compute_severity_from_empty_state(self):
        result = compute_severity_from_state({})
        assert result == 0.0  # No demands → 0

    def test_compute_severity_with_demands(self):
        state = {
            "demands": [{"item": "FG-001", "quantity": 100, "priority": 90}],
        }
        result = compute_severity_from_state(state)
        assert result > 0  # Has demands → non-zero

    def test_determine_escalation_level(self):
        level = determine_escalation_level("po_delay", 500)
        assert level.value == "manager"


# =============================================================================
# Supervisor Pattern Tests
# =============================================================================


class TestSupervisor:
    def test_classify_agents_empty_state(self):
        agents = classify_agents_needed({})
        assert "commercial" in agents

    def test_classify_agents_with_demands(self):
        agents = classify_agents_needed({"demands": [{"item": "FG-001"}]})
        assert "commercial" in agents

    def test_classify_agents_with_deadlock(self):
        agents = classify_agents_needed({"deadlock": True})
        assert "operations" in agents

    def test_classify_agents_vip_first(self):
        agents = classify_agents_needed(
            {
                "demands": [{"priority": 95}],
                "supplies": [{"item": "RM-001"}],
            }
        )
        assert agents[0] == "commercial"

    def test_supervisor_dispatch_first_round(self):
        target, updates = supervisor_dispatch({"demands": [{"item": "FG-001"}]}, 0)
        assert target == "agent_commercial"
        assert updates["_supervisor_round"] == 1

    def test_supervisor_dispatch_all_consulted(self):
        target, updates = supervisor_dispatch(
            {
                "demands": [{"item": "FG-001"}],
                "_supervisor_consulted": ["commercial"],
            },
            1,
        )
        assert target == "response_node"

    def test_supervisor_max_rounds(self):
        target, updates = supervisor_dispatch({}, MAX_SUPERVISOR_ROUNDS := 6)
        assert target == "response_node"


# =============================================================================
# Escalation Models Tests
# =============================================================================


class TestEscalationModels:
    def test_event_type_values(self):
        assert EventType.PO_DELAY.value == "po_delay"
        assert EventType.PRODUCTION_BROKEN.value == "production_broken"

    def test_severity_scorer_custom(self):
        scorer = SeverityScorer(
            custom_scoring={
                "po_delay": {"impact": 10_000, "urgency": 1.0, "customer_risk": 1.0},
            }
        )
        score = scorer.compute(EventType.PO_DELAY, dept_count=1)
        assert score == 10_000

    def test_override_impact(self):
        scorer = SeverityScorer()
        score = scorer.compute(EventType.PO_DELAY, override_impact=50_000)
        assert score > 100_000  # 50K × 2.5 × 1 × 1.2
