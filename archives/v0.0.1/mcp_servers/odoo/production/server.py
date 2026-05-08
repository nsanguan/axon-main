"""mcp_servers.odoo.production.server — Production Planning MCP server entry point."""
from mcp_servers.odoo.production import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_production_port)
