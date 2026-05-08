"""
mcp_servers.odoo.sales.server — Sales & Marketing MCP server entry point.

Run with:  python -m mcp_servers.odoo.sales.server
"""
from mcp_servers.odoo.sales import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_sales_port)
