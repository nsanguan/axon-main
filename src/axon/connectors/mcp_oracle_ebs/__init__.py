"""Oracle EBS MCP Connector — MCP client only. Connects to separate mcp-oracle-ebs project.

The connector provides:
  - OracleEBSConnector — full Oracle EBS tool surface (legacy/composite)
  - BuyerAgent — sub-agent focused on procurement operations
  - StoreAgent — sub-agent focused on inventory/warehouse operations
"""

from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector
from axon.connectors.mcp_oracle_ebs.mcp_agent_buyer import BuyerAgent
from axon.connectors.mcp_oracle_ebs.mcp_agent_store import StoreAgent

__all__ = [
    "OracleEBSConnector",
    "BuyerAgent",
    "StoreAgent",
]
