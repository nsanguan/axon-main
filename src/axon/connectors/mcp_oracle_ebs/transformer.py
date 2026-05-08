"""
Oracle EBS SemanticTransformer — maps MCPToolOutput → Domain models.

Converts raw MCP responses from mcp-oracle-ebs into Axon core schema types
(Demand, Supply, Allocation). This is the bridge between ERP-native data
and the universal schema that agents reason in.

Usage:
    from axon.connectors.mcp_oracle_ebs.transformer import OracleEBSTransformer

    tx = OracleEBSTransformer()
    demand = tx.to_demand(mcp_output)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

from axon.core.schema import (
    Demand,
    EntityRef,
    MCPToolOutput,
    Period,
    SemanticTransformer,
    Supply,
)


class OracleEBSTransformer(SemanticTransformer):
    """Transforms Oracle EBS MCP tool outputs into Axon domain models.

    Handles the full Oracle EBS tool surface (legacy/composite).
    """

    source_system: ClassVar[str] = "oracle_ebs"
    supported_tools: ClassVar[list[str]] = [
        "get_inventory_levels",
        "get_available_to_promise",
        "get_sales_orders",
        "get_demand_forecast",
        "list_wip_jobs",
        "get_bom",
        "get_work_center_capacity",
        "get_routing",
        "get_suppliers",
        "get_item_costs",
        "get_purchase_orders",
        "get_supplier_performance",
        "get_shipments",
        "get_carrier_rates",
        "get_transit_times",
        "reschedule_wip_job",
        "create_purchase_requisition",
    ]

    # =========================================================================
    # Demand transformations
    # =========================================================================

    def to_demand(self, output: MCPToolOutput) -> list[Demand]:
        """Map an MCP tool output to Demand models.

        Handles: get_sales_orders, get_demand_forecast,
                 get_available_to_promise
        """
        if not self.can_handle(output):
            return []

        data = output.raw_payload
        if not isinstance(data, dict):
            return []

        items = data.get("items", data.get("results", [data]))
        if not isinstance(items, list):
            items = [items]

        demands: list[Demand] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            demands.append(self._row_to_demand(item, output.tool_name))
        return demands

    def _row_to_demand(self, row: dict[str, Any], tool_name: str) -> Demand:
        """Map a single row to a Demand model."""
        now = datetime.now(UTC)
        return Demand(
            item=EntityRef(
                system="oracle_ebs",
                entity_type=self._entity_type(row, tool_name),
                native_id=str(row.get("item_id", row.get("product_id", ""))),
                display_name=row.get("item_name", row.get("product_name")),
            ),
            quantity=Decimal(str(row.get("quantity", row.get("qty_demand", 0)))),
            period=Period(
                start=self._parse_date(row.get("date_from", row.get("period_start", now))),
                end=self._parse_date(row.get("date_to", row.get("due_date", now))),
                granularity="day",
            ),
            source=self._demand_source(tool_name),
            confidence=float(row.get("confidence", 1.0)),
            priority=int(row.get("priority", row.get("priority_weight", 0))),
            metadata={
                k: v
                for k, v in row.items()
                if k
                not in (
                    "item_id",
                    "product_id",
                    "item_name",
                    "product_name",
                    "quantity",
                    "qty_demand",
                    "date_from",
                    "date_to",
                    "due_date",
                    "priority",
                    "priority_weight",
                    "confidence",
                )
            },
        )

    # =========================================================================
    # Supply transformations
    # =========================================================================

    def to_supply(self, output: MCPToolOutput) -> list[Supply]:
        """Map an MCP tool output to Supply models.

        Handles: get_inventory_levels, list_wip_jobs, get_purchase_orders
        """
        if not self.can_handle(output):
            return []

        data = output.raw_payload
        if not isinstance(data, dict):
            return []

        items = data.get("items", data.get("results", [data]))
        if not isinstance(items, list):
            items = [items]

        supplies: list[Supply] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            supplies.append(self._row_to_supply(item, output.tool_name))
        return supplies

    def _row_to_supply(self, row: dict[str, Any], tool_name: str) -> Supply:
        """Map a single row to a Supply model."""
        now = datetime.now(UTC)
        return Supply(
            item=EntityRef(
                system="oracle_ebs",
                entity_type=self._entity_type(row, tool_name),
                native_id=str(row.get("item_id", row.get("product_id", ""))),
                display_name=row.get("item_name", row.get("product_name")),
            ),
            quantity=Decimal(str(row.get("quantity", row.get("qty_available", 0)))),
            period=Period(
                start=self._parse_date(row.get("available_from", now)),
                end=self._parse_date(row.get("available_to", row.get("arrival_date", now))),
                granularity="day",
            ),
            source=self._supply_source(row, tool_name),
            location=EntityRef(
                system="oracle_ebs",
                entity_type="location",
                native_id=str(row.get("location_id", row.get("warehouse_id", ""))),
                display_name=row.get("location_name", row.get("warehouse_name")),
            )
            if row.get("location_id") or row.get("warehouse_id")
            else None,
            lead_time_days=int(row.get("lead_time_days", 0)),
            metadata={
                k: v
                for k, v in row.items()
                if k
                not in (
                    "item_id",
                    "product_id",
                    "item_name",
                    "product_name",
                    "quantity",
                    "qty_available",
                    "available_from",
                    "available_to",
                    "arrival_date",
                    "location_id",
                    "warehouse_id",
                    "location_name",
                    "warehouse_name",
                    "lead_time_days",
                )
            },
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _parse_date(value: Any) -> datetime:
        """Parse a date string or return now."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return datetime.now(UTC)

    @staticmethod
    def _entity_type(row: dict[str, Any], tool_name: str) -> str:
        """Infer entity type from tool context."""
        type_map = {
            "get_sales_orders": "sales_order",
            "get_demand_forecast": "forecast",
            "get_available_to_promise": "finished_good",
            "get_inventory_levels": "inventory_item",
            "list_wip_jobs": "wip_job",
            "get_purchase_orders": "purchase_order",
            "get_bom": "finished_good",
        }
        return row.get("entity_type", type_map.get(tool_name, "item"))

    @staticmethod
    def _demand_source(tool_name: str) -> str:
        """Map tool to demand source."""
        return {
            "get_sales_orders": "sales_order",
            "get_demand_forecast": "forecast",
            "get_available_to_promise": "sales_order",
        }.get(tool_name, "forecast")

    @staticmethod
    def _supply_source(row: dict[str, Any], tool_name: str) -> str:
        """Map tool and row to supply source."""
        source_map = {
            "get_inventory_levels": "on_hand",
            "list_wip_jobs": "wip",
            "get_purchase_orders": "purchase_order",
            "get_shipments": "in_transit",
        }
        return row.get("source", row.get("source_type", source_map.get(tool_name, "planned")))


class BuyerTransformer(OracleEBSTransformer):
    """Transforms MCP outputs from the BuyerAgent sub-agent.

    Handles procurement tools: suppliers, POs, costs, requisitions.
    Reuses all transformation logic from OracleEBSTransformer.
    """

    source_system: ClassVar[str] = "mcp_agent_buyer"
    supported_tools: ClassVar[list[str]] = [
        "get_suppliers",
        "get_item_costs",
        "get_purchase_orders",
        "get_supplier_performance",
        "create_purchase_requisition",
    ]


class StoreTransformer(OracleEBSTransformer):
    """Transforms MCP outputs from the StoreAgent sub-agent.

    Handles inventory/warehouse tools: stock levels, ATP, orders,
    forecasts, shipments, warehouse management.
    Reuses all transformation logic from OracleEBSTransformer.
    """

    source_system: ClassVar[str] = "mcp_agent_store"
    supported_tools: ClassVar[list[str]] = [
        "get_inventory_levels",
        "get_available_to_promise",
        "get_sales_orders",
        "get_demand_forecast",
        "get_safety_stock",
        "get_storage_capacity",
        "get_inventory_aging",
        "get_shipments",
        "get_carrier_rates",
        "get_transit_times",
        "get_delivery_constraints",
        "create_shipment",
    ]
