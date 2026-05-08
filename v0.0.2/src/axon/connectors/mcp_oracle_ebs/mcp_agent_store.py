"""
StoreAgent — MCP sub-agent for inventory and warehouse operations under mcp_oracle_ebs.

Provides a focused interface to Oracle EBS store/inventory tools:
stock levels, ATP, forecasts, orders, shipments, and warehouse management.

Usage:
    from axon.connectors.mcp_oracle_ebs.mcp_agent_store import StoreAgent

    async with StoreAgent(settings.mcp_agent_store) as store:
        inventory = await store.get_inventory_levels("FG-001")
        atp = await store.get_available_to_promise("FG-001", "2026-06-01", "2026-06-30")
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class StoreAgent(BaseMCPConnector):
    """MCP sub-agent for store/inventory — levels, ATP, orders, shipments, warehouse."""

    server_name = "mcp_agent_store"

    # =========================================================================
    # Inventory & Demand
    # =========================================================================

    async def get_inventory_levels(
        self, item_id: str | None = None, location: str | None = None
    ) -> list[dict[str, Any]]:
        """Return on-hand, reserved, and available inventory."""
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        if location:
            args["location"] = location
        result = await self._call_tool("get_inventory_levels", args)
        return result if isinstance(result, list) else [result]

    async def get_available_to_promise(
        self, item_id: str, date_from: str, date_to: str
    ) -> dict[str, Any]:
        """Return ATP quantity and earliest availability date."""
        return await self._call_tool(
            "get_available_to_promise",
            {
                "item_id": item_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    async def get_sales_orders(
        self, status: str = "open", customer_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List open sales orders."""
        args: dict[str, str] = {"status": status}
        if customer_id:
            args["customer_id"] = customer_id
        result = await self._call_tool("get_sales_orders", args)
        return result if isinstance(result, list) else [result]

    async def get_demand_forecast(self, item_id: str, periods: int = 12) -> list[dict[str, Any]]:
        """Return statistical or manual forecast for items by period."""
        result = await self._call_tool(
            "get_demand_forecast",
            {
                "item_id": item_id,
                "periods": periods,
            },
        )
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # Warehouse
    # =========================================================================

    async def get_safety_stock(
        self, item_id: str | None = None, location: str | None = None
    ) -> list[dict[str, Any]]:
        """Return safety stock targets per item × location."""
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        if location:
            args["location"] = location
        result = await self._call_tool("get_safety_stock", args)
        return result if isinstance(result, list) else [result]

    async def get_storage_capacity(self, warehouse_id: str | None = None) -> list[dict[str, Any]]:
        """Return total and available storage capacity (pallet/volume) per warehouse."""
        args: dict[str, Any] = {}
        if warehouse_id:
            args["warehouse_id"] = warehouse_id
        result = await self._call_tool("get_storage_capacity", args)
        return result if isinstance(result, list) else [result]

    async def get_inventory_aging(self, item_id: str | None = None) -> list[dict[str, Any]]:
        """Return inventory aging breakdown (FIFO layers) for items."""
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        result = await self._call_tool("get_inventory_aging", args)
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # Logistics — shipments
    # =========================================================================

    async def get_shipments(self) -> list[dict[str, Any]]:
        """List planned and in-transit shipments."""
        result = await self._call_tool("get_shipments", {})
        return result if isinstance(result, list) else [result]

    async def get_carrier_rates(self, lane: str) -> list[dict[str, Any]]:
        """Return carrier rate cards by lane."""
        result = await self._call_tool("get_carrier_rates", {"lane": lane})
        return result if isinstance(result, list) else [result]

    async def get_transit_times(self, origin: str, destination: str) -> dict[str, Any]:
        """Return standard transit time per lane."""
        return await self._call_tool(
            "get_transit_times",
            {
                "origin": origin,
                "destination": destination,
            },
        )

    async def get_delivery_constraints(
        self, customer_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return customer delivery windows, dock constraints, appointment requirements."""
        args: dict[str, Any] = {}
        if customer_id:
            args["customer_id"] = customer_id
        result = await self._call_tool("get_delivery_constraints", args)
        return result if isinstance(result, list) else [result]

    async def create_shipment(
        self,
        origin: str,
        destination: str,
        items: list[dict[str, Any]],
        carrier: str | None = None,
        expedited: bool = False,
    ) -> dict[str, Any]:
        """Create a shipment record. HITL required for expedited shipments."""
        return await self._call_tool(
            "create_shipment",
            {
                "origin": origin,
                "destination": destination,
                "items": items,
                "carrier": carrier or "",
                "expedited": expedited,
            },
        )
