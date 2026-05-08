"""
mcp_servers.odoo.logistics.server — Logistics & Distribution MCP server entry point.

Run with:  python -m mcp_servers.odoo.logistics.server
"""
from mcp_servers.odoo.logistics import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_logistics_port)
