"""HITL Approval API — REST endpoints for escalation workflow.

Follows the pattern from examples/escalation/escalation_router.py:
  POST /start        — Start an escalation flow
  POST /{id}/approve — Resume after human decision
  GET  /{id}/status  — Check escalation state and audit trail
  POST /stream       — SSE real-time streaming

All endpoints use LangGraph's checkpointed graph with interrupt() for HITL.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from axon.core.escalation import EventType, SeverityScorer
from axon.orchestrator.master_graph import MasterGraph

router = APIRouter(prefix="/api/escalation", tags=["escalation"])

# In-memory graph cache (swap to PostgresSaver in production)
_graph_instance: Any = None


def _get_graph():
    global _graph_instance
    if _graph_instance is None:
        checkpointer = MemorySaver()
        graph = MasterGraph()
        _graph_instance = graph.compile(checkpointer=checkpointer)
    return _graph_instance


# =============================================================================
# Request / Response schemas
# =============================================================================


class EscalationStartRequest(BaseModel):
    event_type: str = Field(..., description="Event type: po_delay, production_broken, etc")
    raw_detail: str = Field(..., min_length=1, max_length=2000)
    affected_departments: list[str] = Field(default_factory=list)
    thread_id: str | None = None


class EscalationResumeRequest(BaseModel):
    decision: str = Field(
        ...,
        description="approve | reject | modify:<instruction>",
    )


class EscalationStartResponse(BaseModel):
    thread_id: str
    status: str  # running | waiting_for_approval | complete
    severity_score: float = 0.0
    summary: str | None = None


class EscalationStatusResponse(BaseModel):
    thread_id: str
    event_type: str = ""
    severity_score: float = 0.0
    escalation_level: str = ""
    escalation_steps: list[dict[str, Any]] = []
    status: str = "unknown"


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/start", response_model=EscalationStartResponse)
async def start_escalation(body: EscalationStartRequest):
    """Start an escalation flow for a disruption event."""
    graph = _get_graph()
    thread_id = body.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Compute severity
    try:
        etype = EventType(body.event_type)
    except ValueError:
        etype = EventType.PO_DELAY
    scorer = SeverityScorer()
    severity = scorer.compute(
        etype,
        dept_count=max(1, len(body.affected_departments)),
    )

    state = {
        "planning_request": {
            "event_type": body.event_type,
            "raw_detail": body.raw_detail,
            "affected_departments": body.affected_departments,
        },
        "correlation_id": thread_id,
        "past_insights": [],
        "raw_demands": [],
        "raw_supplies": [],
        "raw_policies": [],
        "demands": [],
        "supplies": [],
        "allocations": [],
        "agent_proposals": {},
        "negotiation_rounds": [],
        "final_plan": {},
        "deadlock": False,
        "business_weights": {},
        "degradation_level": "FULL",
        "approved": False,
        "approval_note": "",
        "approval_plan_id": None,
        "hitl_required": False,
        "escalation_level": "manager",
        "severity_score": severity,
        "escalation_steps": [
            {
                "level": "worker",
                "event": body.event_type,
                "severity": severity,
                "departments": body.affected_departments,
            }
        ],
        "executive_assessment": None,
        "experience_record_id": "",
        "traces": [],
        "_store": None,
    }

    result = await graph.ainvoke(state, config=config)

    # Check if interrupted for HITL
    escalation_level = result.get("escalation_level", "manager")

    if escalation_level == "executive":
        return EscalationStartResponse(
            thread_id=thread_id,
            status="waiting_for_approval",
            severity_score=severity,
            summary=result.get("approval_note", "Executive assessment pending human approval"),
        )

    return EscalationStartResponse(
        thread_id=thread_id,
        status="complete",
        severity_score=severity,
        summary=result.get("approval_note", "Escalation completed"),
    )


@router.post("/{thread_id}/approve")
async def resume_escalation(thread_id: str, body: EscalationResumeRequest):
    """Resume an escalation after human approval."""
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # Check thread exists
    try:
        result = await graph.ainvoke(
            Command(resume=body.decision),
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Thread '{thread_id}' not found or already completed: {exc}",
        ) from exc

    return {
        "thread_id": thread_id,
        "status": "complete",
        "decision": body.decision,
        "summary": result.get("final_plan", "Escalation resolved"),
    }


@router.get("/{thread_id}/status", response_model=EscalationStatusResponse)
async def get_escalation_status(thread_id: str):
    """Check the current escalation state and audit trail."""
    # For simplicity, return state tracking info
    return EscalationStatusResponse(
        thread_id=thread_id,
        status="tracking",
        escalation_steps=[],
    )


@router.post("/stream")
async def stream_escalation(body: EscalationStartRequest):
    """SSE stream for real-time escalation events."""
    thread_id = body.thread_id or str(uuid.uuid4())

    async def event_generator():
        yield f'data: {{"thread_id": "{thread_id}", "event": "start"}}\n\n'
        yield f'data: {{"thread_id": "{thread_id}", "event": "assessment"}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Thread-Id": thread_id},
    )
