"""Odoo MCP Connector — MCP client and tool wrappers."""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class OdooConnector(BaseMCPConnector):
    """MCP client for Odoo."""

    server_name = "odoo"

    async def get_inventory_levels(self, item_id: str | None = None) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        result = await self._call_tool("get_inventory_levels", args)
        return result if isinstance(result, list) else [result]

    async def get_sales_orders(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_sales_orders", {})
        return result if isinstance(result, list) else [result]

    async def get_purchase_orders(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_purchase_orders", {})
        return result if isinstance(result, list) else [result]

    async def get_suppliers(self, item_id: str) -> list[dict[str, Any]]:
        result = await self._call_tool("get_suppliers", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def list_wip_jobs(self) -> list[dict[str, Any]]:
        result = await self._call_tool("list_wip_jobs", {})
        return result if isinstance(result, list) else [result]
