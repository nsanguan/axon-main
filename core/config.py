from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # ignore DB-direct vars (ODOO_DB_HOST etc.) — not used here
    )

    # Odoo connection
    odoo_url: str = "http://202.71.1.13:8069"
    odoo_db: str = "odoo_db"
    odoo_user: str = "admin@eraowl.com"
    odoo_api_key: str = ""

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

    # MCP Server ports (local dev)
    mcp_planning_port: int = 8001
    mcp_procurement_port: int = 8002
    mcp_inventory_port: int = 8003


settings = Settings()
