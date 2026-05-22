"""Mock MCP Server — returns canned ERP data for integration testing.

Since all ERP MCP servers are separate projects and may not be running,
this mock provides pre-defined responses so connectors and transformers
can be tested in isolation.

The mock is NOT a real MCP server — it's a drop-in that intercepts
BaseMCPConnector._call_tool() and returns canned data.

Usage:
    from tests.mocks import apply_mock_responses

    apply_mock_responses(connector)  # intercepts _call_tool
    result = await connector.get_inventory_levels("FG-001")
    # Returns canned data without network calls
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

# =============================================================================
# Canned response data
# =============================================================================

MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    # Inventory
    "get_inventory_levels": {
        "items": [
            {
                "item_id": "FG-001",
                "item_name": "Aircraft Bolt AN4-10A",
                "quantity": 3000,
                "qty_available": 3000,
                "qty_reserved": 500,
                "available_from": "2026-05-01",
                "available_to": "2026-12-31",
                "location_id": "WH-01",
                "location_name": "Warehouse A",
                "lot": "LOT-2026-0512",
                "quality": "A",
            },
            {
                "item_id": "RM-001",
                "item_name": "Titanium Alloy Ti-6Al-4V Sheet",
                "quantity": 1500,
                "qty_available": 1500,
                "available_from": "2026-05-20",
                "available_to": "2026-12-31",
                "location_id": "WH-02",
                "location_name": "Raw Materials",
                "lot": "LOT-2026-0420",
                "quality": "A",
            },
        ]
    },
    # Sales
    "get_sales_orders": {
        "items": [
            {
                "item_id": "FG-001",
                "item_name": "Aircraft Bolt AN4-10A",
                "quantity": 5000,
                "qty_demand": 5000,
                "date_from": "2026-06-01",
                "due_date": "2026-06-30",
                "priority": 90,
                "priority_weight": 90,
                "customer": "Boeing",
                "order_ref": "SO-2026-0421",
                "confidence": 0.95,
            },
            {
                "item_id": "FG-002",
                "item_name": "Hydraulic Seal HS-22B",
                "quantity": 800,
                "qty_demand": 800,
                "date_from": "2026-07-01",
                "due_date": "2026-07-31",
                "priority": 40,
                "priority_weight": 40,
                "customer": "Airbus",
                "order_ref": "SO-2026-0510",
                "confidence": 0.90,
            },
        ]
    },
    # Demand forecast
    "get_demand_forecast": {
        "items": [
            {
                "item_id": "RM-001",
                "item_name": "Titanium Alloy Ti-6Al-4V Sheet",
                "quantity": 1200,
                "qty_demand": 1200,
                "date_from": "2026-05-15",
                "due_date": "2026-06-15",
                "priority": 60,
                "priority_weight": 60,
                "confidence": 0.80,
                "forecast_method": "statistical",
            },
        ]
    },
    # WIP
    "list_wip_jobs": {
        "items": [
            {
                "item_id": "FG-001",
                "item_name": "Aircraft Bolt AN4-10A",
                "quantity": 2500,
                "qty_available": 2500,
                "wip_job": "WIP-10234",
                "status": "in_progress",
                "start_date": "2026-05-01",
                "end_date": "2026-06-10",
                "available_from": "2026-06-10",
                "arrival_date": "2026-06-10",
                "lead_time_days": 30,
                "work_center": "WC-03",
                "routing": "CNC-OP-10",
            },
        ]
    },
    # BOM
    "get_bom": {
        "items": [
            {"component": "RM-001", "component_name": "Titanium Alloy", "qty_per_assembly": 0.5},
            {"component": "RM-003", "component_name": "Steel Washer", "qty_per_assembly": 1.0},
        ],
        "revision": "B",
        "effective_date": "2025-01-01",
    },
    # Suppliers
    "get_suppliers": {
        "items": [
            {
                "supplier_id": "SUP-01",
                "supplier_name": "TitaniumMet Inc",
                "lead_time_days": 45,
                "price_per_unit": 120.50,
                "moq": 100,
                "reliability": 0.92,
            },
            {
                "supplier_id": "SUP-02",
                "supplier_name": "AeroMetals GmbH",
                "lead_time_days": 60,
                "price_per_unit": 108.00,
                "moq": 200,
                "reliability": 0.85,
            },
        ]
    },
    # Costs
    "get_item_costs": {
        "standard_cost": 5.20,
        "actual_cost": 5.35,
        "last_po_price": 5.10,
        "currency": "USD",
    },
    # Purchase orders
    "get_purchase_orders": {
        "items": [
            {
                "item_id": "RM-001",
                "item_name": "Titanium Alloy Ti-6Al-4V Sheet",
                "quantity": 1500,
                "qty_available": 1500,
                "po_number": "PO-2026-0891",
                "supplier": "TitaniumMet Inc",
                "supplier_id": "SUP-01",
                "due_date": "2026-06-20",
                "arrival_date": "2026-06-20",
                "status": "confirmed",
            },
        ]
    },
    # Shipments
    "get_shipments": {
        "items": [
            {
                "shipment_id": "SHIP-001",
                "origin": "WH-01",
                "destination": "Boeing-Seattle",
                "items": [{"item_id": "FG-001", "quantity": 2000}],
                "eta": "2026-06-05",
                "carrier": "FedEx Freight",
            },
        ]
    },
    # Work center capacity
    "get_work_center_capacity": {
        "items": [
            {
                "work_center": "WC-03",
                "available_hours": 160,
                "total_hours": 176,
                "period": "2026-06",
            },
            {
                "work_center": "WC-05",
                "available_hours": 140,
                "total_hours": 176,
                "period": "2026-06",
            },
        ]
    },
    # Supplier performance
    "get_supplier_performance": {
        "on_time_pct": 92.5,
        "quality_score": 0.95,
        "lead_time_variance_days": 2.3,
    },
    # LLMWiki tools
    "get_sop": {
        "process_code": "manufacturing.bolts",
        "title": "Aerospace Bolt Manufacturing SOP",
        "content": "1. Verify material certs for Ti-6Al-4V per AMS-4911.\n"
        "2. CNC machining tolerance ±0.005mm.\n"
        "3. 100% dimensional inspection required.\n"
        "4. Lot traceability mandatory.",
        "version": "v2.4",
    },
    "check_compliance": {
        "compliant": True,
        "violations": [],
        "recommendations": [],
    },
    # Empty / default
    "get_carrier_rates": {"items": []},
    "get_transit_times": {"transit_days": 5},
    "get_routing": {"operations": [{"op": 10, "work_center": "WC-03", "hours": 0.5}]},
}


# =============================================================================
# Mock application
# =============================================================================


class MockMCPResponder:
    """Returns pre-defined canned responses for MCP tool calls.

    Implements the same interface as BaseMCPConnector._call_tool
    so it can replace real MCP calls in tests.
    """

    def __init__(self, custom_responses: dict[str, Any] | None = None):
        self.responses = {**MOCK_RESPONSES}
        if custom_responses:
            self.responses.update(custom_responses)
        self.call_history: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Return canned response for tool_name, recording the call.

        Returns the items list directly (not wrapped in {"items": ...})
        so connector methods that expect list[dict] work correctly.
        """
        self.call_history.append((tool_name, arguments))
        response = self.responses.get(
            tool_name,
            {"items": [], "_note": "mock: no data for this tool"},
        )
        # Unwrap items list if response is dict with items key
        if isinstance(response, dict) and "items" in response:
            return response["items"]
        return response

    @property
    def last_call(self) -> tuple[str, dict[str, Any]] | None:
        return self.call_history[-1] if self.call_history else None

    def was_called(self, tool_name: str) -> bool:
        return any(c[0] == tool_name for c in self.call_history)


def patch_connector(connector) -> MockMCPResponder:
    """Replace a connector's _call_tool with a mock responder.

    Args:
        connector: Any BaseMCPConnector subclass

    Returns:
        MockMCPResponder for assertions on call history
    """
    mock = MockMCPResponder()
    connector._call_tool = mock
    return mock


def create_mocked_connector(connector_class, config=None):
    """Create a connector instance with mocked _call_tool.

    No network connection needed — returns canned data for all tools.

    Usage:
        from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector
        ebs = create_mocked_connector(OracleEBSConnector)
        inventory = await ebs.get_inventory_levels("FG-001")
    """
    from axon.core.config import MCPServerConfig

    cfg = config or MCPServerConfig(
        url="http://mock:8000/mcp",
        enabled=True,
    )
    connector = connector_class(cfg)
    # Bypass connect/disconnect — mock the session call_tool
    connector.connect = AsyncMock()
    connector.disconnect = AsyncMock()
    connector._session = None  # Will be bypassed
    mock = MockMCPResponder()
    connector._call_tool = mock
    return connector, mock
