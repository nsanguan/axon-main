"""
adapters.legacy_db — Legacy SQL Database Protocol Implementations.

This package will house concrete implementations of the Axon provider
protocols for any legacy SQL database (MySQL, PostgreSQL, MSSQL, Oracle DB):

  demand.py    — AxonDemandProvider for legacy DB (calls axon_legacy_get_demand via MCP)
  supply.py    — AxonSupplyProvider for legacy DB (calls axon_legacy_get_supply / axon_legacy_get_on_hand)
  allocation.py — AxonAllocationWriter for legacy DB (calls axon_legacy_write_allocation)
  activity.py  — AxonActivityWriter for legacy DB (calls axon_legacy_create_activity / check)
  chatter.py   — AxonReasoningLogger for legacy DB (calls axon_legacy_post_comment)

These implementations are called by orchestrator nodes to remain ERP-agnostic.
Each implementation:
  1. Calls the appropriate MCP tool via the Legacy DB MCP server
  2. Feeds the result through adapters/mapping/legacy_db.py to produce universal schema objects
  3. Returns AxonDemandItem / AxonSupplyItem / AxonAllocation to the orchestrator

Activation: set MCP_LEGACY_DB_URL=http://<host>:8040/sse in .env
"""
