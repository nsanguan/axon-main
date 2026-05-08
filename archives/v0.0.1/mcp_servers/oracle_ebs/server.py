"""
mcp_servers.oracle_ebs.server — Oracle E-Business Suite MCP Adapter (Placeholder).

Exposes Oracle EBS planning, procurement, and inventory data to the Axon
reasoning layer via SSE transport.  Implement each tool using cx_Oracle or
the Oracle EBS REST Services / SOAP APIs.

Tools exposed (all prefixed axon_):
  axon_ebs_get_demand          — read MDS/MRP demand from MRP_GROSS_REQUIREMENTS
  axon_ebs_get_supply          — read supply from WIP + PO_REQUISITIONS + MTL_ONHAND
  axon_ebs_get_stock           — on-hand stock from MTL_ONHAND_QUANTITIES_DETAIL
  axon_ebs_create_requisition  — create a Purchase Requisition (PO_REQUISITIONS_INTERFACE)
  axon_ebs_confirm_po          — approve a PO via PO_APPROVALS API
  axon_ebs_post_comment        — write AI reasoning to FND_NOTES / workflow notes
  axon_ebs_create_activity     — create an approval workflow notification (HITL)
  axon_ebs_check_activity_done — poll WF_NOTIFICATIONS for completion

To activate:
  1. Set MCP_EBS_PLANNING_URL=http://<host>:8020/sse in .env
  2. Set MCP_EBS_PROCUREMENT_URL and MCP_EBS_INVENTORY_URL similarly
  3. Set EBS_DB_DSN, EBS_DB_USER, EBS_DB_PASSWORD in .env (cx_Oracle connection)
  4. Run: python mcp_servers/oracle_ebs/server.py

Transport: SSE (FastMCP)
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-oracle-ebs",
    instructions=(
        "Oracle E-Business Suite adapter for Axon. "
        "Tools map EBS MRP demand, WIP/PO supply, and MTL on-hand data "
        "into Axon's universal AxonDemandItem / AxonSupplyItem schema."
    ),
)


# ── Input / output models ─────────────────────────────────────────────────────


class EbsDemandQuery(BaseModel):
    organization_id: int = Field(description="EBS inventory organization ID")
    plan_name: str = Field(description="MPS/MRP plan name (e.g. 'MASTER_PLAN')")
    item_number: str | None = Field(None, description="Inventory item number filter")
    date_from: str | None = Field(None, description="Demand date from (YYYY-MM-DD)")
    date_to: str | None = Field(None, description="Demand date to (YYYY-MM-DD)")
    limit: int = Field(500, description="Max records to return")


class EbsSupplyQuery(BaseModel):
    organization_id: int = Field(description="EBS inventory organization ID")
    item_number: str | None = Field(None, description="Inventory item number filter")
    supply_types: list[str] = Field(
        default_factory=lambda: ["PO", "WO", "REQ"],
        description="Supply types: PO (purchase order), WO (work order), REQ (requisition)",
    )
    date_from: str | None = Field(None, description="Expected receipt date from (YYYY-MM-DD)")
    limit: int = Field(500, description="Max records to return")


class EbsOnHandQuery(BaseModel):
    organization_id: int = Field(description="EBS inventory organization ID")
    item_number: str = Field(description="Inventory item number")
    subinventory: str | None = Field(None, description="Optional subinventory filter")


class EbsRequisitionInput(BaseModel):
    organization_id: int = Field(description="EBS inventory organization ID")
    item_number: str = Field(description="Inventory item number")
    quantity: float = Field(description="Required quantity")
    need_by_date: str = Field(description="Need-by date (YYYY-MM-DD)")
    suggested_vendor: str | None = Field(None, description="Suggested vendor name")
    ai_context: str = Field(description="AI reasoning — written to requisition description")


class EbsPoApprovalInput(BaseModel):
    po_header_id: int = Field(description="EBS PO_HEADERS_ALL.PO_HEADER_ID")
    action: str = Field("APPROVE", description="Workflow action: APPROVE or REJECT")
    ai_context: str = Field(description="AI reasoning context for audit trail")


class EbsCommentInput(BaseModel):
    entity_name: str = Field(description="EBS entity name (e.g. 'PO_HEADERS_ALL')")
    pk1_value: str = Field(description="Primary key value (e.g. PO_HEADER_ID)")
    note_text: str = Field(description="AI reasoning text to post as FND note")
    ai_context: str = Field(description="AI reasoning context for audit trail")


class EbsActivityInput(BaseModel):
    item_type: str = Field(description="Oracle Workflow item type (e.g. 'POAPPRV')")
    item_key: str = Field(description="Workflow item key (unique per instance)")
    notification_subject: str = Field(description="HITL notification subject")
    notification_body: str = Field(description="HITL notification body (include AI reasoning)")
    recipient_role: str = Field(description="Oracle WF role to notify (e.g. 'PROCUREMENT_MGR')")


class EbsActivityStatusQuery(BaseModel):
    notification_id: int = Field(description="WF_NOTIFICATIONS.NOTIFICATION_ID to poll")


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def axon_ebs_get_demand(query: EbsDemandQuery) -> list[dict]:
    """
    [TODO] Fetch MRP/MDS demand elements from Oracle EBS.

    Implementation guide:
      - Query MRP_GROSS_REQUIREMENTS or MSC_DEMANDS for the given plan
      - Map demand_type to AxonDemandSource (FORECAST, SALE_ORDER, etc.)
      - Return list of dicts matching AxonDemandItem field names:
        {id, source_type, source_ref, product_id, demand_qty, demand_date, status}

    Oracle tables:
      MRP_GROSS_REQUIREMENTS  — MRP demand details
      MRP_PLANS               — plan metadata
      MSC_DEMANDS             — ASCP demand (if using Oracle ASCP)
    """
    raise NotImplementedError(
        "Oracle EBS demand adapter not implemented. "
        "Use cx_Oracle: cx_Oracle.connect(dsn=EBS_DB_DSN) and query MRP_GROSS_REQUIREMENTS."
    )


@mcp.tool()
def axon_ebs_get_supply(query: EbsSupplyQuery) -> list[dict]:
    """
    [TODO] Fetch open supply (POs, WOs, requisitions) from Oracle EBS.

    Implementation guide:
      - PO supply: query PO_LINES_ALL + PO_LINE_LOCATIONS_ALL for open POs
      - WO supply: query WIP_DISCRETE_JOBS for open work orders
      - Map to AxonSupplyItem field names:
        {id, source_type, source_ref, product_id, supply_qty, available_qty, supply_date}

    Oracle tables:
      PO_HEADERS_ALL / PO_LINES_ALL / PO_LINE_LOCATIONS_ALL
      WIP_DISCRETE_JOBS
      PO_REQUISITIONS_INTERFACE_ALL
    """
    raise NotImplementedError(
        "Oracle EBS supply adapter not implemented. "
        "Query PO_LINES_ALL and WIP_DISCRETE_JOBS via cx_Oracle."
    )


@mcp.tool()
def axon_ebs_get_stock(query: EbsOnHandQuery) -> float:
    """
    [TODO] Fetch on-hand quantity from Oracle EBS MTL_ONHAND_QUANTITIES_DETAIL.

    Implementation guide:
      - Query MTL_ONHAND_QUANTITIES_DETAIL where INVENTORY_ITEM_ID matches item_number
      - Join MTL_SYSTEM_ITEMS_B for item lookup
      - Sum PRIMARY_TRANSACTION_QUANTITY grouped by ORGANIZATION_ID
      - Return total on-hand as float

    Oracle table:
      MTL_ONHAND_QUANTITIES_DETAIL
    """
    raise NotImplementedError(
        "Oracle EBS stock adapter not implemented. "
        "Query MTL_ONHAND_QUANTITIES_DETAIL via cx_Oracle."
    )


@mcp.tool()
def axon_ebs_create_requisition(input: EbsRequisitionInput) -> dict:
    """
    [TODO] Create a Purchase Requisition in Oracle EBS via the interface table.

    Implementation guide:
      - INSERT into PO_REQUISITIONS_INTERFACE_ALL with PROCESS_FLAG='PENDING'
      - Call FND_REQUEST.SUBMIT_REQUEST('PO','REQIMPORT',...) to trigger import
      - Write ai_context to DESCRIPTION or ATTRIBUTE1 column
      - Return {requisition_number, status, message}

    Oracle table:
      PO_REQUISITIONS_INTERFACE_ALL  — staging table for requisition import
    """
    raise NotImplementedError(
        "Oracle EBS requisition adapter not implemented. "
        "Insert into PO_REQUISITIONS_INTERFACE_ALL and call REQIMPORT concurrent program."
    )


@mcp.tool()
def axon_ebs_confirm_po(input: EbsPoApprovalInput) -> dict:
    """
    [TODO] Approve or reject a PO via Oracle Workflow / PO Approval API.

    Implementation guide:
      - Call PO_DOCUMENT_ACTION_PVT.do_action (via DBMS_JAVA or EBS REST)
      - Or submit WF_ENGINE.HandleError for workflow action
      - Write ai_context to PO_HEADERS_ALL.ATTRIBUTE1 or FND_NOTES
      - Return {po_number, new_status, message}
    """
    raise NotImplementedError(
        "Oracle EBS PO approval adapter not implemented. "
        "Use PO_DOCUMENT_ACTION_PVT.do_action or the EBS REST API."
    )


@mcp.tool()
def axon_ebs_post_comment(input: EbsCommentInput) -> dict:
    """
    [TODO] Write AI reasoning to Oracle EBS as an FND note.

    Implementation guide:
      - INSERT into FND_NOTES with SOURCE_OBJECT_CODE matching entity_name
      - Set NOTES = note_text, SOURCE_OBJECT_ID = pk1_value
      - Return {note_id, status}

    Oracle table:
      FND_NOTES — generic notes attached to any EBS entity
    """
    raise NotImplementedError(
        "Oracle EBS notes adapter not implemented. "
        "Insert into FND_NOTES via cx_Oracle."
    )


@mcp.tool()
def axon_ebs_create_activity(input: EbsActivityInput) -> dict:
    """
    [TODO] Create an Oracle Workflow notification for HITL approval.

    Implementation guide:
      - Call WF_ENGINE.CreateProcess and WF_ENGINE.StartProcess
      - Or call WF_NOTIFICATION.Send to raise a standalone notification
      - Return {notification_id, message_id}
    """
    raise NotImplementedError(
        "Oracle EBS workflow notification adapter not implemented. "
        "Use WF_NOTIFICATION.Send or WF_ENGINE via cx_Oracle."
    )


@mcp.tool()
def axon_ebs_check_activity_done(query: EbsActivityStatusQuery) -> dict:
    """
    [TODO] Poll whether an Oracle Workflow notification has been actioned.

    Implementation guide:
      - SELECT STATUS, RESPONDER, RESPOND_DATE
        FROM WF_NOTIFICATIONS WHERE NOTIFICATION_ID = :id
      - Return {done: bool, status, responder, respond_date}

    Oracle table:
      WF_NOTIFICATIONS
    """
    raise NotImplementedError(
        "Oracle EBS workflow status adapter not implemented. "
        "Query WF_NOTIFICATIONS via cx_Oracle."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_EBS_PLANNING_PORT", "8020"))
    mcp.run(transport="sse", port=port)
