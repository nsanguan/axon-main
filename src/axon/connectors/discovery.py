"""MCP Tool Discovery Service — scans MCP servers and registers tools.

Runs at startup to discover which tools each MCP server exposes,
then registers them in the shared tool registry for agent assignment.

Usage:
    from axon.connectors.discovery import discover_all_tools

    tools = await discover_all_tools(connectors, registry)
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from axon.connectors.base import BaseMCPConnector
from axon.core.telemetry import log_event


@dataclass
class ToolDiscoveryResult:
    """Result of scanning one MCP server for tools."""

    server_name: str
    tools_found: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    connected: bool = False

    @property
    def tool_count(self) -> int:
        return len(self.tools_found)


@dataclass
class DiscoveryReport:
    """Aggregate result from scanning all MCP servers."""

    server_results: dict[str, ToolDiscoveryResult] = field(default_factory=dict)
    total_tools: int = 0
    total_servers: int = 0
    healthy_servers: int = 0

    def to_summary(self) -> dict[str, Any]:
        return {
            "total_tools": self.total_tools,
            "total_servers": self.total_servers,
            "healthy_servers": self.healthy_servers,
            "servers": {
                name: {
                    "tools": r.tool_count,
                    "connected": r.connected,
                    "errors": r.errors,
                }
                for name, r in self.server_results.items()
            },
        }


async def discover_server_tools(
    connector: BaseMCPConnector,
) -> ToolDiscoveryResult:
    """Connect to one MCP server and discover its tools.

    Returns a result even if connection fails — errors are collected,
    not raised. This allows partial discovery when some servers are down.
    """
    result = ToolDiscoveryResult(server_name=connector.server_name)

    if not connector.enabled:
        result.errors.append("Server disabled in config")
        return result

    try:
        await connector.connect()
        result.connected = True
        result.tools_found = await connector.discover_tools()
        log_event(
            "info",
            "tool_discovery_complete",
            server_name=connector.server_name,
            tool_count=len(result.tools_found),
        )
    except Exception as exc:
        result.errors.append(str(exc))
        log_event(
            "warn",
            "tool_discovery_failed",
            server_name=connector.server_name,
            error=str(exc),
        )
    finally:
        with contextlib.suppress(Exception):
            await connector.disconnect()

    return result


async def discover_all_tools(
    connectors: list[BaseMCPConnector],
) -> DiscoveryReport:
    """Scan all MCP servers and return a consolidated report.

    Each server is scanned independently — failure in one does not
    block discovery of others.
    """
    report = DiscoveryReport()
    report.total_servers = len(connectors)

    # Discover in parallel for speed
    import asyncio

    tasks = [discover_server_tools(c) for c in connectors]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for connector, result in zip(connectors, results, strict=False):
        if isinstance(result, Exception):
            result = ToolDiscoveryResult(
                server_name=connector.server_name,
                errors=[str(result)],
            )
        report.server_results[connector.server_name] = result
        if result.connected:
            report.healthy_servers += 1
        report.total_tools += len(result.tools_found)

    log_event(
        "info",
        "discovery_complete",
        healthy=report.healthy_servers,
        total_servers=report.total_servers,
        total_tools=report.total_tools,
    )
    return report
