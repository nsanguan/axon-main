"""mcp_servers.odoo.pd.server — Product Development MCP server entry point."""
from mcp_servers.odoo.pd import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_pd_port)
