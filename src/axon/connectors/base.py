"""Base MCP Connector — universal transport, circuit breaker, cache, retry for all ERP connectors.

Supports the EBS MCP Agent's 10-server architecture as well as SAP, Odoo, and
any other MCP-compliant server. Every connector subclass provides tool wrappers
and a SemanticTransformer.

Key features:
  - Dual transport: SSE (legacy) or Streamable HTTP (MCP 2024-11-05 spec)
  - Circuit breaker integrated into every _call_tool() invocation
  - Retry logic: single retry on transient failures, then degrade
  - Cache-aside: read-before-call, write-through on response
  - Auth: X-EBS-Session-Token for Oracle EBS, X-API-Key for RAG
  - Span instrumentation via Logfire for every MCP call
  - Error classification: MCP server errors → circuit breaker, data errors → log

Usage:
    from axon.connectors.base import BaseMCPConnector

    class EBSDemandConnector(BaseMCPConnector):
        server_name = "ebs_demand"
        ...
"""

from __future__ import annotations

from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared._httpx_utils import create_mcp_http_client

from axon.connectors.cache import mcp_cache_get, mcp_cache_set
from axon.connectors.circuit_breaker import BreakerState, CircuitBreaker
from axon.core.config import MCPServerConfig
from axon.core.telemetry import get_correlation_id, log_event, trace_mcp_call


class MCPConnectionError(Exception):
    """Raised when the MCP server is unreachable or the circuit breaker is open."""

    def __init__(self, server_name: str, reason: str):
        self.server_name = server_name
        self.reason = reason
        super().__init__(f"MCPConnectionError({server_name}): {reason}")


class MCPTransportError(Exception):
    """Raised on transport-level failures (connection refused, timeout)."""

    def __init__(self, server_name: str, tool_name: str, cause: str):
        self.server_name = server_name
        self.tool_name = tool_name
        super().__init__(f"MCPTransportError({server_name}/{tool_name}): {cause}")


class BaseMCPConnector:
    """Shared MCP client transport for all ERP connectors.

    Each ERP gets its own subclass with tool-specific wrappers.
    """

    server_name: str = "base"  # override in subclasses

    def __init__(self, config: MCPServerConfig):
        self._config = config
        self._session: ClientSession | None = None
        self._read: Any = None
        self._write: Any = None
        self._transport_ctx: Any = None  # SSE or Streamable HTTP context manager
        self._circuit_breaker = CircuitBreaker(
            server_name=self.server_name,
            failure_threshold=config.circuit_breaker_threshold,
            cooldown_seconds=config.circuit_breaker_cooldown,
        )

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def url(self) -> str:
        return str(self._config.url)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def transport(self) -> str:
        return self._config.transport

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    @property
    def circuit_state(self) -> BreakerState:
        return self._circuit_breaker.state

    # =========================================================================
    # Connection lifecycle
    # =========================================================================

    async def __aenter__(self) -> BaseMCPConnector:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish MCP connection using configured transport."""
        if self._session is not None:
            return

        log_event("info", "mcp_connecting", server_name=self.server_name, transport=self.transport)

        headers = self._build_headers()

        if self.transport == "streamable_http":
            self._transport_ctx = streamablehttp_client(
                url=self.url,
                headers=headers,
                timeout=self._config.timeout_seconds,
                httpx_client_factory=create_mcp_http_client,
            )
            read_stream, write_stream, _get_session_id = await self._transport_ctx.__aenter__()
        else:
            self._transport_ctx = sse_client(
                url=self.url,
                headers=headers,
                timeout=self._config.timeout_seconds,
                httpx_client_factory=create_mcp_http_client,
            )
            read_stream, write_stream = await self._transport_ctx.__aenter__()

        self._session = ClientSession(read_stream, write_stream)
        await self._session.initialize()
        self._read = read_stream
        self._write = write_stream

        log_event("info", "mcp_connected", server_name=self.server_name, transport=self.transport)

    async def disconnect(self) -> None:
        """Close the MCP connection."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
            self._read = None
            self._write = None
        if self._transport_ctx:
            await self._transport_ctx.__aexit__(None, None, None)
            self._transport_ctx = None

    async def reconnect(self) -> None:
        """Reconnect after transport failure (e.g., circuit breaker HALF_OPEN probe)."""
        await self.disconnect()
        await self.connect()

    # =========================================================================
    # Health check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """Ping the MCP server's health endpoint.

        Returns:
            {"status": "HEALTHY", "tools": N} or raises on failure.
        """
        base_url = str(self._config.url).replace("/mcp/", "/").replace("/mcp", "/")
        path = self._config.health_path.lstrip("/")
        health_url = f"{base_url}{path}"
        headers = self._build_headers()
        async with httpx.AsyncClient(timeout=httpx.Timeout(10), headers=headers) as client:
            resp = await client.get(health_url)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    # =========================================================================
    # Tool discovery
    # =========================================================================

    async def discover_tools(self) -> list[dict[str, Any]]:
        """List all tools exposed by this MCP server.

        Returns list of {"name": str, "description": str, "inputSchema": dict}.
        """
        assert self._session is not None, f"{self.server_name}: not connected"
        tools_result = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
            }
            for t in tools_result.tools
        ]

    # =========================================================================
    # Internal: call_tool with circuit breaker, cache, and retry
    # =========================================================================

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        use_cache: bool = True,
    ) -> Any:
        """Call an MCP tool with full resilience stack.

        Flow:
          1. Check circuit breaker — reject if OPEN
          2. Check cache (READ tools only) — return if hit
          3. Execute call with span instrumentation
          4. On failure: retry once, then record failure in circuit breaker
          5. On success: record success, write to cache, return

        Args:
            tool_name: MCP tool to call (e.g. "get_inventory_levels")
            arguments: Tool arguments dict
            use_cache: Whether to check/store the response cache

        Returns:
            Parsed tool response (dict, list, str, or empty dict)

        Raises:
            MCPConnectionError: circuit breaker is OPEN
            MCPTransportError: transport failure after retries exhausted
        """
        assert self._session is not None, f"{self.server_name}: not connected"

        correlation_id = str(get_correlation_id())

        # Step 1 — Circuit breaker guard
        if not self._circuit_breaker.allow_call():
            raise MCPConnectionError(
                self.server_name,
                f"Circuit breaker OPEN — {self._circuit_breaker.state.value}",
            )

        # Step 2 — Cache lookup (READ tools only, write tools have TTL=0)
        if use_cache:
            cached = await mcp_cache_get(self.server_name, tool_name, arguments)
            if cached is not None:
                return cached

        # Step 3 — Execute with retry
        last_error: Exception | None = None
        max_attempts = 1 + self._config.retry_count  # 1 primary + N retries

        for attempt in range(max_attempts):
            try:
                result = await self._execute_single_call(tool_name, arguments, correlation_id)

                # Success — record in circuit breaker and cache
                self._circuit_breaker.record_success()
                if use_cache:
                    await mcp_cache_set(self.server_name, tool_name, arguments, result)
                return result

            except MCPConnectionError:
                raise  # Don't retry on circuit breaker OPEN

            except Exception as exc:
                last_error = exc
                log_event(
                    "warn",
                    "mcp_call_attempt_failed",
                    server_name=self.server_name,
                    tool_name=tool_name,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error=str(exc),
                )

                if attempt < max_attempts - 1:
                    # Retry: reconnect and try again
                    with __import__("contextlib", fromlist=["suppress"]).suppress(Exception):
                        await self.reconnect()
                    continue

        # All attempts exhausted — record failure and raise
        self._circuit_breaker.record_failure()

        raise MCPTransportError(
            self.server_name,
            tool_name,
            f"All {max_attempts} attempt(s) failed: {last_error}",
        ) from last_error

    async def _execute_single_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        correlation_id: str,
    ) -> Any:
        """Execute a single MCP tool call with span instrumentation.

        Handles response parsing: JSON text → dict/list, or raw text,
        or content block data.
        """
        with trace_mcp_call(self.server_name, tool_name) as span:
            span.set_attribute("correlation_id", correlation_id)

            result = await self._session.call_tool(tool_name, arguments)  # type: ignore[union-attr]

            if result.content and len(result.content) > 0:
                first = result.content[0]
                if hasattr(first, "text"):
                    import json

                    try:
                        parsed = json.loads(first.text)
                        span.set_attribute("result_type", type(parsed).__name__)
                        return parsed
                    except json.JSONDecodeError:
                        span.set_attribute("result_type", "raw_text")
                        return first.text
                span.set_attribute("result_type", type(first).__name__)
                return first

            span.set_attribute("result", "empty")
            return {}

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for the MCP connection."""
        headers: dict[str, str] = {}

        # API key (e.g., for external RAG)
        if self._config.api_key:
            headers["X-API-Key"] = self._config.api_key.get_secret_value()

        # Session token (e.g., X-EBS-Session-Token for Oracle EBS)
        if self._config.auth_token:
            headers["X-EBS-Session-Token"] = self._config.auth_token.get_secret_value()

        # Correlation ID for full-trace auditability
        with __import__("contextlib", fromlist=["suppress"]).suppress(Exception):
            headers["X-Correlation-ID"] = str(get_correlation_id())

        return headers
