"""EBSAuthConnector — MCP client for the EBS authentication server (port 8101).

Provides session management and credential verification for Oracle EBS MCP connections.

Usage:
    from axon.connectors.mcp_oracle_ebs.ebs_auth_connector import EBSAuthConnector

    async with EBSAuthConnector(settings.mcp_ebs_auth) as auth:
        token = await auth.authenticate()
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class EBSAuthConnector(BaseMCPConnector):
    """MCP client for ebs-auth server (port 8101)."""

    server_name = "ebs_auth"

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate and return a session token."""
        return await self._call_tool("authenticate", {})

    async def validate_session(self, token: str) -> dict[str, Any]:
        """Validate an existing session token."""
        return await self._call_tool("validate_session", {"token": token})

    async def refresh_token(self, token: str) -> dict[str, Any]:
        """Refresh an expiring session token."""
        return await self._call_tool("refresh_token", {"token": token})

    async def get_permissions(self) -> list[dict[str, Any]]:
        """Return RBAC permissions for the current session."""
        result = await self._call_tool("get_permissions", {})
        return result if isinstance(result, list) else [result]
