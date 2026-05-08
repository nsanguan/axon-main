"""
adapters.oracle_ebs — Oracle EBS Protocol Implementations.

This package will house concrete implementations of the Axon provider
protocols for Oracle E-Business Suite (EBS):

  demand.py    — AxonDemandProvider for EBS (calls axon_ebs_get_demand via MCP)
  supply.py    — AxonSupplyProvider for EBS (calls axon_ebs_get_supply / axon_ebs_get_stock)
  allocation.py — AxonAllocationWriter for EBS (calls axon_ebs_create_requisition / axon_ebs_confirm_po)
  activity.py  — AxonActivityWriter for EBS (calls axon_ebs_create_activity / check)
  chatter.py   — AxonReasoningLogger for EBS (calls axon_ebs_post_comment)

These implementations are called by orchestrator nodes to remain ERP-agnostic.
Each implementation:
  1. Calls the appropriate MCP tool via the Oracle EBS MCP server
  2. Feeds the result through adapters/mapping/oracle_ebs.py to produce universal schema objects
  3. Returns AxonDemandItem / AxonSupplyItem / AxonAllocation to the orchestrator

Activation: set MCP_EBS_PLANNING_URL / MCP_EBS_PROCUREMENT_URL / MCP_EBS_INVENTORY_URL in .env
"""
