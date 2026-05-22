"""Circuit Breaker state machine tests.

Verifies the CLOSED → OPEN → HALF_OPEN → CLOSED transition cycle per
the spec in docs/architecture.md:
  - 3 consecutive failures → OPEN
  - OPEN blocks all calls
  - HALF_OPEN after cooldown elapses
  - 1 success in HALF_OPEN → CLOSED
  - 1 failure in HALF_OPEN → OPEN again

Also tests per-server independence and DegradationMonitor.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from axon.connectors.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    DegradationLevel,
    DegradationMonitor,
)

# =============================================================================
# Helpers
# =============================================================================


def make_breaker(
    server: str = "test_server", threshold: int = 3, cooldown: int = 60
) -> CircuitBreaker:
    return CircuitBreaker(
        server_name=server, failure_threshold=threshold, cooldown_seconds=cooldown
    )


# =============================================================================
# Initial state
# =============================================================================


def test_initial_state_is_closed():
    cb = make_breaker()
    assert cb.state == BreakerState.CLOSED
    assert cb.failure_count == 0


def test_closed_allows_calls():
    cb = make_breaker()
    assert cb.allow_call() is True


# =============================================================================
# CLOSED → OPEN
# =============================================================================


def test_transitions_to_open_after_threshold_failures():
    cb = make_breaker(threshold=3)
    cb.record_failure()
    assert cb.state == BreakerState.CLOSED
    cb.record_failure()
    assert cb.state == BreakerState.CLOSED
    cb.record_failure()
    assert cb.state == BreakerState.OPEN


def test_open_blocks_calls_within_cooldown():
    cb = make_breaker(cooldown=9999)
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == BreakerState.OPEN
    assert cb.allow_call() is False


def test_force_open_transitions_from_closed():
    cb = make_breaker()
    cb.force_open()
    assert cb.state == BreakerState.OPEN


# =============================================================================
# OPEN → HALF_OPEN (cooldown elapsed)
# =============================================================================


def test_transitions_to_half_open_after_cooldown():
    cb = make_breaker(cooldown=1)
    # Trip to OPEN
    for _ in range(3):
        cb.record_failure()
    assert cb.state == BreakerState.OPEN

    # Backdate last_failure_time so cooldown appears elapsed
    cb.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
    assert cb.allow_call() is True
    assert cb.state == BreakerState.HALF_OPEN


def test_open_still_blocks_before_cooldown():
    cb = make_breaker(cooldown=9999)
    for _ in range(3):
        cb.record_failure()
    # Set a very recent failure time
    cb.last_failure_time = datetime.now(UTC)
    assert cb.allow_call() is False
    assert cb.state == BreakerState.OPEN


# =============================================================================
# HALF_OPEN → CLOSED (success recovers)
# =============================================================================


def test_success_in_half_open_closes_breaker():
    cb = make_breaker(cooldown=1)
    for _ in range(3):
        cb.record_failure()
    cb.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
    cb.allow_call()  # trigger HALF_OPEN
    assert cb.state == BreakerState.HALF_OPEN

    cb.record_success()
    assert cb.state == BreakerState.CLOSED
    assert cb.failure_count == 0


# =============================================================================
# HALF_OPEN → OPEN (failure re-trips)
# =============================================================================


def test_failure_in_half_open_reopens_breaker():
    cb = make_breaker(cooldown=1)
    for _ in range(3):
        cb.record_failure()
    cb.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
    cb.allow_call()  # trigger HALF_OPEN
    assert cb.state == BreakerState.HALF_OPEN

    cb.record_failure()
    assert cb.state == BreakerState.OPEN


# =============================================================================
# Reset
# =============================================================================


def test_reset_restores_closed_state():
    cb = make_breaker()
    for _ in range(3):
        cb.record_failure()
    assert cb.state == BreakerState.OPEN
    cb.reset()
    assert cb.state == BreakerState.CLOSED
    assert cb.failure_count == 0
    assert cb.allow_call() is True


# =============================================================================
# Success in CLOSED resets failure count
# =============================================================================


def test_success_in_closed_resets_failure_count():
    cb = make_breaker(threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == BreakerState.CLOSED


# =============================================================================
# Per-server independence
# =============================================================================


def test_per_server_independence():
    """Tripping one server's breaker must not affect another."""
    cb_a = make_breaker("server_a")
    cb_b = make_breaker("server_b")

    for _ in range(3):
        cb_a.record_failure()

    assert cb_a.state == BreakerState.OPEN
    assert cb_b.state == BreakerState.CLOSED
    assert cb_b.allow_call() is True


# =============================================================================
# DegradationMonitor
# =============================================================================


def test_degradation_full_when_all_closed():
    monitor = DegradationMonitor()
    monitor.breakers = {
        "oracle_ebs": make_breaker("oracle_ebs"),
        "sap": make_breaker("sap"),
        "llmwiki": make_breaker("llmwiki"),
    }
    monitor.evaluate()
    assert monitor.level == DegradationLevel.FULL


def test_degradation_degraded_when_one_open():
    monitor = DegradationMonitor()
    cb_ebs = make_breaker("oracle_ebs")
    for _ in range(3):
        cb_ebs.record_failure()
    monitor.breakers = {
        "oracle_ebs": cb_ebs,
        "sap": make_breaker("sap"),
        "llmwiki": make_breaker("llmwiki"),
    }
    monitor.evaluate()
    assert monitor.level == DegradationLevel.DEGRADED


def test_degradation_limited_when_rag_open():
    """RAG server open → LIMITED (even if ERP servers are healthy)."""
    monitor = DegradationMonitor()
    cb_rag = make_breaker("llmwiki")
    for _ in range(3):
        cb_rag.record_failure()
    monitor.breakers = {
        "oracle_ebs": make_breaker("oracle_ebs"),
        "sap": make_breaker("sap"),
        "llmwiki": cb_rag,
    }
    monitor.evaluate()
    assert monitor.level == DegradationLevel.LIMITED


def test_degradation_critical_when_all_erp_open():
    """All ERP servers OPEN → CRITICAL."""
    monitor = DegradationMonitor()
    cb_ebs = make_breaker("oracle_ebs")
    cb_sap = make_breaker("sap")
    for _ in range(3):
        cb_ebs.record_failure()
        cb_sap.record_failure()
    monitor.breakers = {
        "oracle_ebs": cb_ebs,
        "sap": cb_sap,
        "llmwiki": make_breaker("llmwiki"),
    }
    monitor.evaluate()
    assert monitor.level == DegradationLevel.CRITICAL


def test_degradation_critical_when_rag_open_plus_others():
    monitor = DegradationMonitor()
    cb_ebs = make_breaker("oracle_ebs")
    cb_sap = make_breaker("sap")
    cb_rag = make_breaker("llmwiki")
    for _ in range(3):
        cb_ebs.record_failure()
        cb_sap.record_failure()
        cb_rag.record_failure()
    monitor.breakers = {
        "oracle_ebs": cb_ebs,
        "sap": cb_sap,
        "llmwiki": cb_rag,
    }
    monitor.evaluate()
    assert monitor.level == DegradationLevel.CRITICAL
