"""
E2E Simulation Scenario — YAML scenario frame for deterministic planning cycles.

Scenarios define initial Demand/Supply state, business weights, and expected
outcomes. The simulator runs a deterministic planning cycle and validates
the results against expectations.

Run:
    python -m tests.scenarios.run_scenario tests/scenarios/basic_plan.yaml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationScenario:
    """A complete E2E simulation scenario."""

    name: str = "unnamed"
    description: str = ""

    # Initial state
    demands: list[dict[str, Any]] = field(default_factory=list)
    supplies: list[dict[str, Any]] = field(default_factory=list)
    policies: list[dict[str, Any]] = field(default_factory=list)

    # Configuration
    business_weights: dict[str, float] = field(
        default_factory=lambda: {
            "cost": 0.3,
            "delivery": 0.3,
            "quality": 0.2,
            "sustainability": 0.1,
            "flexibility": 0.1,
        }
    )
    max_negotiation_rounds: int = 5
    auto_approve: bool = False

    # Expected results (for validation)
    expected_allocation_count: int | None = None
    expected_confidence_min: float = 0.0
    expected_deadlock: bool | None = None
    expected_violations: int = 0

    # Agent proposals (simulated)
    agent_proposals: dict[str, dict[str, Any]] = field(default_factory=dict)
