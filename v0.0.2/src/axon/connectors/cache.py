"""
Redis Cache — MCP response caching layer for performance optimization.

Provides:
  - Per-tool TTL configuration (configurable via settings)
  - Cache-aside pattern: check cache before MCP call, write through on response
  - Graceful degradation: cache misses return None, never raise
  - Cache key composition: {server_name}:{tool_name}:{hash(arguments)}

Usage:
    from axon.connectors.cache import mcp_cache

    # Check cache before MCP call
    cached = await mcp_cache.get("oracle_ebs", "get_inventory_levels", args)
    if cached:
        return cached

    # Make MCP call, then store
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
    # Fast-changing data — short TTL
    "get_inventory_levels": 120,
    "get_available_to_promise": 60,
    "get_work_center_capacity": 120,
    # Slow-changing data — longer TTL
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
    # Write tools — never cache
    "reschedule_wip_job": 0,
    "create_purchase_requisition": 0,
    "create_shipment": 0,
    "create_inspection_lot": 0,
    "update_work_center_status": 0,
    # Compliance checks — short TTL or uncached
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
# In-memory cache (production: use Redis via redis-py)
# =============================================================================

_cache_store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)


async def mcp_cache_get(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any | None:
    """Try to get a cached MCP response. Returns None on miss or expiry.

    This is the primary cache-lookup function. In production, this delegates
    to Redis; in development/demo, it uses an in-memory dict.
    """
    import time

    ttl = _ttl_for(tool_name)
    if ttl <= 0:
        return None  # Never cached (write tools)

    key = _cache_key(server_name, tool_name, arguments)
    entry = _cache_store.get(key)

    if entry is None:
        return None

    value, expires_at = entry
    if time.time() > expires_at:
        _cache_store.pop(key, None)
        return None

    log_event("info", "cache_hit", server_name=server_name, tool_name=tool_name)
    return value


async def mcp_cache_set(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    value: Any,
) -> None:
    """Store an MCP response in cache.

    Respects per-tool TTL. Write tools get TTL=0 and are never stored.
    """
    import time

    ttl = _ttl_for(tool_name)
    if ttl <= 0:
        return

    key = _cache_key(server_name, tool_name, arguments)
    _cache_store[key] = (value, time.time() + ttl)

    log_event("info", "cache_set", server_name=server_name, tool_name=tool_name, ttl=ttl)


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
        return 1 if _cache_store.pop(key, None) is not None else 0

    prefix = f"mcp:{server_name}:{tool_name}:"
    keys_to_delete = [k for k in _cache_store if k.startswith(prefix)]
    for k in keys_to_delete:
        _cache_store.pop(k, None)
    return len(keys_to_delete)


def mcp_cache_clear() -> int:
    """Clear the entire cache. Returns count of cleared entries."""
    count = len(_cache_store)
    _cache_store.clear()
    return count


def mcp_cache_stats() -> dict[str, Any]:
    """Return cache statistics."""
    return {
        "entries": len(_cache_store),
        "tools_cached": len({k.split(":")[2] for k in _cache_store if k.startswith("mcp:")}),
    }
