"""Orchestrator Logging — per-node execution logging for MasterGraph.

Logs every node invocation in the planning cycle: start time, end time,
state delta, errors, and duration. Data is written to the `orchestrator_logs`
table for real-time dashboard visibility and post-hoc debugging.

A PostgreSQL NOTIFY (LISTEN/NOTIFY) is fired on each insert so the
dashboard can stream live execution events via WebSocket.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import asyncpg

from axon.core.config import settings
from axon.core.telemetry import log_event

# Lazy pool singleton
_log_pool: asyncpg.Pool | None = None


async def _get_log_pool() -> asyncpg.Pool:
    """Get or create the log connection pool (separate from ledger pool)."""
    global _log_pool
    if _log_pool is None:
        url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
        _log_pool = await asyncpg.create_pool(
            url,
            min_size=1,
            max_size=3,
            timeout=10,
        )
    return _log_pool


async def close_log_pool() -> None:
    """Close the log connection pool."""
    global _log_pool
    if _log_pool:
        await _log_pool.close()
        _log_pool = None


INSERT_LOG_SQL = """
INSERT INTO orchestrator_logs
    (run_id, node_name, event_type, event_data, state_before, state_after,
     error_message, duration_ms)
VALUES
    ($1::uuid, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8)
"""


async def write_log(
    run_id: UUID,
    node_name: str,
    event_type: str,  # "start", "end", "error"
    event_data: dict[str, Any] | None = None,
    state_before: dict[str, Any] | None = None,
    state_after: dict[str, Any] | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Insert a single orchestrator_logs row.

    Runs in fire-and-forget fashion — failures are logged but never
    propagated, ensuring the logging subsystem never breaks the graph.
    """
    try:
        pool = await _get_log_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                INSERT_LOG_SQL,
                run_id,
                node_name,
                event_type,
                json.dumps(event_data) if event_data else None,
                json.dumps(state_before, default=str) if state_before else None,
                json.dumps(state_after, default=str) if state_after else None,
                error_message,
                duration_ms,
            )
    except Exception as exc:
        log_event("warn", "orchestrator_log_write_failed", error=str(exc))


def logged_node(node_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory that wraps a graph node with execution logging.

    Usage in master_graph.py:
        @logged_node("retrieve_context")
        async def node_retrieve_context(state): ...

    The wrapper:
      1. Captures a snapshot of state keys before execution
      2. Records "start" event
      3. Executes the node
      4. Captures what changed in state
      5. Records "end" event with duration
      6. On error, records "error" event and re-raises
    """

    def decorator(
        node_fn: Callable[..., Any],
    ) -> Callable[..., Any]:
        async def wrapper(state: dict[str, Any]) -> Any:
            run_id = state.get("_run_id")
            if run_id is None:
                run_id = uuid4()
                state["_run_id"] = run_id

            state_before = _capture_state_snapshot(state)
            event_data = {"node": node_name}
            start = time.monotonic()

            await write_log(run_id, node_name, "start", event_data, state_before)

            try:
                result = await node_fn(state)

                elapsed_ms = int((time.monotonic() - start) * 1000)

                state_after = _capture_state_snapshot(state, result)

                await write_log(
                    run_id,
                    node_name,
                    "end",
                    event_data={"node": node_name, "result_keys": list(result.keys())},
                    state_before=state_before,
                    state_after=state_after,
                    duration_ms=elapsed_ms,
                )

                return result

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                error_msg = f"{type(exc).__name__}: {exc}"

                await write_log(
                    run_id,
                    node_name,
                    "error",
                    event_data={"node": node_name},
                    state_before=state_before,
                    error_message=error_msg,
                    duration_ms=elapsed_ms,
                )

                log_event(
                    "warn",
                    "node_execution_error",
                    node=node_name,
                    error=error_msg,
                )
                raise

        return wrapper

    return decorator


def _capture_state_snapshot(
    state: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a lightweight snapshot of state for logging.

    Omits internal keys (_store, _run_id) and truncates large lists
    to keep the JSONB payload manageable.
    """
    snapshot: dict[str, Any] = {}

    for key in state:
        if key.startswith("_"):
            continue
        val = state[key]
        snapshot[key] = _truncate_value(val)

    if result:
        for key in result:
            snapshot[key] = _truncate_value(result[key])

    return snapshot


def _truncate_value(val: Any, max_list: int = 100) -> Any:
    """Truncate large lists to avoid bloated log rows."""
    if isinstance(val, list):
        if len(val) > max_list:
            return {
                "_truncated": True,
                "count": len(val),
                "sample": val[:max_list],
            }
        return val
    if isinstance(val, dict):
        return {k: _truncate_value(v, max_list) for k, v in val.items()}
    return val
