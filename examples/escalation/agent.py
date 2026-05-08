"""
agents/executive/agent.py
==========================
Executive Agent — PydanticAI implementation
สองโหมด: Intent Router (ทุก request) + Crisis Decider (escalation เท่านั้น)

PydanticAI ดูแล:
  - Type-safe input/output ผ่าน BaseModel
  - Auto self-correction (retry) เมื่อ LLM ตอบผิด schema
  - Dependency injection สำหรับ config

LangGraph ดูแล:
  - เรียก agent นี้เป็น node
  - ส่ง state เข้า / รับ result ออก
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from agents.executive.prompts import (
    RETRY_HINT,
    build_coordinator_prompt,
    build_crisis_decider_prompt,
    build_intent_router_prompt,
)
from agents.executive.schemas import (
    EscalationStep,
    ExecutiveInput,
    ExecutiveOutput,
    IntentClassification,
    RiskLevel,
    StrategicAction,
    ActionType,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Config / Dependencies (inject via RunContext)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExecutiveAgentDeps:
    """
    Dependencies ที่ inject เข้า agent ตอน run
    ใช้ RunContext[ExecutiveAgentDeps] ใน tool functions
    """
    model_name:  str   = "gpt-4o"          # swap to "claude-sonnet-4-20250514"
    max_retries: int   = 3
    temperature: float = 0.1               # ต่ำ = deterministic, ดีสำหรับ routing
    log_level:   str   = "INFO"


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 — Intent Router
# ─────────────────────────────────────────────────────────────────────────────

_intent_router_agent: Agent[ExecutiveAgentDeps, IntentClassification] = Agent(
    model=OpenAIModel("gpt-4o"),
    result_type=IntentClassification,    # PydanticAI enforce schema ให้เลย
    system_prompt=build_intent_router_prompt(),
    retries=3,                           # retry อัตโนมัติถ้า LLM ตอบผิด schema
    result_retries=2,                    # retry เฉพาะ result validation
)


@_intent_router_agent.system_prompt
def _inject_timestamp(ctx: RunContext[ExecutiveAgentDeps]) -> str:
    """Inject current time ทุกครั้งที่ call — ช่วย urgency detection"""
    return f"Current time: {datetime.now(timezone.utc).isoformat()}"


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 — Crisis Decider
# ─────────────────────────────────────────────────────────────────────────────

_crisis_decider_agent: Agent[ExecutiveAgentDeps, ExecutiveOutput] = Agent(
    model=OpenAIModel("gpt-4o"),
    result_type=ExecutiveOutput,
    system_prompt=RETRY_HINT,            # base prompt — override per-call below
    retries=3,
    result_retries=3,                    # crisis decisions need more retry budget
)


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Intent Router
# ─────────────────────────────────────────────────────────────────────────────

async def classify_intent(
    user_message: str,
    deps: ExecutiveAgentDeps | None = None,
) -> IntentClassification:
    """
    Classify user message → route to correct flow
    เรียกจาก LangGraph node ทุก request

    Args:
        user_message: raw user input
        deps: optional override config

    Returns:
        IntentClassification with flow_name + entities
    """
    if deps is None:
        deps = ExecutiveAgentDeps()

    logger.info(f"[Executive:IntentRouter] Classifying: {user_message[:80]}...")

    result = await _intent_router_agent.run(
        user_message,
        deps=deps,
    )

    logger.info(
        f"[Executive:IntentRouter] → flow={result.data.flow_name} "
        f"confidence={result.data.confidence:.2f} "
        f"priority={result.data.priority}"
    )
    return result.data


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Crisis Decider
# ─────────────────────────────────────────────────────────────────────────────

async def assess_crisis(
    executive_input: ExecutiveInput,
    deps: ExecutiveAgentDeps | None = None,
) -> ExecutiveOutput:
    """
    Strategic assessment of escalated business-critical event
    เรียกจาก LangGraph executive_node หลังจาก Director escalate

    Args:
        executive_input: structured context from Director
        deps: optional override config

    Returns:
        ExecutiveOutput with recommended_actions (pending human approval)
    """
    if deps is None:
        deps = ExecutiveAgentDeps()

    # Build escalation trail text
    trail = "\n".join(
        f"  [{s.level}] {s.agent}: {s.summary}"
        for s in executive_input.escalation_history
    ) or "  (no prior escalation steps recorded)"

    # Build dynamic system prompt with full context
    system_prompt = build_crisis_decider_prompt(
        event_type=executive_input.event_type.value,
        severity_score=executive_input.severity_score,
        affected_departments=executive_input.affected_departments,
        director_summary=executive_input.director_summary,
        financial_exposure=executive_input.financial_exposure_thb,
        decision_deadline=executive_input.decision_deadline_utc.isoformat(),
        escalation_trail=trail,
    )

    logger.info(
        f"[Executive:CrisisDecider] Assessing event={executive_input.event_type.value} "
        f"score={executive_input.severity_score:,.0f} "
        f"depts={executive_input.affected_departments}"
    )

    # Override system prompt per-call for full context injection
    result = await _crisis_decider_agent.run(
        executive_input.model_dump_json(indent=2),
        deps=deps,
        model_settings={"temperature": deps.temperature},
        system_prompt=system_prompt,      # dynamic override
    )

    assessment: ExecutiveOutput = result.data

    logger.info(
        f"[Executive:CrisisDecider] risk={assessment.risk_level} "
        f"actions={len(assessment.recommended_actions)} "
        f"board={assessment.escalate_to_board}"
    )

    return assessment


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph Node functions
# ─────────────────────────────────────────────────────────────────────────────

async def executive_intent_router_node(state: dict) -> dict:
    """
    LangGraph Node — Intent Router mode
    เรียกตอนเริ่ม flow ทุกครั้ง เพื่อ classify user message

    State keys read  : messages[-1].content (user message)
    State keys written: intent_classification, flow_name, entities, priority
    """
    from langchain_core.messages import AIMessage

    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if hasattr(m, "content") and m.content:
            user_msg = m.content
            break

    if not user_msg:
        logger.warning("[Executive:Node] No user message found in state")
        return {
            "flow_name": "general_inquiry_flow",
            "entities":  {},
            "priority":  "normal",
        }

    classification = await classify_intent(user_msg)

    return {
        "intent_id":             classification.intent_id,
        "flow_name":             classification.flow_name,
        "entities":              classification.entities,
        "priority":              classification.priority,
        "intent_confidence":     classification.confidence,
        "messages": [
            AIMessage(
                content=(
                    f"[Executive:Router] Intent={classification.intent_id} "
                    f"→ {classification.flow_name} "
                    f"(confidence={classification.confidence:.0%})"
                )
            )
        ],
    }


async def executive_crisis_node(state: dict) -> dict:
    """
    LangGraph Node — Crisis Decider mode
    เรียกเมื่อ severity score > 10,000 หรือ event อยู่ใน ALWAYS_EXECUTIVE list

    State keys read  : event_type, severity_score, affected_departments,
                       director_result, escalation_history, raw_detail
    State keys written: executive_result, messages
    """
    from langchain_core.messages import AIMessage

    # ── Build ExecutiveInput from LangGraph state ─────────────────────────────
    director_result = state.get("director_result")
    director_summary = (
        director_result.escalation_reason
        if director_result and hasattr(director_result, "escalation_reason")
        else state.get("raw_detail", "No director summary available")
    )

    # Estimate financial exposure from severity score (override with real ERP data)
    financial_exposure = state.get("financial_exposure_thb", state.get("severity_score", 0) * 1.5)

    # Default deadline: 4 hours from now for critical events
    deadline = datetime.now(timezone.utc) + timedelta(hours=4)

    executive_input = ExecutiveInput(
        event_type=state["event_type"],
        severity_score=state["severity_score"],
        affected_departments=state.get("affected_departments", ["operations"]),
        director_summary=director_summary,
        escalation_history=[
            EscalationStep(
                level=s.level if hasattr(s, "level") else str(s.get("level", "unknown")),
                agent=s.agent if hasattr(s, "agent") else str(s.get("agent", "unknown")),
                summary=s.summary if hasattr(s, "summary") else str(s.get("summary", "")),
            )
            for s in state.get("escalation_history", [])
        ],
        financial_exposure_thb=financial_exposure,
        decision_deadline_utc=deadline,
    )

    assessment = await assess_crisis(executive_input)

    # Format actions for logging
    actions_log = "; ".join(
        f"{a.action_type.value}:{a.target}"
        for a in assessment.recommended_actions
    )
    logger.info(f"[Executive:Node] Actions: {actions_log}")

    return {
        "executive_result": assessment,
        "messages": [
            AIMessage(
                content=(
                    f"[Executive:Crisis] risk={assessment.risk_level} | "
                    f"{len(assessment.recommended_actions)} actions | "
                    f"board={assessment.escalate_to_board} | "
                    f"brief: {assessment.executive_brief}"
                )
            )
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator (fan-out synthesis)
# ─────────────────────────────────────────────────────────────────────────────

async def synthesize_department_plans(
    department_plans: dict[str, str],
    deps: ExecutiveAgentDeps | None = None,
) -> str:
    """
    ใช้เมื่อ Executive ต้องรวม action plans จากหลาย Director
    Returns: unified_directive string
    """
    if deps is None:
        deps = ExecutiveAgentDeps()

    prompt = build_coordinator_prompt(department_plans)

    # Simple text completion — no structured output needed for coordinator
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = init_chat_model(f"openai:{deps.model_name}")
    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Please synthesize the above department plans into a unified executive directive."),
    ])
    return response.content


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: mock factory for testing without real LLM
# ─────────────────────────────────────────────────────────────────────────────

def make_mock_executive_output(event_type: str = "machine_broken") -> ExecutiveOutput:
    """
    สร้าง mock output สำหรับ unit test
    ไม่ต้องเรียก LLM จริง
    """
    return ExecutiveOutput(
        risk_level=RiskLevel.HIGH,
        rationale=(
            "Directors were unable to resolve the cross-departmental impact. "
            "Production halt affects delivery commitments to 3 key customers. "
            "Emergency procurement and production rescheduling required."
        ),
        recommended_actions=[
            StrategicAction(
                action_type=ActionType.HALT,
                target="production_line_A_B",
                description="Halt lines A and B immediately to prevent further WIP accumulation",
                estimated_impact="Stops 50% of output but preserves quality standards",
                reversible=True,
                urgency_hours=0,
                responsible_dept="production",
            ),
            StrategicAction(
                action_type=ActionType.NOTIFY,
                target="key_customers_TH001_TH003",
                description="Notify customers TH001 and TH003 of 2-day delivery delay",
                estimated_impact="Maintains customer trust through proactive communication",
                reversible=True,
                urgency_hours=2,
                responsible_dept="sales",
            ),
            StrategicAction(
                action_type=ActionType.APPROVE,
                target="emergency_maintenance_budget",
                description="Approve emergency budget 500,000 THB for spare parts procurement",
                estimated_impact="Enables immediate machine repair",
                reversible=False,
                urgency_hours=1,
                responsible_dept="finance",
            ),
        ],
        requires_human_approval=True,
        notify_external=True,
        external_notify_list=["customer_TH001", "customer_TH003"],
        estimated_resolution_hours=8,
        escalate_to_board=False,
        executive_brief=(
            f"Critical {event_type} event affecting production and 2 key customers. "
            "Recommend immediate production halt, emergency maintenance approval, "
            "and proactive customer notification. Est. 8h resolution."
        ),
    )
