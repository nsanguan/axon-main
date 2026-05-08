"""ExperienceLedger — Postgres-backed plan recording, retrieval, and semantic search."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg

from axon.core.config import settings
from axon.core.learning.embedder import EmbeddingProvider, TagBasedEmbedder
from axon.core.learning.schema import (
    ExperienceRecord,
    LedgerQuery,
    PlanContext,
    PlanOutcome,
    PlanTrace,
    SimilarPlanResult,
)
from axon.core.telemetry import log_event

RETENTION_HOT_DAYS = 90
RETENTION_WARM_DAYS = 730


class ExperienceLedger:
    """Core ledger for recording, retrieving, and querying planning experiences."""

    def __init__(
        self,
        pool: asyncpg.Pool | None = None,
        embedder: EmbeddingProvider | None = None,
    ):
        self._pool = pool
        self._own_pool = pool is None
        self._embedder = embedder or TagBasedEmbedder()

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            url = settings.database.url
            pg_url = url.replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(
                pg_url,
                min_size=1,
                max_size=5,
                timeout=15,
            )
        return self._pool

    async def close(self) -> None:
        if self._own_pool and self._pool:
            await self._pool.close()
            self._pool = None

    async def record(self, record: ExperienceRecord) -> UUID:
        """Write an ExperienceRecord to the ledger."""
        pool = await self._get_pool()
        record.tags = list(set(record.tags))

        async with pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                    INSERT INTO experience_records
                        (plan_id, context_snapshot, final_plan, negotiations,
                         outcome, tags, plan_confidence, created_at)
                    VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb,
                            $5::jsonb, $6, $7, $8)
                    RETURNING id
                    """,
                record.plan_id,
                record.context.model_dump(mode="json") if record.context else {},
                record.final_plan,
                record.negotiations,
                record.outcome.model_dump(mode="json") if record.outcome else None,
                record.tags,
                record.plan_confidence,
                record.created_at,
            )
            db_id = row["id"]

            if record.traces:
                await conn.executemany(
                    """
                        INSERT INTO plan_traces
                            (decision_id, step_sequence, trigger_event, agent_id,
                             logic_version, input_snapshot, output_snapshot,
                             confidence, duration_ms, model_used)
                        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb,
                                $8, $9, $10)
                        """,
                    [
                        (
                            t.decision_id,
                            t.step_sequence,
                            t.trigger_event,
                            t.agent_id,
                            t.logic_version,
                            t.input_snapshot,
                            t.output_snapshot,
                            t.confidence,
                            t.duration_ms,
                            t.model_used,
                        )
                        for t in record.traces
                    ],
                )

            try:
                embedding = await self._embedder.embed(record)
                if embedding is not None:
                    await conn.execute(
                        "UPDATE experience_records SET embedding = $1::vector(384) WHERE id = $2",
                        embedding,
                        db_id,
                    )
            except Exception:
                pass

            log_event(
                "info",
                "ledger_record_written",
                plan_id=str(record.plan_id),
                trace_count=len(record.traces),
                tags=record.tags,
            )
            return db_id

    async def get(self, plan_id: UUID) -> ExperienceRecord | None:
        """Retrieve a single experience record by plan_id."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM experience_records WHERE plan_id = $1",
                plan_id,
            )
            return self._row_to_record(row) if row else None

    async def query(self, query: LedgerQuery) -> list[ExperienceRecord]:
        """Query experience records with filters."""
        pool = await self._get_pool()
        conditions = []
        params = []
        idx = 1

        if query.tags:
            conditions.append(f"tags && ${idx}::text[]")
            params.append(query.tags)
            idx += 1
        if query.date_from:
            conditions.append(f"created_at >= ${idx}")
            params.append(query.date_from)
            idx += 1
        if query.date_to:
            conditions.append(f"created_at <= ${idx}")
            params.append(query.date_to)
            idx += 1
        if query.plan_id:
            conditions.append(f"plan_id = ${idx}")
            params.append(query.plan_id)
            idx += 1

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"""
            SELECT * FROM experience_records
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([query.limit, query.offset])

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [self._row_to_record(r) for r in rows]

    async def count(self) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT count(*) FROM experience_records")
            return row["count"] if row else 0

    async def update_outcome(self, plan_id: UUID, outcome: PlanOutcome) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE experience_records SET outcome = $1::jsonb WHERE plan_id = $2",
                outcome.model_dump(mode="json"),
                plan_id,
            )
            return result == "UPDATE 1"

    async def apply_retention(self, dry_run: bool = False) -> dict[str, int]:
        pool = await self._get_pool()
        now = datetime.now(UTC)
        results = {"compressed": 0, "purged": 0}

        async with pool.acquire() as conn:
            purge_cutoff = now - timedelta(days=RETENTION_WARM_DAYS)
            if dry_run:
                row = await conn.fetchrow(
                    "SELECT count(*) FROM experience_records "
                    "WHERE created_at < $1 AND NOT ($2::text[] && tags)",
                    purge_cutoff,
                    ["reference"],
                )
                results["purged"] = row["count"]
            else:
                result = await conn.execute(
                    "DELETE FROM experience_records "
                    "WHERE created_at < $1 AND NOT ($2::text[] && tags)",
                    purge_cutoff,
                    ["reference"],
                )
                results["purged"] = int(result.split()[-1])

            compress_cutoff = now - timedelta(days=RETENTION_HOT_DAYS)
            if not dry_run:
                await conn.execute(
                    """
                    UPDATE experience_records
                    SET context_snapshot = jsonb_build_object(
                            '_summary', jsonb_build_object(
                                'demand_count',
                                COALESCE(jsonb_array_length(context_snapshot->'demands'), 0),
                                'supply_count',
                                COALESCE(jsonb_array_length(context_snapshot->'supplies'), 0),
                                'degradation', context_snapshot->>'degradation_level'
                            )
                        ),
                        final_plan = jsonb_build_object(
                            '_summary', jsonb_build_object(
                                'allocation_count',
                                jsonb_array_length(COALESCE(final_plan, '[]'::jsonb))
                            )
                        ),
                        negotiations = jsonb_build_object(
                            '_summary', jsonb_build_object(
                                'round_count',
                                jsonb_array_length(COALESCE(negotiations, '[]'::jsonb))
                            )
                        )
                    WHERE created_at BETWEEN $1 AND $2
                    """,
                    compress_cutoff,
                    purge_cutoff,
                )
                results["compressed"] = 1
        return results

    async def retrieve_similar(
        self,
        demand_profile: dict[str, Any],
        constraint_set: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[SimilarPlanResult]:
        """Find past plans similar to the current planning context."""
        pool = await self._get_pool()
        query_context = {**demand_profile}
        if constraint_set:
            query_context["constraints"] = constraint_set

        query_emb = await self._embedder.embed_query(query_context)
        async with pool.acquire() as conn:
            if query_emb is not None:
                try:
                    rows = await conn.fetch(
                        """
                        SELECT *, 1 - (embedding <=> $1::vector(384)) AS similarity
                        FROM experience_records
                        WHERE embedding IS NOT NULL
                        ORDER BY similarity DESC LIMIT $2
                        """,
                        query_emb,
                        top_k,
                    )
                    if rows:
                        return [
                            SimilarPlanResult(
                                plan=self._row_to_record(r),
                                similarity_score=float(r["similarity"]),
                                match_reasons=["embedding_similarity"],
                            )
                            for r in rows
                        ]
                except Exception:
                    pass

            keywords = self._extract_keywords(demand_profile)
            rows = await conn.fetch(
                "SELECT * FROM experience_records "
                "WHERE tags && $1::text[] ORDER BY created_at DESC LIMIT $2",
                keywords,
                top_k,
            )
            return [
                SimilarPlanResult(
                    plan=self._row_to_record(r),
                    similarity_score=0.5,
                    match_reasons=["tag_match"],
                )
                for r in rows
            ]

    async def record_plan_from_state(self, state: dict) -> UUID:
        """Record a plan from a PlanningState dictionary.

        Convenience method used by MasterGraph's approve/learn nodes.
        Extracts context, allocations, negotiations, and traces from state.
        """
        from uuid import uuid4

        from axon.core.learning.schema import ExperienceRecord, PlanContext

        plan_id = uuid4()
        ctx = PlanContext(
            demands=state.get("demands", []),
            supplies=state.get("supplies", []),
            policies=state.get("raw_policies", []),
            business_weights=state.get("business_weights", {}),
            degradation_level=state.get("degradation_level", "FULL"),
            correlation_id=state.get("correlation_id", ""),
        )

        final_plan = state.get("final_plan", [])
        if isinstance(final_plan, dict):
            final_plan = [final_plan]

        traces_raw = state.get("traces", [])
        traces = []
        for i, t in enumerate(traces_raw):
            if isinstance(t, dict):
                traces.append(
                    PlanTrace(
                        decision_id=plan_id,
                        step_sequence=i + 1,
                        trigger_event=t.get("trigger_event", "unknown"),
                        agent_id=t.get("agent_id", "unknown"),
                        logic_version=t.get("logic_version"),
                        input_snapshot=t.get("input_snapshot", {}),
                        output_snapshot=t.get("output_snapshot", {}),
                        confidence=t.get("confidence", 0.5),
                        duration_ms=t.get("duration_ms", 0),
                        model_used=t.get("model_used"),
                    )
                )

        tags = ["approved" if state.get("approved") else "pending"]
        if state.get("deadlock"):
            tags.append("deadlock_resolved")
        if state.get("hitl_required"):
            tags.append("hitl_reviewed")

        # Track plan confidence from traces
        plan_confidence = None
        if traces:
            confs = [t.confidence for t in traces if t.confidence is not None]
            if confs:
                plan_confidence = sum(confs) / len(confs)

        record = ExperienceRecord(
            plan_id=plan_id,
            correlation_id=state.get("correlation_id", ""),
            context=ctx,
            final_plan=final_plan,
            negotiations=state.get("negotiation_rounds", []),
            traces=traces,
            tags=tags,
            plan_confidence=plan_confidence,
        )

        return await self.record(record)

    async def record_outcome(self, plan_id: UUID, outcome: PlanOutcome) -> bool:
        """Record a plan outcome. Delegates to update_outcome()."""
        return await self.update_outcome(plan_id, outcome)

    @staticmethod
    def _row_to_record(row) -> ExperienceRecord:
        return ExperienceRecord(
            id=row["id"],
            plan_id=row["plan_id"],
            context=PlanContext(**row.get("context_snapshot") or {}),
            final_plan=row.get("final_plan") or [],
            negotiations=row.get("negotiations") or [],
            outcome=PlanOutcome(**row["outcome"]) if row.get("outcome") else None,
            tags=list(row.get("tags") or []),
            plan_confidence=row.get("plan_confidence"),
            created_at=row["created_at"],
        )

    @staticmethod
    def _extract_keywords(context: dict[str, Any]) -> list[str]:
        keywords = []
        items = context.get("items", [])
        if isinstance(items, list):
            for item in items[:5]:
                if isinstance(item, dict):
                    for key in ("item_id", "sku", "native_id", "item"):
                        val = item.get(key)
                        if val:
                            keywords.append(str(val))
                            break
        priority = context.get("priority")
        if priority:
            keywords.append(f"priority_{priority}")
        return list(set(keywords))[:10]
