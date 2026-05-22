"""BoardRepository — DB-backed storage for dashboard Control Tower state.

Wraps the ``axon_board`` schema tables:
  - ``business_weights``  — strategic weight vector (single row, id=1)
  - ``system_config``     — HITL thresholds and negotiation settings
  - ``hitl_queue``        — persistent HITL approval queue
  - ``approval_audit``    — immutable approval / rejection log
  - ``board_events``      — system activity feed
  - ``board_kpis``        — periodic KPI snapshots

Every public method suppresses its own errors: callers should wrap calls in
``contextlib.suppress(Exception)`` or ``try/except`` for graceful fallback
to in-memory state when the DB is unavailable.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg

from axon.core.config import settings
from axon.core.telemetry import log_event


class BoardRepository:
    """Async repository for the ``axon_board`` Postgres schema."""

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        self._pool = pool
        self._own_pool = pool is None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(
                url,
                min_size=1,
                max_size=3,
                timeout=10,
                command_timeout=10,
            )
        return self._pool

    async def close(self) -> None:
        """Close the connection pool (only if this instance owns it)."""
        if self._own_pool and self._pool:
            await self._pool.close()
            self._pool = None

    # ------------------------------------------------------------------
    # Business weights
    # ------------------------------------------------------------------

    async def get_weights(self) -> dict[str, float] | None:
        """Return the current weight row from ``axon_board.business_weights``.

        Returns ``None`` if the row does not yet exist.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT cost, delivery, quality, sustainability, flexibility "
                "FROM axon_board.business_weights WHERE id = 1"
            )
            return dict(row) if row else None

    async def save_weights(self, weights: dict[str, float]) -> None:
        """Upsert the ``axon_board.business_weights`` singleton row."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE axon_board.business_weights
                   SET cost=$1, delivery=$2, quality=$3,
                       sustainability=$4, flexibility=$5,
                       updated_at=now(), updated_by='api'
                 WHERE id = 1
                """,
                float(weights.get("cost", 0.3)),
                float(weights.get("delivery", 0.3)),
                float(weights.get("quality", 0.2)),
                float(weights.get("sustainability", 0.1)),
                float(weights.get("flexibility", 0.1)),
            )
        log_event("info", "board:weights_saved", weights=weights)

    # ------------------------------------------------------------------
    # System config
    # ------------------------------------------------------------------

    async def get_config(self) -> dict[str, Any] | None:
        """Return the singleton HITL configuration row."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM axon_board.system_config WHERE id = 1")
            if row is None:
                return None
            # Convert asyncpg Record to plain dict (Decimal → float for JSON compat)
            result: dict[str, Any] = {}
            for k, v in dict(row).items():
                result[k] = (
                    float(v)
                    if hasattr(v, "__float__") and not isinstance(v, (int, float, bool))
                    else v
                )
            return result

    # ------------------------------------------------------------------
    # HITL queue
    # ------------------------------------------------------------------

    async def add_to_hitl_queue(self, plan_id: UUID, data: dict[str, Any]) -> None:
        """Persist a new pending approval entry to ``axon_board.hitl_queue``."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO axon_board.hitl_queue
                    (plan_id, context_summary, deadlock, demand_count, supply_count,
                     agent_proposals, negotiation_rounds, global_utility,
                     requires_approval, reason, raw_context)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
                ON CONFLICT (plan_id) DO NOTHING
                """,
                plan_id,
                data.get("context_summary", ""),
                bool(data.get("deadlock", False)),
                int(data.get("demand_count", 0)),
                int(data.get("supply_count", 0)),
                int(data.get("agent_proposals", 0)),
                int(data.get("negotiation_rounds", 0)),
                data.get("global_utility"),
                bool(data.get("requires_approval", True)),
                data.get("reason", ""),
                json.dumps(data),
            )

    async def remove_from_hitl_queue(self, plan_id: UUID) -> dict[str, Any] | None:
        """Delete and return the queue entry for *plan_id*."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM axon_board.hitl_queue WHERE plan_id=$1 RETURNING *",
                plan_id,
            )
            return dict(row) if row else None

    async def list_hitl_queue(self) -> list[dict[str, Any]]:
        """Return all pending approvals from the persistent queue."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM axon_board.hitl_queue ORDER BY created_at")
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Approval audit
    # ------------------------------------------------------------------

    async def record_approval(
        self,
        plan_id: UUID,
        approved: bool,
        note: str = "",
        decided_by: str = "planning_manager",
    ) -> None:
        """Append an approval decision to the immutable audit trail."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO axon_board.approval_audit
                    (plan_id, approved, note, decided_by)
                VALUES ($1, $2, $3, $4)
                """,
                plan_id,
                approved,
                note,
                decided_by,
            )
        log_event(
            "info",
            "board:approval_recorded",
            plan_id=str(plan_id),
            approved=approved,
            decided_by=decided_by,
        )

    # ------------------------------------------------------------------
    # Board events
    # ------------------------------------------------------------------

    async def record_event(
        self,
        event_type: str,
        actor: str = "system",
        plan_id: UUID | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append an entry to the board activity feed."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO axon_board.board_events
                    (event_type, actor, plan_id, detail)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                event_type,
                actor,
                plan_id,
                json.dumps(detail or {}),
            )

    # ------------------------------------------------------------------
    # KPI snapshots
    # ------------------------------------------------------------------

    async def record_kpi_snapshot(
        self,
        total_plans: int,
        pending_approvals: int,
        approved_24h: int = 0,
        rejected_24h: int = 0,
        avg_confidence: float | None = None,
        degradation_level: str = "FULL",
        healthy_server_count: int = 0,
    ) -> None:
        """Insert a KPI snapshot row into ``axon_board.board_kpis``."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO axon_board.board_kpis
                    (total_plans, pending_approvals, approved_24h, rejected_24h,
                     avg_confidence, degradation_level, healthy_server_count)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                """,
                total_plans,
                pending_approvals,
                approved_24h,
                rejected_24h,
                avg_confidence,
                degradation_level,
                healthy_server_count,
            )
