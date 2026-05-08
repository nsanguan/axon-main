"""Integration tests — MCP connectors + SemanticTransformers with mock data.

Phase 2.5 — verifies the FETCH → TRANSFORM pipeline works end-to-end
without requiring real MCP servers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from axon.connectors.mcp_odoo.connector import OdooConnector
from axon.connectors.mcp_odoo.transformer import OdooTransformer
from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector
from axon.connectors.mcp_oracle_ebs.transformer import OracleEBSTransformer
from axon.connectors.mcp_sap.connector import SAPConnector
from axon.connectors.mcp_sap.transformer import SAPTransformer
from axon.core.schema import MCPToolOutput
from tests.mocks import create_mocked_connector

# =============================================================================
# Oracle EBS — connector + transformer pipeline
# =============================================================================


class TestOracleEBSIntegration:
    @pytest.mark.asyncio
    async def test_fetch_inventory_and_transform(self):
        """Fetch inventory via mock connector → transform to Supply models."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        tx = OracleEBSTransformer()

        # FETCH
        raw = await ebs.get_inventory_levels("FG-001")
        assert len(raw) == 2
        assert raw[0]["item_id"] == "FG-001"

        # TRANSFORM
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="get_inventory_levels",
            raw_payload={"items": raw},
        )
        supplies = tx.to_supply(output)
        assert len(supplies) == 2
        assert supplies[0].item.native_id == "FG-001"
        assert supplies[0].source == "on_hand"
        assert supplies[0].quantity == Decimal("3000")

    @pytest.mark.asyncio
    async def test_fetch_sales_orders_and_transform(self):
        """Fetch sales orders → transform to Demand models."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        tx = OracleEBSTransformer()

        raw = await ebs.get_sales_orders()
        assert len(raw) == 2

        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="get_sales_orders",
            raw_payload={"items": raw},
        )
        demands = tx.to_demand(output)
        assert len(demands) == 2
        assert demands[0].item.native_id == "FG-001"
        assert demands[0].source == "sales_order"
        assert demands[0].quantity == Decimal("5000")
        assert demands[0].priority == 90

    @pytest.mark.asyncio
    async def test_fetch_wip_and_transform(self):
        """Fetch WIP jobs → transform to Supply models."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        tx = OracleEBSTransformer()

        raw = await ebs.list_wip_jobs()
        assert len(raw) == 1

        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="list_wip_jobs",
            raw_payload={"items": raw},
        )
        supplies = tx.to_supply(output)
        assert len(supplies) == 1
        assert supplies[0].source == "wip"
        assert supplies[0].lead_time_days == 30

    @pytest.mark.asyncio
    async def test_transformer_routing_wrong_server_rejected(self):
        """Transformer rejects output from wrong server."""
        tx = OracleEBSTransformer()
        output = MCPToolOutput(
            server_name="sap",
            tool_name="get_inventory_levels",
            raw_payload={"items": [{"item_id": "X", "quantity": 1}]},
        )
        assert tx.to_demand(output) == []
        assert tx.to_supply(output) == []

    @pytest.mark.asyncio
    async def test_mock_call_history(self):
        """Verify mock records tool calls for audit."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        await ebs.get_inventory_levels("FG-001")
        await ebs.get_sales_orders()
        await ebs.get_suppliers("RM-001")

        assert mock.was_called("get_inventory_levels")
        assert mock.was_called("get_sales_orders")
        assert mock.was_called("get_suppliers")
        assert len(mock.call_history) == 3

    @pytest.mark.asyncio
    async def test_fetch_forecast_and_transform(self):
        """Fetch demand forecast → transform to Demand."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        tx = OracleEBSTransformer()

        raw = await ebs.get_demand_forecast("RM-001")
        assert len(raw) == 1

        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="get_demand_forecast",
            raw_payload={"items": raw},
        )
        demands = tx.to_demand(output)
        assert len(demands) == 1
        assert demands[0].source == "forecast"
        assert demands[0].confidence == 0.80

    @pytest.mark.asyncio
    async def test_fetch_suppliers_and_transform(self):
        """Fetch suppliers — raw data passes through connector."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        raw = await ebs.get_suppliers("RM-001")
        assert len(raw) == 2
        assert raw[0]["supplier_name"] == "TitaniumMet Inc"

    @pytest.mark.asyncio
    async def test_fetch_costs(self):
        """Fetch item costs."""
        ebs, mock = create_mocked_connector(OracleEBSConnector)
        raw = await ebs.get_item_costs("FG-001")
        assert raw["standard_cost"] == 5.20
        assert raw["currency"] == "USD"


# =============================================================================
# SAP — connector + transformer
# =============================================================================


class TestSAPIntegration:
    @pytest.mark.asyncio
    async def test_fetch_and_transform(self):
        """SAP connector fetches and transforms inventory."""
        sap, mock = create_mocked_connector(SAPConnector)
        tx = SAPTransformer()

        raw = await sap.get_inventory_levels()
        assert len(raw) == 2

        output = MCPToolOutput(
            server_name="sap",
            tool_name="get_inventory_levels",
            raw_payload={"items": raw},
        )
        supplies = tx.to_supply(output)
        assert len(supplies) == 2
        assert supplies[0].item.system == "sap"
        assert supplies[0].source == "on_hand"


# =============================================================================
# Odoo — connector + transformer
# =============================================================================


class TestOdooIntegration:
    @pytest.mark.asyncio
    async def test_fetch_and_transform(self):
        """Odoo connector fetches and transforms inventory."""
        odoo, mock = create_mocked_connector(OdooConnector)
        tx = OdooTransformer()

        raw = await odoo.get_inventory_levels()
        assert len(raw) == 2

        output = MCPToolOutput(
            server_name="odoo",
            tool_name="get_inventory_levels",
            raw_payload={"items": raw},
        )
        supplies = tx.to_supply(output)
        assert len(supplies) == 2
        assert supplies[0].item.system == "odoo"
        assert supplies[0].source == "on_hand"


# =============================================================================
# Circuit breaker integration
# =============================================================================


class TestCircuitBreakerIntegration:
    def test_breaker_closed_to_open(self):
        from axon.connectors.circuit_breaker import BreakerState, CircuitBreaker

        cb = CircuitBreaker("test_server", failure_threshold=3)
        assert cb.allow_call()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == BreakerState.CLOSED
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        assert not cb.allow_call()

    def test_degradation_monitor(self):
        from axon.connectors.circuit_breaker import (
            CircuitBreaker,
            DegradationLevel,
            DegradationMonitor,
        )

        monitor = DegradationMonitor()
        monitor.register("oracle_ebs", CircuitBreaker("oracle_ebs"))
        monitor.register("sap", CircuitBreaker("sap"))
        monitor.register("external_rag", CircuitBreaker("external_rag"))

        # All healthy
        assert monitor.evaluate() == DegradationLevel.FULL

        # One ERP down
        monitor.breakers["oracle_ebs"].record_failure()
        monitor.breakers["oracle_ebs"].record_failure()
        monitor.breakers["oracle_ebs"].record_failure()
        assert monitor.evaluate() == DegradationLevel.DEGRADED

        # Two ERP down = CRITICAL (all ERPs are down)
        monitor.breakers["sap"].record_failure()
        monitor.breakers["sap"].record_failure()
        monitor.breakers["sap"].record_failure()
        assert monitor.evaluate() == DegradationLevel.CRITICAL
