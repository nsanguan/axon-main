"""SAP MCP Connector — MCP client and tool wrappers.

Connects to mcp-sap (separate project). Follows the same pattern as
EBSSupplyConnector with SAP-specific tool names and SemanticTransformer.

Usage:
    from axon.connectors.mcp_sap.connector import SAPConnector

    async with SAPConnector(settings.mcp_sap) as sap:
        inventory = await sap.get_inventory_levels()
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class SAPConnector(BaseMCPConnector):
    """MCP client for SAP S/4HANA."""

    server_name = "sap"

    async def get_inventory_levels(self, item_id: str | None = None) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        result = await self._call_tool("get_inventory_levels", args)
        return result if isinstance(result, list) else [result]

    async def get_sales_orders(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_sales_orders", {})
        return result if isinstance(result, list) else [result]

    async def get_demand_forecast(self, item_id: str) -> list[dict[str, Any]]:
        result = await self._call_tool("get_demand_forecast", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def list_wip_jobs(self) -> list[dict[str, Any]]:
        result = await self._call_tool("list_wip_jobs", {})
        return result if isinstance(result, list) else [result]

    async def get_bom(self, item_id: str) -> dict[str, Any]:
        return await self._call_tool("get_bom", {"item_id": item_id})

    async def get_work_center_capacity(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_work_center_capacity", {})
        return result if isinstance(result, list) else [result]

    async def get_suppliers(self, item_id: str) -> list[dict[str, Any]]:
        result = await self._call_tool("get_suppliers", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def get_item_costs(self, item_id: str) -> dict[str, Any]:
        return await self._call_tool("get_item_costs", {"item_id": item_id})

    async def get_purchase_orders(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_purchase_orders", {})
        return result if isinstance(result, list) else [result]

    async def get_shipments(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_shipments", {})
        return result if isinstance(result, list) else [result]
