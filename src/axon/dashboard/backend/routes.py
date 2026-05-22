"""Control Tower API routes — weights, plans, HITL approvals, system health."""

from __future__ import annotations

import contextlib
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from axon.agents.tools import TOOL_CATALOG
from axon.connectors.circuit_breaker import DegradationMonitor
from axon.core.config import settings
from axon.core.learning import ExperienceLedger, LedgerQuery
from axon.dashboard.backend.board_repo import BoardRepository
from axon.dashboard.backend.models import (
    AgentInfo,
    ApprovalAction,
    PendingApproval,
    PlanDetailResponse,
    PlanListResponse,
    PlanSummary,
    SystemHealth,
    WeightsResponse,
    WeightsUpdateRequest,
)
from axon.dashboard.backend.notifications import (
    get_pending_approvals,
)
from axon.dashboard.backend.notifications import (
    remove_pending_approval as _remove_pending,
)
from axon.orchestrator.conflict_resolver import BusinessWeights, NegotiationConfig

router = APIRouter(tags=["Control Tower"])


# ---------------------------------------------------------------------------
# Singletons — in-memory state with DB persistence (axon_board schema)
# ---------------------------------------------------------------------------

_current_weights = BusinessWeights()
_negotiation_config = NegotiationConfig(weights=_current_weights)
_ledger: ExperienceLedger | None = None
_board: BoardRepository | None = None


def _get_ledger() -> ExperienceLedger:
    global _ledger
    if _ledger is None:
        _ledger = ExperienceLedger()
    return _ledger


def _get_board() -> BoardRepository:
    global _board
    if _board is None:
        _board = BoardRepository()
    return _board


# =========================================================================
# Health & Status
# =========================================================================


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check — minimal, always returns 200 if the process is alive."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready")
async def readiness():
    """Readiness check — verifies downstream dependencies are available."""
    from typing import Any

    checks: dict[str, str] = {}
    healthy = True

    # Check DB connectivity
    try:
        board = _get_board()
        await board.list_hitl_queue()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        healthy = False

    # Check Redis (best-effort)
    try:
        from redis.asyncio import Redis as AsyncRedis

        r: AsyncRedis[Any] = AsyncRedis.from_url(
            settings.redis.url,
            socket_timeout=3,
        )
        _ = await r.ping()
        await r.close()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"unavailable: {exc}"

    status_code = 200 if healthy else 503
    return {"status": "ready" if healthy else "not ready", "checks": checks}, status_code


@router.get("/system", response_model=SystemHealth)
async def system_health():
    """Return system-wide health and degradation status."""
    monitor = DegradationMonitor()
    ledger = _get_ledger()

    try:
        total = await ledger.count()
    except Exception:
        total = 0

    # Degradation level from config or monitor
    deg_level = "FULL"
    with contextlib.suppress(Exception):
        deg_level = monitor.evaluate().value

    return SystemHealth(
        degradation_level=deg_level,
        healthy_servers=monitor.healthy_servers,
        unhealthy_servers=monitor.unhealthy_servers,
        total_plans=total,
        pending_approvals=len(get_pending_approvals()),
    )


# =========================================================================
# Business Weights
# =========================================================================


@router.get("/weights", response_model=WeightsResponse)
async def get_weights():
    """Return current strategic business weights (DB-backed, in-memory fallback)."""
    global _current_weights
    with contextlib.suppress(Exception):
        db_w = await _get_board().get_weights()
        if db_w:
            _current_weights = BusinessWeights(**db_w)
    return WeightsResponse(weights=_current_weights)


@router.put("/weights", response_model=WeightsResponse)
async def update_weights(update: WeightsUpdateRequest):
    """Update strategic business weights and persist to DB."""
    global _current_weights
    _current_weights = update.apply_to(_current_weights)
    with contextlib.suppress(Exception):
        board = _get_board()
        await board.save_weights(_current_weights.model_dump())
        await board.record_event(
            "weights_updated", actor="api", detail=_current_weights.model_dump()
        )
    return WeightsResponse(weights=_current_weights)


@router.get("/weights/defaults", response_model=WeightsResponse)
async def reset_weights():
    """Reset weights to defaults and persist to DB."""
    global _current_weights
    _current_weights = BusinessWeights()
    with contextlib.suppress(Exception):
        await _get_board().save_weights(_current_weights.model_dump())
    return WeightsResponse(weights=_current_weights)


# =========================================================================
# Plans (from Experience Ledger)
# =========================================================================


@router.get("/plans", response_model=PlanListResponse)
async def list_plans(
    limit: int = 20,
    offset: int = 0,
    tag: str | None = None,
):
    """List plans from the Experience Ledger."""
    ledger = _get_ledger()
    query = LedgerQuery(limit=limit, offset=offset)
    if tag:
        query.tags = [tag]

    try:
        records = await ledger.query(query)
        total = await ledger.count()
    except Exception:
        records = []
        total = 0

    plans = [
        PlanSummary(
            plan_id=r.plan_id,
            created_at=r.created_at,
            tags=r.tags,
            plan_confidence=r.plan_confidence,
            allocation_count=len(r.final_plan),
            deadlock="deadlock" in str(r.tags),
            approved="approved" in str(r.tags),
        )
        for r in records
    ]

    return PlanListResponse(plans=plans, total=total, offset=offset, limit=limit)


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(plan_id: UUID):
    """Get full detail for a single plan."""
    ledger = _get_ledger()
    try:
        record = await ledger.get(plan_id)
    except Exception:
        record = None

    if record is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanDetailResponse(
        plan_id=record.plan_id,
        context=record.context.model_dump(mode="json") if record.context else {},
        final_plan=record.final_plan,
        negotiations=record.negotiations,
        traces=[t.model_dump(mode="json") for t in record.traces],
        outcome=record.outcome.model_dump(mode="json") if record.outcome else None,
        tags=record.tags,
        plan_confidence=record.plan_confidence,
        created_at=record.created_at,
    )


# =========================================================================
# HITL Approvals
# =========================================================================


@router.get("/approvals/pending", response_model=list[PendingApproval])
async def list_pending_approvals():
    """List all plans pending human approval (DB-backed queue merged with in-memory)."""
    merged: dict[str, PendingApproval] = {}

    # 1. Load from persistent DB queue (seed data + runtime submissions)
    with contextlib.suppress(Exception):
        db_rows = await _get_board().list_hitl_queue()
        for row in db_rows:
            pid = str(row["plan_id"])
            merged[pid] = PendingApproval(
                plan_id=row["plan_id"],
                context_summary=row.get("context_summary", ""),
                deadlock=bool(row.get("deadlock", False)),
                demand_count=int(row.get("demand_count", 0)),
                supply_count=int(row.get("supply_count", 0)),
                agent_proposals=int(row.get("agent_proposals", 0)),
                negotiation_rounds=int(row.get("negotiation_rounds", 0)),
                global_utility=row.get("global_utility"),
                created_at=row.get("created_at"),
                requires_approval=bool(row.get("requires_approval", True)),
            )

    # 2. Overlay in-memory approvals (runtime submissions take precedence)
    for plan_id, data in get_pending_approvals().items():
        pid = str(plan_id)
        merged[pid] = PendingApproval(
            plan_id=plan_id,
            context_summary=data.get("context_summary", ""),
            deadlock=data.get("deadlock", False),
            demand_count=data.get("demand_count", 0),
            supply_count=data.get("supply_count", 0),
            agent_proposals=data.get("agent_proposals", 0),
            negotiation_rounds=data.get("negotiation_rounds", 0),
            global_utility=data.get("global_utility"),
            created_at=data.get("created_at"),
            requires_approval=data.get("requires_approval", True),
        )

    return list(merged.values())


@router.post("/approvals/action")
async def approve_or_reject(action: ApprovalAction):
    """Approve or reject a plan pending HITL approval."""
    plan_id = action.plan_id
    data = _remove_pending(plan_id)  # remove from in-memory queue first

    # Also remove from DB queue; covers DB-seeded items not in the in-memory dict
    db_row: dict | None = None
    with contextlib.suppress(Exception):
        db_row = await _get_board().remove_from_hitl_queue(plan_id)
    if data is None:
        data = db_row

    if data is None:
        raise HTTPException(status_code=404, detail="No pending approval for this plan")
    note = action.note or ("Approved" if action.approved else "Rejected")

    # Persist audit record and board event (best-effort, never blocks response)
    with contextlib.suppress(Exception):
        board = _get_board()
        await board.record_approval(plan_id, action.approved, note)
        event_type = "plan_approved" if action.approved else "plan_rejected"
        await board.record_event(
            event_type, actor="planning_manager", plan_id=plan_id, detail={"note": note}
        )

    # Tag the experience ledger record (best-effort)
    ledger = _get_ledger()
    try:
        record = await ledger.get(plan_id)
        if record:
            record.tags.append("approved" if action.approved else "rejected")
    except Exception:
        pass

    return {
        "plan_id": plan_id,
        "approved": action.approved,
        "note": note,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/approvals/config")
async def get_approval_config():
    """Return HITL configuration settings (DB-backed, defaults as fallback)."""
    db_cfg: dict = {}
    with contextlib.suppress(Exception):
        db_cfg = await _get_board().get_config() or {}
    return {
        "max_rounds_before_deadlock": db_cfg.get(
            "max_negotiation_rounds", _negotiation_config.max_rounds
        ),
        "requires_approval_for_deadlock": True,
        "requires_approval_for_high_impact": True,
        "high_impact_threshold": 0.8,
        "vip_priority_threshold": db_cfg.get("vip_priority_threshold", 80),
        "hitl_delay_days": db_cfg.get("hitl_delay_days", 7),
        "hitl_cost_threshold": float(db_cfg.get("hitl_cost_threshold", 50000.0)),
        "auto_approve_confidence": db_cfg.get("auto_approve_confidence", 0.5),
    }


# =========================================================================
# Agents & Tools
# =========================================================================


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """List all domain agents and their assigned tools."""
    from axon.agents.tools import TOOL_CATALOG

    agents: dict[str, AgentInfo] = {}

    # Collect agents from tool catalog
    for tool in TOOL_CATALOG:
        for agent_id in tool.agent_ids:
            if agent_id not in agents:
                domain = "unknown"
                # Map agent_id to domain
                if agent_id in ("sales", "finance", "procurement"):
                    domain = "commercial"
                elif agent_id in ("production", "warehouse", "logistics"):
                    domain = "operations"
                elif agent_id in ("maintenance", "pd", "qa", "qc"):
                    domain = "technical"
                agents[agent_id] = AgentInfo(
                    agent_id=agent_id,
                    domain=domain,
                    tool_count=0,
                    tool_names=[],
                )
            agents[agent_id].tool_names.append(tool.name)

    for agent in agents.values():
        agent.tool_count = len(agent.tool_names)
        agent.tool_names.sort()

    return sorted(agents.values(), key=lambda a: a.agent_id)


@router.get("/tools")
async def list_tools():
    """List all registered MCP tools."""
    tools = []
    for tool in TOOL_CATALOG:
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "server": tool.server,
                "direction": tool.direction,
                "agent_ids": tool.agent_ids,
            }
        )
    return {"tools": tools, "total": len(tools)}
