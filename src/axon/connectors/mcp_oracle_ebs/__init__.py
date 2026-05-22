"""Oracle EBS MCP Connector — MCP client only. Connects to separate mcp-oracle-ebs project.

The connector provides:
  - OracleEBSConnector — full Oracle EBS tool surface (legacy/composite)
  - BuyerAgent — sub-agent focused on procurement operations
  - StoreAgent — sub-agent focused on inventory/warehouse operations
"""

from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector
from axon.connectors.mcp_oracle_ebs.mcp_agent_buyer import BuyerAgent
from axon.connectors.mcp_oracle_ebs.mcp_agent_store import StoreAgent

# Register connector classes with the factory for dynamic loading
from axon.connectors.registry import register_connector_class

register_connector_class("oracle_ebs", OracleEBSConnector)
register_connector_class("mcp_agent_buyer", BuyerAgent)
register_connector_class("mcp_agent_store", StoreAgent)

__all__ = [
    "OracleEBSConnector",
    "BuyerAgent",
    "StoreAgent",
]
