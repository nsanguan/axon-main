"""mcp_servers.odoo.qa.server — Quality Assurance MCP server entry point."""
from mcp_servers.odoo.qa import mcp

if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_qa_port)
