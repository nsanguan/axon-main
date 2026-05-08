"""
WriteGate — HITL-gating and audit layer for WRITE MCP tool calls.

All WRITE tool calls from agents pass through WriteGate, which:
  1. Checks whether HITL approval is required (based on gating rules)
  2. Routes to HITL queue (dashboard pending_approvals) when needed
  3. Logs every write to the Experience Ledger for audit trail
  4. Raises WriteGateError if HITL required but not yet approved

Gating rules (from docs/mcp-tools.md):
  - Purchase requisition amount > threshold    → HITL required
  - Schedule change shifting delivery > 7 days → HITL required
  - All other WRITE tools                      → auto-execute + audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from axon.core.config import settings
from axon.core.telemetry import log_event

# =============================================================================
# Types
# =============================================================================


@dataclass
class WriteAuditRecord:
    """Immutable audit record for a single WRITE tool execution."""

    audit_id: UUID = field(default_factory=uuid4)
    tool_name: str = ""
    agent_id: str = ""
    server_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    hitl_required: bool = False
    hitl_approved: bool = False
    approved_by: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": str(self.audit_id),
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "server_name": self.server_name,
            "arguments": self.arguments,
            "hitl_required": self.hitl_required,
            "hitl_approved": self.hitl_approved,
            "approved_by": self.approved_by,
            "result": self.result,
            "error": self.error,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }


class WriteGateError(Exception):
    """Raised when a WRITE tool call requires HITL but approval is missing."""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        audit_id: UUID | None = None,
    ):
        self.tool_name = tool_name
        self.reason = reason
        self.audit_id = audit_id
        super().__init__(f"WriteGate: {tool_name} — {reason}")


# =============================================================================
# In-memory audit store (production: flushed to Postgres)
# =============================================================================

_audit_records: list[dict[str, Any]] = []
_pending_write_approvals: dict[str, dict[str, Any]] = {}


# =============================================================================
# Gating logic
# =============================================================================


def requires_hitl(
    tool_name: str,
    arguments: dict[str, Any],
    tool_spec_direction: str = "WRITE",
) -> tuple[bool, str]:
    """Determine if a WRITE tool call requires human approval.

    Args:
        tool_name: MCP tool name being called
        arguments: Tool call arguments
        tool_spec_direction: Direction from tool catalog

    Returns:
        (requires_hitl: bool, reason: str)
    """
    if tool_spec_direction != "WRITE":
        return False, "READ tools never require HITL"

    if not settings.writeback.enabled:
        return False, "Write-back disabled in config"

    # Rule 1: Purchase requisitions over threshold
    if tool_name == "create_purchase_requisition":
        qty = float(arguments.get("quantity", 0))
        price_per_unit = float(arguments.get("price_per_unit", 0))
        total = qty * price_per_unit if price_per_unit > 0 else qty * 100  # estimate
        threshold = settings.writeback.purchase_req_threshold
        if total >= threshold:
            return True, f"Purchase req amount ${total:.0f} ≥ ${threshold:.0f} threshold"

    # Rule 2: Schedule shifts > 7 days
    if tool_name == "reschedule_wip_job":
        import datetime as dt

        try:
            new_end = dt.date.fromisoformat(arguments.get("new_end", ""))
            if "old_end" in arguments:
                old_end = dt.date.fromisoformat(arguments["old_end"])
                shift = abs((new_end - old_end).days)
            else:
                shift = 999  # No baseline — conservatively flag
            threshold = settings.writeback.schedule_shift_days_threshold
            if shift >= threshold:
                return True, f"Schedule shift {shift}d ≥ {threshold}d threshold"
        except (ValueError, TypeError):
            pass  # Can't parse dates — flag for safety
            return True, "Could not validate schedule shift — flagging for review"

    # Rule 3: All other WRITE tools — no HITL needed, just audit
    return False, ""


# =============================================================================
# WriteGate execution
# =============================================================================


async def gate_write_call(
    tool_name: str,
    agent_id: str,
    server_name: str,
    arguments: dict[str, Any],
    correlation_id: str = "",
    call_fn=None,
) -> Any:
    """Gate and execute a WRITE tool call.

    Steps:
      1. Determine if HITL is required
      2. If HITL required and not pre-approved, raise WriteGateError
      3. Execute the call via call_fn
      4. Audit the result

    Args:
        tool_name: MCP tool name
        agent_id: Calling agent
        server_name: MCP server name
        arguments: Tool arguments
        correlation_id: Optional correlation ID
        call_fn: Async callable that executes the MCP tool

    Returns:
        Tool result

    Raises:
        WriteGateError if HITL required but not approved
    """
    hitl_needed, reason = requires_hitl(tool_name, arguments)

    audit = WriteAuditRecord(
        tool_name=tool_name,
        agent_id=agent_id,
        server_name=server_name,
        arguments=arguments,
        hitl_required=hitl_needed,
        correlation_id=correlation_id,
    )

    if hitl_needed:
        # Check if pre-approved via pending queue
        approval_key = f"{tool_name}:{hash(frozenset(arguments.items()))}"
        pending = _pending_write_approvals.get(approval_key)

        if not pending or not pending.get("approved"):
            audit.error = f"HITL pending: {reason}"
            _audit_records.append(audit.to_dict())

            # Register in pending queue for dashboard
            plan_id = uuid4()
            _pending_write_approvals[approval_key] = {
                "plan_id": str(plan_id),
                "tool_name": tool_name,
                "agent_id": agent_id,
                "arguments": arguments,
                "reason": reason,
                "approved": False,
                "created_at": datetime.now(UTC).isoformat(),
            }

            log_event(
                "warn",
                "write_gate_hitl_required",
                tool_name=tool_name,
                agent_id=agent_id,
                reason=reason,
            )

            # Notify dashboard
            try:
                from axon.dashboard.backend import notify_pending_approval

                await notify_pending_approval(plan_id, f"Write: {tool_name} — {reason}")
            except Exception:
                pass

            raise WriteGateError(
                tool_name=tool_name,
                reason=reason,
                audit_id=audit.audit_id,
            )

        # Pre-approved
        audit.hitl_approved = True
        audit.approved_by = pending.get("approved_by", "dashboard")
        _pending_write_approvals.pop(approval_key, None)

    # Execute the tool call
    if call_fn is None:
        audit.error = "No call_fn provided"
        _audit_records.append(audit.to_dict())
        raise ValueError(f"WriteGate: no call_fn for {tool_name}")

    try:
        result = await call_fn(**arguments)
        audit.result = result if isinstance(result, dict) else {"result": str(result)}
    except Exception as exc:
        audit.error = str(exc)
        _audit_records.append(audit.to_dict())
        raise

    # Audit the successful call
    _audit_records.append(audit.to_dict())

    log_event(
        "info",
        "write_tool_executed",
        tool_name=tool_name,
        agent_id=agent_id,
        hitl_needed=hitl_needed,
        audit_id=str(audit.audit_id),
    )

    return audit.result


# =============================================================================
# Approval interface (called from dashboard)
# =============================================================================


def approve_pending_write(
    plan_id: str,
    approved: bool,
    approved_by: str = "dashboard",
) -> bool:
    """Approve or reject a pending WRITE tool call.

    Called from the dashboard API when a human reviews a pending write.

    Returns True if found and updated, False if not found.
    """
    for _key, pending in list(_pending_write_approvals.items()):
        if pending.get("plan_id") == plan_id:
            pending["approved"] = approved
            pending["approved_by"] = approved_by
            pending["resolved_at"] = datetime.now(UTC).isoformat()
            log_event(
                "info",
                "write_gate_resolved",
                tool_name=pending["tool_name"],
                approved=approved,
                by=approved_by,
            )
            return True
    return False


# =============================================================================
# Audit retrieval
# =============================================================================


def get_write_audit_log(
    limit: int = 50,
    offset: int = 0,
    tool_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent write audit records, with optional tool filter."""
    records = list(reversed(_audit_records))  # newest first
    if tool_name:
        records = [r for r in records if r["tool_name"] == tool_name]
    return records[offset : offset + limit]


def count_write_audit_records() -> int:
    """Return total count of write audit records."""
    return len(_audit_records)
