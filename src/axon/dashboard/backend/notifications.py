"""Dashboard notifications — WebSocket and in-memory event bus for the Control Tower.

Provides the notification functions called by the Master Graph to alert
the dashboard of pending approvals and new plan records.
"""

from __future__ import annotations

from uuid import UUID

from axon.core.telemetry import log_event

# =============================================================================
# In-memory pending approvals (shared with routes.py)
# =============================================================================

_pending_approvals: dict[UUID, dict[str, object]] = {}


async def notify_pending_approval(
    plan_id: UUID,
    reason: str,
    context: dict[str, object] | None = None,
) -> None:
    """Called by MasterGraph when a plan enters HITL approval state.

    Adds the plan to the pending approvals queue for the dashboard.
    """
    _pending_approvals[plan_id] = {
        "plan_id": plan_id,
        "reason": reason,
        "context": context or {},
        "status": "pending",
    }
    log_event("info", "dashboard:approval_pending", plan_id=str(plan_id), reason=reason)


async def notify_plan_recorded(
    plan_id: UUID,
    traces: list[dict[str, object]] | None = None,
    confidence: float | None = None,
) -> None:
    """Called by MasterGraph when a plan is recorded in the Experience Ledger."""
    log_event("info", "dashboard:plan_recorded", plan_id=str(plan_id), confidence=confidence)


def get_pending_approvals() -> dict[UUID, dict[str, object]]:
    """Return all pending approvals (called by routes.py)."""
    return _pending_approvals


def remove_pending_approval(plan_id: UUID) -> dict[str, object] | None:
    """Remove and return a pending approval (called on approve/reject)."""
    return _pending_approvals.pop(plan_id, None)
