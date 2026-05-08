"""SAP SemanticTransformer — maps SAP MCPToolOutput → Domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

from axon.core.schema import Demand, EntityRef, MCPToolOutput, Period, SemanticTransformer, Supply


class SAPTransformer(SemanticTransformer):
    """Transforms SAP MCP tool outputs into Axon domain models."""

    source_system: ClassVar[str] = "sap"
    supported_tools: ClassVar[list[str]] = [
        "get_inventory_levels",
        "get_sales_orders",
        "get_demand_forecast",
        "list_wip_jobs",
        "get_bom",
        "get_work_center_capacity",
        "get_suppliers",
        "get_item_costs",
        "get_purchase_orders",
        "get_shipments",
    ]

    def to_demand(self, output: MCPToolOutput) -> list[Demand]:
        if not self.can_handle(output):
            return []
        data = output.raw_payload
        items = data.get("items", data.get("results", [data])) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = [items]
        return [self._row_to_demand(r, output.tool_name) for r in items if isinstance(r, dict)]

    def to_supply(self, output: MCPToolOutput) -> list[Supply]:
        if not self.can_handle(output):
            return []
        data = output.raw_payload
        items = data.get("items", data.get("results", [data])) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = [items]
        return [self._row_to_supply(r, output.tool_name) for r in items if isinstance(r, dict)]

    def _row_to_demand(self, row: dict[str, Any], tool_name: str) -> Demand:
        return Demand(
            item=EntityRef(
                system="sap", entity_type="material", native_id=str(row.get("material", ""))
            ),
            quantity=Decimal(str(row.get("quantity", 0))),
            period=Period(start=datetime.now(UTC), end=datetime.now(UTC)),
            source="sales_order" if tool_name == "get_sales_orders" else "forecast",
        )

    def _row_to_supply(self, row: dict[str, Any], tool_name: str) -> Supply:
        return Supply(
            item=EntityRef(
                system="sap", entity_type="material", native_id=str(row.get("material", ""))
            ),
            quantity=Decimal(str(row.get("quantity", 0))),
            period=Period(start=datetime.now(UTC), end=datetime.now(UTC)),
            source="on_hand" if tool_name == "get_inventory_levels" else "planned",
        )
