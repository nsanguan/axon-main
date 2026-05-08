"""
tests/test_executive_agent.py
==============================
Unit tests สำหรับ Executive Agent
ใช้ mock output — ไม่ต้องเรียก LLM จริง
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from datetime import datetime, timezone, timedelta

# ── Test schemas ──────────────────────────────────────────────────────────────
from agents.executive.schemas import (
    ExecutiveInput,
    ExecutiveOutput,
    IntentClassification,
    StrategicAction,
    ActionType,
    EventType,
    RiskLevel,
    EscalationStep,
    CustomerImpact,
)
from agents.executive.agent import make_mock_executive_output
from agents.executive.prompts import (
    build_intent_router_prompt,
    build_crisis_decider_prompt,
    build_coordinator_prompt,
)


def test_executive_output_schema():
    """ExecutiveOutput validates correctly"""
    output = make_mock_executive_output("machine_broken")
    assert output.risk_level == RiskLevel.HIGH
    assert output.requires_human_approval is True
    assert len(output.recommended_actions) >= 1
    assert all(isinstance(a, StrategicAction) for a in output.recommended_actions)
    print("✅ test_executive_output_schema passed")


def test_executive_output_rejects_false_approval():
    """requires_human_approval=False must raise ValidationError"""
    from pydantic import ValidationError
    try:
        ExecutiveOutput(
            risk_level=RiskLevel.HIGH,
            rationale="x" * 50,
            recommended_actions=[
                StrategicAction(
                    action_type=ActionType.HALT,
                    target="test",
                    description="test action description here",
                    estimated_impact="some impact",
                    reversible=True,
                    urgency_hours=1,
                    responsible_dept="ops",
                )
            ],
            requires_human_approval=False,   # ← ต้อง raise
            notify_external=False,
            estimated_resolution_hours=4,
            executive_brief="Test brief for executive review and approval",
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "requires_human_approval" in str(e)
        print("✅ test_executive_output_rejects_false_approval passed")


def test_executive_input_schema():
    """ExecutiveInput validates correctly"""
    inp = ExecutiveInput(
        event_type=EventType.PRODUCTION_BROKEN,
        severity_score=1_500_000.0,
        affected_departments=["production", "sales", "warehouse", "purchasing"],
        director_summary="All 4 production lines halted. Director cannot resolve without Executive authority to halt facility and notify customers.",
        escalation_history=[
            EscalationStep(level="worker",   agent="worker_agent",    summary="Detected production stop"),
            EscalationStep(level="manager",  agent="manager_agent",   summary="Could not resolve"),
            EscalationStep(level="director", agent="director_agent",  summary="Needs Executive authority"),
        ],
        financial_exposure_thb=5_000_000.0,
        decision_deadline_utc=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    assert inp.event_type == EventType.PRODUCTION_BROKEN
    assert len(inp.affected_departments) == 4
    print("✅ test_executive_input_schema passed")


def test_intent_classification_schema():
    """IntentClassification validates correctly"""
    cls = IntentClassification(
        intent_id="stock_check_reorder",
        flow_name="stock_check_reorder_flow",
        confidence=0.97,
        entities={"wh": "WH01", "store": "KB-001"},
        priority="normal",
    )
    assert 0.0 <= cls.confidence <= 1.0
    assert cls.fallback is False
    print("✅ test_intent_classification_schema passed")


def test_intent_classification_rejects_bad_confidence():
    """confidence > 1.0 must raise ValidationError"""
    from pydantic import ValidationError
    try:
        IntentClassification(
            intent_id="test",
            flow_name="test_flow",
            confidence=1.5,       # ← invalid
            priority="normal",
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("✅ test_intent_classification_rejects_bad_confidence passed")


def test_board_escalation_requires_reason():
    """escalate_to_board=True without reason must raise ValidationError"""
    from pydantic import ValidationError
    try:
        ExecutiveOutput(
            risk_level=RiskLevel.CRITICAL,
            rationale="x" * 50,
            recommended_actions=[
                StrategicAction(
                    action_type=ActionType.ESCALATE,
                    target="board",
                    description="escalate to board immediately",
                    estimated_impact="board level decision",
                    reversible=False,
                    urgency_hours=0,
                    responsible_dept="executive",
                )
            ],
            requires_human_approval=True,
            notify_external=True,
            estimated_resolution_hours=24,
            executive_brief="Critical event requiring board decision",
            escalate_to_board=True,
            board_escalation_reason="",   # ← ต้อง raise
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "board_escalation_reason" in str(e)
        print("✅ test_board_escalation_requires_reason passed")


def test_prompts_build_without_error():
    """All prompt builders return non-empty strings"""
    p1 = build_intent_router_prompt()
    assert len(p1) > 100
    print(f"✅ intent_router_prompt: {len(p1)} chars")

    p2 = build_crisis_decider_prompt(
        event_type="production_broken",
        severity_score=1_500_000,
        affected_departments=["production", "sales"],
        director_summary="Director could not resolve cross-dept impact",
        financial_exposure=5_000_000,
        decision_deadline="2026-05-05T10:00:00Z",
        escalation_trail="  [worker] detected | [manager] failed | [director] escalated",
    )
    assert "production_broken" in p2
    print(f"✅ crisis_decider_prompt: {len(p2)} chars")

    p3 = build_coordinator_prompt({
        "production": "Halt line A",
        "sales": "Notify customers",
    })
    assert "production" in p3.lower()
    print(f"✅ coordinator_prompt: {len(p3)} chars")

    print("✅ test_prompts_build_without_error passed")


def test_mock_executive_output_for_all_events():
    """mock factory works for all event types"""
    for event in ["machine_broken", "production_broken", "po_delay", "damage_stock"]:
        out = make_mock_executive_output(event)
        assert out.requires_human_approval is True
        assert len(out.recommended_actions) >= 1
        assert len(out.executive_brief) >= 30
    print("✅ test_mock_executive_output_for_all_events passed")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Executive Agent — Unit Tests")
    print("="*60 + "\n")

    test_executive_output_schema()
    test_executive_output_rejects_false_approval()
    test_executive_input_schema()
    test_intent_classification_schema()
    test_intent_classification_rejects_bad_confidence()
    test_board_escalation_requires_reason()
    test_prompts_build_without_error()
    test_mock_executive_output_for_all_events()

    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
