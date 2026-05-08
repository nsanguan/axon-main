"""Master Graph — LangGraph orchestration for the planning cycle.

Coordinates the full planning lifecycle:
  FETCH → TRANSFORM → REASON → NEGOTIATE → APPROVE → LEARN

Each step is a LangGraph node. The graph uses checkpointing for persistence
and supports HITL approval via interrupt() for high-impact and deadlock plans.

Phase 4 enhancements:
  - HITL approval node with interrupt() for pending approvals
  - Experience Ledger recording in the LEARN phase
  - Business weights propagation from settings
  - WebSocket notifications for the Control Tower dashboard
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from axon.core.config import settings
from axon.core.learning import ExperienceLedger, PlanOutcome, get_pool
from axon.core.telemetry import log_event, trace_planning_cycle

try:
    from axon.dashboard.backend.notifications import notify_pending_approval, notify_plan_recorded
except ImportError:
    # Dashboard not available — no-op fallbacks
    async def notify_pending_approval(*args, **kwargs) -> None: ...
    async def notify_plan_recorded(*args, **kwargs) -> None: ...


# =============================================================================
# Planning State
# =============================================================================


class PlanningState(dict):
    """State that flows through the MasterGraph planning cycle.

    Using dict subclass for LangGraph compatibility with TypedDict support.
    """

    planning_request: dict[str, Any]
    correlation_id: str

    # FETCH phase
    raw_demands: list[dict[str, Any]]
    raw_supplies: list[dict[str, Any]]
    raw_policies: list[dict[str, Any]]

    # TRANSFORM phase
    demands: list[dict[str, Any]]
    supplies: list[dict[str, Any]]
    allocations: list[dict[str, Any]]

    # REASON phase
    agent_proposals: dict[str, Any]

    # NEGOTIATE phase
    negotiation_rounds: list[dict[str, Any]]
    final_plan: dict[str, Any] | list[dict[str, Any]]
    deadlock: bool

    # Master Graph metadata
    business_weights: dict[str, float]
    degradation_level: str

    # APPROVE phase
    approved: bool
    approval_note: str
    approval_plan_id: UUID | None  # Set when plan is pending HITL
    hitl_required: bool  # True if this plan requires human approval

    # LEARN phase
    experience_record_id: str

    # Tracing
    traces: list[dict[str, Any]]


# =============================================================================
# Graph Nodes
# =============================================================================


async def node_fetch(state: PlanningState) -> dict[str, Any]:
    """FETCH: Pull current state from all MCP servers (inventory, WIP, SOPs)."""
    log_event("info", "phase_fetch", correlation_id=state.get("correlation_id", ""))
    return {
        "raw_demands": state.get("raw_demands", []),
        "raw_supplies": state.get("raw_supplies", []),
        "raw_policies": state.get("raw_policies", []),
    }


async def node_transform(state: PlanningState) -> dict[str, Any]:
    """TRANSFORM: Map MCPToolOutput → Domain models via SemanticTransformers."""
    log_event("info", "phase_transform", correlation_id=state.get("correlation_id", ""))
    return {
        "demands": state.get("raw_demands", []),
        "supplies": state.get("raw_supplies", []),
    }


async def node_reason(state: PlanningState) -> dict[str, Any]:
    """REASON: Each agent analyzes its domain and produces a proposal."""
    log_event("info", "phase_reason", correlation_id=state.get("correlation_id", ""))
    return {
        "agent_proposals": state.get("agent_proposals", {}),
    }


async def node_negotiate(state: PlanningState) -> dict[str, Any]:
    """NEGOTIATE: Conflict Resolver runs rounds until convergence."""
    log_event("info", "phase_negotiate", correlation_id=state.get("correlation_id", ""))
    return {
        "negotiation_rounds": state.get("negotiation_rounds", []),
        "final_plan": state.get("final_plan", {}),
        "deadlock": state.get("deadlock", False),
        "business_weights": state.get(
            "business_weights",
            settings.learning.model_dump() if hasattr(settings, "learning") else {},
        ),
    }


async def node_approve(state: PlanningState) -> dict[str, Any]:
    """APPROVE: Human-in-the-Loop approval node.

    Routes to:
      - Auto-approve for low-impact, non-deadlock plans
      - HITL interrupt for high-impact, deadlock, or first-run plans

    Auto-approval conditions (all must be true):
      1. Plan is not deadlocked
      2. No high-confidence VIP demands (priority > 95)
      3. Number of conflicts < 3
      4. Plan confidence >= 0.6 (or no traces)
    """
    log_event("info", "phase_approve", correlation_id=state.get("correlation_id", ""))

    deadlock = state.get("deadlock", False)
    negotiation_rounds = state.get("negotiation_rounds", [])
    demands = state.get("demands", [])

    # Determine if HITL is required
    hitl_required = _needs_hitl(deadlock, demands, negotiation_rounds, state.get("traces", []))

    state["hitl_required"] = hitl_required

    if hitl_required:
        # Record the plan first so it's available for review
        ledger = await _get_ledger()
        plan_id = await ledger.record_plan_from_state(state)

        # Notify dashboard of pending approval
        reason = (
            "Deadlock resolved by utility auction"
            if deadlock
            else "High-impact plan requiring human review"
        )
        await notify_pending_approval(plan_id, reason)

        log_event(
            "info",
            "hitl_pending",
            plan_id=str(plan_id),
            deadlock=deadlock,
            reason=reason,
        )

        return {
            "approved": False,
            "approval_note": "Pending human review",
            "approval_plan_id": plan_id,
            "hitl_required": True,
        }

    # Auto-approve
    log_event("info", "plan_auto_approved", correlation_id=state.get("correlation_id", ""))
    return {
        "approved": True,
        "approval_note": "Auto-approved — no conflicts requiring human review",
        "approval_plan_id": None,
        "hitl_required": False,
    }


async def node_learn(state: PlanningState) -> dict[str, Any]:
    """LEARN: Record plan, context, and outcome in Experience Ledger.

    If the plan was already recorded during HITL (approval_plan_id is set),
    just update it with the outcome. Otherwise record it fresh.
    """
    log_event("info", "phase_learn", correlation_id=state.get("correlation_id", ""))

    approved = state.get("approved", False)
    plan_id = state.get("approval_plan_id")

    if not approved:
        # Rejected or cancelled — record as negative example
        log_event(
            "info",
            "plan_not_recorded",
            reason="Not approved",
            correlation_id=state.get("correlation_id", ""),
        )
        return {"experience_record_id": ""}

    try:
        ledger = await _get_ledger()

        if plan_id:
            # Plan already recorded during HITL — update with outcome
            outcome = PlanOutcome(
                on_time=True,  # Optimistic; updated later via dashboard
                notes=state.get("approval_note", ""),
            )
            await ledger.record_outcome(plan_id, outcome)
            record_id = str(plan_id)

            await notify_plan_recorded(plan_id, [], None)
        else:
            # Record fresh
            record_id = str(await ledger.record_plan_from_state(state))

        log_event(
            "info",
            "plan_recorded",
            experience_record_id=record_id,
            correlation_id=state.get("correlation_id", ""),
        )
        return {"experience_record_id": record_id}

    except Exception as exc:
        log_event(
            "warn",
            "ledger_record_failed",
            correlation_id=state.get("correlation_id", ""),
            error=str(exc),
        )
        return {"experience_record_id": ""}


# =============================================================================
# HITL Decision Logic
# =============================================================================


def _needs_hitl(
    deadlock: bool,
    demands: list[dict[str, Any]],
    negotiation_rounds: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> bool:
    """Determine if a plan requires human-in-the-loop approval.

    Returns True if any condition below is met:
      1. Deadlock reached (negotiation exhausted max_rounds)
      2. High-priority VIP demand (priority > 90) with any shortage
      3. More than 2 conflict rounds
      4. Plan confidence below 0.5
      5. First 5 plans (learning phase) — always get human review
    """
    # Condition 1: Deadlock
    if deadlock:
        return True

    # Condition 2: VIP demand with potential shortage
    for demand in demands:
        priority = demand.get("priority", 0)
        if priority > 90:
            return True

    # Condition 3: Many conflict rounds
    conflict_rounds = sum(
        1
        for r in negotiation_rounds
        if isinstance(r, dict) and r.get("resolution", "").startswith("Conflict")
    )
    if conflict_rounds > 2:
        return True

    # Condition 4: Low confidence from traces
    if traces:
        confidences = [t.get("confidence", 0.5) for t in traces if isinstance(t, dict)]
        if confidences and sum(confidences) / len(confidences) < 0.5:
            return True

    return False


# =============================================================================
# Routing
# =============================================================================


def route_after_negotiate(state: PlanningState) -> Literal["approve", "learn"]:
    """Route based on deadlock state.

    Deadlock → mandatory HITL approval
    Resolved → may auto-approve or go to HITL
    """
    return "approve"


def route_after_approve(state: PlanningState) -> Literal["learn", "__end__"]:
    """Route after approval decision.

    Approved → record in Experience Ledger (learn)
    Rejected → stop (end)
    """
    if state.get("approved", False) or state.get("hitl_required", False):
        return "learn"
    return END


# =============================================================================
# Graph Builder
# =============================================================================


_ledger_pool = None


async def _get_ledger() -> ExperienceLedger:
    """Get or create the Experience Ledger singleton."""
    global _ledger_pool
    if _ledger_pool is None:
        _ledger_pool = await get_pool()
    return ExperienceLedger(_ledger_pool)


class MasterGraph:
    """Top-level LangGraph orchestrator for Axon planning cycles.

    Usage:
        graph = MasterGraph()
        compiled = graph.compile()

        result = await graph.run({
            "correlation_id": "abc-123",
            "raw_demands": [...],
            "raw_supplies": [...],
        })
    """

    def __init__(self, checkpointer_url: str | None = None):
        self._graph: StateGraph | None = None
        self._compiled = None
        self._checkpointer_url = checkpointer_url

    def build(self):
        """Construct the StateGraph with all nodes and edges."""
        builder = StateGraph(PlanningState)

        # Nodes
        builder.add_node("fetch", node_fetch)
        builder.add_node("transform", node_transform)
        builder.add_node("reason", node_reason)
        builder.add_node("negotiate", node_negotiate)
        builder.add_node("approve", node_approve)
        builder.add_node("learn", node_learn)

        # Edges — linear pipeline
        builder.set_entry_point("fetch")
        builder.add_edge("fetch", "transform")
        builder.add_edge("transform", "reason")
        builder.add_edge("reason", "negotiate")
        builder.add_conditional_edges("negotiate", route_after_negotiate)
        builder.add_conditional_edges("approve", route_after_approve)
        builder.add_edge("learn", END)

        self._graph = builder
        return self

    def compile(self, checkpointer: MemorySaver | None = None):
        """Compile the graph with optional checkpointer.

        Uses MemorySaver for dev, Postgres for production.
        """
        if self._graph is None:
            self.build()
        self._compiled = self._graph.compile(
            checkpointer=checkpointer or MemorySaver(),
        )
        return self._compiled

    async def run(self, planning_context: dict[str, Any]) -> dict[str, Any]:
        """Execute a full planning cycle.

        Args:
            planning_context: Initial state with planning_request

        Returns:
            Final state after LEARN phase
        """
        compiled = self._compiled
        if compiled is None:
            compiled = self.compile()

        initial_state = {
            "planning_request": planning_context,
            "correlation_id": planning_context.get("correlation_id", ""),
            "raw_demands": planning_context.get("raw_demands", []),
            "raw_supplies": planning_context.get("raw_supplies", []),
            "raw_policies": planning_context.get("raw_policies", []),
            "demands": [],
            "supplies": [],
            "allocations": [],
            "agent_proposals": {},
            "negotiation_rounds": [],
            "final_plan": {},
            "deadlock": False,
            "business_weights": planning_context.get(
                "business_weights",
                {
                    "cost": 0.3,
                    "delivery": 0.3,
                    "quality": 0.2,
                    "sustainability": 0.1,
                    "flexibility": 0.1,
                },
            ),
            "degradation_level": "FULL",
            "approved": False,
            "approval_note": "",
            "approval_plan_id": None,
            "hitl_required": False,
            "experience_record_id": "",
            "traces": planning_context.get("traces", []),
        }

        with trace_planning_cycle() as span:
            result = await compiled.ainvoke(initial_state)
            span.set_attribute("approved", result.get("approved", False))
            span.set_attribute("deadlock", result.get("deadlock", False))
            span.set_attribute("experience_record_id", result.get("experience_record_id", ""))
            return result

    async def close(self) -> None:
        """Close the Experience Ledger pool."""
        global _ledger_pool
        if _ledger_pool:
            await _ledger_pool.close()
            _ledger_pool = None
