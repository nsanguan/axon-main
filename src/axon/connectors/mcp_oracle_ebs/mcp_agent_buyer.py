"""
BuyerAgent — MCP sub-agent for procurement operations under mcp_oracle_ebs.

Provides a focused interface to Oracle EBS buyer/procurement tools:
suppliers, purchase orders, costs, and requisitions.

Usage:
    from axon.connectors.mcp_oracle_ebs.mcp_agent_buyer import BuyerAgent

    async with BuyerAgent(settings.mcp_agent_buyer) as buyer:
        suppliers = await buyer.get_suppliers("RM-001")
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class BuyerAgent(BaseMCPConnector):
    """MCP sub-agent for procurement — suppliers, POs, costs, requisitions."""

    server_name = "mcp_agent_buyer"

    # =========================================================================
    # Procurement — suppliers
    # =========================================================================

    async def get_suppliers(self, item_id: str) -> list[dict[str, Any]]:
        """Return approved suppliers with lead times and pricing."""
        result = await self._call_tool("get_suppliers", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def get_supplier_performance(self, supplier_id: str) -> dict[str, Any]:
        """Return on-time delivery %, quality score, lead time variance."""
        return await self._call_tool(
            "get_supplier_performance",
            {"supplier_id": supplier_id},
        )

    # =========================================================================
    # Procurement — purchase orders
    # =========================================================================

    async def get_purchase_orders(self, status: str = "open") -> list[dict[str, Any]]:
        """List open purchase orders."""
        result = await self._call_tool("get_purchase_orders", {"status": status})
        return result if isinstance(result, list) else [result]

    async def create_purchase_requisition(
        self,
        item_id: str,
        quantity: float,
        supplier_id: str,
        due_date: str,
        price_per_unit: float | None = None,
    ) -> dict[str, Any]:
        """Create a purchase requisition. Requires HITL if amount > threshold."""
        args: dict[str, Any] = {
            "item_id": item_id,
            "quantity": quantity,
            "supplier_id": supplier_id,
            "due_date": due_date,
        }
        if price_per_unit is not None:
            args["price_per_unit"] = price_per_unit
        return await self._call_tool("create_purchase_requisition", args)

    # =========================================================================
    # Procurement — costs
    # =========================================================================

    async def get_item_costs(self, item_id: str) -> dict[str, Any]:
        """Return standard and actual costs for an item."""
        return await self._call_tool("get_item_costs", {"item_id": item_id})
