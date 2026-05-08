"""
adapters.mapping.sap — SAP → Axon Universal Schema Mapper.

Translates raw dict records returned by the SAP MCP server tools
(axon_sap_get_demand, axon_sap_get_supply, axon_sap_get_stock)
into Axon's universal schema objects.

SAP field → Axon field mappings:
  MD04 / BAPI_MATERIAL_AVAILABILITY demand row → AxonDemandItem
  ME2M / BAPI purchase order row              → AxonSupplyItem (purchase_order)
  BAPI_PRODORD_GET_LIST production order row  → AxonSupplyItem (manufacturing_order)
  MARD / BAPI_MATERIAL_AVAILABILITY stock row → AxonSupplyItem (on_hand)
  Allocation write-back row                   → AxonAllocation

SAP MRP element type codes (SOBKZ / OTYPE):
  KU = Customer Order (sale demand)
  VP = Forecast Consumption
  PIR = Planned Independent Requirement (MPS)
  AF = Order Reservation (MRP)
  NB = Purchase Order
  WO = Work Order / Production Order
  TR = Stock Transfer
"""

from __future__ import annotations

from datetime import date

from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus
from core.schema.allocation import AxonAllocation, AxonAllocationStatus

_ERP = "sap"

# ── Internal helpers ──────────────────────────────────────────────────────────

_SAP_MRP_ELEMENT_TO_DEMAND_SOURCE: dict[str, AxonDemandSource] = {
    "KU":  AxonDemandSource.SALE_ORDER,
    "KUNA": AxonDemandSource.SALE_ORDER,
    "VP":  AxonDemandSource.FORECAST,
    "PIR": AxonDemandSource.MPS,
    "AF":  AxonDemandSource.MRP,
    "PRTO": AxonDemandSource.TRANSFER,
}

_SAP_MRP_ELEMENT_TO_SUPPLY_SOURCE: dict[str, AxonSupplySource] = {
    "NB":   AxonSupplySource.PURCHASE_ORDER,
    "WO":   AxonSupplySource.MANUFACTURING_ORDER,
    "TR":   AxonSupplySource.TRANSFER,
    "UB":   AxonSupplySource.TRANSFER,    # stock transport order
    "PLO":  AxonSupplySource.MANUFACTURING_ORDER,  # planned order
}

_SAP_DEMAND_STATUS_MAP: dict[str, AxonDemandStatus] = {
    "OPEN": AxonDemandStatus.OPEN,
    "PART": AxonDemandStatus.PARTIAL,
    "COMP": AxonDemandStatus.CLOSED,
    "EXCP": AxonDemandStatus.EXCEPTION,
}

_SAP_SUPPLY_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "OPEN":    AxonSupplyStatus.OPEN,
    "PARTIAL": AxonSupplyStatus.PARTIAL,
    "GR":      AxonSupplyStatus.RECEIVED,    # Goods Receipt posted
    "CANC":    AxonSupplyStatus.CANCELLED,
}


def _parse_sap_date(value: str | None) -> date:
    """Parse SAP date strings: YYYYMMDD or YYYY-MM-DD."""
    if not value:
        return date.today()
    value = str(value).strip()
    # SAP native format YYYYMMDD (8 digits, no separators)
    if len(value) == 8 and value.isdigit():
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        except ValueError:
            pass
    # ISO fallback
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return date.today()


def _counter(prefix: str, value: int | str | None) -> str:
    return f"{_ERP}:{prefix}:{value}" if value is not None else f"{_ERP}:{prefix}:unknown"


# ── Demand mappers ────────────────────────────────────────────────────────────

def axon_sap_demand_row_to_item(row: dict) -> AxonDemandItem:
    """
    Map a SAP MD04 / BAPI_MATERIAL_AVAILABILITY demand row to AxonDemandItem.

    Expected row keys (BAPI_MATERIAL_AVAILABILITY MDPS output):
      MATDOC_ITEM, SOBKZ (MRP element type), MATNR (material), WERKS (plant),
      DELKZ (MRP sub-element), DMDNR (item), BDMNG (requirement qty),
      AUFNR / VBELN (order/SO number), BEDAT / BSDAT (requirement date),
      WBS_ELEMENT, KOSTL
    """
    mrp_type = str(row.get("SOBKZ") or row.get("element_type") or "AF").strip()
    ref = (
        row.get("AUFNR")
        or row.get("VBELN")
        or row.get("BSTNR")
        or row.get("source_ref", "")
    )
    material = str(row.get("MATNR") or row.get("material") or "")
    demand_qty = float(row.get("BDMNG") or row.get("demand_qty") or 0.0)
    confirmed_qty = float(row.get("LGMNG") or row.get("confirmed_qty") or 0.0)
    raw_date = row.get("BEDAT") or row.get("BSDAT") or row.get("demand_date")
    row_id = row.get("DMDNR") or row.get("id") or ref or material
    status_raw = str(row.get("status") or "OPEN").upper()

    return AxonDemandItem(
        id=_counter("demand", row_id),
        source_type=_SAP_MRP_ELEMENT_TO_DEMAND_SOURCE.get(mrp_type, AxonDemandSource.MRP),
        source_ref=str(ref),
        erp_id=None,
        product_id=_counter("material", material),
        product_name=str(row.get("MAKTX") or row.get("product_name") or material),
        product_sku=material,
        demand_qty=demand_qty,
        confirmed_qty=confirmed_qty,
        uom=str(row.get("MEINS") or row.get("uom") or "EA"),
        demand_date=_parse_sap_date(raw_date),
        status=_SAP_DEMAND_STATUS_MAP.get(status_raw, AxonDemandStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Supply mappers ────────────────────────────────────────────────────────────

def axon_sap_supply_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a SAP ME2M purchase order / production order row to AxonSupplyItem.

    Expected row keys (ME2M / BAPI_PRODORD_GET_LIST output):
      EBELN / AUFNR (doc number), MATNR (material), WERKS (plant),
      MENGE (order qty), WEMNG (GR qty), EINDT (delivery date),
      LIFNR (vendor), SOBKZ (element type)
    """
    mrp_type = str(row.get("SOBKZ") or row.get("element_type") or "NB").strip()
    ref = (
        row.get("EBELN")      # PO number
        or row.get("AUFNR")   # production order
        or row.get("UMLGO")   # transfer order
        or row.get("source_ref", "")
    )
    material = str(row.get("MATNR") or row.get("material") or "")
    supply_qty = float(row.get("MENGE") or row.get("supply_qty") or 0.0)
    gr_qty = float(row.get("WEMNG") or row.get("received_qty") or 0.0)
    available_qty = supply_qty - gr_qty
    raw_date = row.get("EINDT") or row.get("PSTTR") or row.get("supply_date")
    row_id = row.get("EBELN") or row.get("AUFNR") or row.get("id") or material
    status_raw = str(row.get("status") or "OPEN").upper()

    return AxonSupplyItem(
        id=_counter("supply", row_id),
        source_type=_SAP_MRP_ELEMENT_TO_SUPPLY_SOURCE.get(mrp_type, AxonSupplySource.PURCHASE_ORDER),
        source_ref=str(ref),
        erp_id=None,
        product_id=_counter("material", material),
        product_name=str(row.get("MAKTX") or row.get("product_name") or material),
        product_sku=material,
        supply_qty=supply_qty,
        available_qty=max(available_qty, 0.0),
        uom=str(row.get("MEINS") or row.get("uom") or "EA"),
        supply_date=_parse_sap_date(raw_date),
        vendor_ref=str(row.get("LIFNR") or row.get("vendor_ref") or ""),
        location_ref=str(row.get("LGORT") or row.get("WERKS") or ""),
        status=_SAP_SUPPLY_STATUS_MAP.get(status_raw, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_sap_stock_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a SAP MARD / BAPI_MATERIAL_AVAILABILITY unrestricted stock row to AxonSupplyItem.

    Expected row keys:
      MATNR (material), WERKS (plant), LGORT (storage location),
      LABST (unrestricted stock qty), MEINS (UoM)
    """
    material = str(row.get("MATNR") or row.get("material") or "")
    plant = str(row.get("WERKS") or row.get("plant") or "")
    sloc = str(row.get("LGORT") or row.get("storage_location") or "")
    on_hand = float(row.get("LABST") or row.get("AV_QTY_PLT") or row.get("on_hand_qty") or 0.0)
    row_id = f"{plant}-{sloc}-{material}"

    return AxonSupplyItem(
        id=_counter("stock", row_id),
        source_type=AxonSupplySource.ON_HAND,
        source_ref="stock",
        erp_id=None,
        product_id=_counter("material", material),
        product_name=str(row.get("MAKTX") or row.get("product_name") or material),
        product_sku=material,
        supply_qty=on_hand,
        available_qty=on_hand,
        uom=str(row.get("MEINS") or row.get("uom") or "EA"),
        supply_date=date.today(),
        location_ref=f"{plant}/{sloc}" if sloc else plant,
        status=AxonSupplyStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Allocation mappers ────────────────────────────────────────────────────────

def axon_sap_allocation_row_to_allocation(row: dict) -> AxonAllocation:
    """
    Map a SAP MD04 pegging or Axon allocation write-back row to AxonAllocation.

    Used when reading back an allocation record that was written to SAP
    (e.g. from a custom Z-table or from the Axon legacy audit record).
    """
    material = str(row.get("MATNR") or row.get("material") or "")
    row_id = row.get("id") or row.get("DMDNR") or material
    status_raw = str(row.get("status") or "draft").lower()
    try:
        status = AxonAllocationStatus(status_raw)
    except ValueError:
        status = AxonAllocationStatus.DRAFT

    return AxonAllocation(
        id=_counter("alloc", row_id),
        erp_id=None,
        demand_id=_counter("demand", row.get("demand_ref") or row.get("DMDNR") or row_id),
        supply_id=_counter("supply", row.get("supply_ref") or row.get("EBELN") or row_id),
        demand_ref=str(row.get("demand_ref") or row.get("VBELN") or ""),
        supply_ref=str(row.get("supply_ref") or row.get("EBELN") or ""),
        product_id=_counter("material", material),
        product_name=str(row.get("MAKTX") or row.get("product_name") or material),
        allocated_qty=float(row.get("allocated_qty") or row.get("BDMNG") or 0.0),
        uom=str(row.get("MEINS") or row.get("uom") or "EA"),
        status=status,
        ai_context=str(row.get("ai_context") or ""),
        metadata={"_erp": _ERP, "_raw": row},
    )
