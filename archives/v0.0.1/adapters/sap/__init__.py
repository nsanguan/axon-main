"""
adapters.sap — SAP Protocol Implementations.

This package will house concrete implementations of the Axon provider
protocols for SAP:

  demand.py    — AxonDemandProvider for SAP (calls axon_sap_get_demand via MCP)
  supply.py    — AxonSupplyProvider for SAP (calls axon_sap_get_supply / axon_sap_get_stock)
  allocation.py — AxonAllocationWriter for SAP (calls axon_sap_create_pr / axon_sap_confirm_po)
  activity.py  — AxonActivityWriter for SAP (calls axon_sap_create_activity / check)
  chatter.py   — AxonReasoningLogger for SAP (calls axon_sap_post_comment)

These implementations are called by orchestrator nodes to remain ERP-agnostic.
Each implementation:
  1. Calls the appropriate MCP tool via the SAP MCP server
  2. Feeds the result through adapters/mapping/sap.py to produce universal schema objects
  3. Returns AxonDemandItem / AxonSupplyItem / AxonAllocation to the orchestrator

Activation: set MCP_SAP_PLANNING_URL / MCP_SAP_PROCUREMENT_URL / MCP_SAP_INVENTORY_URL in .env
"""
