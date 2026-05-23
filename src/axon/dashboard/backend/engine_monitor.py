"""Engine thread registry — in-memory tracking of LangGraph orchestration threads.

Provides a lightweight observability layer for the Control Tower dashboard.
Threads are registered by the escalation API and polled by the Engine
Monitoring page.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from axon.dashboard.backend.models import EngineSummary, ThreadInfo

_lock = threading.RLock()
_registry: dict[str, dict[str, Any]] = {}

MAX_RETAINED_THREADS = 500

STATUS_ORDER: list[str] = ["running", "waiting_for_approval", "completed", "error"]


def register_thread(
    thread_id: str,
    event_type: str,
    severity_score: float = 0.0,
    escalation_level: str = "worker",
    affected_departments: list[str] | None = None,
    summary: str = "",
) -> None:
    now = datetime.now(UTC).isoformat()
    progress = _compute_progress(escalation_level)

    with _lock:
        _registry[thread_id] = {
            "thread_id": thread_id,
            "event_type": event_type,
            "status": "running",
            "progress": progress,
            "severity_score": severity_score,
            "escalation_level": escalation_level,
            "affected_departments": affected_departments or [],
            "summary": summary,
            "created_at": now,
            "updated_at": now,
        }


def update_thread(
    thread_id: str,
    *,
    status: str | None = None,
    progress: float | None = None,
    escalation_level: str | None = None,
    severity_score: float | None = None,
    summary: str | None = None,
) -> None:
    with _lock:
        entry = _registry.get(thread_id)
        if entry is None:
            return
        now = datetime.now(UTC).isoformat()
        if status is not None:
            entry["status"] = status
        if progress is not None:
            entry["progress"] = progress
        if escalation_level is not None:
            entry["escalation_level"] = escalation_level
            entry["progress"] = _compute_progress(escalation_level)
        if severity_score is not None:
            entry["severity_score"] = severity_score
        if summary is not None:
            entry["summary"] = summary
        entry["updated_at"] = now


def mark_completed(thread_id: str, summary: str = "") -> None:
    update_thread(thread_id, status="completed", progress=1.0, summary=summary)


def mark_waiting_approval(thread_id: str, escalation_level: str = "executive", summary: str = "") -> None:
    progress = _compute_progress(escalation_level)
    update_thread(thread_id, status="waiting_for_approval", progress=progress, summary=summary)


def mark_error(thread_id: str, summary: str = "") -> None:
    update_thread(thread_id, status="error", summary=summary)


def list_threads() -> list[ThreadInfo]:
    with _lock:
        entries = list(_registry.values())
        _prune_if_needed()

    entries.sort(
        key=lambda e: (
            STATUS_ORDER.index(e["status"]) if e["status"] in STATUS_ORDER else 99,
            e["created_at"],
        ),
        reverse=False,
    )

    active_first = sorted(entries, key=lambda e: e["status"] == "completed")
    return [ThreadInfo(**e) for e in active_first]


def get_summary() -> EngineSummary:
    with _lock:
        threads = list(_registry.values())
        _prune_if_needed()

    total = len(threads)
    running = sum(1 for t in threads if t["status"] == "running")
    waiting = sum(1 for t in threads if t["status"] == "waiting_for_approval")
    completed = sum(1 for t in threads if t["status"] == "completed")
    error_count = sum(1 for t in threads if t["status"] == "error")

    scores = [t["severity_score"] for t in threads if t["severity_score"] > 0]
    avg_severity = sum(scores) / len(scores) if scores else 0.0

    levels = [t["escalation_level"] for t in threads]
    top_level = "none"
    for lv in ("executive", "director", "manager", "worker"):
        if lv in levels:
            top_level = lv
            break

    return EngineSummary(
        total_threads=total,
        running=running,
        waiting_for_approval=waiting,
        completed=completed,
        error=error_count,
        avg_severity=round(avg_severity, 1),
        top_escalation_level=top_level,
    )


def _prune_if_needed() -> None:
    with _lock:
        if len(_registry) <= MAX_RETAINED_THREADS:
            return
        completed_entries = [
            tid for tid, t in _registry.items()
            if t["status"] in ("completed", "error")
        ]
        if len(_registry) - len(completed_entries) >= MAX_RETAINED_THREADS:
            for tid in completed_entries[: len(completed_entries) // 2]:
                del _registry[tid]
        else:
            overflow = len(_registry) - MAX_RETAINED_THREADS
            for tid in completed_entries[:overflow]:
                del _registry[tid]


def _compute_progress(escalation_level: str) -> float:
    """Estimate progress based on escalation tier reached."""
    mapping: dict[str, float] = {
        "worker": 0.10,
        "manager": 0.35,
        "director": 0.65,
        "executive": 0.85,
    }
    return mapping.get(escalation_level, 0.05)
