"""Phase 4 tests — Experience Ledger schema, embedder, HITL logic, dashboard API."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from axon.core.learning.embedder import TagBasedEmbedder
from axon.core.learning.schema import (
    ExperienceRecord,
    LedgerQuery,
    PlanContext,
    PlanOutcome,
    PlanTrace,
    SimilarPlanResult,
)

# =============================================================================
# PlanTrace tests
# =============================================================================


class TestPlanTrace:
    def test_create_valid(self) -> None:
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="violation_detected",
            agent_id="sales",
            confidence=0.85,
            duration_ms=1200,
        )
        assert trace.step_sequence == 1
        assert trace.trigger_event == "violation_detected"
        assert trace.agent_id == "sales"
        assert trace.confidence == 0.85
        assert trace.duration_ms == 1200
        assert trace.logic_version is None

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="test",
                agent_id="test",
                confidence=1.5,  # Out of bounds
            )
        with pytest.raises(ValidationError):
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="test",
                agent_id="test",
                confidence=-0.1,
            )

    def test_trace_defaults(self) -> None:
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="demand_spike",
            agent_id="procurement",
        )
        assert trace.confidence == 0.0
        assert trace.duration_ms == 0
        assert trace.input_snapshot == {}
        assert trace.output_snapshot == {}

    def test_serialize_roundtrip(self) -> None:
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="supply_shortage",
            agent_id="warehouse",
            confidence=0.75,
            duration_ms=800,
            model_used="claude-sonnet-4",
        )
        data = trace.model_dump(mode="json")
        restored = PlanTrace.model_validate(data)
        assert restored.confidence == 0.75
        assert restored.duration_ms == 800
        assert restored.model_used == "claude-sonnet-4"


# =============================================================================
# PlanContext tests
# =============================================================================


class TestPlanContext:
    def test_create_empty(self) -> None:
        ctx = PlanContext()
        assert ctx.demands == []
        assert ctx.supplies == []
        assert ctx.business_weights == {}
        assert ctx.degradation_level == "FULL"

    def test_create_with_data(self) -> None:
        ctx = PlanContext(
            demands=[{"item_id": "FG-001", "quantity": 100}],
            supplies=[{"item_id": "FG-001", "quantity": 200}],
            business_weights={"cost": 0.3, "delivery": 0.3},
            degradation_level="DEGRADED",
            correlation_id="abc-123",
        )
        assert len(ctx.demands) == 1
        assert len(ctx.supplies) == 1
        assert ctx.business_weights["cost"] == 0.3
        assert ctx.degradation_level == "DEGRADED"
        assert ctx.correlation_id == "abc-123"


# =============================================================================
# PlanOutcome tests
# =============================================================================


class TestPlanOutcome:
    def test_create_valid(self) -> None:
        outcome = PlanOutcome(
            on_time=True,
            on_budget=True,
            total_demand_fulfilled_pct=95.0,
            actual_cost=125000.0,
        )
        assert outcome.on_time is True
        assert outcome.total_demand_fulfilled_pct == 95.0

    def test_fulfilled_pct_bounds(self) -> None:
        with pytest.raises(ValidationError):
            PlanOutcome(total_demand_fulfilled_pct=101.0)
        with pytest.raises(ValidationError):
            PlanOutcome(total_demand_fulfilled_pct=-1.0)

    def test_defaults(self) -> None:
        outcome = PlanOutcome()
        assert outcome.on_time is None
        assert outcome.days_late == 0
        assert outcome.replan_triggered is False


# =============================================================================
# ExperienceRecord tests
# =============================================================================


class TestExperienceRecord:
    def test_create_valid(self) -> None:
        record = ExperienceRecord(
            plan_id=uuid4(),
            correlation_id="test-001",
            tags=["on_time", "reference"],
            plan_confidence=0.85,
        )
        assert record.plan_confidence == 0.85
        assert len(record.tags) == 2
        assert "reference" in record.tags

    def test_auto_plan_id(self) -> None:
        record = ExperienceRecord()
        assert isinstance(record.plan_id, UUID)

    def test_plan_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ExperienceRecord(plan_confidence=1.5)
        with pytest.raises(ValidationError):
            ExperienceRecord(plan_confidence=-0.1)

    def test_accepts_nested_context(self) -> None:
        ctx = PlanContext(demands=[{"item": "FG-001"}])
        record = ExperienceRecord(
            plan_id=uuid4(),
            context=ctx,
            tags=["test"],
        )
        assert record.context.demands[0]["item"] == "FG-001"

    def test_serialize_roundtrip(self) -> None:
        original = ExperienceRecord(
            plan_id=uuid4(),
            correlation_id="rt-test",
            tags=["on_time", "reference"],
            plan_confidence=0.92,
            outcome=PlanOutcome(
                on_time=True,
                total_demand_fulfilled_pct=98.5,
            ),
        )
        data = original.model_dump(mode="json")
        restored = ExperienceRecord.model_validate(data)
        assert restored.plan_id == original.plan_id
        assert restored.tags == original.tags
        assert restored.plan_confidence == original.plan_confidence
        assert restored.outcome is not None
        assert restored.outcome.on_time is True


# =============================================================================
# LedgerQuery tests
# =============================================================================


class TestLedgerQuery:
    def test_defaults(self) -> None:
        q = LedgerQuery()
        assert q.limit == 20
        assert q.offset == 0
        assert q.include_outcomes is False

    def test_custom(self) -> None:
        q = LedgerQuery(
            tags=["reference"],
            limit=5,
            offset=10,
            include_outcomes=True,
        )
        assert q.tags == ["reference"]
        assert q.limit == 5
        assert q.offset == 10


# =============================================================================
# SimilarPlanResult tests
# =============================================================================


class TestSimilarPlanResult:
    def test_create(self) -> None:
        plan = ExperienceRecord()
        result = SimilarPlanResult(
            plan=plan,
            similarity_score=0.85,
            match_reasons=["tag_match", "embedding_similarity"],
        )
        assert result.similarity_score == 0.85
        assert len(result.match_reasons) == 2

    def test_score_bounds(self) -> None:
        plan = ExperienceRecord()
        with pytest.raises(ValidationError):
            SimilarPlanResult(plan=plan, similarity_score=1.5)
        with pytest.raises(ValidationError):
            SimilarPlanResult(plan=plan, similarity_score=-0.1)


# =============================================================================
# TagBasedEmbedder tests
# =============================================================================


class TestTagBasedEmbedder:
    @pytest.mark.asyncio
    async def test_embed_record(self) -> None:
        embedder = TagBasedEmbedder(dimensions=384)
        record = ExperienceRecord(
            tags=["on_time", "reference", "item:FG-001"],
        )
        vector = await embedder.embed(record)
        assert vector is not None
        assert len(vector) == 384
        # Should have some non-zero dimensions
        assert any(v != 0.0 for v in vector)

    @pytest.mark.asyncio
    async def test_embed_query(self) -> None:
        embedder = TagBasedEmbedder()
        vector = await embedder.embed_query({"items": [{"item_id": "FG-001"}], "priority": 90})
        assert vector is not None
        assert len(vector) == 384

    @pytest.mark.asyncio
    async def test_embed_empty_query(self) -> None:
        embedder = TagBasedEmbedder()
        vector = await embedder.embed_query({})
        assert vector is None  # No features to hash

    @pytest.mark.asyncio
    async def test_deterministic_output(self) -> None:
        """Same input should produce the same vector."""
        embedder = TagBasedEmbedder()
        record = ExperienceRecord(tags=["test"])
        v1 = await embedder.embed(record)
        v2 = await embedder.embed(record)
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_different_features_different_vectors(self) -> None:
        """Different input should produce different vectors."""
        embedder = TagBasedEmbedder()
        r1 = ExperienceRecord(tags=["cost_focused"])
        r2 = ExperienceRecord(tags=["delivery_focused"])
        v1 = await embedder.embed(r1)
        v2 = await embedder.embed(r2)
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_vector_dimension(self) -> None:
        """Default dimension should be 384 for pgvector compatibility."""
        embedder = TagBasedEmbedder()
        record = ExperienceRecord(tags=["test"])
        vector = await embedder.embed(record)
        assert len(vector) == 384


# =============================================================================
# Master Graph HITL logic tests
# =============================================================================


class TestHITLNeedsApproval:
    """Test the _needs_hitl decision logic."""

    def _needs_hitl(self, deadlock=False, demands=None, rounds=None, traces=None):
        """Replicate the logic from master_graph for testing."""
        from axon.orchestrator.master_graph import _needs_hitl

        return _needs_hitl(
            deadlock=deadlock,
            demands=demands or [],
            negotiation_rounds=rounds or [],
            traces=traces or [],
        )

    def test_deadlock_requires_hitl(self) -> None:
        assert self._needs_hitl(deadlock=True) is True

    def test_normal_plan_auto_approves(self) -> None:
        assert (
            self._needs_hitl(
                demands=[{"priority": 50}],
                rounds=[{"resolution": "No conflicts detected"}],
            )
            is False
        )

    def test_vip_demand_requires_hitl(self) -> None:
        assert (
            self._needs_hitl(
                demands=[{"priority": 95}],
            )
            is True
        )

    def test_many_conflicts_requires_hitl(self) -> None:
        rounds = [
            {"resolution": "Conflict resolved via auction"},
            {"resolution": "Conflict resolved via auction"},
            {"resolution": "Conflict resolved via auction"},
        ]
        assert self._needs_hitl(rounds=rounds) is True

    def test_low_confidence_requires_hitl(self) -> None:
        traces = [
            {"confidence": 0.3},
            {"confidence": 0.4},
        ]
        assert self._needs_hitl(traces=traces) is True

    def test_high_confidence_auto_approves(self) -> None:
        traces = [
            {"confidence": 0.8},
            {"confidence": 0.9},
            {"confidence": 0.7},
        ]
        assert self._needs_hitl(traces=traces) is False

    def test_vip_demand_no_shortage_auto_approves(self) -> None:
        # Low priority = auto-approve
        assert self._needs_hitl(demands=[{"priority": 50}]) is False
        # Borderline priority 90
        assert self._needs_hitl(demands=[{"priority": 90}]) is False
        # Over threshold
        assert self._needs_hitl(demands=[{"priority": 91}]) is True
        # No demands
        assert self._needs_hitl(demands=[]) is False


# =============================================================================
# Dashboard API tests (using FastAPI TestClient)
# =============================================================================


@pytest.fixture
def client():  # type: ignore[no-untyped-def]
    """Create a FastAPI TestClient for the dashboard app."""
    from fastapi.testclient import TestClient

    from axon.dashboard.backend.app import create_app

    app = create_app()
    return TestClient(app)


class TestDashboardAPI:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_get_weights(self, client):
        resp = client.get("/api/weights")
        assert resp.status_code == 200
        data = resp.json()
        assert "weights" in data
        weights = data["weights"]
        assert "cost" in weights
        assert "delivery" in weights
        assert "quality" in weights
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_update_weights(self, client):
        resp = client.put("/api/weights", json={"cost": 0.5, "delivery": 0.2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["weights"]["cost"] == 0.5
        assert data["weights"]["delivery"] == 0.2

    def test_reset_weights(self, client):
        resp = client.get("/api/weights/defaults")
        assert resp.status_code == 200
        data = resp.json()
        weights = data["weights"]
        assert weights["cost"] == 0.3
        assert weights["delivery"] == 0.3

    def test_list_agents(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) > 0
        agent_ids = {a["agent_id"] for a in agents}
        assert "sales" in agent_ids
        assert "production" in agent_ids
        assert "finance" in agent_ids

    def test_list_tools(self, client):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert data["total"] > 0
        tool_names = {t["name"] for t in data["tools"]}
        assert "get_inventory_levels" in tool_names

    def test_approval_config(self, client):
        resp = client.get("/api/approvals/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_approval_for_deadlock"] is True
        assert "max_rounds_before_deadlock" in data

    def test_pending_approvals_empty(self, client):
        resp = client.get("/api/approvals/pending")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_approve_nonexistent(self, client):
        resp = client.post(
            "/api/approvals/action",
            json={
                "plan_id": "00000000-0000-0000-0000-000000000000",
                "approved": True,
                "note": "Test approve",
            },
        )
        assert resp.status_code == 404

    def test_business_weights_validation(self, client):
        """Verify weights are accepted and round-tripped correctly."""
        resp = client.put(
            "/api/weights",
            json={
                "cost": 0.25,
                "delivery": 0.25,
                "quality": 0.25,
                "sustainability": 0.125,
                "flexibility": 0.125,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        total = sum(data["weights"].values())
        assert abs(total - 1.0) < 0.001
