"""Axon simulation framework.

Run planning scenarios from YAML files without real MCP servers or LLM keys.

Usage::

    axon-sim run tests/scenarios/basic_plan.yaml
    axon-sim run tests/scenarios/
"""

from __future__ import annotations

from axon.sim.runner import SimulationResult, SimulationRunner, load_scenario

__all__ = ["SimulationRunner", "SimulationResult", "load_scenario"]
