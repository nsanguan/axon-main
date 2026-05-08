"""Tests for LangGraph short-term and long-term memory integration.

Covers:
  - PostgresStore unit tests (long-term memory)
  - MasterGraph memory node behavior (retrieve_context, store_insights)
  - Full MasterGraph compilation with store
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from axon.core.memory import PostgresStore
from axon.orchestrator.master_graph import (
    MasterGraph,
    node_retrieve_context,
    node_store_insights,
)

# =============================================================================
# PostgresStore — Long-term Memory Tests
# =============================================================================


class TestPostgresStoreConstruction:
    """Tests for PostgresStore construction and setup."""

    def test_constructor(self):
        """PostgresStore can be constructed with no arguments."""
        store = PostgresStore()
        assert store._pool is None
        assert store._own_pool is True

    @pytest.mark.asyncio
    async def test_from_conn_string_fails_without_server(self):
        """from_conn_string raises OSError without a live DB.

        Expected to fail in CI/dev without PostgreSQL running.
        This test just verifies the error type.
        """
        with pytest.raises((OSError, ConnectionError)):
            await PostgresStore.from_conn_string(
                "postgresql://no-such-host:5432/no_db"
            )


# =============================================================================
# PostgresStore — Operation Tests (using mock pool)
# =============================================================================


class TestPostgresStoreOperations:
    """Unit tests for PostgresStore operation handlers using mocked pg.

    We test the handler methods directly by passing a mocked connection.
    """

    @pytest.fixture
    def store(self):
        """Create a PostgresStore with a mock pool."""
        store = PostgresStore()
        store._pool = MagicMock()
        return store

    @pytest.fixture
    def mock_conn(self):
        """Create a mock asyncpg connection."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.fetch = AsyncMock()
        conn.execute = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_aput_upsert(self, store, mock_conn):
        """aput stores a value via upsert SQL."""
        await store._handle_put(mock_conn, MagicMock(
            namespace=("agent_insights", "sales"),
            key="bottleneck_note",
            value={"note": "Line 3 is slow"},
        ))
        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO memory_store" in sql
        assert "ON CONFLICT" in sql

    @pytest.mark.asyncio
    async def test_aput_delete(self, store, mock_conn):
        """aput with value=None deletes the item."""
        await store._handle_put(mock_conn, MagicMock(
            namespace=("agent_insights", "sales"),
            key="bottleneck_note",
            value=None,
        ))
        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "DELETE FROM memory_store" in sql

    @pytest.mark.asyncio
    async def test_aget_found(self, store, mock_conn):
        """aget returns Item when row exists."""
        from datetime import datetime
        mock_conn.fetchrow.return_value = {
            "namespace": ["agent_insights", "sales"],
            "key": "bottleneck_note",
            "value": {"note": "Line 3 is slow"},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        result = await store._handle_get(mock_conn, MagicMock(
            namespace=("agent_insights", "sales"),
            key="bottleneck_note",
        ))
        assert result is not None
        assert result.namespace == ("agent_insights", "sales")
        assert result.key == "bottleneck_note"
        assert result.value == {"note": "Line 3 is slow"}

    @pytest.mark.asyncio
    async def test_aget_not_found(self, store, mock_conn):
        """aget returns None when row does not exist."""
        mock_conn.fetchrow.return_value = None
        result = await store._handle_get(mock_conn, MagicMock(
            namespace=("test",),
            key="nonexistent",
        ))
        assert result is None

    @pytest.mark.asyncio
    async def test_asearch_with_prefix(self, store, mock_conn):
        """asearch queries by namespace prefix."""
        from datetime import datetime
        now = datetime.now(UTC)
        mock_conn.fetch.return_value = [
            {
                "namespace": ["agent_insights", "sales"],
                "key": "note1",
                "value": {"data": "insight 1"},
                "created_at": now,
                "updated_at": now,
            },
        ]
        results = await store._handle_search(mock_conn, MagicMock(
            namespace_prefix=("agent_insights",),
            filter=None,
            limit=10,
            offset=0,
            query=None,
        ))
        assert len(results) == 1
        assert results[0].namespace == ("agent_insights", "sales")
        assert results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_asearch_with_filter(self, store, mock_conn):
        """asearch applies JSONB containment filter."""
        from datetime import datetime
        now = datetime.now(UTC)
        mock_conn.fetch.return_value = [
            {
                "namespace": ["agent_insights", "production"],
                "key": "bottleneck",
                "value": {"type": "capacity", "severity": "high"},
                "created_at": now,
                "updated_at": now,
            },
        ]
        results = await store._handle_search(mock_conn, MagicMock(
            namespace_prefix=("agent_insights",),
            filter={"severity": "high"},
            limit=10,
            offset=0,
            query=None,
        ))
        assert len(results) == 1
        assert results[0].key == "bottleneck"

    @pytest.mark.asyncio
    async def test_alist_namespaces(self, store, mock_conn):
        """alist_namespaces returns distinct namespace tuples."""
        mock_conn.fetch.return_value = [
            {"ns": ["agent_insights", "sales"]},
            {"ns": ["agent_insights", "production"]},
            {"ns": ["plan_history"]},
        ]
        results = await store._handle_list_namespaces(mock_conn, MagicMock(
            match_conditions=(),
            max_depth=None,
            limit=100,
            offset=0,
        ))
        assert len(results) == 3
        assert ("agent_insights", "sales") in results
        assert ("plan_history",) in results

    @pytest.mark.asyncio
    async def test_alist_namespaces_with_prefix(self, store, mock_conn):
        """alist_namespaces filters by prefix."""
        from langgraph.store.base import MatchCondition
        mock_conn.fetch.return_value = [
            {"ns": ["agent_insights", "sales"]},
        ]
        results = await store._handle_list_namespaces(mock_conn, MagicMock(
            match_conditions=(
                MatchCondition(match_type="prefix", path=("agent_insights",)),
            ),
            max_depth=None,
            limit=100,
            offset=0,
        ))
        assert len(results) == 1
        assert results[0] == ("agent_insights", "sales")


# =============================================================================
# MasterGraph — Memory Node Tests
# =============================================================================


class TestMemoryNodes:
    """Tests for the RETRIEVE and STORE memory nodes."""

    @pytest.mark.asyncio
    async def test_node_retrieve_context_no_store(self):
        """Without a store, retrieve_context returns empty insights."""
        state = {"_store": None}
        result = await node_retrieve_context(state)
        assert result == {"past_insights": []}

    @pytest.mark.asyncio
    async def test_node_retrieve_context_with_store(self):
        """With a store, retrieve_context returns recent insights."""
        store = AsyncMock(spec=PostgresStore)

        # Mock asearch to return items
        from datetime import datetime

        from langgraph.store.base import SearchItem

        now = datetime.now(UTC)
        store.asearch = AsyncMock()
        store.asearch.side_effect = [
            # First call: agent_insights results
            [
                SearchItem(
                    namespace=("agent_insights", "sales"),
                    key="insight_1",
                    value={"note": "demand spike expected"},
                    created_at=now,
                    updated_at=now,
                    score=0.95,
                ),
            ],
            # Second call: plan_history results
            [
                SearchItem(
                    namespace=("plan_history",),
                    key="plan_1",
                    value={"correlation_id": "abc", "approved": True},
                    created_at=now,
                    updated_at=now,
                    score=0.85,
                ),
            ],
        ]

        result = await node_retrieve_context({"_store": store, "correlation_id": "test-123"})

        assert "past_insights" in result
        assert len(result["past_insights"]) == 2
        assert result["past_insights"][0]["namespace"] == ("agent_insights", "sales")
        assert result["past_insights"][1]["type"] == "plan_history"

    @pytest.mark.asyncio
    async def test_node_store_insights_no_store(self):
        """Without a store, store_insights returns empty dict."""
        result = await node_store_insights({"_store": None})
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_store_insights_with_data(self):
        """With a store and agent proposals, store_insights persists them."""
        store = AsyncMock(spec=PostgresStore)
        store.aput = AsyncMock()

        state = {
            "_store": store,
            "correlation_id": "test-123",
            "approved": True,
            "deadlock": False,
            "demands": [{"item": "FG-001"}],
            "final_plan": [{"allocation": "alloc_1"}],
            "negotiation_rounds": [{"round": 1}, {"round": 2}, {"round": 3}],
            "agent_proposals": {
                "sales": {"action": "increase_allocation"},
                "production": {"action": "adjust_schedule"},
            },
            "experience_record_id": "rec_1",
            "business_weights": {"cost": 0.3, "delivery": 0.3},
        }

        result = await node_store_insights(state)

        assert result == {}
        # Should have been called: 1 plan_history + 2 agent insights + 1 negotiation pattern
        assert store.aput.call_count >= 4


# =============================================================================
# MasterGraph — Construction & Compilation Tests
# =============================================================================


class TestMasterGraphMemory:
    """Tests for MasterGraph with memory integration."""

    def test_construction_defaults(self):
        """Default MasterGraph uses MemorySaver and no store."""
        graph = MasterGraph()
        assert graph._store is None

    def test_construction_with_store(self):
        """MasterGraph accepts an explicit store."""
        store = PostgresStore()
        graph = MasterGraph(store=store)
        assert graph._store is store

    def test_build_includes_memory_nodes(self):
        """build() graph includes memory nodes."""
        graph = MasterGraph()
        builder = graph.build()
        nodes = [n for n in builder.nodes]
        assert "retrieve_context" in nodes
        assert "store_insights" in nodes
        assert nodes[0] == "retrieve_context"  # entry point

    def test_compile_succeeds(self):
        """Compiling the graph with memory nodes works."""
        graph = MasterGraph()
        compiled = graph.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_run_without_db(self):
        """Running a minimal planning cycle with MemorySaver (no DB)."""
        graph = MasterGraph()
        graph.compile()

        result = await graph.run({
            "correlation_id": "test-run-001",
            "raw_demands": [{"item": "FG-001", "quantity": 100}],
            "raw_supplies": [{"item": "FG-001", "quantity": 200}],
        })

        assert result is not None
        assert result.get("correlation_id") == "test-run-001"
        assert "_store" not in result  # internal key cleaned up

    @pytest.mark.asyncio
    async def test_run_includes_past_insights(self):
        """Past insights from retrieve_context are available in state."""
        graph = MasterGraph()
        graph.compile()

        # Without a store, past_insights should be empty
        result = await graph.run({
            "correlation_id": "test-insights",
            "raw_demands": [],
            "raw_supplies": [],
        })

        assert result.get("past_insights") == []


# =============================================================================
# Memory Config Tests
# =============================================================================


class TestMemoryConfig:
    """Tests for the MemoryConfig settings."""

    def test_default_values(self):
        """MemoryConfig has sensible defaults."""
        from axon.core.config import MemoryConfig

        config = MemoryConfig()
        assert config.checkpoint_enabled is True
        assert config.checkpoint_ttl_seconds == 604800  # 7 days
        assert config.store_enabled is True
        assert "agent_insights" in config.store_namespaces
        assert config.store_search_limit == 10

    def test_settings_integration(self):
        """settings.memory is a MemoryConfig instance."""
        from axon.core.config import settings

        assert hasattr(settings, "memory")
        assert settings.memory.store_enabled is True
