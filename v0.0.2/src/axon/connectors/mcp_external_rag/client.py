"""MCP client for mcp-policy-server (External RAG).

Connects to mcp-policy-server (port 8021) to retrieve SOPs, policies,
and compliance checks. This is an MCP client only — the server is a
separate project. Axon never touches the RAG database directly.

Usage:
    from axon.connectors.mcp_external_rag.client import PolicyServerClient

    async with PolicyServerClient(settings.mcp_external_rag) as client:
        sop = await client.get_sop("manufacturing.bolts")
        result = await client.check_compliance(plan_data)
"""

from __future__ import annotations

from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

from axon.core.config import MCPServerConfig
from axon.core.telemetry import get_correlation_id, log_event, trace_mcp_call


class PolicyServerClient:
    """MCP client for the mcp-policy-server.

    Wraps the MCP SSE transport and exposes the RAG tools as typed methods.
    """

    def __init__(self, config: MCPServerConfig):
        self._config = config
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._http_client: httpx.AsyncClient | None = None

    @property
    def server_url(self) -> str:
        return str(self._config.url)

    async def __aenter__(self) -> PolicyServerClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish MCP SSE connection to the policy server."""
        if self._session is not None:
            return

        log_event("info", "policy_server_connecting", server_name="external_rag")

        headers: dict[str, str] = {}
        if self._config.api_key:
            headers["X-API-Key"] = self._config.api_key.get_secret_value()

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
            headers=headers,
        )

        # SSE transport for MCP
        self._read, self._write = await sse_client(
            url=self.server_url,
            httpx_client=self._http_client,
        ).__aenter__()

        self._session = ClientSession(self._read, self._write)
        await self._session.initialize()

        log_event("info", "policy_server_connected", server_name="external_rag")

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
    # Tool wrappers
    # =========================================================================

    async def get_sop(self, process_code: str) -> dict[str, Any]:
        """Retrieve a Standard Operating Procedure for a process code.

        Args:
            process_code: e.g. "manufacturing.bolts", "quality.inspection"

        Returns:
            {"process_code": str, "title": str, "content": str, "version": str}
        """
        get_correlation_id()
        with trace_mcp_call("external_rag", "get_sop") as span:
            span.set_attribute("process_code", process_code)
            result = await self._call_tool("get_sop", {"process_code": process_code})
            span.set_attribute("found", bool(result))
            return result

    async def check_compliance(self, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Verify a plan or change against regulatory constraints and SOPs.

        Args:
            plan_data: Plan context with items, quantities, timelines

        Returns:
            {"compliant": bool, "violations": list[dict], "recommendations": list[str]}
        """
        with trace_mcp_call("external_rag", "check_compliance") as span:
            result = await self._call_tool("check_compliance", {"plan": plan_data})
            span.set_attribute("compliant", result.get("compliant", False))
            span.set_attribute("violation_count", len(result.get("violations", [])))
            return result

    async def get_audit_history(
        self, process_code: str | None = None, item_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return recent audit findings relevant to a process or item."""
        args: dict[str, str] = {}
        if process_code:
            args["process_code"] = process_code
        if item_id:
            args["item_id"] = item_id
        with trace_mcp_call("external_rag", "get_audit_history") as span:
            result = await self._call_tool("get_audit_history", args)
            span.set_attribute("finding_count", len(result) if isinstance(result, list) else 0)
            return result if isinstance(result, list) else []

    async def get_regulatory_requirements(self, product_category: str) -> dict[str, Any]:
        """Return applicable regulations (FDA, ISO, GMP) for a product category."""
        with trace_mcp_call("external_rag", "get_regulatory_requirements") as span:
            span.set_attribute("category", product_category)
            result = await self._call_tool(
                "get_regulatory_requirements",
                {"product_category": product_category},
            )
            return result

    async def list_tools(self) -> list[dict[str, Any]]:
        """List all tools exposed by the policy server."""
        assert self._session is not None, "Not connected"
        tools_result = await self._session.list_tools()
        return [{"name": t.name, "description": t.description} for t in tools_result.tools]

    # =========================================================================
    # Internal
    # =========================================================================

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return parsed result."""
        assert self._session is not None, "Not connected"

        try:
            result = await self._session.call_tool(name, arguments)
            # MCP returns content blocks; extract text or data
            if result.content and len(result.content) > 0:
                first = result.content[0]
                if hasattr(first, "text"):
                    import json as _json

                    try:
                        return _json.loads(first.text)
                    except _json.JSONDecodeError:
                        return first.text
                return first
            return {}
        except Exception as exc:
            log_event(
                "error",
                "mcp_call_failed",
                server_name="external_rag",
                tool_name=name,
                error=str(exc),
            )
            raise
