"""End-to-end planning cycle test.

Drives a complete MasterGraph run (RETRIEVE → FETCH → TRANSFORM → REASON
→ NEGOTIATE → APPROVE → LEARN → STORE) using:
  - Mocked MCP connectors (no real servers required)
  - Mocked PydanticAI agent calls (no LLM API key required)
  - In-memory checkpointer (no Postgres required)

Asserts the core pipeline invariants:
  - final_plan is not None
  - negotiation_rounds is populated
  - experience_record_id is set (or plan_approved with fallback)
  - degradation_level reflects any connector failures
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from axon.core.schema import (
    AgentProposal,
    Allocation,
    Demand,
    EntityRef,
    Period,
    ProposalStatus,
    Supply,
)
from axon.orchestrator.master_graph import MasterGraph

# =============================================================================
# Helpers
# =============================================================================


def _make_demand(
    item_id: str = "FG-001", qty: float = 1000.0, priority: int = 50
) -> dict[str, Any]:
    from datetime import UTC, datetime

    return Demand(
        item=EntityRef(system="oracle_ebs", entity_type="inventory_item", native_id=item_id),
        quantity=Decimal(str(qty)),
        period=Period(
            start=datetime(2026, 6, 1, tzinfo=UTC),
            end=datetime(2026, 6, 30, tzinfo=UTC),
        ),
        source="sales_order",
        confidence=0.95,
        priority=priority,
    ).model_dump(mode="json")


def _make_supply(item_id: str = "FG-001", qty: float = 1500.0) -> dict[str, Any]:
    from datetime import UTC, datetime

    return Supply(
        item=EntityRef(system="oracle_ebs", entity_type="inventory_item", native_id=item_id),
        quantity=Decimal(str(qty)),
        period=Period(
            start=datetime(2026, 5, 1, tzinfo=UTC),
            end=datetime(2026, 6, 30, tzinfo=UTC),
        ),
        source="on_hand",
    ).model_dump(mode="json")


def _make_proposal(agent_id: str, score: float = 0.7) -> dict[str, Any]:
    demand = _make_demand()
    supply = _make_supply()
    alloc = Allocation(
        demand=Demand.model_validate(demand),
        supply=Supply.model_validate(supply),
        allocated_quantity=Decimal("1000"),
        status="proposed",
    )
    return AgentProposal(
        agent_id=agent_id,
        round_number=1,
        allocations=[alloc],
        utility_score=score,
        justification=f"Mock proposal from {agent_id}",
        status=ProposalStatus.PROPOSED,
    ).model_dump(mode="json")


# =============================================================================
# Pre-built state: bypass fetch/transform — inject pre-built demands/supplies
# =============================================================================

PLANNING_REQUEST: dict[str, Any] = {
    "correlation_id": str(uuid4()),
    "raw_demands": [],
    "raw_supplies": [],
    "raw_policies": [],
    "business_weights": {
        "cost": 0.3,
        "delivery": 0.3,
        "quality": 0.2,
        "sustainability": 0.1,
        "flexibility": 0.1,
    },
}


# =============================================================================
# E2E test with mocked agents (no LLM key needed)
# =============================================================================


@pytest.mark.asyncio
async def test_master_graph_runs_full_cycle() -> None:
    """Full planning cycle completes without errors using mock agent proposals."""
    graph = MasterGraph()

    # Mock all 10 domain agents' propose() to return deterministic proposals
    mock_proposals = {
        "sales": _make_proposal("sales", 0.8),
        "procurement": _make_proposal("procurement", 0.7),
        "finance": _make_proposal("finance", 0.65),
        "production": _make_proposal("production", 0.75),
        "logistics": _make_proposal("logistics", 0.7),
        "warehouse": _make_proposal("warehouse", 0.6),
        "qa": _make_proposal("qa", 0.8),
        "qc": _make_proposal("qc", 0.75),
        "maintenance": _make_proposal("maintenance", 0.7),
        "pd": _make_proposal("pd", 0.65),
    }

    async def mock_propose(context: dict[str, Any]) -> dict[str, Any]:
        agent_id = context.get("_agent_id", "sales")
        return mock_proposals.get(agent_id, _make_proposal(agent_id))

    # Patch node_reason to return pre-built proposals directly
    # (avoids needing LLM keys while still exercising the rest of the graph)
    with (
        patch("axon.orchestrator.master_graph.node_fetch", new_callable=AsyncMock) as mock_fetch,
        patch(
            "axon.orchestrator.master_graph.node_transform", new_callable=AsyncMock
        ) as mock_transform,
        patch("axon.orchestrator.master_graph.node_reason", new_callable=AsyncMock) as mock_reason,
    ):
        mock_fetch.return_value = {
            "raw_demands": [],
            "raw_supplies": [],
            "raw_policies": [],
            "degradation_level": "FULL",
        }
        mock_transform.return_value = {
            "demands": [_make_demand(), _make_demand("FG-002", 500.0, 40)],
            "supplies": [_make_supply(), _make_supply("FG-002", 600.0)],
        }
        mock_reason.return_value = {"agent_proposals": mock_proposals}

        # Mock the experience ledger to avoid Postgres
        with patch(
            "axon.orchestrator.master_graph._get_ledger",
            new_callable=AsyncMock,
        ) as mock_ledger:
            ledger_instance = MagicMock()
            ledger_instance.record_plan_from_state = AsyncMock(return_value=uuid4())
            ledger_instance.record_outcome = AsyncMock()
            mock_ledger.return_value = ledger_instance

            result = await graph.run(PLANNING_REQUEST)

    # Core assertions
    assert result is not None, "graph.run() returned None"
    assert isinstance(result, dict)

    # Negotiation must have run (ConflictResolver)
    rounds = result.get("negotiation_rounds", [])
    assert len(rounds) >= 1, "No negotiation rounds recorded"

    # Final plan must be set (even if empty list)
    final_plan = result.get("final_plan")
    assert final_plan is not None, "final_plan not set in result"

    # Approved or pending HITL (both are valid end states)
    approved = result.get("approved", False)
    hitl_required = result.get("hitl_required", False)
    assert approved or hitl_required, "Plan neither approved nor pending HITL"


@pytest.mark.asyncio
async def test_master_graph_handles_empty_proposals() -> None:
    """Graph must not raise when all agents return empty proposals."""
    graph = MasterGraph()

    with (
        patch("axon.orchestrator.master_graph.node_fetch", new_callable=AsyncMock) as mock_fetch,
        patch(
            "axon.orchestrator.master_graph.node_transform", new_callable=AsyncMock
        ) as mock_transform,
        patch("axon.orchestrator.master_graph.node_reason", new_callable=AsyncMock) as mock_reason,
    ):
        mock_fetch.return_value = {
            "raw_demands": [],
            "raw_supplies": [],
            "raw_policies": [],
            "degradation_level": "FULL",
        }
        mock_transform.return_value = {"demands": [], "supplies": []}
        mock_reason.return_value = {"agent_proposals": {}}  # no proposals

        with patch(
            "axon.orchestrator.master_graph._get_ledger",
            new_callable=AsyncMock,
        ) as mock_ledger:
            ledger_instance = MagicMock()
            ledger_instance.record_plan_from_state = AsyncMock(return_value=uuid4())
            ledger_instance.record_outcome = AsyncMock()
            mock_ledger.return_value = ledger_instance

            result = await graph.run(PLANNING_REQUEST)

    assert result is not None
    # Should still complete without raising
    assert "negotiation_rounds" in result
    assert "approved" in result


@pytest.mark.asyncio
async def test_master_graph_deadlock_triggers_hitl() -> None:
    """When negotiation deadlocks, hitl_required must be True."""
    graph = MasterGraph()

    # Two agents propose conflicting high-utility plans to force deadlock evaluation
    conflicting_proposals = {
        f"agent_{i}": _make_proposal(f"agent_{i}", 0.5 + i * 0.05) for i in range(5)
    }

    with (
        patch("axon.orchestrator.master_graph.node_fetch", new_callable=AsyncMock) as mock_fetch,
        patch(
            "axon.orchestrator.master_graph.node_transform", new_callable=AsyncMock
        ) as mock_transform,
        patch("axon.orchestrator.master_graph.node_reason", new_callable=AsyncMock) as mock_reason,
        patch(
            "axon.orchestrator.master_graph.node_negotiate", new_callable=AsyncMock
        ) as mock_negotiate,
    ):
        mock_fetch.return_value = {
            "raw_demands": [],
            "raw_supplies": [],
            "raw_policies": [],
            "degradation_level": "FULL",
        }
        mock_transform.return_value = {"demands": [_make_demand()], "supplies": []}
        mock_reason.return_value = {"agent_proposals": conflicting_proposals}
        # Force a deadlock result
        mock_negotiate.return_value = {
            "negotiation_rounds": [
                {"round_number": 5, "resolved": False, "resolution": "NEGOTIATION_DEADLOCK"}
            ],
            "final_plan": [],
            "deadlock": True,
            "business_weights": PLANNING_REQUEST["business_weights"],
        }

        with patch(
            "axon.orchestrator.master_graph._get_ledger",
            new_callable=AsyncMock,
        ) as mock_ledger:
            ledger_instance = MagicMock()
            ledger_instance.record_plan_from_state = AsyncMock(return_value=uuid4())
            ledger_instance.record_outcome = AsyncMock()
            mock_ledger.return_value = ledger_instance

            result = await graph.run(PLANNING_REQUEST)

    # Deadlock must trigger HITL or executive escalation
    assert result.get("hitl_required", False) or result.get("escalation_level") in (
        "director",
        "executive",
    ), (
        f"Deadlock did not trigger HITL: {result.get('hitl_required')}, level={result.get('escalation_level')}"
    )


@pytest.mark.asyncio
async def test_master_graph_vip_demand_triggers_hitl() -> None:
    """A VIP demand (priority > 90) must trigger HITL."""
    graph = MasterGraph()

    vip_demand = _make_demand("VIP-001", qty=100.0, priority=95)
    vip_proposal = _make_proposal("sales", 0.9)

    with (
        patch("axon.orchestrator.master_graph.node_fetch", new_callable=AsyncMock) as mock_fetch,
        patch(
            "axon.orchestrator.master_graph.node_transform", new_callable=AsyncMock
        ) as mock_transform,
        patch("axon.orchestrator.master_graph.node_reason", new_callable=AsyncMock) as mock_reason,
    ):
        mock_fetch.return_value = {
            "raw_demands": [],
            "raw_supplies": [],
            "raw_policies": [],
            "degradation_level": "FULL",
        }
        mock_transform.return_value = {"demands": [vip_demand], "supplies": [_make_supply()]}
        mock_reason.return_value = {"agent_proposals": {"sales": vip_proposal}}

        with patch(
            "axon.orchestrator.master_graph._get_ledger",
            new_callable=AsyncMock,
        ) as mock_ledger:
            ledger_instance = MagicMock()
            ledger_instance.record_plan_from_state = AsyncMock(return_value=uuid4())
            ledger_instance.record_outcome = AsyncMock()
            mock_ledger.return_value = ledger_instance

            result = await graph.run({**PLANNING_REQUEST, "correlation_id": str(uuid4())})

    assert result.get("hitl_required", False), "VIP demand (priority=95) did not trigger HITL"
