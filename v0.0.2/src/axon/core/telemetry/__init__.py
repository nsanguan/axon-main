"""
Axon Telemetry — Logfire / OpenTelemetry instrumentation.

Provides structured logging, span tracing, and correlation-ID propagation
across all layers: MCP connectors → agents → orchestrator → experience ledger.

Usage:
    from axon.core.telemetry import log, span, trace_mcp_call, trace_agent_reasoning
    from axon.core.config import settings

    # Initialize once at startup:
    init_telemetry(settings)
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

import logfire
import structlog

from axon.core.config import Settings

# =============================================================================
# Correlation ID — propagated through contextvars across async boundaries
# =============================================================================

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

# =============================================================================
# Structured logger (structlog)
# =============================================================================

logger: structlog.BoundLogger = structlog.get_logger("axon")


def init_telemetry(settings: Settings) -> None:
    """Initialize Logfire and structlog for the Axon application.

    Call once at startup, before any agents or connectors are created.
    PydanticAI auto-instruments if Logfire is configured first.
    """
    logfire.configure(
        token=settings.logfire_token or None,
        service_name="axon",
        service_version="0.0.2",
        environment="development",
        send_to_logfire=bool(settings.logfire_token),
        console=logfire.ConsoleOptions(
            colors="auto",
            verbose=False,
        ),
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger.info("telemetry_initialized", service="axon", version="0.0.2")


# =============================================================================
# Correlation ID management
# =============================================================================


def set_correlation_id(cid: str | None = None) -> str:
    """Set or generate a correlation ID for the current context.

    Returns the ID so callers can pass it downstream.
    """
    cid = cid or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Return the current correlation ID, generating one if none set."""
    cid = _correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
    return cid


# =============================================================================
# Span helpers — use as decorators or context managers
# =============================================================================


def trace_mcp_call(server_name: str, tool_name: str) -> logfire.LogfireSpan:
    """Start a span for an MCP tool call. Use as context manager.

    Example:
        with trace_mcp_call("oracle_ebs", "get_inventory_levels") as span:
            result = await session.call_tool(...)
            span.set_attribute("item_count", len(result))
    """
    span = logfire.span(
        f"mcp_call:{server_name}.{tool_name}",
        server=server_name,
        tool=tool_name,
        correlation_id=get_correlation_id(),
    )
    return span


def trace_agent_reasoning(agent_id: str, round_number: int = 0) -> logfire.LogfireSpan:
    """Start a span for agent reasoning.

    Example:
        with trace_agent_reasoning("sales", round_number=1) as span:
            proposal = await agent.propose(context)
            span.set_attribute("confidence", proposal.confidence)
    """
    span = logfire.span(
        f"agent_reasoning:{agent_id}",
        agent_id=agent_id,
        round_number=round_number,
        correlation_id=get_correlation_id(),
    )
    return span


def trace_negotiation_round(round_number: int) -> logfire.LogfireSpan:
    """Start a span for a negotiation round.

    Example:
        with trace_negotiation_round(1) as span:
            result = await resolver.resolve(proposals)
            span.set_attribute("resolved", result.resolved)
            span.set_attribute("global_utility", result.global_utility)
    """
    span = logfire.span(
        f"negotiation_round:{round_number}",
        round_number=round_number,
        correlation_id=get_correlation_id(),
    )
    return span


def trace_planning_cycle() -> logfire.LogfireSpan:
    """Start a top-level span for a full planning cycle.

    Example:
        with trace_planning_cycle() as span:
            plan = await master_graph.run(context)
            span.set_attribute("plan_id", str(plan.id))
    """
    cid = set_correlation_id()
    span = logfire.span(
        "planning_cycle",
        correlation_id=cid,
    )
    return span


# =============================================================================
# Structured logging helpers
# =============================================================================


def log_event(
    level: str,
    event: str,
    agent_id: str | None = None,
    server_name: str | None = None,
    tool_name: str | None = None,
    **kwargs: Any,
) -> None:
    """Log a structured event with correlation ID and optional context.

    Args:
        level: "info", "warn", "error"
        event: Human-readable event name
        agent_id: Which agent produced this event
        server_name: Which MCP server was involved
        tool_name: Which MCP tool was called
        **kwargs: Additional structured fields
    """
    log_fn = getattr(logger, level, logger.info)
    log_fn(
        event,
        correlation_id=get_correlation_id(),
        agent_id=agent_id,
        server=server_name,
        tool=tool_name,
        **kwargs,
    )


def log_mcp_error(server_name: str, tool_name: str, error: str, attempts: int = 0) -> None:
    """Log an MCP error for circuit breaker tracking."""
    logger.error(
        "mcp_error",
        correlation_id=get_correlation_id(),
        server=server_name,
        tool=tool_name,
        error=error,
        consecutive_failures=attempts,
    )


def log_degradation(level: str, condition: str) -> None:
    """Log a degradation level change."""
    logger.warning(
        "degradation_change",
        correlation_id=get_correlation_id(),
        level=level,
        condition=condition,
    )
