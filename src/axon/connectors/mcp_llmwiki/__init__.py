"""LLMWiki Knowledge Bridge — connects to EraOwl-LLMWiki Company Policy MCP Server.

The LLMWiki MCP server (port 8000) exposes 24 tools for policy retrieval,
compliance checking, procurement validation, and strategic review against
the company's policy vault.

Content is served from the policy-docs vault (markdown + YAML frontmatter)
via the MCP protocol (SSE or streamable-http transport).
"""

from axon.connectors.mcp_llmwiki.client import PolicyServerClient
from axon.connectors.registry import register_connector_class

register_connector_class("llmwiki", PolicyServerClient)

__all__ = ["PolicyServerClient"]
