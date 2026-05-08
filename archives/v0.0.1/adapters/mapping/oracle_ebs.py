"""
adapters.mapping.oracle_ebs — Oracle EBS → Axon Universal Schema Mapper.

Translates raw dict records returned by the Oracle EBS MCP server tools
(axon_ebs_get_demand, axon_ebs_get_supply, axon_ebs_get_stock)
into Axon's universal schema objects.

Oracle EBS field → Axon field mappings:
  MRP_GROSS_REQUIREMENTS row          → AxonDemandItem
  PO_LINES_ALL / WIP_DISCRETE_JOBS    → AxonSupplyItem (purchase / manufacturing)
  MTL_ONHAND_QUANTITIES_DETAIL row    → AxonSupplyItem (on_hand)
  PO_REQUISITIONS_INTERFACE_ALL row   → AxonAllocation

Key EBS tables / views referenced:
  MTL_SYSTEM_ITEMS_B  (material master)
  MRP_GROSS_REQUIREMENTS (demand)
  PO_LINES_ALL, PO_HEADERS_ALL (purchase orders)
  WIP_DISCRETE_JOBS (manufacturing orders / work orders)
  MTL_ONHAND_QUANTITIES_DETAIL (stock)
  WF_NOTIFICATIONS (workflow / HITL tasks)
"""

from __future__ import annotations

from datetime import date

from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus
from core.schema.allocation import AxonAllocation, AxonAllocationStatus

_ERP = "ebs"

# ── Internal helpers ──────────────────────────────────────────────────────────

# MRP_GROSS_REQUIREMENTS.ORIGINATION_TYPE values
_EBS_ORIGINATION_TYPE_MAP: dict[int, AxonDemandSource] = {
    1: AxonDemandSource.SALE_ORDER,         # Sales order
    2: AxonDemandSource.FORECAST,           # Forecast
    3: AxonDemandSource.MPS,                # Master schedule
    4: AxonDemandSource.MRP,                # MRP component demand
    5: AxonDemandSource.MRP,                # WIP component demand
    7: AxonDemandSource.TRANSFER,           # Inter-org demand
    8: AxonDemandSource.MANUAL,             # Manual MDS
    11: AxonDemandSource.FORECAST,          # Interplant demand
}

_EBS_DEMAND_STATUS_MAP: dict[str, AxonDemandStatus] = {
    "OPEN":    AxonDemandStatus.OPEN,
    "PEGGED":  AxonDemandStatus.PEGGED,
    "PARTIAL": AxonDemandStatus.PARTIAL,
    "EXCP":    AxonDemandStatus.EXCEPTION,
    "CLOSED":  AxonDemandStatus.CLOSED,
}

_EBS_SUPPLY_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "OPEN":      AxonSupplyStatus.OPEN,
    "APPROVED":  AxonSupplyStatus.OPEN,
    "RECEIVED":  AxonSupplyStatus.RECEIVED,
    "PARTIAL":   AxonSupplyStatus.PARTIAL,
    "CANCELLED": AxonSupplyStatus.CANCELLED,
    "CLOSED":    AxonSupplyStatus.RECEIVED,
}


def _parse_ebs_date(value: str | None) -> date:
    """Parse Oracle date: ISO string, or date object, or None."""
    if not value:
        return date.today()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return date.today()


def _counter(prefix: str, value: int | str | None) -> str:
    return f"{_ERP}:{prefix}:{value}" if value is not None else f"{_ERP}:{prefix}:unknown"


# ── Demand mappers ────────────────────────────────────────────────────────────

def axon_ebs_demand_row_to_item(row: dict) -> AxonDemandItem:
    """
    Map an Oracle EBS MRP_GROSS_REQUIREMENTS row to AxonDemandItem.

    Expected row keys (MRP_GROSS_REQUIREMENTS):
      DEMAND_ID, INVENTORY_ITEM_ID, ORGANIZATION_ID,
      ORIGINATION_TYPE (int), ORIGINATION_REFERENCE (SO/WO number),
      USING_ASSEMBLY_DEMAND_DATE, USING_REQUIREMENT_QUANTITY,
      DAILY_DEMAND_RATE, STATUS_TYPE
    """
    orig_type = int(row.get("ORIGINATION_TYPE") or row.get("origination_type") or 4)
    ref = str(
        row.get("ORIGINATION_REFERENCE")
        or row.get("source_ref")
        or row.get("DEMAND_ID")
        or ""
    )
    item_id = row.get("INVENTORY_ITEM_ID") or row.get("inventory_item_id")
    demand_qty = float(row.get("USING_REQUIREMENT_QUANTITY") or row.get("demand_qty") or 0.0)
    raw_date = (
        row.get("USING_ASSEMBLY_DEMAND_DATE")
        or row.get("ASSEMBLY_DEMAND_DATE")
        or row.get("demand_date")
    )
    demand_id = row.get("DEMAND_ID") or row.get("id") or ref
    status_raw = str(row.get("STATUS_TYPE") or row.get("status") or "OPEN").upper()

    return AxonDemandItem(
        id=_counter("demand", demand_id),
        source_type=_EBS_ORIGINATION_TYPE_MAP.get(orig_type, AxonDemandSource.MRP),
        source_ref=ref,
        erp_id=int(demand_id) if str(demand_id).isdigit() else None,
        product_id=_counter("item", item_id),
        product_name=str(row.get("ITEM_NAME") or row.get("product_name") or item_id or ""),
        product_sku=str(row.get("ITEM_NUMBER") or row.get("product_sku") or ""),
        demand_qty=demand_qty,
        confirmed_qty=float(row.get("PEGGED_QTY") or row.get("confirmed_qty") or 0.0),
        uom=str(row.get("UNIT_OF_MEASURE") or row.get("uom") or "Ea"),
        demand_date=_parse_ebs_date(raw_date),
        status=_EBS_DEMAND_STATUS_MAP.get(status_raw, AxonDemandStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Supply mappers ────────────────────────────────────────────────────────────

def axon_ebs_po_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map an Oracle EBS PO_LINES_ALL / PO_HEADERS_ALL row to AxonSupplyItem.

    Expected row keys:
      LINE_ID, HEADER_ID, SEGMENT1 (PO number), INVENTORY_ITEM_ID,
      QUANTITY (ordered), QUANTITY_RECEIVED, QUANTITY_CANCELLED,
      NEED_BY_DATE, VENDOR_NAME, LINE_STATUS_LOOKUP_CODE
    """
    po_num = str(row.get("SEGMENT1") or row.get("po_number") or row.get("HEADER_ID") or "")
    item_id = row.get("INVENTORY_ITEM_ID") or row.get("inventory_item_id")
    ordered_qty = float(row.get("QUANTITY") or row.get("supply_qty") or 0.0)
    received_qty = float(row.get("QUANTITY_RECEIVED") or row.get("received_qty") or 0.0)
    cancelled_qty = float(row.get("QUANTITY_CANCELLED") or 0.0)
    available_qty = max(ordered_qty - received_qty - cancelled_qty, 0.0)
    raw_date = row.get("NEED_BY_DATE") or row.get("PROMISED_DATE") or row.get("supply_date")
    status_raw = str(row.get("LINE_STATUS_LOOKUP_CODE") or row.get("status") or "OPEN").upper()
    row_id = row.get("LINE_ID") or row.get("id") or po_num

    return AxonSupplyItem(
        id=_counter("po", row_id),
        source_type=AxonSupplySource.PURCHASE_ORDER,
        source_ref=po_num,
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        product_id=_counter("item", item_id),
        product_name=str(row.get("ITEM_NAME") or row.get("product_name") or item_id or ""),
        product_sku=str(row.get("ITEM_NUMBER") or row.get("product_sku") or ""),
        supply_qty=ordered_qty,
        available_qty=available_qty,
        uom=str(row.get("UNIT_MEAS_LOOKUP_CODE") or row.get("uom") or "Ea"),
        supply_date=_parse_ebs_date(raw_date),
        vendor_ref=str(row.get("VENDOR_NAME") or row.get("vendor_ref") or ""),
        location_ref=str(row.get("SHIP_TO_LOCATION") or row.get("location_ref") or ""),
        status=_EBS_SUPPLY_STATUS_MAP.get(status_raw, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_ebs_wip_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map an Oracle EBS WIP_DISCRETE_JOBS row to AxonSupplyItem (manufacturing_order).

    Expected row keys:
      WIP_ENTITY_ID, WIP_ENTITY_NAME, INVENTORY_ITEM_ID,
      START_QUANTITY, QUANTITY_COMPLETED, QUANTITY_SCRAPPED,
      SCHEDULED_COMPLETION_DATE, STATUS_TYPE
    """
    wip_name = str(row.get("WIP_ENTITY_NAME") or row.get("source_ref") or "")
    item_id = row.get("INVENTORY_ITEM_ID") or row.get("inventory_item_id")
    qty = float(row.get("START_QUANTITY") or row.get("supply_qty") or 0.0)
    completed = float(row.get("QUANTITY_COMPLETED") or 0.0)
    scrapped = float(row.get("QUANTITY_SCRAPPED") or 0.0)
    available = max(qty - completed - scrapped, 0.0)
    raw_date = row.get("SCHEDULED_COMPLETION_DATE") or row.get("supply_date")
    status_code = int(row.get("STATUS_TYPE") or 0)
    # WIP status: 1=Unreleased, 3=Released, 4=Complete, 5=Complete-No Charges, 7=Cancelled
    status_map = {1: AxonSupplyStatus.OPEN, 3: AxonSupplyStatus.OPEN,
                  4: AxonSupplyStatus.RECEIVED, 5: AxonSupplyStatus.RECEIVED,
                  7: AxonSupplyStatus.CANCELLED}
    row_id = row.get("WIP_ENTITY_ID") or row.get("id") or wip_name

    return AxonSupplyItem(
        id=_counter("wip", row_id),
        source_type=AxonSupplySource.MANUFACTURING_ORDER,
        source_ref=wip_name,
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        product_id=_counter("item", item_id),
        product_name=str(row.get("ITEM_NAME") or row.get("product_name") or item_id or ""),
        product_sku=str(row.get("ITEM_NUMBER") or row.get("product_sku") or ""),
        supply_qty=qty,
        available_qty=available,
        uom=str(row.get("PRIMARY_UOM_CODE") or row.get("uom") or "Ea"),
        supply_date=_parse_ebs_date(raw_date),
        status=status_map.get(status_code, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_ebs_onhand_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map an Oracle EBS MTL_ONHAND_QUANTITIES_DETAIL row to AxonSupplyItem (on_hand).

    Expected row keys:
      INVENTORY_ITEM_ID, ORGANIZATION_ID, SUBINVENTORY_CODE,
      TRANSACTION_QUANTITY (on-hand qty), PRIMARY_UOM_CODE
    """
    item_id = row.get("INVENTORY_ITEM_ID") or row.get("inventory_item_id")
    org_id = row.get("ORGANIZATION_ID") or row.get("organization_id")
    subinv = str(row.get("SUBINVENTORY_CODE") or row.get("location_ref") or "")
    on_hand = float(row.get("TRANSACTION_QUANTITY") or row.get("on_hand_qty") or 0.0)
    row_id = f"{org_id}-{subinv}-{item_id}"

    return AxonSupplyItem(
        id=_counter("stock", row_id),
        source_type=AxonSupplySource.ON_HAND,
        source_ref="stock",
        erp_id=None,
        product_id=_counter("item", item_id),
        product_name=str(row.get("ITEM_NAME") or row.get("product_name") or item_id or ""),
        product_sku=str(row.get("ITEM_NUMBER") or row.get("product_sku") or ""),
        supply_qty=on_hand,
        available_qty=on_hand,
        uom=str(row.get("PRIMARY_UOM_CODE") or row.get("uom") or "Ea"),
        supply_date=date.today(),
        location_ref=f"{org_id}/{subinv}" if subinv else str(org_id),
        status=AxonSupplyStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Allocation mappers ────────────────────────────────────────────────────────

def axon_ebs_requisition_row_to_allocation(row: dict) -> AxonAllocation:
    """
    Map an Oracle EBS PO_REQUISITIONS_INTERFACE_ALL / requisition row to AxonAllocation.

    Used when reading back a requisition that Axon created (write-back confirmation).

    Expected row keys:
      REQUISITION_LINE_ID, REQUISITION_HEADER_ID, INVENTORY_ITEM_ID,
      QUANTITY, ALLOCATION_STATUS, DEMAND_REF, SUPPLY_REF
    """
    item_id = row.get("INVENTORY_ITEM_ID") or row.get("inventory_item_id")
    row_id = row.get("REQUISITION_LINE_ID") or row.get("id")
    status_raw = str(row.get("ALLOCATION_STATUS") or row.get("status") or "draft").lower()
    try:
        status = AxonAllocationStatus(status_raw)
    except ValueError:
        status = AxonAllocationStatus.DRAFT

    return AxonAllocation(
        id=_counter("alloc", row_id),
        erp_id=int(row_id) if str(row_id).isdigit() else None,
        demand_id=_counter("demand", row.get("demand_ref") or row.get("DEMAND_ID") or row_id),
        supply_id=_counter("po", row.get("supply_ref") or row.get("PO_LINE_ID") or row_id),
        demand_ref=str(row.get("demand_ref") or row.get("DEMAND_REFERENCE") or ""),
        supply_ref=str(row.get("supply_ref") or row.get("SUPPLY_REFERENCE") or ""),
        product_id=_counter("item", item_id),
        product_name=str(row.get("ITEM_NAME") or row.get("product_name") or item_id or ""),
        allocated_qty=float(row.get("QUANTITY") or row.get("allocated_qty") or 0.0),
        uom=str(row.get("UNIT_OF_MEASURE") or row.get("uom") or "Ea"),
        status=status,
        ai_context=str(row.get("ai_context") or row.get("JUSTIFICATION") or ""),
        metadata={"_erp": _ERP, "_raw": row},
    )
