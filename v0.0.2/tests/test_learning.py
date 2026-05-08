"""Unit tests for the Experience Ledger — models, persistence, and HITL logic.

Phase 4 — Learning Loop & Executive Control.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from axon.core.learning.embedder import TagBasedEmbedder
from axon.core.learning.models import (
    ExperienceRecord,
    PlanContext,
    PlanOutcome,
    PlanTrace,
    compute_plan_confidence,
)
from axon.orchestrator.master_graph import _needs_hitl

# =============================================================================
# Model Tests
# =============================================================================


class TestPlanContext:
    def test_create(self):
        ctx = PlanContext(
            demands=[{"item": "FG-001", "qty": 500}],
            supplies=[{"item": "RM-001", "qty": 1000}],
            correlation_id="test-123",
        )
        assert len(ctx.demands) == 1
        assert ctx.correlation_id == "test-123"
        assert ctx.degradation_level == "FULL"

    def test_defaults(self):
        ctx = PlanContext()
        assert ctx.demands == []
        assert ctx.business_weights == {}


class TestPlanOutcome:
    def test_create(self):
        outcome = PlanOutcome(
            on_time=True,
            quality_score=0.95,
            notes="All good",
        )
        assert outcome.on_time is True
        assert outcome.quality_score == 0.95
        assert outcome.over_budget is False

    def test_quality_bounds(self):
        with pytest.raises(ValueError):
            PlanOutcome(quality_score=1.5)
        with pytest.raises(ValueError):
            PlanOutcome(quality_score=-0.1)


class TestPlanTrace:
    def test_create(self):
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="demand_spike",
            agent_id="sales",
            logic_version="planning_v2.3",
            confidence=0.85,
            duration_ms=1200,
            model_used="claude-sonnet-4",
        )
        assert trace.step_sequence == 1
        assert trace.trigger_event == "demand_spike"
        assert trace.confidence == 0.85

    def test_defaults(self):
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="test",
            agent_id="test",
        )
        assert trace.confidence == 0.5
        assert trace.duration_ms == 0
        assert trace.logic_version == ""


class TestExperienceRecord:
    def test_create_minimal(self):
        record = ExperienceRecord()
        assert isinstance(record.id, UUID)
        assert isinstance(record.plan_id, UUID)
        assert record.tags == []
        assert record.warm_archived is False

    def test_create_with_data(self):
        trace = PlanTrace(
            decision_id=uuid4(),
            step_sequence=1,
            trigger_event="test",
            agent_id="sales",
        )
        record = ExperienceRecord(
            plan_id=uuid4(),
            context=PlanContext(correlation_id="abc"),
            tags=["high_confidence", "on_time"],
            traces=[trace],
            plan_confidence=0.85,
        )
        assert "high_confidence" in record.tags
        assert record.plan_confidence == 0.85
        assert len(record.traces) == 1

    def test_round_trip_json(self):
        record = ExperienceRecord(
            plan_id=uuid4(),
            context=PlanContext(
                demands=[{"item": "FG-001"}],
                business_weights={"cost": 0.3, "delivery": 0.3},
            ),
            tags=["test"],
            plan_confidence=0.75,
        )
        data = record.model_dump(mode="json")
        restored = ExperienceRecord.model_validate(data)
        assert restored.plan_id == record.plan_id
        assert restored.plan_confidence == 0.75
        assert restored.tags == ["test"]
        assert restored.context.demands == [{"item": "FG-001"}]


# =============================================================================
# Plan Confidence Tests
# =============================================================================


class TestComputePlanConfidence:
    def test_no_traces(self):
        confidence = compute_plan_confidence([])
        assert confidence == 0.5

    def test_single_trace(self):
        traces = [
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="test",
                agent_id="a",
                confidence=0.9,
            )
        ]
        confidence = compute_plan_confidence(traces)
        assert confidence == 0.9  # 0.9 × 1.0

    def test_multiple_traces(self):
        traces = [
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="t1",
                agent_id="a",
                confidence=0.9,
            ),
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=2,
                trigger_event="t2",
                agent_id="b",
                confidence=0.7,
            ),
        ]
        confidence = compute_plan_confidence(traces)
        assert confidence == 0.8  # (0.9 + 0.7) / 2 × 1.0

    def test_deadlock_factor(self):
        traces = [
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="t1",
                agent_id="a",
                confidence=0.9,
            ),
        ]
        confidence = compute_plan_confidence(traces, negotiation_resolution_factor=0.7)
        assert confidence == 0.63  # 0.9 × 0.7

    def test_hitl_override_factor(self):
        traces = [
            PlanTrace(
                decision_id=uuid4(),
                step_sequence=1,
                trigger_event="t1",
                agent_id="a",
                confidence=0.8,
            ),
        ]
        confidence = compute_plan_confidence(traces, negotiation_resolution_factor=0.5)
        assert confidence == 0.4  # 0.8 × 0.5


# =============================================================================
# Experience Ledger Unit Tests (DB-independent)
# =============================================================================


class TestTagBasedEmbedder:
    """Tests the TagBasedEmbedder used by the Experience Ledger."""

    async def test_embed_produces_correct_dimensions(self):
        """Embedding produces a vector of the expected dimension."""
        embedder = TagBasedEmbedder(dimensions=384)
        record = ExperienceRecord(
            plan_id=uuid4(),
            tags=["on_time", "high_confidence"],
            outcome=PlanOutcome(on_time=True),
        )
        vector = await embedder.embed(record)
        assert len(vector) == 384

    async def test_embed_query_returns_vector(self):
        """Query embedding produces a vector from context."""
        embedder = TagBasedEmbedder(dimensions=384)
        context = {"items": [{"item_id": "FG-001", "source": "sales_order"}], "priority": "high"}
        vector = await embedder.embed_query(context)
        assert vector is not None
        assert len(vector) == 384

    async def test_embed_query_empty_returns_none(self):
        """Empty query context returns None."""
        embedder = TagBasedEmbedder()
        vector = await embedder.embed_query({})
        assert vector is None

    async def test_similar_records_have_similar_embeddings(self):
        """Records with similar tags/context should have similar vectors.

        Uses cosine similarity: similar tag sets → correlated hash vectors.
        """
        embedder = TagBasedEmbedder()
        record_a = ExperienceRecord(plan_id=uuid4(), tags=["on_time", "high_confidence", "sales"])
        record_b = ExperienceRecord(plan_id=uuid4(), tags=["on_time", "high_confidence", "sales"])
        record_c = ExperienceRecord(plan_id=uuid4(), tags=["over_budget", "replan", "maintenance"])

        emb_a = await embedder.embed(record_a)
        emb_b = await embedder.embed(record_b)
        emb_c = await embedder.embed(record_c)

        # Cosine similarity: A·B should be higher than A·C
        def cosine_sim(v1, v2):
            dot = sum(a * b for a, b in zip(v1, v2, strict=False))
            n1 = sum(a * a for a in v1) ** 0.5
            n2 = sum(b * b for b in v2) ** 0.5
            return dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0

        sim_ab = cosine_sim(emb_a, emb_b)
        sim_ac = cosine_sim(emb_a, emb_c)
        assert sim_ab > sim_ac, f"Expected {sim_ab} > {sim_ac}"


# =============================================================================
# HITL Decision Logic Tests
# =============================================================================


class TestHITLNeeds:
    """Tests the _needs_hitl decision logic."""

    def test_no_hitl_for_simple_plan(self):
        """A straightforward plan with no deadlock, no VIP, few conflicts."""
        result = _needs_hitl(
            deadlock=False,
            demands=[{"priority": 50}],
            negotiation_rounds=[],
            traces=[],
        )
        assert result is False

    def test_hitl_for_deadlock(self):
        """Deadlock always requires HITL."""
        result = _needs_hitl(
            deadlock=True,
            demands=[],
            negotiation_rounds=[],
            traces=[],
        )
        assert result is True

    def test_hitl_for_vip_demand(self):
        """VIP demand (> 90 priority) requires HITL."""
        result = _needs_hitl(
            deadlock=False,
            demands=[{"priority": 95}],
            negotiation_rounds=[],
            traces=[],
        )
        assert result is True

    def test_no_hitl_for_high_but_not_vip(self):
        """High priority (80) but not VIP threshold (90) — no HITL."""
        result = _needs_hitl(
            deadlock=False,
            demands=[{"priority": 80}],
            negotiation_rounds=[],
            traces=[],
        )
        assert result is False

    def test_hitl_for_many_conflicts(self):
        """More than 2 conflict rounds triggers HITL."""
        rounds = [
            {"resolution": "Conflict round 1"},
            {"resolution": "Conflict round 2"},
            {"resolution": "Conflict round 3"},
        ]
        result = _needs_hitl(
            deadlock=False,
            demands=[],
            negotiation_rounds=rounds,
            traces=[],
        )
        assert result is True

    def test_hitl_for_low_confidence(self):
        """Average trace confidence below 0.5 triggers HITL."""
        traces = [
            {"confidence": 0.4},
            {"confidence": 0.3},
        ]
        result = _needs_hitl(
            deadlock=False,
            demands=[],
            negotiation_rounds=[],
            traces=traces,
        )
        assert result is True

    def test_no_hitl_for_acceptable_confidence(self):
        """Trace confidence >= 0.5 does not trigger HITL on confidence alone."""
        traces = [
            {"confidence": 0.7},
            {"confidence": 0.6},
        ]
        result = _needs_hitl(
            deadlock=False,
            demands=[],
            negotiation_rounds=[],
            traces=traces,
        )
        assert result is False


# =============================================================================
# Migration SQL Validation
# =============================================================================


class TestMigrationSchema:
    """Validates the migration SQL creates expected tables and columns."""

    def test_experience_records_has_correlation_id(self):
        """The migration SQL includes correlation_id column."""
        from axon.core.schema.migrate import SCHEMA_SQL

        assert "correlation_id" in SCHEMA_SQL

    def test_experience_records_has_embedding(self):
        """The migration SQL includes embedding vector column."""
        from axon.core.schema.migrate import SCHEMA_SQL

        assert "embedding" in SCHEMA_SQL
        assert "VECTOR" in SCHEMA_SQL

    def test_plan_traces_table_exists(self):
        """The migration SQL creates plan_traces table."""
        from axon.core.schema.migrate import SCHEMA_SQL

        assert "plan_traces" in SCHEMA_SQL

    def test_retention_indexes(self):
        """The migration creates indexes for plan_traces queries."""
        from axon.core.schema.migrate import SCHEMA_SQL

        assert "idx_traces_decision" in SCHEMA_SQL
