"""Orchestrator main entrypoint — runs the LangGraph planning cycle.

Usage:
    python -m axon.orchestrator.main
"""

from __future__ import annotations

import asyncio

from axon.core.config import settings
from axon.core.telemetry import init_telemetry, log_event
from axon.orchestrator.master_graph import MasterGraph


async def main():
    init_telemetry(settings)
    log_event("info", "orchestrator_starting")

    graph = MasterGraph()
    graph.compile()

    # Health check endpoint placeholder — FastMCP or HTTP server
    # For now, run one planning cycle with empty data as smoke test
    log_event("info", "orchestrator_ready")

    # Keep alive until signal
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass
    finally:
        await graph.close()
        log_event("info", "orchestrator_stopped")


if __name__ == "__main__":
    asyncio.run(main())
