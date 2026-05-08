# uv pip install fastapi uvicorn langgraph>=1.0.0 langchain langchain-openai
# uv pip install langgraph-checkpoint-postgres asyncpg pydantic-settings

"""
gateway/routers/escalation.py
==============================
FastAPI endpoints สำหรับ Escalation Flow
รวม HITL resume endpoint สำหรับ Executive approval
"""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

# Import graph builder จาก escalation_flow.py
from escalation_flow import (
    EscalationState,
    EventType,
    build_escalation_graph,
)

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class EscalationRequest(BaseModel):
    event_type:            EventType
    raw_detail:            str = Field(..., min_length=1, max_length=2000)
    affected_departments:  list[str] = Field(default_factory=list)
    thread_id:             Optional[str] = None   # ถ้าไม่ส่ง จะ generate ให้

class ResumeRequest(BaseModel):
    decision: str = Field(
        ...,
        description="approve | reject | modify:<instruction>",
        examples=["approve", "reject", "modify: delay halt by 2 hours"],
    )

class EscalationStartResponse(BaseModel):
    thread_id:      str
    status:         str   # "running" | "waiting_for_approval" | "complete"
    interrupt_data: Optional[dict] = None
    summary:        Optional[str]  = None

class ResumeResponse(BaseModel):
    thread_id: str
    status:    str
    summary:   Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# App + Lifespan (graph compiled once at startup)
# ─────────────────────────────────────────────────────────────────────────────

_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph

    # ── Production: swap MemorySaver → AsyncPostgresSaver ─────────────────
    # from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    # checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
    # await checkpointer.setup()
    checkpointer = MemorySaver()

    _graph = build_escalation_graph(checkpointer=checkpointer)
    print("✅ Escalation graph compiled and ready")
    yield

def get_graph():
    if _graph is None:
        raise RuntimeError("Graph not initialised — check lifespan setup")
    return _graph


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/escalation", tags=["escalation"])


@router.post("/start", response_model=EscalationStartResponse)
async def start_escalation(
    body: EscalationRequest,
    graph=Depends(get_graph),
):
    """
    รับ event → เริ่ม escalation flow
    ถ้า severity สูงถึง Executive จะ return status='waiting_for_approval'
    พร้อม interrupt_data ที่ frontend ต้องแสดงให้ human อนุมัติ
    """
    thread_id = body.thread_id or str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    initial_state: EscalationState = {
        "event_type":           body.event_type.value,
        "raw_detail":           body.raw_detail,
        "affected_departments": body.affected_departments,
        "messages":             [HumanMessage(f"Event: {body.event_type.value} — {body.raw_detail}")],
        "escalation_history":   [],
        "severity_score":       0.0,
        "worker_result":        None,
        "manager_result":       None,
        "director_result":      None,
        "executive_result":     None,
        "human_decision":       "",
        "final_summary":        "",
    }

    result = await graph.ainvoke(initial_state, config=config, version="v2")

    # ── Graph paused at Executive interrupt ───────────────────────────────────
    if result.interrupts:
        interrupt_payload = result.interrupts[0].value
        return EscalationStartResponse(
            thread_id=thread_id,
            status="waiting_for_approval",
            interrupt_data=interrupt_payload,
        )

    # ── Completed without escalation to Executive ─────────────────────────────
    return EscalationStartResponse(
        thread_id=thread_id,
        status="complete",
        summary=result.value.get("final_summary", ""),
    )


@router.post("/{thread_id}/approve", response_model=ResumeResponse)
async def resume_escalation(
    thread_id: str,
    body: ResumeRequest,
    graph=Depends(get_graph),
):
    """
    Human อนุมัติ / ปฏิเสธ / แก้ไข Executive action
    ส่ง decision กลับเพื่อ resume graph จาก interrupt point

    decision formats:
      - "approve"            → execute all recommended actions
      - "reject"             → cancel, no action taken
      - "modify: <text>"     → apply modification before executing
    """
    config = {"configurable": {"thread_id": thread_id}}

    # ── ตรวจว่า thread นี้รอ approval อยู่จริงไหม ─────────────────────────
    snapshot = await graph.aget_state(config)
    if not snapshot or not snapshot.tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Thread '{thread_id}' not found or already completed",
        )

    # ── Resume graph ──────────────────────────────────────────────────────────
    result = await graph.ainvoke(
        Command(resume=body.decision),
        config=config,
        version="v2",
    )

    return ResumeResponse(
        thread_id=thread_id,
        status="complete",
        summary=result.value.get("final_summary", ""),
    )


@router.get("/{thread_id}/status")
async def get_status(
    thread_id: str,
    graph=Depends(get_graph),
):
    """
    ดูสถานะปัจจุบันของ thread
    รวม escalation_history เพื่อ audit trail
    """
    config   = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Thread not found")

    state: EscalationState = snapshot.values
    return {
        "thread_id":           thread_id,
        "event_type":          state.get("event_type"),
        "severity_score":      state.get("severity_score"),
        "final_summary":       state.get("final_summary"),
        "escalation_history": [
            {"level": s.level.value, "agent": s.agent, "summary": s.summary}
            for s in state.get("escalation_history", [])
        ],
        "pending_interrupt":   bool(snapshot.tasks),
    }


@router.post("/stream")
async def stream_escalation(
    body: EscalationRequest,
    graph=Depends(get_graph),
):
    """
    SSE stream — real-time token streaming กลับ WebApp
    แต่ละ node ส่ง event กลับทันที ไม่ต้องรอจบทั้ง flow
    """
    thread_id = body.thread_id or str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    initial_state: EscalationState = {
        "event_type":           body.event_type.value,
        "raw_detail":           body.raw_detail,
        "affected_departments": body.affected_departments,
        "messages":             [HumanMessage(f"Event: {body.event_type.value}")],
        "escalation_history":   [],
        "severity_score":       0.0,
        "worker_result":        None,
        "manager_result":       None,
        "director_result":      None,
        "executive_result":     None,
        "human_decision":       "",
        "final_summary":        "",
    }

    async def event_generator():
        yield f"data: {{\"thread_id\": \"{thread_id}\"}}\n\n"
        async for event in graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            kind = event.get("event", "")
            # Stream LLM tokens
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield f"data: {chunk}\n\n"
            # Node started/ended — useful for progress indicators
            elif kind == "on_chain_start":
                node = event.get("name", "")
                if node in ("worker_node", "supervisor_node", "manager_node",
                            "director_node", "executive_node"):
                    yield f"event: node_start\ndata: {node}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Thread-Id": thread_id},
    )


# ─────────────────────────────────────────────────────────────────────────────
# App entry point (dev)
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Escalation Flow API", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("escalation_router:app", host="0.0.0.0", port=8000, reload=True)
