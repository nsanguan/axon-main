"""
adapters.dynamics365 — Microsoft Dynamics 365 SCM Protocol Implementations.

This package will house concrete implementations of the Axon provider
protocols for Microsoft Dynamics 365 Supply Chain Management (D365 SCM):

  demand.py    — AxonDemandProvider for D365 (calls axon_d365_get_demand via MCP)
  supply.py    — AxonSupplyProvider for D365 (calls axon_d365_get_supply / axon_d365_get_stock)
  allocation.py — AxonAllocationWriter for D365 (calls axon_d365_create_pr / axon_d365_confirm_po)
  activity.py  — AxonActivityWriter for D365 (calls axon_d365_create_activity / check)
  chatter.py   — AxonReasoningLogger for D365 (calls axon_d365_post_comment)

These implementations are called by orchestrator nodes to remain ERP-agnostic.
Each implementation:
  1. Calls the appropriate MCP tool via the Dynamics 365 MCP server
  2. Feeds the result through adapters/mapping/dynamics365.py to produce universal schema objects
  3. Returns AxonDemandItem / AxonSupplyItem / AxonAllocation to the orchestrator

Activation: set MCP_D365_PLANNING_URL / MCP_D365_PROCUREMENT_URL / MCP_D365_INVENTORY_URL in .env
"""
