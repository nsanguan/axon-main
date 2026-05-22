"""Connector Registry — dynamic MCP connector management and tool catalog sync.

Provides:
  - ConnectorRegistry: maps server_name → connector instance, with lookup
  - ConnectorFactory: creates connectors from MCPServerConfig entries
  - Dynamic tool catalog sync: merges discovered tools into TOOL_CATALOG
  - Health aggregation: monitors all connectors at once

Design:
  The registry is the single source of truth for which connectors are active.
  It replaces ad-hoc connector instantiation in the orchestrator with a
  structured lookup. Tool discovery results are merged into the static
  TOOL_CATALOG at startup so agents always have an up-to-date view.

Usage:
    from axon.connectors.registry import ConnectorRegistry, ConnectorFactory

    registry = ConnectorRegistry()
    factory = ConnectorFactory(settings)
    await factory.load_all(registry)
    await registry.discover_all_tools()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from axon.connectors.base import BaseMCPConnector
from axon.connectors.discovery import ToolDiscoveryResult, discover_server_tools
from axon.core.config import MCPServerConfig
from axon.core.telemetry import log_event

# Connector class registry — maps config key to connector class
# Extended by subpackages (oracle_ebs, sap, odoo) via register_connector_class()
_CONNECTOR_CLASSES: dict[str, type[BaseMCPConnector]] = {}


def register_connector_class(name: str, cls: type[BaseMCPConnector]) -> None:
    """Register a connector class for a given server config key."""
    _CONNECTOR_CLASSES[name] = cls


def get_connector_class(name: str) -> type[BaseMCPConnector] | None:
    """Look up a connector class by server config key."""
    return _CONNECTOR_CLASSES.get(name)


# =============================================================================
# Connector Registry
# =============================================================================


@dataclass
class ConnectorRegistry:
    """Central registry of all active MCP connectors.

    Provides lookup by server_name, by agent requirements, and bulk operations
    (connect all, disconnect all, health check all).
    """

    connectors: dict[str, BaseMCPConnector] = field(default_factory=dict)

    def register(self, connector: BaseMCPConnector) -> None:
        """Register a connector in the registry."""
        self.connectors[connector.server_name] = connector

    def get(self, server_name: str) -> BaseMCPConnector | None:
        """Get a connector by server name."""
        return self.connectors.get(server_name)

    def get_all(self) -> list[BaseMCPConnector]:
        """Return all registered connectors."""
        return list(self.connectors.values())

    def get_enabled(self) -> list[BaseMCPConnector]:
        """Return all enabled connectors."""
        return [c for c in self.connectors.values() if c.enabled]

    def get_by_server_names(self, server_names: list[str]) -> list[BaseMCPConnector]:
        """Return connectors matching the given server names, skipping missing."""
        return [c for name in server_names if (c := self.connectors.get(name)) is not None]

    def server_names(self) -> list[str]:
        """Return all registered server names."""
        return list(self.connectors.keys())

    async def connect_all(self) -> dict[str, bool]:
        """Connect all enabled connectors in parallel.

        Returns mapping: server_name → connected (bool).
        """
        import asyncio

        results: dict[str, bool] = {}

        async def _connect_one(connector: BaseMCPConnector) -> tuple[str, bool]:
            try:
                await connector.connect()
                return (connector.server_name, True)
            except Exception as exc:
                log_event(
                    "warn",
                    "registry_connect_failed",
                    server_name=connector.server_name,
                    error=str(exc),
                )
                return (connector.server_name, False)

        tasks = [_connect_one(c) for c in self.get_enabled()]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                log_event("error", "registry_connect_error", error=str(outcome))
            else:
                name, ok = outcome
                results[name] = ok

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        import asyncio

        async def _disconnect_one(connector: BaseMCPConnector) -> None:
            with __import__("contextlib", fromlist=["suppress"]).suppress(Exception):
                await connector.disconnect()

        await asyncio.gather(*[_disconnect_one(c) for c in self.connectors.values()])

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Run health checks against all connected servers.

        Returns: {server_name: health_response_or_error}.
        """
        import asyncio

        results: dict[str, dict[str, Any]] = {}

        async def _health_one(connector: BaseMCPConnector) -> tuple[str, dict[str, Any]]:
            try:
                health = await connector.health_check()
                return (connector.server_name, health)
            except Exception as exc:
                return (connector.server_name, {"status": "UNREACHABLE", "error": str(exc)})

        tasks = [_health_one(c) for c in self.get_enabled()]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                log_event("error", "health_check_error", error=str(outcome))
            else:
                name, data = outcome
                results[name] = data

        return results

    async def discover_all_tools(self) -> dict[str, ToolDiscoveryResult]:
        """Discover tools from all enabled connectors.

        Returns: {server_name: ToolDiscoveryResult}.
        """
        import asyncio

        results: dict[str, ToolDiscoveryResult] = {}

        async def _discover_one(connector: BaseMCPConnector) -> ToolDiscoveryResult:
            return await discover_server_tools(connector)

        connectors = self.get_enabled()
        tasks = [_discover_one(c) for c in connectors]
        discoveries = await asyncio.gather(*tasks, return_exceptions=True)

        for connector, raw_result in zip(connectors, discoveries, strict=False):
            if isinstance(raw_result, BaseException):
                result: ToolDiscoveryResult = ToolDiscoveryResult(
                    server_name=connector.server_name,
                    errors=[str(raw_result)],
                )
            else:
                result = raw_result
            results[connector.server_name] = result

        return results

    # =========================================================================
    # Tool catalog sync
    # =========================================================================

    async def sync_tool_catalog(
        self,
        merge_into_catalog: bool = True,
    ) -> list[dict[str, Any]]:
        """Discover tools and optionally merge into the static TOOL_CATALOG.

        Returns list of discovered tool specs not already in the catalog.
        """
        from axon.agents.tools import TOOL_CATALOG, ToolSpec

        existing_names = {t.name for t in TOOL_CATALOG}
        new_tools: list[dict[str, Any]] = []

        discovery_results = await self.discover_all_tools()

        for server_name, result in discovery_results.items():
            if not result.connected:
                continue

            for tool in result.tools_found:
                tool_name = tool["name"]
                if tool_name in existing_names:
                    continue

                new_tools.append({
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "server": server_name,
                    "input_schema": tool.get("input_schema", {}),
                })

                if merge_into_catalog:
                    TOOL_CATALOG.append(
                        ToolSpec(
                            name=tool_name,
                            description=tool.get("description", ""),
                            server=server_name,
                            direction="READ",  # Conservative default
                            agent_ids=[],  # Caller assigns agents later
                        )
                    )
                    existing_names.add(tool_name)

        if new_tools:
            log_event(
                "info",
                "tool_catalog_synced",
                new_tools=len(new_tools),
                total_tools=len(TOOL_CATALOG),
            )

        return new_tools


# =============================================================================
# Connector Factory
# =============================================================================


class ConnectorFactory:
    """Creates connector instances from typed configuration.

    Supports the universal MCP-ERP design: config keys map to connector classes
    via the _CONNECTOR_CLASSES registry. New ERPs register their connector class
    once, and the factory creates instances from config automatically.
    """

    def __init__(self, settings: Any) -> None:
        """Initialize with the root Settings object.

        Args:
            settings: axon.core.config.Settings instance.
        """
        self._settings = settings
        self._config_map = self._build_config_map()

    def _build_config_map(self) -> dict[str, MCPServerConfig]:
        """Scan settings for all MCPServerConfig fields."""
        config_map: dict[str, MCPServerConfig] = {}
        for attr_name in dir(self._settings):
            if not attr_name.startswith("mcp_"):
                continue
            value = getattr(self._settings, attr_name)
            if isinstance(value, MCPServerConfig):
                # config key: "mcp_oracle_ebs" → "oracle_ebs"
                server_name = attr_name.removeprefix("mcp_")
                config_map[server_name] = value
        return config_map

    def get_config(self, server_name: str) -> MCPServerConfig | None:
        """Get the MCPServerConfig for a server name."""
        return self._config_map.get(server_name)

    def list_configured_servers(self) -> list[str]:
        """Return all configured server names."""
        return list(self._config_map.keys())

    def create_connector(self, server_name: str) -> BaseMCPConnector | None:
        """Create a connector instance for the given server.

        Uses the connector class registry for known ERPs; falls back to
        a generic BaseMCPConnector for unknown servers.
        """
        config = self._config_map.get(server_name)
        if config is None:
            log_event("warn", "connector_no_config", server_name=server_name)
            return None

        if not config.enabled:
            return None

        connector_cls = get_connector_class(server_name)
        if connector_cls is not None:
            return connector_cls(config)

        # Generic fallback for unknown MCP servers
        log_event("info", "connector_generic_fallback", server_name=server_name)
        return _GenericConnector(server_name, config)

    async def load_all(self, registry: ConnectorRegistry) -> ConnectorRegistry:
        """Create and register connectors for all configured servers.

        Args:
            registry: Target ConnectorRegistry to populate.

        Returns:
            The populated registry (same instance).
        """
        for server_name in self._config_map:
            connector = self.create_connector(server_name)
            if connector is not None:
                registry.register(connector)

        log_event(
            "info",
            "connector_factory_loaded",
            registered=len(registry.connectors),
            configured=len(self._config_map),
        )

        return registry


class _GenericConnector(BaseMCPConnector):
    """Fallback connector for MCP servers without a specialized class."""

    def __init__(self, server_name: str, config: MCPServerConfig):
        self.server_name = server_name
        super().__init__(config)
