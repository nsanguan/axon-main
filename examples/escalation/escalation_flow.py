# uv pip install langgraph>=1.0.0 langchain>=0.3.0 langchain-openai pydantic>=2.7.0
# uv pip install langgraph-checkpoint-postgres asyncpg pydantic-ai

"""
escalation_flow.py
==================
Escalation Architecture: Worker → Supervisor → Manager → Director → Executive
พร้อม Human-in-the-Loop interrupt ที่ระดับ Executive

Flow:
  START
    → worker_node          (ตรวจจับ event, score severity)
    → supervisor_node      (conditional: route ตาม score)
        → manager_node     (score ≤ 2,000  — จัดการภายในแผนก)
        → director_node    (score ≤ 10,000 — ข้ามแผนก, fan-out)
        → executive_node   (score > 10,000 — strategy, HITL interrupt)
    → response_node        (สรุปผลกลับ user)
    → END
"""

from __future__ import annotations

import operator
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver  # swap to AsyncPostgresSaver in prod
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, Send, interrupt
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────
llm = init_chat_model("openai:gpt-4o-mini")          # swap to claude-sonnet-4-20250514 if preferred


# ─────────────────────────────────────────────────────────────────────────────
# Enums & Constants
# ─────────────────────────────────────────────────────────────────────────────
class EventType(str, Enum):
    PO_DELAY           = "po_delay"
    PRODUCTION_BROKEN  = "production_broken"
    MACHINE_BROKEN     = "machine_broken"
    DAMAGE_STOCK       = "damage_stock"

class EscalationLevel(str, Enum):
    WORKER    = "worker"
    MANAGER   = "manager"
    DIRECTOR  = "director"
    EXECUTIVE = "executive"

# Events ที่ต้อง escalate ถึง Executive เสมอ ไม่ว่า score จะเท่าไหร่
ALWAYS_EXECUTIVE: set[EventType] = {
    EventType.PRODUCTION_BROKEN,
}

# Score thresholds
MANAGER_MAX   = 2_000
DIRECTOR_MAX  = 10_000
# > DIRECTOR_MAX → Executive


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────
class EscalationStep(BaseModel):
    level:      EscalationLevel
    agent:      str
    summary:    str
    timestamp:  datetime = Field(default_factory=datetime.utcnow)

class ActionType(str, Enum):
    HALT    = "halt"
    NOTIFY  = "notify"
    APPROVE = "approve"
    DEFER   = "defer"

class StrategicAction(BaseModel):
    action_type:       ActionType
    target:            str
    description:       str
    estimated_impact:  str
    reversible:        bool   # สำคัญ: ต้องบอก human ว่า undo ได้ไหม

class WorkerResult(BaseModel):
    event_type:          EventType
    severity_score:      float
    affected_departments: list[str]
    raw_detail:          str

class ManagerResult(BaseModel):
    resolved:          bool
    action_taken:      str
    escalation_needed: bool = False
    escalation_reason: str  = ""

class DirectorResult(BaseModel):
    resolved:                    bool
    cross_dept_actions:          list[str]
    escalation_needed:           bool = False
    escalation_reason:           str  = ""
    recommended_executive_action: str  = ""

class ExecutiveAssessment(BaseModel):
    risk_level:                  Literal["critical", "high", "medium"]
    recommended_actions:         list[StrategicAction]
    rationale:                   str
    requires_human_approval:     bool = True   # เสมอ
    notify_external:             bool
    estimated_resolution_hours:  int
    escalate_to_board:           bool = False


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────
class EscalationState(TypedDict):
    # ── Conversation ──────────────────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Event Info ────────────────────────────────────────────────────────────
    event_type:           str
    severity_score:       float
    affected_departments: list[str]
    raw_detail:           str

    # ── Results per level ─────────────────────────────────────────────────────
    worker_result:    WorkerResult   | None
    manager_result:   ManagerResult  | None
    director_result:  DirectorResult | None
    executive_result: ExecutiveAssessment | None

    # ── Audit trail (appends at each level) ───────────────────────────────────
    escalation_history: Annotated[list[EscalationStep], operator.add]

    # ── Human approval (set by interrupt resume) ──────────────────────────────
    human_decision: str   # "approve" | "reject" | "modify:<instruction>"

    # ── Final output ──────────────────────────────────────────────────────────
    final_summary: str


# ─────────────────────────────────────────────────────────────────────────────
# Helper: severity scoring
# ─────────────────────────────────────────────────────────────────────────────
def compute_severity(
    event_type: EventType,
    impact_value: float,
    urgency: float,
    dept_count: int,
    customer_risk: float = 1.0,
) -> float:
    """score = impact × urgency × dept_count × customer_risk"""
    score = impact_value * urgency * dept_count * customer_risk
    # Hardcoded events always reach Executive regardless of score
    if event_type in ALWAYS_EXECUTIVE:
        score = max(score, DIRECTOR_MAX + 1)
    return round(score, 2)


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1 — Worker Node
# ─────────────────────────────────────────────────────────────────────────────
def worker_node(state: EscalationState) -> dict:
    """
    ตรวจจับ event จาก MCP tools (WMS / ERP / IoT)
    และคำนวณ severity score
    """
    print("\n[Worker] 🔍 Detecting event...")

    # ── ในระบบจริง: เรียก MCP tools ดึง raw data ─────────────────────────────
    # ตัวอย่างนี้ simulate จาก state ที่ส่งเข้ามา
    event_type     = EventType(state["event_type"])
    raw_detail     = state.get("raw_detail", "No detail provided")
    affected_depts = state.get("affected_departments", ["operations"])

    # Simulate scoring logic (ในระบบจริงดึงจาก ERP)
    scoring_map = {
        EventType.PO_DELAY:          (80_000,  2.5, 1.2),
        EventType.PRODUCTION_BROKEN: (500_000, 3.0, 2.0),
        EventType.MACHINE_BROKEN:    (50_000,  1.5, 1.0),
        EventType.DAMAGE_STOCK:      (120_000, 2.0, 1.5),
    }
    impact, urgency, cust_risk = scoring_map.get(event_type, (10_000, 1.0, 1.0))
    score = compute_severity(event_type, impact, urgency, len(affected_depts), cust_risk)

    print(f"[Worker] Event={event_type.value}, Score={score:,.0f}, Depts={affected_depts}")

    result = WorkerResult(
        event_type=event_type,
        severity_score=score,
        affected_departments=affected_depts,
        raw_detail=raw_detail,
    )

    step = EscalationStep(
        level=EscalationLevel.WORKER,
        agent="worker_agent",
        summary=f"Detected {event_type.value} | score={score:,.0f} | depts={affected_depts}",
    )

    return {
        "worker_result":    result,
        "severity_score":   score,
        "escalation_history": [step],
        "messages": [AIMessage(f"[Worker] Event detected: {event_type.value}, severity={score:,.0f}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2 — Supervisor Node (conditional router)
# ─────────────────────────────────────────────────────────────────────────────
def supervisor_node(state: EscalationState) -> Command[
    Literal["manager_node", "director_node", "executive_node"]
]:
    """
    ตรวจ score แล้วตัดสินใจ route ไประดับที่เหมาะสม
    Worker ส่งทุกอย่างขึ้นมาที่นี่ก่อนเสมอ
    """
    score      = state["severity_score"]
    event_type = EventType(state["event_type"])

    print(f"\n[Supervisor] 🔀 Routing score={score:,.0f} ...")

    # Hardcoded events ข้ามไป Executive เสมอ
    if event_type in ALWAYS_EXECUTIVE or score > DIRECTOR_MAX:
        target = "executive_node"
        label  = "EXECUTIVE"
    elif score > MANAGER_MAX:
        target = "director_node"
        label  = "DIRECTOR"
    else:
        target = "manager_node"
        label  = "MANAGER"

    print(f"[Supervisor] → Route to {label}")

    step = EscalationStep(
        level=EscalationLevel.WORKER,
        agent="supervisor",
        summary=f"Routed to {label} (score={score:,.0f})",
    )

    return Command(
        goto=target,
        update={"escalation_history": [step]},
    )


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3a — Manager Node
# ─────────────────────────────────────────────────────────────────────────────
def manager_node(state: EscalationState) -> dict:
    """
    จัดการภายในแผนก — สั่งซื้อ emergency, assign ช่าง
    score ≤ 2,000
    """
    print("\n[Manager] 🛠 Handling within department...")

    worker: WorkerResult = state["worker_result"]
    response = llm.with_structured_output(ManagerResult).invoke([
        SystemMessage(
            "You are a department manager. Given this event, decide if you can resolve it "
            "within your authority or need to escalate. Be concise."
        ),
        HumanMessage(
            f"Event: {worker.event_type.value}\n"
            f"Detail: {worker.raw_detail}\n"
            f"Severity: {worker.severity_score}\n"
            f"Departments: {worker.affected_departments}"
        ),
    ])

    print(f"[Manager] resolved={response.resolved}, escalate={response.escalation_needed}")

    step = EscalationStep(
        level=EscalationLevel.MANAGER,
        agent="manager_agent",
        summary=response.action_taken,
    )

    return {
        "manager_result":     response,
        "escalation_history": [step],
        "messages": [AIMessage(f"[Manager] {response.action_taken}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3b — Director Node (fan-out via Send)
# ─────────────────────────────────────────────────────────────────────────────
def director_node(state: EscalationState) -> dict:
    """
    จัดการข้ามแผนก
    ใช้ LLM ประเมิน cross-dept actions
    (Fan-out จริงๆ ใช้ Send() — ดู director_fanout_node ด้านล่าง)
    """
    print("\n[Director] 🏢 Cross-department coordination...")

    worker: WorkerResult = state["worker_result"]
    response = llm.with_structured_output(DirectorResult).invoke([
        SystemMessage(
            "You are a director managing multiple departments. Coordinate cross-department "
            "response to this event. List specific actions per department."
        ),
        HumanMessage(
            f"Event: {worker.event_type.value}\n"
            f"Detail: {worker.raw_detail}\n"
            f"Severity: {worker.severity_score}\n"
            f"Affected departments: {worker.affected_departments}"
        ),
    ])

    print(f"[Director] resolved={response.resolved}, escalate={response.escalation_needed}")

    step = EscalationStep(
        level=EscalationLevel.DIRECTOR,
        agent="director_agent",
        summary=f"Cross-dept actions: {'; '.join(response.cross_dept_actions[:2])}",
    )

    return {
        "director_result":    response,
        "escalation_history": [step],
        "messages": [AIMessage(f"[Director] {'; '.join(response.cross_dept_actions)}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3c — Executive Node + HITL interrupt
# ─────────────────────────────────────────────────────────────────────────────
def executive_node(state: EscalationState) -> dict:
    """
    ระดับ Executive — ตัดสินใจ business strategy
    HITL: interrupt() รอ human confirm ก่อน execute เสมอ
    """
    print("\n[Executive] 👔 Strategic assessment + HITL...")

    worker: WorkerResult = state["worker_result"]
    history_summary = "\n".join(
        f"  [{s.level.value}] {s.summary}"
        for s in state["escalation_history"]
    )

    # ── Step 1: LLM ประเมิน ───────────────────────────────────────────────────
    assessment: ExecutiveAssessment = llm.with_structured_output(ExecutiveAssessment).invoke([
        SystemMessage(
            "You are the Executive (C-level). You receive escalated business-critical events "
            "that Directors could not resolve. Assess strategic risk, recommend actions, "
            "and always set requires_human_approval=true."
        ),
        HumanMessage(
            f"Event: {worker.event_type.value}\n"
            f"Severity score: {worker.severity_score:,.0f}\n"
            f"Detail: {worker.raw_detail}\n"
            f"Affected departments: {worker.affected_departments}\n\n"
            f"Escalation history:\n{history_summary}"
        ),
    ])

    print(f"[Executive] Risk={assessment.risk_level}, Actions={len(assessment.recommended_actions)}")

    # ── Step 2: interrupt() — รอ human ────────────────────────────────────────
    actions_display = "\n".join(
        f"  [{a.action_type.value}] {a.target}: {a.description} "
        f"({'reversible' if a.reversible else '⚠️  IRREVERSIBLE'})"
        for a in assessment.recommended_actions
    )

    human_decision: str = interrupt({
        "title":          "🚨 Executive Approval Required",
        "event":          worker.event_type.value,
        "risk_level":     assessment.risk_level,
        "rationale":      assessment.rationale,
        "actions":        actions_display,
        "notify_external": assessment.notify_external,
        "est_resolution": f"{assessment.estimated_resolution_hours}h",
        "prompt":         (
            "Options:\n"
            "  approve          — execute all recommended actions\n"
            "  reject           — cancel, take no action\n"
            "  modify:<text>    — change specific action before executing"
        ),
    })

    # ── Step 3: Process human decision ───────────────────────────────────────
    decision_clean = human_decision.strip().lower()

    if decision_clean == "approve":
        status = "✅ Approved — dispatching actions"
    elif decision_clean == "reject":
        status = "❌ Rejected — no action taken"
    elif decision_clean.startswith("modify:"):
        modification = human_decision[7:].strip()
        status = f"✏️  Modified — applying change: {modification}"
    else:
        status = f"⚠️  Unknown decision '{human_decision}' — defaulting to reject"

    print(f"[Executive] Human decision: {status}")

    step = EscalationStep(
        level=EscalationLevel.EXECUTIVE,
        agent="executive_agent",
        summary=f"Risk={assessment.risk_level} | Decision={human_decision} | {status}",
    )

    return {
        "executive_result":   assessment,
        "human_decision":     human_decision,
        "escalation_history": [step],
        "messages": [AIMessage(f"[Executive] {status}")],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 — Response Synthesizer
# ─────────────────────────────────────────────────────────────────────────────
def response_node(state: EscalationState) -> dict:
    """สรุปผลรวมจากทุกระดับ → stream กลับ user"""

    history_lines = "\n".join(
        f"  [{s.level.value.upper():10}] {s.agent}: {s.summary}"
        for s in state["escalation_history"]
    )

    # Determine which level handled it
    if state.get("executive_result"):
        exec_r: ExecutiveAssessment = state["executive_result"]
        outcome = (
            f"Escalated to EXECUTIVE (risk={exec_r.risk_level})\n"
            f"Human decision: {state.get('human_decision', 'pending')}\n"
            f"External notification: {'Yes' if exec_r.notify_external else 'No'}\n"
            f"Est. resolution: {exec_r.estimated_resolution_hours}h"
        )
    elif state.get("director_result"):
        dir_r: DirectorResult = state["director_result"]
        outcome = (
            f"Handled at DIRECTOR level\n"
            f"Actions: {'; '.join(dir_r.cross_dept_actions)}"
        )
    elif state.get("manager_result"):
        mgr_r: ManagerResult = state["manager_result"]
        outcome = (
            f"Handled at MANAGER level\n"
            f"Action: {mgr_r.action_taken}"
        )
    else:
        outcome = "Handled at WORKER level (no escalation needed)"

    summary = (
        f"📋 Escalation Report\n"
        f"{'─'*50}\n"
        f"Event     : {state['event_type']}\n"
        f"Severity  : {state['severity_score']:,.0f}\n"
        f"Depts     : {state.get('affected_departments', [])}\n\n"
        f"Outcome:\n{outcome}\n\n"
        f"Escalation trail:\n{history_lines}"
    )

    print(f"\n[Response]\n{summary}")

    return {
        "final_summary": summary,
        "messages": [AIMessage(summary)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Conditional edge: after manager/director, check if needs further escalation
# ─────────────────────────────────────────────────────────────────────────────
def after_manager(state: EscalationState) -> Literal["director_node", "response_node"]:
    r: ManagerResult = state["manager_result"]
    return "director_node" if r.escalation_needed else "response_node"

def after_director(state: EscalationState) -> Literal["executive_node", "response_node"]:
    r: DirectorResult = state["director_result"]
    return "executive_node" if r.escalation_needed else "response_node"


# ─────────────────────────────────────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────────────────────────────────────
def build_escalation_graph(checkpointer=None):
    builder = StateGraph(EscalationState)

    # Nodes
    builder.add_node("worker_node",     worker_node)
    builder.add_node("supervisor_node", supervisor_node)
    builder.add_node("manager_node",    manager_node)
    builder.add_node("director_node",   director_node)
    builder.add_node("executive_node",  executive_node)
    builder.add_node("response_node",   response_node)

    # Edges
    builder.add_edge(START,            "worker_node")
    builder.add_edge("worker_node",    "supervisor_node")
    # supervisor uses Command(goto=...) internally — no explicit edges needed

    # After manager: may escalate further to director
    builder.add_conditional_edges("manager_node", after_manager, {
        "director_node": "director_node",
        "response_node": "response_node",
    })

    # After director: may escalate further to executive
    builder.add_conditional_edges("director_node", after_director, {
        "executive_node": "executive_node",
        "response_node":  "response_node",
    })

    # Executive always goes to response (after HITL resume)
    builder.add_edge("executive_node", "response_node")
    builder.add_edge("response_node",  END)

    # ── Compile ───────────────────────────────────────────────────────────────
    # interrupt_before="executive_node" เพื่อให้แน่ใจว่า
    # graph หยุดก่อน execute เสมอ (belt-and-suspenders กับ interrupt() ใน node)
    return builder.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["executive_node"],   # compile-time safeguard
    )


# ─────────────────────────────────────────────────────────────────────────────
# Demo runner
# ─────────────────────────────────────────────────────────────────────────────
def run_demo():
    graph = build_escalation_graph()

    # ── Scenario 1: Machine Broken (minor) → Manager handles ─────────────────
    print("\n" + "="*60)
    print("SCENARIO 1: Machine Broken (minor, non-critical)")
    print("="*60)

    config1 = {"configurable": {"thread_id": "incident-001"}}
    result1 = graph.invoke(
        {
            "event_type":           EventType.MACHINE_BROKEN.value,
            "raw_detail":           "MC-12 conveyor belt snap, spare parts available",
            "affected_departments": ["maintenance"],
            "messages":             [HumanMessage("Machine broken at line 3")],
            "escalation_history":   [],
            "human_decision":       "",
            "final_summary":        "",
        },
        config=config1,
        version="v2",
    )
    # No interrupt expected → completes immediately
    print("\n✅ Scenario 1 complete (no HITL needed)")

    # ── Scenario 2: Production Broken (critical) → Executive + HITL ──────────
    print("\n" + "="*60)
    print("SCENARIO 2: Production Broken → Executive HITL")
    print("="*60)

    config2 = {"configurable": {"thread_id": "incident-002"}}

    # Step 1: Run until interrupt
    result2 = graph.invoke(
        {
            "event_type":           EventType.PRODUCTION_BROKEN.value,
            "raw_detail":           "All 4 production lines down, cooling system failure",
            "affected_departments": ["production", "warehouse", "purchasing", "sales"],
            "messages":             [HumanMessage("Production completely stopped!")],
            "escalation_history":   [],
            "human_decision":       "",
            "final_summary":        "",
        },
        config=config2,
        version="v2",
    )

    if result2.interrupts:
        print("\n⏸️  GRAPH PAUSED — Waiting for Executive approval:")
        print("-" * 50)
        payload = result2.interrupts[0].value
        for k, v in payload.items():
            print(f"  {k}: {v}")
        print("-" * 50)

        # Step 2: Human reviews → resumes graph
        # In production: this comes from a REST endpoint POST /approve/{thread_id}
        human_input = "approve"   # or "reject" or "modify: delay halt by 2h"
        print(f"\n👤 Human decision: '{human_input}'")

        from langgraph.types import Command as LGCommand
        result2_final = graph.invoke(
            LGCommand(resume=human_input),
            config=config2,
            version="v2",
        )
        print("\n✅ Scenario 2 complete (after HITL approval)")
        print(result2_final.value.get("final_summary", ""))

    # ── Scenario 3: PO Delay (cross-dept) → Director ─────────────────────────
    print("\n" + "="*60)
    print("SCENARIO 3: PO Delay (cross-dept) → Director")
    print("="*60)

    config3 = {"configurable": {"thread_id": "incident-003"}}
    result3 = graph.invoke(
        {
            "event_type":           EventType.PO_DELAY.value,
            "raw_detail":           "SUP-01 delayed 5 days, affects production schedule",
            "affected_departments": ["purchasing", "production", "sales"],
            "messages":             [HumanMessage("PO from SUP-01 is delayed 5 days")],
            "escalation_history":   [],
            "human_decision":       "",
            "final_summary":        "",
        },
        config=config3,
        version="v2",
    )
    print("\n✅ Scenario 3 complete")


if __name__ == "__main__":
    run_demo()
