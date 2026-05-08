"""EmbeddingProvider — abstract interface and implementations for semantic plan retrieval.

Provides two implementations:
  1. TagBasedEmbedder — keyword/tag matching fallback (no external dependencies)
  2. OpenAIEmbedder — real embedding via OpenAI-compatible API (requires API key)

The embedder produces 384-dimensional vectors compatible with pgvector.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any

from axon.core.learning.schema import ExperienceRecord


class EmbeddingProvider(ABC):
    """Abstract interface for plan embedding and similarity search."""

    @abstractmethod
    async def embed(self, record: ExperienceRecord) -> list[float] | None:
        """Embed a full ExperienceRecord into a vector. Returns None if not possible."""
        ...

    @abstractmethod
    async def embed_query(self, context: dict[str, Any]) -> list[float] | None:
        """Embed a query context into a vector for similarity search."""
        ...


# ---------------------------------------------------------------------------
# TagBasedEmbedder — keyword signature matching
# ---------------------------------------------------------------------------

VECTOR_DIM = 384


class TagBasedEmbedder(EmbeddingProvider):
    """Lightweight embedder that produces deterministic hash-based vectors.

    Uses feature hashing: each keyword/tag maps to a fixed set of dimensions
    via MD5 hash, producing a sparse binary vector. This supports pgvector
    cosine-similarity queries without any external embedding model.

    For production use, swap with OpenAIEmbedder or sentence-transformers.
    """

    def __init__(self, dimensions: int = VECTOR_DIM):
        self._dimensions = dimensions

    async def embed(self, record: ExperienceRecord) -> list[float] | None:
        """Produce a sparse vector from the record's tags and context."""
        features = self._extract_features(record)
        return self._hash_to_vector(features)

    async def embed_query(self, context: dict[str, Any]) -> list[float] | None:
        """Produce a vector from a query context."""
        features = self._extract_query_features(context)
        if not features:
            return None
        return self._hash_to_vector(features)

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def _extract_features(self, record: ExperienceRecord) -> list[str]:
        features: list[str] = []
        features.extend(record.tags)

        ctx = record.context
        if ctx:
            for d in ctx.demands:
                item = d.get("item", {})
                if isinstance(item, dict):
                    features.append(f"item:{item.get('native_id', '')}")
                    features.append(f"source:{item.get('source', d.get('source', ''))}")
            for s in ctx.supplies:
                features.append(f"supply_source:{s.get('source', '')}")
            features.extend(f"weight:{k}:{v}" for k, v in ctx.business_weights.items())
            if ctx.degradation_level != "FULL":
                features.append(f"degradation:{ctx.degradation_level}")

        if record.outcome:
            if record.outcome.on_time:
                features.append("outcome:on_time")
            if record.outcome.replan_triggered:
                features.append("outcome:replan")

        return list(set(features))

    @staticmethod
    def _extract_query_features(context: dict[str, Any]) -> list[str]:
        features: list[str] = []
        items = context.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for key in ("item_id", "sku", "native_id", "item_type"):
                        val = item.get(key)
                        if val:
                            features.append(f"item:{val}")
        for key in ("source", "priority", "item_type"):
            val = context.get(key)
            if val:
                features.append(f"{key}:{val}")
        constraints = context.get("constraints")
        if constraints and isinstance(constraints, dict):
            for k, v in constraints.items():
                features.append(f"constraint:{k}:{v}")
        return list(set(features))

    # ------------------------------------------------------------------
    # Feature hashing → vector
    # ------------------------------------------------------------------

    def _hash_to_vector(self, features: list[str]) -> list[float]:
        """Deterministic feature hashing to a float vector.

        Each feature is MD5-hashed to pick dimensions, with sign
        determined by one bit of the hash.
        """
        vec = [0.0] * self._dimensions
        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).digest()
            # Use first 4 bytes for dimension index (mod DIM)
            idx = int.from_bytes(digest[:4], "little") % self._dimensions
            # Use 5th byte for sign
            sign = 1.0 if (digest[4] & 1) else -1.0
            vec[idx] += sign
        return vec
