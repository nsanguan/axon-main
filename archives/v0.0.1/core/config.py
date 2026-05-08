from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Axon runtime configuration.

    All values are loaded from the .env file at the project root.

    MCP adapter URLs follow the pattern:
        MCP_<ERP>_<SERVER>_URL = http://<host>:<port>/sse

    Set a URL to a non-empty string to enable that adapter.
    Leave empty ("") to disable it — the adapter registry will skip it.
    Remote deployments just change the host/port in the URL; the agent
    code never changes.

    Supported ERP adapters (each has its own MCP server process):
        Odoo          — mcp_odoo_*_url    (reference implementation)
        SAP           — mcp_sap_*_url
        Oracle EBS    — mcp_ebs_*_url
        MS Dynamics   — mcp_d365_*_url
        Legacy SQL DB — mcp_legacy_db_url (single server, all domains)
        Custom ERP    — mcp_custom_*_url  (bring-your-own adapter)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Odoo credentials (used by Odoo MCP adapter servers) ──────────────────
    odoo_url: str = "http://localhost:8069"
    odoo_db: str = "odoo_db"
    odoo_user: str = "admin"
    odoo_api_key: str = ""

    # ── LLM configuration ────────────────────────────────────────────────────
    # Ollama base URL (used when provider prefix is 'ollama')
    ollama_base_url: str = "http://localhost:11434"

    # LLM model specs — format: 'provider:model_name'
    # Supported providers: ollama, anthropic, openai, google-gla, groq, mistral, cohere
    # Examples:
    #   ollama:gemma4:e4b                  (local Ollama)
    #   anthropic:claude-sonnet-4-6        (Anthropic Cloud — needs ANTHROPIC_API_KEY)
    #   openai:gpt-4o                      (OpenAI — needs OPENAI_API_KEY)
    #   google-gla:gemini-2.0-flash        (Google — needs GOOGLE_API_KEY)
    #   groq:llama-3.3-70b-versatile       (Groq — needs GROQ_API_KEY)
    llm_planning_model: str = "ollama:gemma4:e4b"
    llm_buyer_model: str = "ollama:gemma4:e4b"
    llm_executive_model: str = "ollama:gemma4:e4b"
    llm_sales_model: str = "ollama:gemma4:e4b"
    llm_production_model: str = "ollama:gemma4:e4b"
    llm_quality_model: str = "ollama:gemma4:e4b"
    llm_finance_model: str = "ollama:gemma4:e4b"
    llm_logistics_model: str = "ollama:gemma4:e4b"

    # ── Odoo MCP adapter — SSE URLs (remote-ready) ───────────────────────────
    # Override in .env to point at a remote host, e.g.:
    #   MCP_ODOO_PLANNING_URL=http://mcp-server.internal:8001/sse
    mcp_odoo_planning_url: str = "http://localhost:8001/sse"
    mcp_odoo_procurement_url: str = "http://localhost:8002/sse"
    mcp_odoo_inventory_url: str = "http://localhost:8003/sse"
    mcp_odoo_sales_url: str = "http://localhost:8004/sse"
    mcp_odoo_logistics_url: str = "http://localhost:8005/sse"
    mcp_odoo_production_url: str = "http://localhost:8006/sse"
    mcp_odoo_pd_url: str = "http://localhost:8007/sse"
    mcp_odoo_maintenance_url: str = "http://localhost:8008/sse"
    mcp_odoo_qa_url: str = "http://localhost:8009/sse"
    mcp_odoo_qc_url: str = "http://localhost:8010/sse"
    mcp_odoo_finance_url: str = "http://localhost:8011/sse"

    # Legacy port aliases — used by the Odoo MCP server __main__ entry points
    mcp_planning_port: int = 8001
    mcp_procurement_port: int = 8002
    mcp_inventory_port: int = 8003
    mcp_sales_port: int = 8004
    mcp_logistics_port: int = 8005
    mcp_production_port: int = 8006
    mcp_pd_port: int = 8007
    mcp_maintenance_port: int = 8008
    mcp_qa_port: int = 8009
    mcp_qc_port: int = 8010
    mcp_finance_port: int = 8011

    # ── SAP MCP adapter — SSE URLs ────────────────────────────────────────────
    # Empty string = adapter disabled. Set to enable:
    #   MCP_SAP_PLANNING_URL=http://sap-mcp-host:8010/sse
    mcp_sap_planning_url: str = ""
    mcp_sap_procurement_url: str = ""
    mcp_sap_inventory_url: str = ""

    # ── Oracle EBS MCP adapter — SSE URLs ────────────────────────────────────
    #   MCP_EBS_PLANNING_URL=http://ebs-mcp-host:8020/sse
    mcp_ebs_planning_url: str = ""
    mcp_ebs_procurement_url: str = ""
    mcp_ebs_inventory_url: str = ""

    # ── Microsoft Dynamics 365 MCP adapter — SSE URLs ────────────────────────
    #   MCP_D365_PLANNING_URL=http://d365-mcp-host:8030/sse
    mcp_d365_planning_url: str = ""
    mcp_d365_procurement_url: str = ""
    mcp_d365_inventory_url: str = ""

    # ── Legacy SQL DB MCP adapter — SSE URL ──────────────────────────────────
    # Single server covers planning + procurement + inventory for legacy DBs.
    #   MCP_LEGACY_DB_URL=http://legacy-mcp-host:8040/sse
    mcp_legacy_db_url: str = ""

    # ── Oracle NetSuite MCP adapter — SSE URLs ──────────────────────────────
    #   MCP_NETSUITE_PLANNING_URL=http://netsuite-mcp-host:8050/sse
    mcp_netsuite_planning_url: str = ""
    mcp_netsuite_procurement_url: str = ""
    mcp_netsuite_inventory_url: str = ""

    # ── Custom / bring-your-own ERP — SSE URLs ───────────────────────────────
    # Plug any MCP-compatible adapter here without changing agent code.
    #   MCP_CUSTOM_PLANNING_URL=http://custom-mcp:8060/sse
    mcp_custom_planning_url: str = ""
    mcp_custom_procurement_url: str = ""
    mcp_custom_inventory_url: str = ""


settings = Settings()
