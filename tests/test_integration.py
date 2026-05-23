"""Integration tests — MCP connectors + SemanticTransformers with mock data.

Phase 2.5 — verifies the FETCH → TRANSFORM pipeline works end-to-end
without requiring real MCP servers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from axon.connectors.mcp_odoo.connector import OdooConnector
from axon.connectors.mcp_odoo.transformer import OdooTransformer
from axon.connectors.mcp_oracle_ebs.domain_connectors import EBSSupplyConnector
from axon.connectors.mcp_oracle_ebs.ebs_auth_connector import EBSAuthConnector
from axon.connectors.mcp_oracle_ebs.transformer import OracleEBSTransformer
from axon.connectors.mcp_sap.connector import SAPConnector
from axon.connectors.mcp_sap.transformer import SAPTransformer
from axon.core.schema import MCPToolOutput
from tests.mocks import create_mocked_connector

# =============================================================================
# Oracle EBS — connector + transformer pipeline
# =============================================================================


class TestEBSSupplyIntegration:
    @pytest.mark.asyncio
    async def test_fetch_inventory_and_transform(self):
        """Fetch inventory via mock connector → transform to Supply models."""
        supply, mock = create_mocked_connector(EBSSupplyConnector)
        tx = OracleEBSTransformer()

        # FETCH
        raw = await supply.get_inventory_levels(item_ids=["FG-001"])
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
    async def test_fetch_purchase_orders(self):
        """Fetch POs via EBSSupplyConnector."""
        supply, mock = create_mocked_connector(EBSSupplyConnector)

        raw = await supply.get_purchase_orders("open")
        assert len(raw) == 1
        assert raw[0]["po_number"] == "PO-2026-0891"

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
        supply, mock = create_mocked_connector(EBSSupplyConnector)
        await supply.get_inventory_levels(item_ids=["FG-001"])
        await supply.get_purchase_orders()

        assert mock.was_called("get_inventory_levels")
        assert mock.was_called("get_purchase_orders")
        assert len(mock.call_history) == 2

    @pytest.mark.asyncio
    async def test_fetch_item_costs(self):
        """Fetch item costs."""
        supply, mock = create_mocked_connector(EBSSupplyConnector)
        mock.responses["get_item_costs"] = {
            "items": [
                {"standard_cost": 5.20, "currency": "USD", "item_id": "FG-001"},
            ],
        }
        raw = await supply.get_item_costs(item_ids=["FG-001"])
        assert len(raw) == 1
        assert raw[0]["standard_cost"] == 5.20
        assert raw[0]["currency"] == "USD"


# =============================================================================
# EBSAuthConnector integration
# =============================================================================


class TestEBSAuthIntegration:
    """Verify EBSAuthConnector (auth server at port 8101)."""

    @pytest.mark.asyncio
    async def test_authenticate(self):
        """EBSAuthConnector authenticates and returns a token."""
        auth, mock = create_mocked_connector(EBSAuthConnector)
        mock.responses["authenticate"] = {
            "token": "session-token-123",
            "user": "admin",
        }

        result = await auth.authenticate()
        assert result["token"] == "session-token-123"
        assert result["user"] == "admin"

    @pytest.mark.asyncio
    async def test_validate_session(self):
        """EBSAuthConnector validates a session token."""
        auth, mock = create_mocked_connector(EBSAuthConnector)
        mock.responses["validate_session"] = {
            "valid": True,
            "user": "admin",
        }

        result = await auth.validate_session("session-token-123")
        assert result["valid"] is True
        assert result["user"] == "admin"

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """EBSAuthConnector refreshes a session token."""
        auth, mock = create_mocked_connector(EBSAuthConnector)
        mock.responses["refresh_token"] = {
            "token": "new-session-token-456",
        }

        result = await auth.refresh_token("session-token-123")
        assert result["token"] == "new-session-token-456"

    @pytest.mark.asyncio
    async def test_get_permissions(self):
        """EBSAuthConnector fetches RBAC permissions."""
        auth, mock = create_mocked_connector(EBSAuthConnector)
        mock.responses["get_permissions"] = {
            "items": [
                {"resource": "inventory", "access": "read"},
                {"resource": "orders", "access": "write"},
            ],
        }

        result = await auth.get_permissions()
        assert len(result) == 2
        assert result[0]["resource"] == "inventory"

    @pytest.mark.asyncio
    async def test_mock_call_history(self):
        """Verify EBSAuthConnector mock records calls."""
        auth, mock = create_mocked_connector(EBSAuthConnector)
        await auth.authenticate()
        assert mock.was_called("authenticate")
        assert len(mock.call_history) == 1


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
        monitor.register("llmwiki", CircuitBreaker("llmwiki"))

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
