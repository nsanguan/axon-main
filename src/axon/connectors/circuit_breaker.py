"""Circuit Breaker — per-MCP-server resilience with degradation levels.

Implements the state machine:
  CLOSED ──(3 consecutive failures)──▶ OPEN ──(60s cooldown)──▶ HALF_OPEN
  HALF_OPEN ──(1 success)──▶ CLOSED
  HALF_OPEN ──(1 failure)──▶ OPEN

Plus system-wide degradation levels:
  FULL → DEGRADED → LIMITED → CRITICAL

Usage:
    from axon.connectors.circuit_breaker import CircuitBreaker, DegradationMonitor

    cb = CircuitBreaker("oracle_ebs")
    if cb.allow_call():
        try:
            result = await connector.get_inventory_levels()
            cb.record_success()
        except Exception:
            cb.record_failure()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from axon.core.telemetry import log_degradation, log_event, log_mcp_error

# =============================================================================
# State enums
# =============================================================================


class BreakerState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class DegradationLevel(StrEnum):
    FULL = "FULL"  # All MCP servers healthy
    DEGRADED = "DEGRADED"  # 1 server unhealthy
    LIMITED = "LIMITED"  # 2+ servers or RAG unhealthy
    CRITICAL = "CRITICAL"  # All servers unhealthy


# =============================================================================
# Circuit Breaker (per server)
# =============================================================================


@dataclass
class CircuitBreaker:
    """Per-MCP-server circuit breaker with state machine.

    Defaults: 3 failures to OPEN, 60s cooldown before HALF_OPEN.
    """

    server_name: str
    failure_threshold: int = 3
    cooldown_seconds: int = 60

    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: datetime | None = None
    last_state_change: datetime = field(default_factory=lambda: datetime.now(UTC))

    def allow_call(self) -> bool:
        """Return True if a call to this server is allowed."""
        if self.state == BreakerState.CLOSED:
            return True
        if self.state == BreakerState.HALF_OPEN:
            return True
        # OPEN — check cooldown
        if self._cooldown_elapsed():
            self._transition_to(BreakerState.HALF_OPEN)
            return True
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == BreakerState.HALF_OPEN:
            self._transition_to(BreakerState.CLOSED)
            self.failure_count = 0
        elif self.state == BreakerState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        log_mcp_error(self.server_name, "unknown", "circuit_breaker_failure", self.failure_count)

        if (
            self.state == BreakerState.CLOSED
            and self.failure_count >= self.failure_threshold
            or self.state == BreakerState.HALF_OPEN
        ):
            self._transition_to(BreakerState.OPEN)

    def force_open(self) -> None:
        """Manually trip the breaker (e.g., on transform failure)."""
        self._transition_to(BreakerState.OPEN)

    def reset(self) -> None:
        """Force-reset to CLOSED state (for testing or manual recovery)."""
        self.failure_count = 0
        self.last_failure_time = None
        self._transition_to(BreakerState.CLOSED)

    # =========================================================================
    # Internal
    # =========================================================================

    def _cooldown_elapsed(self) -> bool:
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        return elapsed >= self.cooldown_seconds

    def _transition_to(self, new_state: BreakerState) -> None:
        if self.state != new_state:
            old = self.state
            self.state = new_state
            self.last_state_change = datetime.now(UTC)
            log_event(
                "warn",
                "circuit_breaker_state_change",
                server_name=self.server_name,
                from_state=old.value,
                to_state=new_state.value,
            )


# =============================================================================
# Degradation Monitor (system-wide)
# =============================================================================


@dataclass
class DegradationMonitor:
    """Monitors all MCP server circuit breakers and computes system-wide level."""

    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    rag_server_name: str = "llmwiki"
    level: DegradationLevel = DegradationLevel.FULL

    def register(self, server_name: str, breaker: CircuitBreaker) -> None:
        self.breakers[server_name] = breaker

    def evaluate(self) -> DegradationLevel:
        """Recompute the degradation level based on breaker states."""
        unhealthy = [name for name, cb in self.breakers.items() if cb.state != BreakerState.CLOSED]
        rag_unhealthy = self.rag_server_name in unhealthy
        erp_unhealthy = [n for n in unhealthy if n != self.rag_server_name]
        count = len(erp_unhealthy)

        erp_count = len(self.breakers) - (1 if self.rag_server_name in self.breakers else 0)

        if len(unhealthy) == 0:
            new_level = DegradationLevel.FULL
        elif count >= erp_count:  # all ERP servers down
            new_level = DegradationLevel.CRITICAL
        elif count >= 2 or rag_unhealthy:
            new_level = DegradationLevel.LIMITED
        else:
            new_level = DegradationLevel.DEGRADED

        if new_level != self.level:
            self.level = new_level
            log_degradation(
                level=new_level.value,
                condition=f"Unhealthy servers: {unhealthy}",
            )

        return self.level

    @property
    def healthy_servers(self) -> list[str]:
        return [n for n, cb in self.breakers.items() if cb.state == BreakerState.CLOSED]

    @property
    def unhealthy_servers(self) -> list[str]:
        return [n for n, cb in self.breakers.items() if cb.state != BreakerState.CLOSED]
