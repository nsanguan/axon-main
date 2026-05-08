"""
adapters.mapping.legacy_db — Legacy SQL Database → Axon Universal Schema Mapper.

Translates raw dict records returned by the Legacy DB MCP server tools
(axon_legacy_get_demand, axon_legacy_get_supply, axon_legacy_get_on_hand)
into Axon's universal schema objects.

Because legacy databases have highly varied schemas, this mapper uses
flexible key resolution: it tries multiple possible column names (common
aliases) for each Axon field so that minimal SQL view renaming is required.

Recommended SQL view column names (to match primary keys below):
  demand view : product_code, demand_qty, demand_date, source_type, source_ref, status
  supply view : product_code, supply_qty, available_qty, supply_date, source_type, source_ref
  stock view  : product_code, warehouse, on_hand_qty
  allocation  : demand_ref, supply_ref, product_code, allocated_qty, status, ai_context
"""

from __future__ import annotations

from datetime import date

from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus
from core.schema.allocation import AxonAllocation, AxonAllocationStatus

_ERP = "legacy"

# ── Internal helpers ──────────────────────────────────────────────────────────

def _get(row: dict, *keys: str, default=None):
    """Return first non-None value found for any of the given keys."""
    for k in keys:
        v = row.get(k)
        if v is not None:
            return v
    return default


def _parse_date(value) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return date.today()


def _counter(prefix: str, value) -> str:
    return f"{_ERP}:{prefix}:{value}" if value is not None else f"{_ERP}:{prefix}:unknown"


_DEMAND_SOURCE_MAP: dict[str, AxonDemandSource] = {
    "sale_order":  AxonDemandSource.SALE_ORDER,
    "so":          AxonDemandSource.SALE_ORDER,
    "sales":       AxonDemandSource.SALE_ORDER,
    "forecast":    AxonDemandSource.FORECAST,
    "fcst":        AxonDemandSource.FORECAST,
    "mps":         AxonDemandSource.MPS,
    "mrp":         AxonDemandSource.MRP,
    "transfer":    AxonDemandSource.TRANSFER,
    "manual":      AxonDemandSource.MANUAL,
}

_DEMAND_STATUS_MAP: dict[str, AxonDemandStatus] = {
    "open":      AxonDemandStatus.OPEN,
    "pegged":    AxonDemandStatus.PEGGED,
    "partial":   AxonDemandStatus.PARTIAL,
    "exception": AxonDemandStatus.EXCEPTION,
    "closed":    AxonDemandStatus.CLOSED,
    "done":      AxonDemandStatus.CLOSED,
}

_SUPPLY_SOURCE_MAP: dict[str, AxonSupplySource] = {
    "po":                  AxonSupplySource.PURCHASE_ORDER,
    "purchase_order":      AxonSupplySource.PURCHASE_ORDER,
    "purchase":            AxonSupplySource.PURCHASE_ORDER,
    "wo":                  AxonSupplySource.MANUFACTURING_ORDER,
    "work_order":          AxonSupplySource.MANUFACTURING_ORDER,
    "manufacturing_order": AxonSupplySource.MANUFACTURING_ORDER,
    "mo":                  AxonSupplySource.MANUFACTURING_ORDER,
    "transfer":            AxonSupplySource.TRANSFER,
    "on_hand":             AxonSupplySource.ON_HAND,
    "stock":               AxonSupplySource.ON_HAND,
}

_SUPPLY_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "open":      AxonSupplyStatus.OPEN,
    "allocated": AxonSupplyStatus.ALLOCATED,
    "partial":   AxonSupplyStatus.PARTIAL,
    "received":  AxonSupplyStatus.RECEIVED,
    "done":      AxonSupplyStatus.RECEIVED,
    "cancelled": AxonSupplyStatus.CANCELLED,
}


# ── Demand mappers ────────────────────────────────────────────────────────────

def axon_legacy_demand_row_to_item(row: dict) -> AxonDemandItem:
    """
    Map a legacy SQL demand view row to AxonDemandItem.

    Tries common column name variants so that minimal SQL view changes are needed.

    Primary column names (recommended):
      product_code, product_name, demand_qty, demand_date, source_type, source_ref, status
    Also handles:
      sku, item_code, item_number, required_qty, need_date, so_number, order_number
    """
    product_code = str(
        _get(row, "product_code", "sku", "item_code", "item_number", "ITEM", default="")
    )
    product_name = str(
        _get(row, "product_name", "description", "item_name", default=product_code)
    )
    demand_qty = float(_get(row, "demand_qty", "required_qty", "qty", "QUANTITY", default=0.0))
    confirmed_qty = float(_get(row, "confirmed_qty", "allocated_qty", "pegged_qty", default=0.0))
    raw_date = _get(row, "demand_date", "need_date", "required_date", "due_date")
    source_type_raw = str(_get(row, "source_type", "order_type", "demand_type", default="manual")).lower()
    source_ref = str(_get(row, "source_ref", "so_number", "order_number", "reference", default=""))
    status_raw = str(_get(row, "status", "demand_status", default="open")).lower()
    row_id = _get(row, "id", "demand_id", "line_id", default=f"{product_code}-{source_ref}")

    return AxonDemandItem(
        id=_counter("demand", row_id),
        source_type=_DEMAND_SOURCE_MAP.get(source_type_raw, AxonDemandSource.MANUAL),
        source_ref=source_ref,
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        product_id=_counter("product", product_code),
        product_name=product_name,
        product_sku=product_code,
        demand_qty=demand_qty,
        confirmed_qty=confirmed_qty,
        uom=str(_get(row, "uom", "unit", "UOM", default="units")),
        demand_date=_parse_date(raw_date),
        status=_DEMAND_STATUS_MAP.get(status_raw, AxonDemandStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Supply mappers ────────────────────────────────────────────────────────────

def axon_legacy_supply_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a legacy SQL supply view row to AxonSupplyItem.

    Primary column names (recommended):
      product_code, supply_qty, available_qty, supply_date, source_type, source_ref, status
    Also handles:
      sku, po_number, wo_number, expected_date, vendor
    """
    product_code = str(
        _get(row, "product_code", "sku", "item_code", "item_number", "ITEM", default="")
    )
    product_name = str(_get(row, "product_name", "description", default=product_code))
    supply_qty = float(_get(row, "supply_qty", "ordered_qty", "qty", "QUANTITY", default=0.0))
    available_qty = float(_get(row, "available_qty", "remaining_qty", "open_qty", default=supply_qty))
    raw_date = _get(row, "supply_date", "expected_date", "due_date", "eta")
    source_type_raw = str(_get(row, "source_type", "order_type", "supply_type", default="po")).lower()
    source_ref = str(_get(row, "source_ref", "po_number", "wo_number", "order_number", default=""))
    status_raw = str(_get(row, "status", "supply_status", default="open")).lower()
    row_id = _get(row, "id", "supply_id", "line_id", default=f"{product_code}-{source_ref}")

    return AxonSupplyItem(
        id=_counter("supply", row_id),
        source_type=_SUPPLY_SOURCE_MAP.get(source_type_raw, AxonSupplySource.PURCHASE_ORDER),
        source_ref=source_ref,
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        product_id=_counter("product", product_code),
        product_name=product_name,
        product_sku=product_code,
        supply_qty=supply_qty,
        available_qty=available_qty,
        uom=str(_get(row, "uom", "unit", "UOM", default="units")),
        supply_date=_parse_date(raw_date),
        vendor_ref=str(_get(row, "vendor", "vendor_ref", "supplier", default="")),
        location_ref=str(_get(row, "warehouse", "location", "location_ref", default="")),
        status=_SUPPLY_STATUS_MAP.get(status_raw, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_legacy_stock_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a legacy SQL stock view row to AxonSupplyItem (on_hand).

    Primary column names (recommended): product_code, on_hand_qty, warehouse
    Also handles: sku, stock_qty, quantity, location
    """
    product_code = str(
        _get(row, "product_code", "sku", "item_code", "item_number", default="")
    )
    product_name = str(_get(row, "product_name", "description", default=product_code))
    on_hand = float(_get(row, "on_hand_qty", "stock_qty", "quantity", "qty", default=0.0))
    warehouse = str(_get(row, "warehouse", "location", "location_ref", default=""))
    row_id = _get(row, "id", "stock_id", default=f"{product_code}-{warehouse}")

    return AxonSupplyItem(
        id=_counter("stock", row_id),
        source_type=AxonSupplySource.ON_HAND,
        source_ref="stock",
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        product_id=_counter("product", product_code),
        product_name=product_name,
        product_sku=product_code,
        supply_qty=on_hand,
        available_qty=on_hand,
        uom=str(_get(row, "uom", "unit", "UOM", default="units")),
        supply_date=date.today(),
        location_ref=warehouse,
        status=AxonSupplyStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Allocation mappers ────────────────────────────────────────────────────────

def axon_legacy_allocation_row_to_allocation(row: dict) -> AxonAllocation:
    """
    Map a legacy SQL allocation table row to AxonAllocation.

    Primary column names (recommended):
      id, demand_ref, supply_ref, product_code, allocated_qty, status, ai_context

    This is the read-back mapper for rows written via axon_legacy_write_allocation.
    """
    product_code = str(_get(row, "product_code", "sku", "item_code", default=""))
    product_name = str(_get(row, "product_name", "description", default=product_code))
    row_id = _get(row, "id", "allocation_id", default=None)
    demand_ref = str(_get(row, "demand_ref", "so_number", "demand_reference", default=""))
    supply_ref = str(_get(row, "supply_ref", "po_number", "supply_reference", default=""))
    allocated_qty = float(_get(row, "allocated_qty", "quantity", "qty", default=0.0))
    status_raw = str(_get(row, "status", "allocation_status", default="draft")).lower()
    try:
        status = AxonAllocationStatus(status_raw)
    except ValueError:
        status = AxonAllocationStatus.DRAFT

    return AxonAllocation(
        id=_counter("alloc", row_id),
        erp_id=int(row_id) if row_id is not None and str(row_id).isdigit() else None,
        demand_id=_counter("demand", demand_ref),
        supply_id=_counter("supply", supply_ref),
        demand_ref=demand_ref,
        supply_ref=supply_ref,
        product_id=_counter("product", product_code),
        product_name=product_name,
        allocated_qty=allocated_qty,
        uom=str(_get(row, "uom", "unit", "UOM", default="units")),
        status=status,
        ai_context=str(_get(row, "ai_context", "notes", "comment", default="")),
        metadata={"_erp": _ERP, "_raw": row},
    )
