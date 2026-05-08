# uv pip install langgraph>=1.0.0 langchain>=0.3.0 langchain-openai pydantic>=2.7.0

"""
orchestrator/nodes/supervisor.py
==================================
Supervisor Node — routes between WhereHouseAgent and BuyerAgent
ใช้ LangGraph Command API + conditional edges

Flow:
  START
    → supervisor_node     (LLM decides first agent to call)
    → where_house_node    (check stock, location, WH ops)
        ↘ back to supervisor (if more work needed)
    → buyer_node          (PO, supplier, price lookup)
        ↘ back to supervisor (if more work needed)
    → response_node       (synthesize final answer)
    → END

Supervisor pattern:
  - LLM reads current state + history → decides NEXT agent or FINISH
  - Each agent reports back to supervisor after completing its task
  - Supervisor can call agents multiple times if needed
  - Prevents agents from calling each other directly (no mesh chaos)
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────
llm = init_chat_model("openai:gpt-4o-mini")

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schema — supervisor routing decision
# ─────────────────────────────────────────────────────────────────────────────

class SupervisorDecision(BaseModel):
    """What the supervisor LLM decides next"""
    next_agent: Literal["where_house_agent", "buyer_agent", "FINISH"] = Field(
        ...,
        description=(
            "where_house_agent = ตรวจ stock / location / WH operations\n"
            "buyer_agent       = PO / supplier / price lookup\n"
            "FINISH            = งานเสร็จแล้ว ไม่ต้องเรียก agent เพิ่ม"
        ),
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="อธิบายว่าทำไมถึงเลือก next_agent นี้",
    )
    task_for_agent: str = Field(
        default="",
        description="คำสั่งเฉพาะที่ส่งให้ agent ถัดไป — blank ถ้า FINISH",
    )


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class SupervisorState(TypedDict):
    # ── Conversation history ──────────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Task context (set by caller / Executive router) ───────────────────────
    original_request:     str        # "ตรวจสอบ Stock WH01 KB-001 ต้องเพิ่มอะไร"
    entities:             dict       # { "wh": "WH01", "store": "KB-001" }

    # ── Agent results (filled as agents complete) ─────────────────────────────
    stock_result:         dict       # WhereHouseAgent output
    purchase_suggestion:  dict       # BuyerAgent output

    # ── Supervisor routing state ──────────────────────────────────────────────
    next_agent:           str        # latest supervisor decision
    agent_call_count:     Annotated[int, operator.add]   # guard against infinite loop
    supervisor_reasoning: Annotated[list[str], operator.add]  # audit trail

    # ── Final ─────────────────────────────────────────────────────────────────
    final_answer:         str


MAX_AGENT_CALLS = 6   # safety ceiling — prevents infinite supervisor loops


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR NODE
# ─────────────────────────────────────────────────────────────────────────────

SUPERVISOR_SYSTEM = """\
You are the Supervisor coordinating two specialist agents:

  1. where_house_agent  — เชี่ยวชาญ: ตรวจสอบ stock level, stock location,
                          warehouse operations, replenishment suggestion
  2. buyer_agent        — เชี่ยวชาญ: สร้าง purchase order, ค้นหา supplier,
                          เปรียบเทียบราคา, draft PO

## Your job
Read the conversation history and decide which agent to call next, OR decide FINISH.

## Decision rules
- Call where_house_agent FIRST if the request involves stock/inventory/location
- Call buyer_agent if stock result shows shortage and external purchase is needed
- Call buyer_agent directly if request is purely about PO/pricing
- FINISH only when you have enough info to give a complete answer to the user
- If both agents have reported back and question is answered → FINISH
- If agent calls exceed {max_calls} → FINISH immediately (safety)

## Output
Return ONLY valid JSON matching SupervisorDecision schema.
""".format(max_calls=MAX_AGENT_CALLS)


def supervisor_node(
    state: SupervisorState,
) -> Command[Literal["where_house_node", "buyer_node", "response_node"]]:
    """
    Supervisor reads full conversation history + current state
    → decides which agent to call next (or FINISH)
    → returns Command(goto=target) to LangGraph
    """
    call_count = state.get("agent_call_count", 0)

    # ── Safety: force finish if too many calls ────────────────────────────────
    if call_count >= MAX_AGENT_CALLS:
        print(f"[Supervisor] ⚠️  Max calls ({MAX_AGENT_CALLS}) reached → forcing FINISH")
        return Command(
            goto="response_node",
            update={
                "next_agent": "FINISH",
                "supervisor_reasoning": [f"Forced FINISH after {call_count} calls"],
            },
        )

    # ── Build context snapshot for LLM ───────────────────────────────────────
    stock_status = (
        f"Stock result: {state['stock_result']}"
        if state.get("stock_result")
        else "Stock result: not yet checked"
    )
    po_status = (
        f"Purchase suggestion: {state['purchase_suggestion']}"
        if state.get("purchase_suggestion")
        else "Purchase suggestion: not yet created"
    )

    context = (
        f"Original request: {state['original_request']}\n"
        f"Entities: {state.get('entities', {})}\n"
        f"{stock_status}\n"
        f"{po_status}\n"
        f"Agent calls so far: {call_count}/{MAX_AGENT_CALLS}"
    )

    # ── LLM decides next step ─────────────────────────────────────────────────
    decision: SupervisorDecision = (
        llm.with_structured_output(SupervisorDecision).invoke([
            SystemMessage(SUPERVISOR_SYSTEM),
            *state["messages"],
            HumanMessage(f"[STATE SNAPSHOT]\n{context}\n\nWhat should be done next?"),
        ])
    )

    print(
        f"[Supervisor] call={call_count+1} "
        f"next={decision.next_agent} | {decision.reasoning[:60]}..."
    )

    # ── Map decision to graph node name ───────────────────────────────────────
    node_map = {
        "where_house_agent": "where_house_node",
        "buyer_agent":       "buyer_node",
        "FINISH":            "response_node",
    }
    target_node = node_map[decision.next_agent]

    return Command(
        goto=target_node,
        update={
            "next_agent":           decision.next_agent,
            "agent_call_count":     1,   # operator.add accumulates this
            "supervisor_reasoning": [
                f"[call {call_count+1}] → {decision.next_agent}: {decision.reasoning}"
            ],
            "messages": [
                AIMessage(
                    content=f"[Supervisor] → {decision.next_agent}: {decision.task_for_agent or decision.reasoning}"
                )
            ],
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# WHERE HOUSE AGENT NODE
# ─────────────────────────────────────────────────────────────────────────────

class StockCheckResult(BaseModel):
    wh:                str
    store:             str
    onhand:            int   = Field(..., ge=0)
    min_stock:         int   = Field(..., ge=0)
    items_below_min:   list[str]
    shortage_detected: bool
    replenish_from_main_wh: bool   # True = main WH มี stock พอ
    main_wh_onhand:    int   = Field(default=0, ge=0)
    summary:           str


def where_house_node(state: SupervisorState) -> Command[Literal["supervisor_node"]]:
    """
    WhereHouseAgent — เชี่ยวชาญ WH operations
    ตรวจ stock แล้วส่งผลกลับ supervisor เสมอ
    """
    print("\n[WhereHouseAgent] 🏭 Checking stock...")

    entities = state.get("entities", {})
    wh       = entities.get("wh",    "WH01")
    store    = entities.get("store", "KB-001")

    # ── In production: call MCP store tools ──────────────────────────────────
    # result = await mcp_client.call("get_stock_onhand", wh=wh, store=store)
    # Simulated here:
    result: StockCheckResult = llm.with_structured_output(StockCheckResult).invoke([
        SystemMessage(
            "You are a warehouse management system. "
            "Return realistic stock check data as JSON. "
            "Simulate a shortage scenario where onhand=0 for at least 2 SKUs."
        ),
        HumanMessage(
            f"Check stock for warehouse={wh}, store={store}.\n"
            f"Original request: {state['original_request']}"
        ),
    ])

    print(
        f"[WhereHouseAgent] onhand={result.onhand}, "
        f"shortage={result.shortage_detected}, "
        f"items_below_min={result.items_below_min}"
    )

    return Command(
        goto="supervisor_node",   # always report back to supervisor
        update={
            "stock_result": result.model_dump(),
            "messages": [
                AIMessage(
                    content=(
                        f"[WhereHouseAgent] WH={wh} Store={store}: "
                        f"onhand={result.onhand}, shortage={result.shortage_detected}, "
                        f"items={result.items_below_min}, "
                        f"main_wh_has_stock={result.replenish_from_main_wh}"
                    )
                )
            ],
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUYER AGENT NODE
# ─────────────────────────────────────────────────────────────────────────────

class PurchaseSuggestion(BaseModel):
    items:          list[str]
    quantities:     dict[str, int]   # { "SKU-A": 50, "SKU-B": 60 }
    supplier:       str
    unit_prices:    dict[str, float]
    total_cost_thb: float = Field(..., ge=0)
    lead_time_days: int   = Field(..., ge=0)
    po_draft_id:    str
    requires_approval: bool = True   # PO ต้องรอ human approve ก่อนส่งเสมอ
    summary:        str


def buyer_node(state: SupervisorState) -> Command[Literal["supervisor_node"]]:
    """
    BuyerAgent — เชี่ยวชาญ procurement
    รับ stock shortage context จาก state → สร้าง PO draft
    ส่งผลกลับ supervisor เสมอ
    """
    print("\n[BuyerAgent] 🛒 Creating purchase suggestion...")

    stock = state.get("stock_result", {})
    items = stock.get("items_below_min", ["SKU-UNKNOWN"])

    # ── In production: call MCP buyer tools ──────────────────────────────────
    # supplier = await mcp_client.call("get_best_supplier", items=items)
    # prices   = await mcp_client.call("get_price_quote", supplier=supplier, items=items)
    # Simulated here:
    result: PurchaseSuggestion = llm.with_structured_output(PurchaseSuggestion).invoke([
        SystemMessage(
            "You are a procurement system. "
            "Return a realistic purchase order suggestion as JSON. "
            "Use supplier SUP-01 and realistic Thai baht pricing."
        ),
        HumanMessage(
            f"Create purchase suggestion for items: {items}\n"
            f"Target warehouse: {state.get('entities', {}).get('wh', 'WH01')}\n"
            f"Stock context: {stock.get('summary', 'shortage detected')}\n"
            f"Original request: {state['original_request']}"
        ),
    ])

    print(
        f"[BuyerAgent] supplier={result.supplier}, "
        f"items={len(result.items)}, "
        f"total={result.total_cost_thb:,.0f} THB"
    )

    return Command(
        goto="supervisor_node",   # always report back to supervisor
        update={
            "purchase_suggestion": result.model_dump(),
            "messages": [
                AIMessage(
                    content=(
                        f"[BuyerAgent] Draft PO={result.po_draft_id}: "
                        f"{len(result.items)} items from {result.supplier}, "
                        f"total={result.total_cost_thb:,.0f} THB, "
                        f"lead_time={result.lead_time_days} days"
                    )
                )
            ],
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE NODE — synthesize final answer
# ─────────────────────────────────────────────────────────────────────────────

def response_node(state: SupervisorState) -> dict:
    """Synthesize all agent results into final answer for user"""
    print("\n[Response] 📋 Synthesizing final answer...")

    stock = state.get("stock_result",        {})
    po    = state.get("purchase_suggestion", {})

    response = llm.invoke([
        SystemMessage(
            "You are summarizing the results of a warehouse and procurement investigation. "
            "Be clear, structured, and actionable. Write in Thai."
        ),
        HumanMessage(
            f"Original request: {state['original_request']}\n\n"
            f"Stock check result:\n{stock}\n\n"
            f"Purchase suggestion:\n{po}\n\n"
            f"Supervisor reasoning trail:\n"
            + "\n".join(state.get("supervisor_reasoning", []))
        ),
    ])

    print(f"[Response] Done. Total agent calls: {state.get('agent_call_count', 0)}")

    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build graph
# ─────────────────────────────────────────────────────────────────────────────

def build_supervisor_graph():
    from langgraph.checkpoint.memory import MemorySaver

    builder = StateGraph(SupervisorState)

    builder.add_node("supervisor_node",  supervisor_node)
    builder.add_node("where_house_node", where_house_node)
    builder.add_node("buyer_node",       buyer_node)
    builder.add_node("response_node",    response_node)

    # Entry point → supervisor decides first
    builder.add_edge(START, "supervisor_node")

    # supervisor uses Command(goto=...) internally — no explicit edges needed
    # where_house and buyer always return Command(goto="supervisor_node")

    builder.add_edge("response_node", END)

    return builder.compile(checkpointer=MemorySaver())


# ─────────────────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────────────────

def run_demo():
    graph  = build_supervisor_graph()
    config = {"configurable": {"thread_id": "demo-001"}}

    print("=" * 60)
    print("User: ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร")
    print("=" * 60)

    result = graph.invoke(
        {
            "messages":          [HumanMessage("ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร")],
            "original_request":  "ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร",
            "entities":          {"wh": "WH01", "store": "KB-001"},
            "stock_result":      {},
            "purchase_suggestion": {},
            "next_agent":        "",
            "agent_call_count":  0,
            "supervisor_reasoning": [],
            "final_answer":      "",
        },
        config=config,
        version="v2",
    )

    print("\n" + "=" * 60)
    print("FINAL ANSWER:")
    print("=" * 60)
    print(result.value.get("final_answer", "No answer generated"))

    print("\n--- Supervisor reasoning trail ---")
    for r in result.value.get("supervisor_reasoning", []):
        print(f"  {r}")


if __name__ == "__main__":
    run_demo()
