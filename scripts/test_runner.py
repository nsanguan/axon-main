#!/usr/bin/env python3
"""Axon Scenario Test Runner — loads Markdown scenarios and runs them.

Usage:
    # Run all scenarios
    python scripts/test_runner.py

    # Run a specific scenario
    python scripts/test_runner.py tests/scenarios/delay_shipment_po.md

    # List available scenarios
    python scripts/test_runner.py --list
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

# Ensure axon package is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def list_scenarios(scenarios_dir: str) -> list[str]:
    """List all .md scenario files in the directory."""
    pattern = os.path.join(scenarios_dir, "*.md")
    return sorted(glob.glob(pattern))


def load_scenario(path: str) -> dict:
    """Parse a Markdown scenario file into structured fields.

    Returns dict with: title, type, severity, given, setup_mcp, trigger, steps.
    """
    with open(path) as f:
        content = f.read()

    lines = content.split("\n")
    title = ""
    scenario_type = ""
    severity = ""
    given = ""
    trigger = ""

    state = "header"
    for line in lines:
        if line.startswith("# Scenario:"):
            title = line.replace("# Scenario:", "").strip()
        elif line.startswith("## File:"):
            pass  # filename — skip for content
        elif line.startswith("## Type:"):
            scenario_type = line.replace("## Type:", "").strip()
        elif line.startswith("## Severity:"):
            severity = line.replace("## Severity:", "").strip()
        elif line.strip() == "### Given (Context)":
            state = "given"
        elif line.strip() == "### When (Trigger)":
            state = "trigger"
        elif line.strip().startswith("### Then"):
            state = "then"
        elif state == "given" and line.strip() and not line.startswith("###"):
            given += line + "\n"
        elif state == "trigger" and line.strip() and not line.startswith("###"):
            trigger += line + "\n"

    return {
        "title": title,
        "type": scenario_type,
        "severity": severity,
        "given": given.strip(),
        "trigger": trigger.strip(),
        "content": content,
        "path": path,
    }


def run_scenario(scenario: dict, dry_run: bool = False) -> dict:
    """Execute a single scenario against the orchestrator.

    In dry_run mode, only prints the parsed scenario. In live mode,
    it would invoke the LangGraph MasterGraph with the scenario context.
    """
    print(f"\n{'='*70}")
    print(f"  RUNNING: {scenario['title']}")
    print(f"  Type: {scenario['type']}  |  Severity: {scenario['severity']}")
    print(f"  File: {scenario['path']}")
    print(f"{'='*70}")
    print()
    print("  Given:")
    for line in scenario["given"].split("\n"):
        print(f"    {line}")
    print()
    print(f"  Trigger: {scenario['trigger'][:80]}...")
    print()

    if dry_run:
        print("  [DRY RUN] — no orchestrator invoked")
        result = {"status": "dry_run", "scenario": scenario["title"]}
    else:
        # TODO: Wire this to the actual LangGraph MasterGraph
        # from axon.orchestrator.master_graph import MasterGraph
        # graph = MasterGraph()
        # result = await graph.run(planning_context)
        print("  ⚠ Orchestrator invocation not yet wired.")
        print("  To enable: import MasterGraph and call graph.run(context)")
        result = {"status": "simulated", "scenario": scenario["title"]}

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Axon Scenario Test Runner",
    )
    parser.add_argument("path", nargs="?", help="Path to a single .md scenario file")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display scenarios without invoking the orchestrator",
    )
    parser.add_argument(
        "--scenarios-dir",
        default="tests/scenarios",
        help="Directory containing .md scenario files (default: tests/scenarios)",
    )

    args = parser.parse_args()

    if args.list:
        print("Available scenarios:")
        for path in list_scenarios(args.scenarios_dir):
            scenario = load_scenario(path)
            print(f"  [{scenario['severity']}] {scenario['title']}")
            print(f"       {scenario['type']}  —  {path}")
        return

    paths = [args.path] if args.path else list_scenarios(args.scenarios_dir)

    if not paths:
        print(f"No scenario files found in '{args.scenarios_dir}/'")
        print("Create .md files there, or specify a path with --scenarios-dir")
        sys.exit(1)

    print(f"Found {len(paths)} scenario(s)")
    results = []

    for path in paths:
        scenario = load_scenario(path)
        result = run_scenario(scenario, dry_run=args.dry_run)
        results.append(result)

    print(f"\n{'='*70}")
    print(f"  COMPLETE: {len(results)} scenario(s) executed")
    for r in results:
        print(f"  [{r['status']}] {r['scenario']}")


if __name__ == "__main__":
    main()
