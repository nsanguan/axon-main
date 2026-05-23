"""
Redis Cache — MCP response caching layer backed by external Redis.

Provides:
  - Per-tool TTL configuration (configurable via settings)
  - Cache-aside pattern: check cache before MCP call, write through on response
  - Redis-backed caching with transparent in-memory fallback
  - Graceful degradation: Redis failures fall through to cache miss
  - Cache key composition: {server_name}:{tool_name}:{hash(arguments)}

Connection: Uses settings.redis.url (e.g. redis://host.docker.internal:6379/0)
via redis.asyncio.ConnectionPool with configurable pool size.

Usage:
    from axon.connectors.cache import mcp_cache

    cached = await mcp_cache.get("oracle_ebs", "get_inventory_levels", args)
    if cached:
        return cached

    result = await call_mcp()
    await mcp_cache.set("oracle_ebs", "get_inventory_levels", args, result)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from axon.core.config import settings
from axon.core.telemetry import log_event

# Per-tool TTL overrides (seconds). Falls back to settings.redis.ttl_seconds.
_TOOL_TTL_OVERRIDES: dict[str, int] = {
    "get_inventory_levels": 120,
    "get_available_to_promise": 60,
    "get_work_center_capacity": 120,
    "get_item_costs": 600,
    "get_suppliers": 600,
    "get_bom": 3600,
    "get_routing": 3600,
    "get_carrier_rates": 3600,
    "get_transit_times": 3600,
    "get_safety_stock": 1800,
    "get_storage_capacity": 1800,
    "get_delivery_constraints": 1800,
    "get_budget": 3600,
    "get_gl_accounts": 7200,
    "get_profitability": 600,
    "get_sop": 3600,
    "get_regulatory_requirements": 7200,
    "get_inspection_plan": 600,
    "get_defect_history": 600,
    "get_item_master": 3600,
    "get_engineering_changes": 600,
    "get_asset_health": 300,
    "get_maintenance_schedule": 600,
    "get_downtime_history": 600,
    "reschedule_wip_job": 0,
    "create_purchase_requisition": 0,
    "create_shipment": 0,
    "create_inspection_lot": 0,
    "update_work_center_status": 0,
    "check_compliance": 120,
    "get_audit_history": 300,
}


def _cache_key(server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
    """Build a deterministic cache key for an MCP call."""
    args_json = json.dumps(arguments, sort_keys=True, default=str)
    args_hash = hashlib.md5(args_json.encode()).hexdigest()[:12]
    return f"mcp:{server_name}:{tool_name}:{args_hash}"


def _ttl_for(tool_name: str) -> int:
    """Return TTL in seconds for a given tool. 0 means never cache."""
    return _TOOL_TTL_OVERRIDES.get(tool_name, settings.redis.ttl_seconds)


# =============================================================================
# Redis connection pool (lazy, created on first use)
# =============================================================================

_redis_pool: Any = None
_redis_client: Any = None


def _get_redis() -> Any | None:
    """Return a connected Redis async client, or None if unavailable."""
    global _redis_pool, _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        from redis.asyncio import ConnectionPool, Redis as AsyncRedis

        _redis_pool = ConnectionPool.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            socket_timeout=3,
            socket_connect_timeout=3,
            retry_on_timeout=True,
        )
        _redis_client = AsyncRedis(connection_pool=_redis_pool)
        return _redis_client
    except Exception:
        log_event("warning", "redis_fallback", reason="Unable to create Redis client — using in-memory fallback")
        return None


# =============================================================================
# In-memory fallback (when Redis is unavailable)
# =============================================================================

_fallback_store: dict[str, tuple[str, float]] = {
}  # key → (json_value, expires_at)


async def _redis_get(key: str) -> str | None:
    """Get value from Redis. Returns None on miss or error."""
    client = _get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception:
        log_event("warning", "redis_get_failed", key=key)
        return None


async def _redis_set(key: str, value: str, ttl: int) -> bool:
    """Set value in Redis with TTL. Returns True on success."""
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.set(key, value, ex=ttl)
        return True
    except Exception:
        log_event("warning", "redis_set_failed", key=key, ttl=ttl)
        return False


async def _redis_delete(key: str) -> bool:
    """Delete a key from Redis. Returns True on success."""
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.delete(key)
        return True
    except Exception:
        return False


async def _redis_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    client = _get_redis()
    if client is None:
        return 0
    try:
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception:
        log_event("warning", "redis_delete_pattern_failed", pattern=pattern)
        return 0


async def _redis_flush() -> int:
    """Clear all cache keys. Returns count cleared."""
    client = _get_redis()
    if client is None:
        return 0
    try:
        keys = await client.keys("mcp:*")
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception:
        log_event("warning", "redis_flush_failed")
        return 0


async def _redis_dbsize() -> int:
    """Return count of mcp cache keys."""
    client = _get_redis()
    if client is None:
        return 0
    try:
        keys = await client.keys("mcp:*")
        return len(keys)
    except Exception:
        return 0


# =============================================================================
# Public API
# =============================================================================


async def mcp_cache_get(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any | None:
    """Try to get a cached MCP response. Returns None on miss, expiry, or error.

    Attempts Redis first, falls back to in-memory store if Redis is unavailable.
    """
    import time

    ttl = _ttl_for(tool_name)
    if ttl <= 0:
        return None

    key = _cache_key(server_name, tool_name, arguments)

    raw = await _redis_get(key)
    if raw is not None:
        try:
            value = json.loads(raw)
            log_event("info", "cache_hit", server_name=server_name, tool_name=tool_name, backend="redis")
            return value
        except (json.JSONDecodeError, TypeError):
            await _redis_delete(key)

    # In-memory fallback
    entry = _fallback_store.get(key)
    if entry is None:
        return None

    serialized, expires_at = entry
    if time.time() > expires_at:
        _fallback_store.pop(key, None)
        return None

    try:
        value = json.loads(serialized)
        log_event("info", "cache_hit", server_name=server_name, tool_name=tool_name, backend="memory")
        return value
    except (json.JSONDecodeError, TypeError):
        _fallback_store.pop(key, None)
        return None


async def mcp_cache_set(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    value: Any,
) -> None:
    """Store an MCP response in cache.

    Writes to Redis first, then updates in-memory fallback. If Redis
    write fails, falls back to in-memory-only.
    """
    import time

    ttl = _ttl_for(tool_name)
    if ttl <= 0:
        return

    key = _cache_key(server_name, tool_name, arguments)
    serialized = json.dumps(value, default=str)

    redis_ok = await _redis_set(key, serialized, ttl)

    # Always update in-memory fallback
    _fallback_store[key] = (serialized, time.time() + ttl)

    backend = "redis" if redis_ok else "memory"
    log_event("info", "cache_set", server_name=server_name, tool_name=tool_name, ttl=ttl, backend=backend)


async def mcp_cache_invalidate(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> int:
    """Invalidate cache entries for a tool.

    If arguments is provided, only that specific call is invalidated.
    If arguments is None, all entries for that server+tool are invalidated.

    Returns count of invalidated entries.
    """
    if arguments is not None:
        key = _cache_key(server_name, tool_name, arguments)
        del_redis = await _redis_delete(key)
        del_fallback = 1 if _fallback_store.pop(key, None) is not None else 0
        return max(del_redis, del_fallback)

    pattern = f"mcp:{server_name}:{tool_name}:*"
    del_redis = await _redis_delete_pattern(pattern)

    prefix = f"mcp:{server_name}:{tool_name}:"
    keys_to_delete = [k for k in _fallback_store if k.startswith(prefix)]
    for k in keys_to_delete:
        _fallback_store.pop(k, None)
    del_fallback = len(keys_to_delete)

    return max(del_redis, del_fallback)


def mcp_cache_clear() -> int:
    """Clear the entire cache (memory fallback only — Redis flush is async).

    For full Redis flush, call `await _redis_flush()`.
    """
    count = len(_fallback_store)
    _fallback_store.clear()
    return count


def mcp_cache_stats() -> dict[str, Any]:
    """Return cache statistics (in-memory fallback snapshot)."""
    return {
        "entries": len(_fallback_store),
        "tools_cached": len({k.split(":")[2] for k in _fallback_store if k.startswith("mcp:")}),
    }


async def mcp_cache_health() -> dict[str, Any]:
    """Check Redis connectivity and return detailed cache health."""
    client = _get_redis()
    redis_ok = False
    redis_keys = 0
    if client is not None:
        try:
            await client.ping()
            redis_ok = True
            redis_keys = await _redis_dbsize()
        except Exception:
            redis_ok = False

    return {
        "redis_available": redis_ok,
        "redis_url": settings.redis.url,
        "redis_keys": redis_keys,
        "fallback_entries": len(_fallback_store),
    }
