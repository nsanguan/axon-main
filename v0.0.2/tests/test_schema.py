"""Unit tests for Axon Core Schema models, configuration, and tools.

Phase 1.6 — Testing Foundation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

import pytest
from pydantic import ValidationError

from axon.agents.tools import get_tools_for_agent
from axon.core.config import MCPServerConfig
from axon.core.schema import (
    AgentProposal,
    Allocation,
    Demand,
    EntityRef,
    MCPToolOutput,
    NegotiationRound,
    Period,
    SemanticTransformer,
    Supply,
)

# =============================================================================
# Test fixtures
# =============================================================================


@pytest.fixture
def sample_period() -> Period:
    return Period(
        start=datetime(2026, 6, 1, tzinfo=UTC),
        end=datetime(2026, 6, 30, tzinfo=UTC),
        granularity="month",
    )


@pytest.fixture
def sample_item() -> EntityRef:
    return EntityRef(
        system="oracle_ebs",
        entity_type="finished_good",
        native_id="FG-001",
        display_name="Aircraft Bolt AN4-10A",
    )


@pytest.fixture
def sample_demand(sample_period, sample_item) -> Demand:
    return Demand(
        item=sample_item,
        quantity=Decimal("5000"),
        period=sample_period,
        source="sales_order",
        confidence=0.95,
        priority=90,
    )


@pytest.fixture
def sample_supply(sample_period, sample_item) -> Supply:
    return Supply(
        item=sample_item,
        quantity=Decimal("3000"),
        period=sample_period,
        source="on_hand",
        lead_time_days=0,
    )


@pytest.fixture
def sample_allocation(sample_demand, sample_supply) -> Allocation:
    return Allocation(
        demand=sample_demand,
        supply=sample_supply,
        allocated_quantity=Decimal("3000"),
    )


# =============================================================================
# Schema round-trip tests
# =============================================================================


class TestDemand:
    def test_create_valid(self, sample_demand):
        assert sample_demand.quantity == Decimal("5000")
        assert sample_demand.confidence == 0.95
        assert sample_demand.priority == 90
        assert isinstance(sample_demand.id, UUID)

    def test_confidence_bounds(self, sample_period, sample_item):
        # Valid bounds
        Demand(
            item=sample_item,
            quantity=Decimal("100"),
            period=sample_period,
            source="forecast",
            confidence=0.0,
        )
        Demand(
            item=sample_item,
            quantity=Decimal("100"),
            period=sample_period,
            source="forecast",
            confidence=1.0,
        )

    def test_confidence_out_of_bounds(self, sample_period, sample_item):
        with pytest.raises(ValidationError):
            Demand(
                item=sample_item,
                quantity=Decimal("100"),
                period=sample_period,
                source="forecast",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            Demand(
                item=sample_item,
                quantity=Decimal("100"),
                period=sample_period,
                source="forecast",
                confidence=-0.1,
            )

    def test_serialize_deserialize(self, sample_demand):
        data = sample_demand.model_dump(mode="json")
        # JSON serializes UUID and Decimal as strings
        assert data["quantity"] == "5000"
        assert "id" in data
        # Round-trip
        restored = Demand.model_validate(data)
        assert restored.quantity == Decimal("5000")
        assert restored.priority == 90


class TestSupply:
    def test_create_valid(self, sample_supply):
        assert sample_supply.source == "on_hand"
        assert sample_supply.lead_time_days == 0

    def test_defaults(self, sample_period, sample_item):
        supply = Supply(
            item=sample_item,
            quantity=Decimal("100"),
            period=sample_period,
            source="planned",
        )
        assert supply.lead_time_days == 0
        assert supply.metadata == {}
        assert isinstance(supply.id, UUID)


class TestAllocation:
    def test_create_valid(self, sample_allocation, sample_demand, sample_supply):
        assert sample_allocation.allocated_quantity == Decimal("3000")
        assert sample_allocation.status == "proposed"
        assert sample_allocation.demand.id == sample_demand.id
        assert sample_allocation.supply.id == sample_supply.id

    def test_allocation_exceeds_supply(self, sample_demand, sample_supply):
        # Should NOT raise at model level — this is a business rule enforced by orchestrator
        alloc = Allocation(
            demand=sample_demand,
            supply=sample_supply,
            allocated_quantity=Decimal("9999"),  # exceeds supply of 3000
        )
        assert alloc.allocated_quantity == Decimal("9999")


class TestAgentProposal:
    def test_create_valid(self, sample_allocation):
        proposal = AgentProposal(
            agent_id="sales",
            round_number=1,
            allocations=[sample_allocation],
            utility_score=0.82,
            justification="Boeing VIP order",
        )
        assert proposal.agent_id == "sales"
        assert proposal.status == "proposed"
        assert len(proposal.amendments) == 0

    def test_amendments(self):
        proposal = AgentProposal(
            agent_id="production",
            round_number=2,
            allocations=[],
            amendments=["Shift WIP-10234 to 6/20"],
        )
        assert len(proposal.amendments) == 1


class TestNegotiationRound:
    def test_create_valid(self):
        round_ = NegotiationRound(
            round_number=1,
            proposals={},
            global_utility=0.72,
            resolved=False,
        )
        assert round_.round_number == 1
        assert not round_.resolved

    def test_resolved_round(self):
        round_ = NegotiationRound(
            round_number=3,
            proposals={},
            global_utility=0.95,
            resolved=True,
            resolution="Utility auction awarded to Production",
        )
        assert round_.resolved
        assert round_.resolution is not None


# =============================================================================
# SemanticTransformer tests
# =============================================================================


class TestSemanticTransformer:
    def test_can_handle_match(self):
        class OracleTx(SemanticTransformer):
            source_system: ClassVar[str] = "oracle_ebs"
            supported_tools: ClassVar[list[str]] = ["get_inventory_levels", "list_wip_jobs"]

        tx = OracleTx()
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="get_inventory_levels",
            raw_payload={"items": []},
        )
        assert tx.can_handle(output) is True

    def test_can_handle_wrong_server(self):
        class OracleTx(SemanticTransformer):
            source_system: ClassVar[str] = "oracle_ebs"
            supported_tools: ClassVar[list[str]] = ["get_inventory_levels"]

        tx = OracleTx()
        output = MCPToolOutput(
            server_name="sap",
            tool_name="get_inventory_levels",
            raw_payload={},
        )
        assert tx.can_handle(output) is False

    def test_can_handle_wrong_tool(self):
        class OracleTx(SemanticTransformer):
            source_system: ClassVar[str] = "oracle_ebs"
            supported_tools: ClassVar[list[str]] = ["get_inventory_levels"]

        tx = OracleTx()
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="list_wip_jobs",
            raw_payload={},
        )
        assert tx.can_handle(output) is False

    def test_can_handle_empty_tools(self):
        class EmptyTx(SemanticTransformer):
            source_system: ClassVar[str] = "oracle_ebs"
            supported_tools: ClassVar[list[str]] = []

        tx = EmptyTx()
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="anything",
            raw_payload={},
        )
        assert tx.can_handle(output) is False


# =============================================================================
# MCPToolOutput tests
# =============================================================================


class TestMCPToolOutput:
    def test_create(self):
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="get_inventory_levels",
            raw_payload={"items": [{"id": 1, "qty": 100}]},
        )
        assert output.server_name == "oracle_ebs"
        assert isinstance(output.correlation_id, UUID)
        assert isinstance(output.fetched_at, datetime)

    def test_extra_fields_allowed(self):
        output = MCPToolOutput(
            server_name="oracle_ebs",
            tool_name="test",
            raw_payload={},
            extra_field="should be allowed",
        )
        assert output.extra_field == "should be allowed"


# =============================================================================
# Configuration tests
# =============================================================================


class TestConfig:
    def test_mcp_server_config_defaults(self):
        cfg = MCPServerConfig()
        assert cfg.timeout_seconds == 30
        assert cfg.max_retries == 3
        assert cfg.enabled is True

    def test_settings_singleton(self):
        from axon.core.config import settings

        assert settings.database.url.startswith("postgresql+asyncpg://")
        assert settings.agent_defaults.negotiation_rounds == 5
        assert settings.agent_defaults.max_retries == 3

    def test_mcp_servers_exist(self):
        from axon.core.config import settings

        assert settings.mcp_oracle_ebs is not None
        assert settings.mcp_sap is not None
        assert settings.mcp_odoo is not None
        assert settings.mcp_external_rag is not None
        assert settings.mcp_postgresql is not None


# =============================================================================
# Tool catalog tests
# =============================================================================


class TestToolCatalog:
    def test_all_agents_have_tools(self):
        all_agents = [
            "sales",
            "production",
            "procurement",
            "warehouse",
            "logistics",
            "finance",
            "qa",
            "qc",
            "pd",
            "maintenance",
        ]
        for agent_id in all_agents:
            tools = get_tools_for_agent(agent_id)
            assert len(tools) > 0, f"{agent_id} has no tools assigned"

    def test_tool_direction_field(self):
        from axon.agents.tools import TOOL_CATALOG

        for tool in TOOL_CATALOG:
            assert tool.direction in ("READ", "WRITE"), (
                f"{tool.name} has invalid direction: {tool.direction}"
            )

    def test_get_tools_for_unknown_agent(self):
        tools = get_tools_for_agent("nonexistent")
        assert tools == []

    def test_shared_tools_multi_agent(self):
        tools = get_tools_for_agent("sales")
        names = {t.name for t in tools}
        assert "get_inventory_levels" in names
        assert "get_available_to_promise" in names


# =============================================================================
# Circuit breaker state machine tests
# =============================================================================


class CircuitBreaker:
    """Minimal circuit breaker for testing state transitions."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time: datetime | None = None

    def record_failure(self) -> str:
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        if (
            self.state == "CLOSED"
            and self.failure_count >= self.failure_threshold
            or self.state == "HALF_OPEN"
        ):
            self.state = "OPEN"
        return self.state

    def record_success(self) -> str:
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = 0
        return self.state

    def try_half_open(self) -> str:
        if self.state == "OPEN":
            self.state = "HALF_OPEN"
        return self.state


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_closed_to_open(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        cb.record_failure()  # 3rd failure
        assert cb.state == "OPEN"

    def test_open_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == "OPEN"
        cb.try_half_open()
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # → OPEN
        cb.try_half_open()  # → HALF_OPEN
        cb.record_success()  # → CLOSED
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # → OPEN
        cb.try_half_open()  # → HALF_OPEN
        cb.record_failure()  # → OPEN again
        assert cb.state == "OPEN"

    def test_closed_success_resets_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0


# =============================================================================
# EntityRef tests
# =============================================================================


class TestEntityRef:
    def test_create(self):
        ref = EntityRef(
            system="oracle_ebs",
            entity_type="inventory_item",
            native_id="ITEM-001",
            display_name=None,
        )
        assert ref.system == "oracle_ebs"
        assert ref.display_name is None

    def test_with_display_name(self):
        ref = EntityRef(
            system="sap",
            entity_type="production_order",
            native_id="PO-12345",
            display_name="Order #12345",
        )
        assert ref.display_name == "Order #12345"
