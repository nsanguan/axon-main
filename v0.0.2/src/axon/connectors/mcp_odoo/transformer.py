"""Odoo SemanticTransformer — maps Odoo MCPToolOutput → Domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

from axon.core.schema import Demand, EntityRef, MCPToolOutput, Period, SemanticTransformer, Supply


class OdooTransformer(SemanticTransformer):
    """Transforms Odoo MCP tool outputs into Axon domain models."""

    source_system: ClassVar[str] = "odoo"
    supported_tools: ClassVar[list[str]] = [
        "get_inventory_levels",
        "get_sales_orders",
        "get_purchase_orders",
        "get_suppliers",
        "list_wip_jobs",
    ]

    def to_demand(self, output: MCPToolOutput) -> list[Demand]:
        if not self.can_handle(output):
            return []
        data = output.raw_payload
        items = data.get("items", data.get("results", [data])) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = [items]
        return [self._row_to_demand(r) for r in items if isinstance(r, dict)]

    def to_supply(self, output: MCPToolOutput) -> list[Supply]:
        if not self.can_handle(output):
            return []
        data = output.raw_payload
        items = data.get("items", data.get("results", [data])) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = [items]
        return [self._row_to_supply(r) for r in items if isinstance(r, dict)]

    def _row_to_demand(self, row: dict[str, Any]) -> Demand:
        return Demand(
            item=EntityRef(system="odoo", entity_type="product", native_id=str(row.get("id", ""))),
            quantity=Decimal(str(row.get("product_uom_qty", 0))),
            period=Period(start=datetime.now(UTC), end=datetime.now(UTC)),
            source="sales_order",
        )

    def _row_to_supply(self, row: dict[str, Any]) -> Supply:
        return Supply(
            item=EntityRef(system="odoo", entity_type="product", native_id=str(row.get("id", ""))),
            quantity=Decimal(str(row.get("quantity", 0))),
            period=Period(start=datetime.now(UTC), end=datetime.now(UTC)),
            source="on_hand",
        )
