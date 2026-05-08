"""Base MCP Connector — shared transport and tool-calling logic for all ERP connectors.

Subclassed by OracleEBS, SAP, Odoo connectors. Each subclass provides
tool wrappers and a SemanticTransformer. The base handles:
  - MCP SSE transport lifecycle (connect / disconnect)
  - Tool discovery (list_tools)
  - Span instrumentation for all MCP calls
  - Retry logic via tenacity (pluggable into circuit breaker)

Usage:
    from axon.connectors.base import BaseMCPConnector

    class OracleEBSConnector(BaseMCPConnector):
        server_name = "oracle_ebs"
        ...
"""

from __future__ import annotations

from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

from axon.core.config import MCPServerConfig
from axon.core.telemetry import log_event, trace_mcp_call


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
        self._http_client: httpx.AsyncClient | None = None

    @property
    def url(self) -> str:
        return str(self._config.url)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    # =========================================================================
    # Connection lifecycle
    # =========================================================================

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish MCP SSE connection."""
        if self._session is not None:
            return

        log_event("info", "mcp_connecting", server_name=self.server_name)

        headers: dict[str, str] = {}
        if self._config.api_key:
            headers["X-API-Key"] = self._config.api_key.get_secret_value()

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
            headers=headers,
        )

        self._read, self._write = await sse_client(
            url=self.url,
            httpx_client=self._http_client,
        ).__aenter__()

        self._session = ClientSession(self._read, self._write)
        await self._session.initialize()

        log_event("info", "mcp_connected", server_name=self.server_name)

    async def disconnect(self) -> None:
        """Close the MCP connection."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
            self._read = None
            self._write = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

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
    # Internal: call_tool with span
    # =========================================================================

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return parsed result with span instrumentation."""
        assert self._session is not None, f"{self.server_name}: not connected"

        with trace_mcp_call(self.server_name, tool_name) as span:
            try:
                result = await self._session.call_tool(tool_name, arguments)
                if result.content and len(result.content) > 0:
                    first = result.content[0]
                    if hasattr(first, "text"):
                        import json

                        try:
                            parsed = json.loads(first.text)
                            return parsed
                        except json.JSONDecodeError:
                            return first.text
                    return first
                span.set_attribute("result", "empty")
                return {}
            except Exception as exc:
                span.record_exception(exc)
                log_event(
                    "error",
                    "mcp_call_failed",
                    server_name=self.server_name,
                    tool_name=tool_name,
                    error=str(exc),
                )
                raise
