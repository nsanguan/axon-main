"""axon-sim CLI entry point.

Usage::

    axon-sim run path/to/scenario.yaml
    axon-sim run tests/scenarios/ --pattern "*.yaml"
    axon-sim run tests/scenarios/ --live    # use real LLM agents
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _print_result(result: SimulationResult) -> None:  # noqa: F821
    ok = "✓" if result.passed else "✗"
    print(f"  {ok} {result.scenario_name} [{result.duration_seconds:.2f}s]")
    for f in result.failures:
        print(f"      FAIL: {f}")
    for w in result.warnings:
        print(f"      WARN: {w}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="axon-sim",
        description="Axon simulation runner — drive planning scenarios without real MCP servers.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run one or more scenario files")
    run_cmd.add_argument("path", help="Path to a .yaml scenario file or a directory")
    run_cmd.add_argument(
        "--pattern",
        default="*.yaml",
        help="Glob pattern for scenario files (default: *.yaml)",
    )
    run_cmd.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Use real PydanticAI agents (requires LLM API key)",
    )

    args = parser.parse_args()

    if args.command == "run":
        _run(Path(args.path), pattern=args.pattern, live=args.live)


def _run(path: Path, pattern: str, live: bool) -> None:
    from axon.sim.runner import SimulationRunner

    runner = SimulationRunner(use_real_agents=live)

    async def _main() -> list:
        if path.is_dir():
            return await runner.run_directory(path, pattern=pattern)
        else:
            return [await runner.run_file(path)]

    results = asyncio.run(_main())

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print(f"\nAxon Simulation Results — {len(results)} scenario(s)")
    print("=" * 50)
    for r in results:
        _print_result(r)
    print("=" * 50)
    print(f"Passed: {passed}  Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
