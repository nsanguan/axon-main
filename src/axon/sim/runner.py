"""Axon simulation runner.

Loads YAML scenario files, drives the MasterGraph, and asserts expected
outcomes. Designed for:
  - CI regression testing
  - Scenario-based planning validation
  - KPI benchmarking (utility scores, HITL rates, etc.)

Usage (via CLI)::

    axon-sim run tests/scenarios/basic_plan.yaml
    axon-sim run tests/scenarios/ --pattern "*.yaml"

Or directly in Python::

    from axon.sim.runner import SimulationRunner
    runner = SimulationRunner()
    result = await runner.run_file("tests/scenarios/basic_plan.yaml")
"""

from __future__ import annotations

import asyncio
import glob
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
import yaml

log = structlog.get_logger(__name__)


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class ScenarioAssertion:
    """Expected outcome checks parsed from a YAML scenario file."""

    expected_allocation_count: int | None = None
    expected_confidence_min: float | None = None
    expected_deadlock: bool | None = None
    expected_violations: int | None = None
    expected_hitl_required: bool | None = None
    expected_status: str | None = None  # "approved", "hitl_required", etc.


@dataclass
class SimulationResult:
    """Outcome of a single simulation run."""

    scenario_name: str
    scenario_path: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    plan_result: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    run_id: str = field(default_factory=lambda: str(uuid4()))


# =============================================================================
# YAML loader
# =============================================================================


def _parse_period(start_str: str | None, end_str: str | None) -> dict[str, Any]:
    """Parse period start/end strings into ISO datetime dicts."""
    def _dt(s: str) -> str:
        # Accept either "YYYY-MM-DD" or full ISO datetime
        if "T" not in s:
            return f"{s}T00:00:00+00:00"
        return s

    return {
        "start": _dt(start_str or "2026-01-01"),
        "end": _dt(end_str or "2026-12-31"),
    }


def load_scenario(path: str | Path) -> dict[str, Any]:
    """Load and validate a YAML scenario file.

    Returns a planning_context dict ready to pass to MasterGraph.run().
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")

    with open(path, "r") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Invalid scenario file: {path} (expected YAML mapping)")

    # Build demands list in domain model format
    demands: list[dict[str, Any]] = []
    for d in raw.get("demands", []):
        demands.append({
            "id": str(uuid4()),
            "item": {
                "system": "oracle_ebs",
                "entity_type": "inventory_item",
                "native_id": d["item_id"],
                "display_name": d.get("customer"),
            },
            "quantity": str(d.get("quantity", 0)),
            "period": _parse_period(d.get("period_start"), d.get("period_end")),
            "source": d.get("source", "forecast"),
            "confidence": float(d.get("confidence", 0.8)),
            "priority": int(d.get("priority", 50)),
        })

    # Build supplies list in domain model format
    supplies: list[dict[str, Any]] = []
    for s in raw.get("supplies", []):
        available_from = s.get("available_from") or s.get("arrival_date") or "2026-01-01"
        available_to = s.get("available_to") or "2026-12-31"
        supplies.append({
            "id": str(uuid4()),
            "item": {
                "system": "oracle_ebs",
                "entity_type": "inventory_item",
                "native_id": s["item_id"],
                "display_name": s.get("location") or s.get("supplier"),
            },
            "quantity": str(s.get("quantity", 0)),
            "period": _parse_period(available_from, available_to),
            "source": s.get("source", "on_hand"),
            "lead_time_days": int(s.get("lead_time_days", 0)),
        })

    weights: dict[str, float] = {
        "cost": float(raw.get("business_weights", {}).get("cost", 0.3)),
        "delivery": float(raw.get("business_weights", {}).get("delivery", 0.3)),
        "quality": float(raw.get("business_weights", {}).get("quality", 0.2)),
        "sustainability": float(raw.get("business_weights", {}).get("sustainability", 0.1)),
        "flexibility": float(raw.get("business_weights", {}).get("flexibility", 0.1)),
    }

    planning_context: dict[str, Any] = {
        "correlation_id": str(uuid4()),
        "raw_demands": [],
        "raw_supplies": [],
        "raw_policies": [],
        "demands": demands,
        "supplies": supplies,
        "business_weights": weights,
        "_scenario_name": raw.get("name", path.stem),
        "_max_negotiation_rounds": raw.get("max_negotiation_rounds", 5),
    }

    # Extract assertions separately (not passed to the graph)
    assertions = ScenarioAssertion(
        expected_allocation_count=raw.get("expected_allocation_count"),
        expected_confidence_min=raw.get("expected_confidence_min"),
        expected_deadlock=raw.get("expected_deadlock"),
        expected_violations=raw.get("expected_violations"),
        expected_hitl_required=raw.get("expected_hitl_required"),
        expected_status=raw.get("expected_status"),
    )

    return planning_context, assertions


# =============================================================================
# Assertions engine
# =============================================================================


def check_assertions(
    result: dict[str, Any],
    assertions: ScenarioAssertion,
) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) list for a completed planning run."""
    failures: list[str] = []
    warnings: list[str] = []

    final_plan: list[Any] = result.get("final_plan") or []
    rounds: list[Any] = result.get("negotiation_rounds") or []
    deadlock: bool = result.get("deadlock", False)
    hitl_required: bool = result.get("hitl_required", False)
    status: str = result.get("status", "unknown")

    # Allocation count
    if assertions.expected_allocation_count is not None:
        if len(final_plan) < assertions.expected_allocation_count:
            failures.append(
                f"Expected ≥{assertions.expected_allocation_count} allocations, got {len(final_plan)}"
            )

    # Deadlock
    if assertions.expected_deadlock is not None:
        if deadlock != assertions.expected_deadlock:
            failures.append(
                f"Expected deadlock={assertions.expected_deadlock}, got {deadlock}"
            )

    # HITL
    if assertions.expected_hitl_required is not None:
        if hitl_required != assertions.expected_hitl_required:
            failures.append(
                f"Expected hitl_required={assertions.expected_hitl_required}, got {hitl_required}"
            )

    # Status
    if assertions.expected_status is not None:
        if status != assertions.expected_status:
            failures.append(f"Expected status={assertions.expected_status!r}, got {status!r}")

    # Basic sanity: rounds must be non-empty (unless no proposals)
    if len(rounds) == 0:
        warnings.append("No negotiation rounds recorded — agents may have returned no proposals")

    return failures, warnings


# =============================================================================
# Runner
# =============================================================================


class SimulationRunner:
    """Drives MasterGraph runs from YAML scenario files and asserts outcomes.

    For CI use, agents are mocked to avoid needing LLM API keys.
    Pass ``use_real_agents=True`` to run with live PydanticAI agents.
    """

    def __init__(self, use_real_agents: bool = False) -> None:
        self.use_real_agents = use_real_agents

    async def run_file(self, path: str | Path) -> SimulationResult:
        """Run a single scenario file and return the result."""
        from axon.orchestrator.master_graph import MasterGraph

        path = Path(path)
        log.info("sim.start", scenario=str(path))
        start = datetime.now(UTC)

        try:
            planning_context, assertions = load_scenario(path)
        except Exception as exc:
            return SimulationResult(
                scenario_name=str(path.stem),
                scenario_path=str(path),
                passed=False,
                failures=[f"Failed to load scenario: {exc}"],
            )

        graph = MasterGraph()

        # Inject pre-built demands/supplies so node_fetch is bypassed
        # when connectors are not available.
        try:
            result = await self._run_graph(graph, planning_context)
        except Exception as exc:
            return SimulationResult(
                scenario_name=planning_context.get("_scenario_name", path.stem),
                scenario_path=str(path),
                passed=False,
                failures=[f"MasterGraph raised: {exc}"],
                duration_seconds=(datetime.now(UTC) - start).total_seconds(),
            )

        failures, warnings = check_assertions(result, assertions)
        passed = len(failures) == 0
        duration = (datetime.now(UTC) - start).total_seconds()

        log.info(
            "sim.complete",
            scenario=planning_context.get("_scenario_name"),
            passed=passed,
            failures=failures,
            duration=duration,
        )

        return SimulationResult(
            scenario_name=planning_context.get("_scenario_name", path.stem),
            scenario_path=str(path),
            passed=passed,
            failures=failures,
            warnings=warnings,
            plan_result=result,
            duration_seconds=duration,
        )

    async def _run_graph(self, graph: Any, planning_context: dict[str, Any]) -> dict[str, Any]:
        """Run the MasterGraph, patching agent calls if not using real agents."""
        if self.use_real_agents:
            return await graph.run(planning_context)

        # Mock agents and connectors for offline simulation
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4 as _uuid4

        demands = planning_context.get("demands", [])
        supplies = planning_context.get("supplies", [])

        # Build one proposal per agent type using whatever demands/supplies are in the scenario
        agent_ids = [
            "sales", "procurement", "finance", "production",
            "logistics", "warehouse", "qa", "qc", "maintenance", "pd",
        ]

        def _mock_proposal(agent_id: str) -> dict[str, Any]:
            from axon.core.schema import AgentProposal, ProposalStatus
            from decimal import Decimal as D

            allocations = []
            for d in demands[:3]:  # allocate up to 3 demands
                matching_supply = next(
                    (s for s in supplies if s["item"]["native_id"] == d["item"]["native_id"]),
                    supplies[0] if supplies else None,
                )
                if matching_supply is None:
                    continue
                from axon.core.schema import Allocation, Demand, Supply
                try:
                    alloc = Allocation(
                        demand=Demand.model_validate(d),
                        supply=Supply.model_validate(matching_supply),
                        allocated_quantity=D(d["quantity"]),
                        status="proposed",
                    )
                    allocations.append(alloc)
                except Exception:
                    pass

            p = AgentProposal(
                agent_id=agent_id,
                round_number=1,
                allocations=allocations,
                utility_score=0.70,
                justification=f"Simulation proposal from {agent_id}",
                status=ProposalStatus.PROPOSED,
            )
            return p.model_dump(mode="json")

        mock_proposals = {aid: _mock_proposal(aid) for aid in agent_ids}

        with (
            patch("axon.orchestrator.master_graph.node_fetch", new_callable=AsyncMock) as mf,
            patch("axon.orchestrator.master_graph.node_transform", new_callable=AsyncMock) as mt,
            patch("axon.orchestrator.master_graph.node_reason", new_callable=AsyncMock) as mr,
            patch("axon.orchestrator.master_graph._get_ledger", new_callable=AsyncMock) as ml,
        ):
            mf.return_value = {
                "raw_demands": [],
                "raw_supplies": [],
                "raw_policies": [],
                "degradation_level": "FULL",
            }
            mt.return_value = {"demands": demands, "supplies": supplies}
            mr.return_value = {"agent_proposals": mock_proposals}

            ledger_instance = MagicMock()
            ledger_instance.record_plan_from_state = AsyncMock(return_value=_uuid4())
            ledger_instance.record_outcome = AsyncMock()
            ml.return_value = ledger_instance

            return await graph.run(planning_context)

    async def run_directory(
        self,
        directory: str | Path,
        pattern: str = "*.yaml",
    ) -> list[SimulationResult]:
        """Run all YAML scenarios in a directory matching the pattern."""
        directory = Path(directory)
        files = sorted(directory.glob(pattern))
        if not files:
            log.warning("sim.no_scenarios", directory=str(directory), pattern=pattern)
            return []

        results = []
        for f in files:
            r = await self.run_file(f)
            results.append(r)
        return results
