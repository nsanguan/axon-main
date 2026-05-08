"""
mcp_servers.sap.server — SAP MCP Adapter (Placeholder).

Exposes SAP planning, procurement, and inventory data to the Axon
reasoning layer via SSE transport.  Implement each tool using the
python-sapnwrfc (pyrfc) library for RFC/BAPI calls, or the SAP OData
/ REST API for S/4HANA Cloud.

Tools exposed (all prefixed axon_):
  axon_sap_get_demand        — MRP demand from MD04 / BAPI_MATERIAL_AVAILABILITY
  axon_sap_get_supply        — open POs / production orders from ME2M / MD04
  axon_sap_get_stock         — on-hand stock from MARD / BAPI_MATERIAL_AVAILABILITY
  axon_sap_create_pr         — create a Purchase Requisition via BAPI_PR_CREATE
  axon_sap_confirm_po        — confirm / approve a PO via ME_APPROVE_PURCHASE_ORDER
  axon_sap_post_comment      — write AI reasoning to SAP long text (BAPI_LONGTEXT_INSERT)
  axon_sap_create_activity   — create a SAP workflow task for HITL approval
  axon_sap_check_activity_done — poll SAP workflow task for completion

To activate:
  1. Set MCP_SAP_PLANNING_URL=http://<host>:8010/sse in .env
  2. Set MCP_SAP_PROCUREMENT_URL and MCP_SAP_INVENTORY_URL similarly
  3. Set SAP_ASHOST, SAP_SYSNR, SAP_CLIENT, SAP_USER, SAP_PASSWORD in .env
  4. Run: python mcp_servers/sap/server.py

Transport: SSE (FastMCP)
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-sap",
    instructions=(
        "SAP Planning, Inventory & Procurement adapter for Axon. "
        "Tools map SAP MD04 / ME2M / MARD / BAPI data into Axon's universal "
        "AxonDemandItem / AxonSupplyItem schema. "
        "Implemented via pyrfc (RFC/BAPI) or SAP OData for S/4HANA Cloud."
    ),
)


# ── Input / output models ─────────────────────────────────────────────────────


class SapDemandQuery(BaseModel):
    plant: str = Field(description="SAP plant code (e.g. '1000')")
    material: str | None = Field(None, description="SAP material number filter")
    mrp_date: str | None = Field(None, description="MRP date filter (YYYYMMDD)")
    limit: int = Field(500, description="Max records to return")


class SapSupplyQuery(BaseModel):
    plant: str = Field(description="SAP plant code")
    material: str | None = Field(None, description="SAP material number filter")
    supply_types: list[str] = Field(
        default_factory=lambda: ["NB", "WO", "TR"],
        description="MRP element types: NB (PO), WO (Work Order), TR (Transfer)",
    )
    date_from: str | None = Field(None, description="Expected date from (YYYYMMDD)")


class SapStockQuery(BaseModel):
    plant: str = Field(description="SAP plant code")
    material: str = Field(description="SAP material number")
    storage_location: str | None = Field(None, description="Optional storage location filter")


class SapPrInput(BaseModel):
    plant: str = Field(description="SAP plant code")
    material: str = Field(description="SAP material number")
    quantity: float = Field(description="Required quantity")
    delivery_date: str = Field(description="Required delivery date (YYYYMMDD)")
    purchase_group: str = Field("001", description="SAP purchasing group")
    vendor: str | None = Field(None, description="Suggested vendor number")
    ai_context: str = Field(description="AI reasoning — written to PR long text")


class SapPoApprovalInput(BaseModel):
    po_number: str = Field(description="SAP PO number (EBELN, e.g. '4500001234')")
    action: str = Field("APPROVE", description="Workflow action: APPROVE or REJECT")
    ai_context: str = Field(description="AI reasoning context for SAP long text")


class SapCommentInput(BaseModel):
    object_type: str = Field(description="SAP text object type (e.g. 'EKKO' for PO header)")
    object_key: str = Field(description="SAP object key (e.g. PO number '4500001234')")
    text_id: str = Field("F01", description="SAP text ID")
    note_text: str = Field(description="AI reasoning text to write as SAP long text")


class SapActivityInput(BaseModel):
    work_item_agent: str = Field(description="SAP workflow agent (user ID or role)")
    task_id: str = Field(description="SAP workflow task code (TS* or WS*)")
    subject: str = Field(description="Workflow work item subject")
    instruction: str = Field(description="Instructions for the approver (include AI reasoning)")
    object_key: str = Field(description="Business object key (e.g. PO number)")


class SapActivityStatusQuery(BaseModel):
    work_item_id: str = Field(description="SAP workflow work item ID (WORKITEMID)")


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def axon_sap_get_demand(query: SapDemandQuery) -> list[dict]:
    """
    [TODO] Fetch MRP demand elements from SAP MD04 / BAPI_MATERIAL_AVAILABILITY.

    Implementation guide:
      - Call RFC BAPI_MATERIAL_AVAILABILITY or MD_MRP_ITEMS_API_READ
      - Map MRP element type to AxonDemandSource (KU=SalesOrder, AF=Forecast, etc.)
      - Return list of dicts matching AxonDemandItem field names:
        {id, source_type, source_ref, product_id, demand_qty, demand_date, status}

    Example pyrfc call:
      conn.call('BAPI_MATERIAL_AVAILABILITY',
                PLANT=query.plant, MATERIAL=query.material,
                UNIT='PC', MRP_ACTIVE='X')
    """
    raise NotImplementedError(
        "SAP demand adapter not implemented. "
        "Use pyrfc: conn.call('BAPI_MATERIAL_AVAILABILITY', PLANT=query.plant)"
    )


@mcp.tool()
def axon_sap_get_supply(query: SapSupplyQuery) -> list[dict]:
    """
    [TODO] Fetch open supply (POs, WOs, transfers) from SAP ME2M / MD04.

    Implementation guide:
      - Call RFC ME_READ_PURCHASING_DOCUMENT or query EKKO/EKPO tables
      - Production orders: BAPI_PRODORD_GET_LIST
      - Map to AxonSupplyItem field names:
        {id, source_type, source_ref, product_id, supply_qty, available_qty, supply_date}

    Example pyrfc call:
      conn.call('BAPI_GOODSMVT_GETDETAIL', MATERIAL=query.material, PLANT=query.plant)
    """
    raise NotImplementedError(
        "SAP supply adapter not implemented. "
        "Use pyrfc to call ME_READ_PURCHASING_DOCUMENT or query EKKO/EKPO."
    )


@mcp.tool()
def axon_sap_get_stock(query: SapStockQuery) -> float:
    """
    [TODO] Fetch unrestricted on-hand stock from SAP MARD / BAPI_MATERIAL_AVAILABILITY.

    Implementation guide:
      - Call BAPI_MATERIAL_AVAILABILITY with ONLY_STOCK=X
      - Or direct RFC read of MARD table (unrestricted stock)
      - Return total unrestricted quantity as float

    Example pyrfc call:
      result = conn.call('BAPI_MATERIAL_AVAILABILITY',
                         PLANT=query.plant, MATERIAL=query.material)
      return result['AV_QTY_PLT']
    """
    raise NotImplementedError(
        "SAP stock adapter not implemented. "
        "Use pyrfc: conn.call('BAPI_MATERIAL_AVAILABILITY', PLANT=..., MATERIAL=...)"
    )


@mcp.tool()
def axon_sap_create_pr(input: SapPrInput) -> dict:
    """
    [TODO] Create a Purchase Requisition in SAP via BAPI_PR_CREATE.

    Implementation guide:
      - Build PRHEADER and PRITEM tables for BAPI_PR_CREATE
      - Write ai_context via BAPI_LONGTEXT_INSERT to BANFN (PR number) long text
      - Return {pr_number, item_number, status, message}

    Example pyrfc call:
      result = conn.call('BAPI_PR_CREATE',
                         PRHEADER={'PRTYPE': 'NB', 'PURGR': input.purchase_group},
                         PRITEM=[{...}])
    """
    raise NotImplementedError(
        "SAP PR adapter not implemented. "
        "Use pyrfc: conn.call('BAPI_PR_CREATE', PRHEADER=..., PRITEM=[...])"
    )


@mcp.tool()
def axon_sap_confirm_po(input: SapPoApprovalInput) -> dict:
    """
    [TODO] Approve a SAP Purchase Order via ME_APPROVE_PURCHASE_ORDER or workflow API.

    Implementation guide:
      - Call ME_APPROVE_PURCHASE_ORDER RFC or use SAP workflow SWIA* BAPIs
      - Write ai_context to PO long text via BAPI_LONGTEXT_INSERT
      - Return {po_number, new_status, message}

    Example pyrfc call:
      conn.call('ME_APPROVE_PURCHASE_ORDER', EBELN=input.po_number)
    """
    raise NotImplementedError(
        "SAP PO approval adapter not implemented. "
        "Use pyrfc: conn.call('ME_APPROVE_PURCHASE_ORDER', EBELN=input.po_number)"
    )


@mcp.tool()
def axon_sap_post_comment(input: SapCommentInput) -> dict:
    """
    [TODO] Write AI reasoning to SAP as long text (BAPI_LONGTEXT_INSERT).

    Implementation guide:
      - Call BAPI_LONGTEXT_INSERT with object_type, object_key, text_id, note_text
      - Return {status, message}

    Example pyrfc call:
      conn.call('BAPI_LONGTEXT_INSERT',
                OBJECT_TYPE=input.object_type, OBJECT_KEY=input.object_key,
                TEXT_ID=input.text_id,
                TEXT_LINES=[{'TDLINE': line} for line in input.note_text.split('\\n')])
    """
    raise NotImplementedError(
        "SAP long text adapter not implemented. "
        "Use pyrfc: conn.call('BAPI_LONGTEXT_INSERT', ...)"
    )


@mcp.tool()
def axon_sap_create_activity(input: SapActivityInput) -> dict:
    """
    [TODO] Create a SAP workflow work item for HITL approval.

    Implementation guide:
      - Call SAP Business Workplace API: SWIA_WI_FORWARD or SWI_CREATE_WORKITEM
      - Or trigger a workflow via SAP_WAPI_WORKITEM_EXECUTE
      - Return {work_item_id, status}

    Example pyrfc call:
      conn.call('SWI_CREATE_WORKITEM', WI_AAGENT=input.work_item_agent,
                WI_TEXT=input.subject, WI_RH_TASK=input.task_id)
    """
    raise NotImplementedError(
        "SAP workflow activity adapter not implemented. "
        "Use pyrfc: conn.call('SWI_CREATE_WORKITEM', ...)"
    )


@mcp.tool()
def axon_sap_check_activity_done(query: SapActivityStatusQuery) -> dict:
    """
    [TODO] Poll SAP workflow work item to check if HITL approval is complete.

    Implementation guide:
      - Call SAP_WAPI_READ_CONTAINER or SWIA_WI_GET_HEADER to read work item status
      - WI_STAT = 'READY' → pending; 'COMPLETED'/'CANCELLED' → done
      - Return {done: bool, status, completed_by, completed_at}

    Example pyrfc call:
      result = conn.call('SWIA_WI_GET_HEADER', WI_ID=query.work_item_id)
    """
    raise NotImplementedError(
        "SAP workflow status adapter not implemented. "
        "Use pyrfc: conn.call('SWIA_WI_GET_HEADER', WI_ID=query.work_item_id)"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_SAP_PLANNING_PORT", "8010"))
    mcp.run(transport="sse", port=port)
