"""Oracle EBS MCP Connector — MCP client and tool wrappers.

Connects to mcp-oracle-ebs (separate project) to query inventory,
WIP jobs, suppliers, purchase orders, and work center capacity.

Usage:
    from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector

    async with OracleEBSConnector(settings.mcp_oracle_ebs) as ebs:
        tools = await ebs.discover_tools()
        inventory = await ebs.get_inventory_levels("FG-001")
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector


class OracleEBSConnector(BaseMCPConnector):
    """MCP client for Oracle EBS — inventory, WIP, orders, suppliers."""

    server_name = "oracle_ebs"

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
    # Production & WIP
    # =========================================================================

    async def list_wip_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all WIP jobs."""
        args: dict[str, Any] = {}
        if status:
            args["status"] = status
        result = await self._call_tool("list_wip_jobs", args)
        return result if isinstance(result, list) else [result]

    async def get_bom(self, item_id: str) -> dict[str, Any]:
        """Return bill of materials for an item."""
        return await self._call_tool("get_bom", {"item_id": item_id})

    async def get_work_center_capacity(
        self, work_center: str | None = None
    ) -> list[dict[str, Any]]:
        """Return available capacity per work center per period."""
        args: dict[str, Any] = {}
        if work_center:
            args["work_center"] = work_center
        result = await self._call_tool("get_work_center_capacity", args)
        return result if isinstance(result, list) else [result]

    async def get_routing(self, item_id: str) -> dict[str, Any]:
        """Return manufacturing routing for an item."""
        return await self._call_tool("get_routing", {"item_id": item_id})

    # =========================================================================
    # Procurement
    # =========================================================================

    async def get_suppliers(self, item_id: str) -> list[dict[str, Any]]:
        """Return approved suppliers with lead times and pricing."""
        result = await self._call_tool("get_suppliers", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def get_item_costs(self, item_id: str) -> dict[str, Any]:
        """Return standard and actual costs for an item."""
        return await self._call_tool("get_item_costs", {"item_id": item_id})

    async def get_purchase_orders(self, status: str = "open") -> list[dict[str, Any]]:
        """List open purchase orders."""
        result = await self._call_tool("get_purchase_orders", {"status": status})
        return result if isinstance(result, list) else [result]

    async def get_supplier_performance(self, supplier_id: str) -> dict[str, Any]:
        """Return on-time delivery %, quality score, lead time variance."""
        return await self._call_tool(
            "get_supplier_performance",
            {
                "supplier_id": supplier_id,
            },
        )

    # =========================================================================
    # Logistics
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
    # Logistics — additional
    # =========================================================================

    async def get_delivery_constraints(
        self, customer_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return customer delivery windows, dock constraints, appointment requirements."""
        args: dict[str, Any] = {}
        if customer_id:
            args["customer_id"] = customer_id
        result = await self._call_tool("get_delivery_constraints", args)
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # Finance
    # =========================================================================

    async def get_budget(
        self, department: str | None = None, period: str | None = None
    ) -> list[dict[str, Any]]:
        """Return budget allocation per department/cost center per period."""
        args: dict[str, Any] = {}
        if department:
            args["department"] = department
        if period:
            args["period"] = period
        result = await self._call_tool("get_budget", args)
        return result if isinstance(result, list) else [result]

    async def get_gl_accounts(self) -> list[dict[str, Any]]:
        """Return chart of accounts (COGS, inventory, variance)."""
        result = await self._call_tool("get_gl_accounts", {})
        return result if isinstance(result, list) else [result]

    async def get_profitability(
        self, item_id: str | None = None, customer_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return margin analysis per item/customer/channel."""
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        if customer_id:
            args["customer_id"] = customer_id
        result = await self._call_tool("get_profitability", args)
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # QC
    # =========================================================================

    async def get_inspection_plan(self, item_id: str, lot_id: str | None = None) -> dict[str, Any]:
        """Return inspection plan (sampling, criteria) for an item/lot."""
        args: dict[str, Any] = {"item_id": item_id}
        if lot_id:
            args["lot_id"] = lot_id
        return await self._call_tool("get_inspection_plan", args)

    async def get_defect_history(
        self, item_id: str, period_from: str | None = None, period_to: str | None = None
    ) -> list[dict[str, Any]]:
        """Return defect rate and Pareto by item, operation, and period."""
        args: dict[str, Any] = {"item_id": item_id}
        if period_from:
            args["period_from"] = period_from
        if period_to:
            args["period_to"] = period_to
        result = await self._call_tool("get_defect_history", args)
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # PD
    # =========================================================================

    async def get_engineering_changes(
        self, item_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        """List ECOs (Engineering Change Orders) with status and effective dates."""
        args: dict[str, Any] = {}
        if item_id:
            args["item_id"] = item_id
        if status:
            args["status"] = status
        result = await self._call_tool("get_engineering_changes", args)
        return result if isinstance(result, list) else [result]

    async def get_item_master(self, item_id: str) -> dict[str, Any]:
        """Return item attributes: make/buy, lead time, lifecycle phase, revision."""
        return await self._call_tool("get_item_master", {"item_id": item_id})

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def get_asset_health(self, asset_id: str | None = None) -> list[dict[str, Any]]:
        """Return current health score, MTBF, and next scheduled maintenance per asset."""
        args: dict[str, Any] = {}
        if asset_id:
            args["asset_id"] = asset_id
        result = await self._call_tool("get_asset_health", args)
        return result if isinstance(result, list) else [result]

    async def get_maintenance_schedule(self, asset_id: str | None = None) -> list[dict[str, Any]]:
        """Return preventive and predictive maintenance schedule per asset."""
        args: dict[str, Any] = {}
        if asset_id:
            args["asset_id"] = asset_id
        result = await self._call_tool("get_maintenance_schedule", args)
        return result if isinstance(result, list) else [result]

    async def get_downtime_history(
        self, asset_id: str, period_from: str | None = None, period_to: str | None = None
    ) -> list[dict[str, Any]]:
        """Return downtime events with duration, cause, and affected capacity."""
        args: dict[str, Any] = {"asset_id": asset_id}
        if period_from:
            args["period_from"] = period_from
        if period_to:
            args["period_to"] = period_to
        result = await self._call_tool("get_downtime_history", args)
        return result if isinstance(result, list) else [result]

    # =========================================================================
    # Write tools
    # =========================================================================

    async def reschedule_wip_job(
        self, wip_job_id: str, new_start: str, new_end: str, old_end: str | None = None
    ) -> dict[str, Any]:
        """Update start/end dates of a WIP job. Requires HITL if shift ≥ 7 days."""
        args: dict[str, Any] = {
            "wip_job_id": wip_job_id,
            "new_start": new_start,
            "new_end": new_end,
        }
        if old_end:
            args["old_end"] = old_end
        return await self._call_tool("reschedule_wip_job", args)

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

    async def create_inspection_lot(
        self,
        item_id: str,
        lot_id: str,
        quantity: float,
        reason: str = "receiving",
    ) -> dict[str, Any]:
        """Create an inspection lot for a received batch. No HITL required."""
        return await self._call_tool(
            "create_inspection_lot",
            {
                "item_id": item_id,
                "lot_id": lot_id,
                "quantity": quantity,
                "reason": reason,
            },
        )
