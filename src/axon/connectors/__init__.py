"""Axon Connectors — universal MCP client layer.

All MCP servers are separate projects; connectors are client adapters only.
The connector registry provides dynamic loading of any MCP-compliant server.

Key exports:
  - BaseMCPConnector: shared transport with circuit breaker, cache, retry
  - ConnectorRegistry / ConnectorFactory: dynamic connector management
  - CircuitBreaker / DegradationMonitor: per-server resilience
  - register_connector_class: plug in new ERP connector types
"""

from axon.connectors.base import BaseMCPConnector, MCPConnectionError, MCPTransportError
from axon.connectors.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    DegradationLevel,
    DegradationMonitor,
)
from axon.connectors.registry import (
    ConnectorFactory,
    ConnectorRegistry,
    get_connector_class,
    register_connector_class,
)

__all__ = [
    "BaseMCPConnector",
    "MCPConnectionError",
    "MCPTransportError",
    "BreakerState",
    "CircuitBreaker",
    "DegradationLevel",
    "DegradationMonitor",
    "ConnectorFactory",
    "ConnectorRegistry",
    "register_connector_class",
    "get_connector_class",
]
