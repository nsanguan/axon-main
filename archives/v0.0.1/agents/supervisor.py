"""
agents.supervisor — Supervisor Node routing logic.

The Supervisor is a deterministic decision node (no LLM) that routes the
workflow after the Planning Manager completes.  It reads ``AxonState`` and
returns the name of the next graph node.

Routing rules (evaluated in priority order):
1. maintenance_constraints non-empty AND planning_decision.action == 'shortage'
   → ``"purchase_cluster"`` (shortage takes priority even with constraints)
2. planning_decision.action == 'shortage' AND shortages non-empty
   → ``"purchase_cluster"`` (trigger the Buyer → Manager → Director cluster)
3. planning_decision.action == 'hitl_required'
   → ``"hitl_checkpoint"`` (pause for human review of planning exception)
4. planning_decision.confidence < 0.7
   → ``"executive_escalation"`` (escalate to Executive Agent)
5. Otherwise (action == 'allocate' or 'no_action')
   → ``"qa_compliance_checkpoint"`` (pass through guardrails then write)
"""

from __future__ import annotations

from orchestrator.state import AxonState


def supervisor_route(state: AxonState) -> str:
    """
    Deterministic supervisor router.

    Called as a LangGraph conditional-edge function after
    ``planning_manager_node``.  Returns the name of the next node.
    """
    decision = state.get("planning_decision") or {}
    action: str = decision.get("action", "no_action")
    confidence: float = decision.get("confidence", 1.0)

    # ── Priority 1: shortage detected → Purchase Cluster ─────────────────────
    if action == "shortage" and state.get("shortages"):
        return "purchase_cluster"

    # ── Priority 2: planning exception → HITL checkpoint ─────────────────────
    if action == "hitl_required":
        return "hitl_checkpoint"

    # ── Priority 3: low confidence → Executive escalation ────────────────────
    if confidence < 0.7:
        return "executive_escalation"

    # ── Default: allocations done → pass through QA + Finance guardrails ─────
    return "qa_compliance_checkpoint"
