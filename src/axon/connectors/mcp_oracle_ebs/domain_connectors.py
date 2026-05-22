"""Oracle EBS Domain Connectors — one per MCP server in the EBS MCP Agent project.

The EBS MCP Agent runs 10 domain-specific MCP servers (ports 8001-8004, 8101-8111).
Each connector maps to a specific server with tool wrappers matching the actual
MCP tools that server exposes. All inherit from BaseMCPConnector.

Server mapping:
  Port   Server name         Connector class         Domain/agent group
  8102   ebs_demand           EBSDemandConnector       Sales/Demand
  8103   ebs_supply           EBSSupplyConnector       Supply/Procurement
  8104   ebs_production       EBSProductionConnector   Production
  8105   ebs_logistics        EBSLogisticsConnector    Logistics
  8106   ebs_quality          EBSQualityConnector      QC/QA
  8107   ebs_asset            EBSAssetConnector        Maintenance
  8108   ebs_finance          EBSFinanceConnector      Finance
  8109   ebs_engineering      EBSEngineeringConnector  PD/Engineering
  8111   ebs_warehouse        EBSWarehouseConnector    Warehouse
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector

# =============================================================================
# EBS Demand (port 8102)
# =============================================================================


class EBSDemandConnector(BaseMCPConnector):
    """MCP client for ebs-demand server (port 8102)."""
    server_name = "ebs_demand"

    async def get_sales_orders(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_sales_orders", {})
        return result if isinstance(result, list) else [result]

    async def get_demand_forecast(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_demand_forecast", {})
        return result if isinstance(result, list) else [result]

    async def get_available_to_promise(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_available_to_promise", {})
        return result if isinstance(result, list) else [result]


# =============================================================================
# EBS Supply (port 8103)
# =============================================================================


class EBSSupplyConnector(BaseMCPConnector):
    """MCP client for ebs-supply server (port 8103)."""
    server_name = "ebs_supply"

    async def get_inventory_levels(
        self, item_ids: list[str], org_id: int | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {"item_ids": item_ids}
        if org_id is not None:
            args["org_id"] = org_id
        result = await self._call_tool("get_inventory_levels", args)
        return result if isinstance(result, list) else [result]

    async def get_safety_stock(self, item_id: int) -> Any:
        return await self._call_tool("get_safety_stock", {"item_id": item_id})

    async def get_storage_capacity(self, warehouse_id: int) -> Any:
        return await self._call_tool("get_storage_capacity", {"warehouse_id": warehouse_id})

    async def get_inventory_aging(self, item_id: int) -> Any:
        return await self._call_tool("get_inventory_aging", {"item_id": item_id})

    async def get_suppliers(self, item_id: int) -> list[dict[str, Any]]:
        result = await self._call_tool("get_suppliers", {"item_id": item_id})
        return result if isinstance(result, list) else [result]

    async def get_item_costs(self, item_ids: list[str]) -> list[dict[str, Any]]:
        result = await self._call_tool("get_item_costs", {"item_ids": item_ids})
        return result if isinstance(result, list) else [result]

    async def get_purchase_orders(self, status: str | None = None) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if status:
            args["status"] = status
        result = await self._call_tool("get_purchase_orders", args)
        return result if isinstance(result, list) else [result]

    async def get_supplier_performance(self, supplier_id: int) -> Any:
        return await self._call_tool("get_supplier_performance", {"supplier_id": supplier_id})

    async def create_purchase_requisition(self, item_id: int, quantity: float) -> Any:
        return await self._call_tool(
            "create_purchase_requisition",
            {"item_id": item_id, "quantity": quantity},
        )


# =============================================================================
# EBS Production (port 8104)
# =============================================================================


class EBSProductionConnector(BaseMCPConnector):
    """MCP client for ebs-production server (port 8104)."""
    server_name = "ebs_production"

    async def list_wip_jobs(self) -> list[dict[str, Any]]:
        result = await self._call_tool("list_wip_jobs", {})
        return result if isinstance(result, list) else [result]

    async def get_bom(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_bom", {})
        return result if isinstance(result, list) else [result]

    async def get_work_center_capacity(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_work_center_capacity", {})
        return result if isinstance(result, list) else [result]

    async def get_routing(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_routing", {})
        return result if isinstance(result, list) else [result]

    async def reschedule_wip_job(self) -> Any:
        return await self._call_tool("reschedule_wip_job", {})

    async def get_item_master(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_item_master", {})
        return result if isinstance(result, list) else [result]


# =============================================================================
# EBS Logistics (port 8105)
# =============================================================================


class EBSLogisticsConnector(BaseMCPConnector):
    """MCP client for ebs-logistics server (port 8105)."""
    server_name = "ebs_logistics"

    async def get_shipments(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_shipments", {})
        return result if isinstance(result, list) else [result]

    async def get_carrier_rates(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_carrier_rates", {})
        return result if isinstance(result, list) else [result]

    async def get_transit_times(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_transit_times", {})
        return result if isinstance(result, list) else [result]

    async def get_delivery_constraints(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_delivery_constraints", {})
        return result if isinstance(result, list) else [result]

    async def create_shipment(self) -> Any:
        return await self._call_tool("create_shipment", {})


# =============================================================================
# EBS Quality (port 8106)
# =============================================================================


class EBSQualityConnector(BaseMCPConnector):
    """MCP client for ebs-quality server (port 8106)."""
    server_name = "ebs_quality"

    async def get_inspection_plan(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_inspection_plan", {})
        return result if isinstance(result, list) else [result]

    async def get_defect_history(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_defect_history", {})
        return result if isinstance(result, list) else [result]

    async def create_inspection_lot(self) -> Any:
        return await self._call_tool("create_inspection_lot", {})


# =============================================================================
# EBS Asset (port 8107)
# =============================================================================


class EBSAssetConnector(BaseMCPConnector):
    """MCP client for ebs-asset server (port 8107)."""
    server_name = "ebs_asset"

    async def get_asset_health(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_asset_health", {})
        return result if isinstance(result, list) else [result]

    async def get_maintenance_schedule(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_maintenance_schedule", {})
        return result if isinstance(result, list) else [result]

    async def get_downtime_history(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_downtime_history", {})
        return result if isinstance(result, list) else [result]

    async def update_work_center_status(self) -> Any:
        return await self._call_tool("update_work_center_status", {})


# =============================================================================
# EBS Finance (port 8108)
# =============================================================================


class EBSFinanceConnector(BaseMCPConnector):
    """MCP client for ebs-finance server (port 8108)."""
    server_name = "ebs_finance"

    async def get_budget(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_budget", {})
        return result if isinstance(result, list) else [result]

    async def get_gl_accounts(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_gl_accounts", {})
        return result if isinstance(result, list) else [result]

    async def get_profitability(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_profitability", {})
        return result if isinstance(result, list) else [result]


# =============================================================================
# EBS Engineering (port 8109)
# =============================================================================


class EBSEngineeringConnector(BaseMCPConnector):
    """MCP client for ebs-engineering server (port 8109)."""
    server_name = "ebs_engineering"

    async def get_engineering_changes(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_engineering_changes", {})
        return result if isinstance(result, list) else [result]

    async def get_bom(self) -> list[dict[str, Any]]:
        result = await self._call_tool("get_bom", {})
        return result if isinstance(result, list) else [result]


# =============================================================================
# EBS Warehouse (port 8111) — 14 tools
# =============================================================================


class EBSWarehouseConnector(BaseMCPConnector):
    """MCP client for ebs-warehouse server (port 8111)."""
    server_name = "ebs_warehouse"

    async def get_warehouse_capacity(self, org_id: int | None = None) -> Any:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        return await self._call_tool("get_warehouse_capacity", args)

    async def get_subinventory_levels(
        self,
        org_id: int | None = None,
        item_ids: list[str] | None = None,
        subinventory_code: str | None = None,
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if item_ids:
            args["item_ids"] = item_ids
        if subinventory_code:
            args["subinventory_code"] = subinventory_code
        result = await self._call_tool("get_subinventory_levels", args)
        return result if isinstance(result, list) else [result]

    async def get_locator_capacity(
        self, org_id: int | None = None, subinventory_code: str | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if subinventory_code:
            args["subinventory_code"] = subinventory_code
        result = await self._call_tool("get_locator_capacity", args)
        return result if isinstance(result, list) else [result]

    async def get_picking_rules(
        self, org_id: int | None = None, item_id: int | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if item_id is not None:
            args["item_id"] = item_id
        result = await self._call_tool("get_picking_rules", args)
        return result if isinstance(result, list) else [result]

    async def get_putaway_rules(
        self, org_id: int | None = None, item_id: int | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if item_id is not None:
            args["item_id"] = item_id
        result = await self._call_tool("get_putaway_rules", args)
        return result if isinstance(result, list) else [result]

    async def get_cycle_count_schedule(
        self, org_id: int | None = None, subinventory_code: str | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if subinventory_code:
            args["subinventory_code"] = subinventory_code
        result = await self._call_tool("get_cycle_count_schedule", args)
        return result if isinstance(result, list) else [result]

    async def get_wave_details(self, wave_id: int) -> list[dict[str, Any]]:
        result = await self._call_tool("get_wave_details", {"wave_id": wave_id})
        return result if isinstance(result, list) else [result]

    async def get_pick_slip_details(
        self, pick_slip_id: int | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if pick_slip_id is not None:
            args["pick_slip_id"] = pick_slip_id
        if status:
            args["status"] = status
        result = await self._call_tool("get_pick_slip_details", args)
        return result if isinstance(result, list) else [result]

    async def get_material_transactions(
        self,
        org_id: int | None = None,
        item_id: int | None = None,
        transaction_type: str | None = None,
        days_back: int | None = None,
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if item_id is not None:
            args["item_id"] = item_id
        if transaction_type:
            args["transaction_type"] = transaction_type
        if days_back is not None:
            args["days_back"] = days_back
        result = await self._call_tool("get_material_transactions", args)
        return result if isinstance(result, list) else [result]

    async def get_receipt_routing(
        self, org_id: int | None = None, po_number: str | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if org_id is not None:
            args["org_id"] = org_id
        if po_number:
            args["po_number"] = po_number
        result = await self._call_tool("get_receipt_routing", args)
        return result if isinstance(result, list) else [result]

    async def get_labeling_rules(
        self, item_id: int | None = None, customer_id: int | None = None
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {}
        if item_id is not None:
            args["item_id"] = item_id
        if customer_id is not None:
            args["customer_id"] = customer_id
        result = await self._call_tool("get_labeling_rules", args)
        return result if isinstance(result, list) else [result]

    async def create_pick_release(
        self, order_id: int, order_line_ids: list[int] | None = None
    ) -> Any:
        args: dict[str, Any] = {"order_id": order_id}
        if order_line_ids:
            args["order_line_ids"] = order_line_ids
        return await self._call_tool("create_pick_release", args)

    async def create_cycle_count_entry(
        self,
        org_id: int,
        item_id: int,
        locator_id: int,
        counted_qty: float,
        lot_number: str | None = None,
    ) -> Any:
        args: dict[str, Any] = {
            "org_id": org_id,
            "item_id": item_id,
            "locator_id": locator_id,
            "counted_qty": counted_qty,
        }
        if lot_number:
            args["lot_number"] = lot_number
        return await self._call_tool("create_cycle_count_entry", args)

    async def create_subinventory_transfer(
        self,
        org_id: int,
        item_id: int,
        quantity: float,
        from_subinventory: str,
        to_subinventory: str,
    ) -> Any:
        return await self._call_tool(
            "create_subinventory_transfer",
            {
                "org_id": org_id,
                "item_id": item_id,
                "quantity": quantity,
                "from_subinventory": from_subinventory,
                "to_subinventory": to_subinventory,
            },
        )
