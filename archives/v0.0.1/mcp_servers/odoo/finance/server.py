"""mcp_servers.odoo.finance.server — Finance MCP server entry point."""
from mcp_servers.odoo.finance import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_finance_port)
