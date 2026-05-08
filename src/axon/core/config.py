"""
Axon Configuration — typed settings via pydantic-settings.

All configuration is loaded from environment variables (or .env file).
No hardcoded values, no scattered os.getenv calls. A single `Settings`
singleton is the source of truth for the entire application.

Nested settings use the double-underscore delimiter:
    AXON_DATABASE__URL  →  settings.database.url
    AXON_LLM__API_KEY   →  settings.llm.api_key
"""

from __future__ import annotations

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseSettings):
    """Configuration for a single MCP server connection."""

    url: AnyHttpUrl = AnyHttpUrl("http://localhost:8001/mcp")
    api_key: SecretStr | None = None
    timeout_seconds: int = 30
    max_retries: int = 3
    enabled: bool = True


class DatabaseConfig(BaseSettings):
    """PostgreSQL connection for LangGraph state persistence."""

    url: str = "postgresql+asyncpg://axon:axon@localhost:5432/axon"
    pool_size: int = 10
    pool_overflow: int = 5


class RedisConfig(BaseSettings):
    """Redis connection for MCP response caching."""

    url: str = "redis://localhost:6379/0"
    ttl_seconds: int = 300
    max_connections: int = 20


class LLMConfig(BaseSettings):
    """LLM model and authentication.

    Model-agnostic — set the model string to whatever your provider supports
    (Claude, GPT, Gemini, or a local model via compatible API).
    """

    model: str = "claude-3-5-sonnet-20241022"
    api_key: SecretStr = SecretStr("")
    max_tokens: int = 4096
    temperature: float = 0.0


class AgentDefaults(BaseSettings):
    """Global defaults for all domain agents."""

    max_retries: int = 3
    timeout_seconds: int = 120
    negotiation_rounds: int = 5


class WriteBackConfig(BaseSettings):
    """Secure write-back configuration — HITL gating thresholds."""

    enabled: bool = True
    purchase_req_threshold: float = 10000.0
    schedule_shift_days_threshold: int = 7
    audit_all_writes: bool = True


class RBACConfig(BaseSettings):
    """Role-based access control configuration."""

    enabled: bool = True
    strict_mode: bool = False  # When True, blocks unregistered tool-agent pairs


class LearningConfig(BaseSettings):
    """Experience Ledger, embedder, and retrieval configuration."""

    enabled: bool = True
    retention_hot_days: int = 90
    retention_warm_days: int = 730
    embedding_dimensions: int = 384
    embedder_type: str = "tag"  # "tag" or "openai"
    similarity_top_k: int = 5
    auto_retention: bool = True


# =============================================================================
# Root Settings
# =============================================================================


class Settings(BaseSettings):
    """Root configuration loaded from environment / .env file.

    Usage:
        from axon.core.config import settings
        print(settings.database.url)
    """

    model_config = SettingsConfigDict(
        env_prefix="AXON_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MCP Servers
    mcp_oracle_ebs: MCPServerConfig = MCPServerConfig()
    mcp_agent_buyer: MCPServerConfig = MCPServerConfig()  # buyer sub-agent under oracle_ebs
    mcp_agent_store: MCPServerConfig = MCPServerConfig()  # store sub-agent under oracle_ebs
    mcp_sap: MCPServerConfig = MCPServerConfig()
    mcp_odoo: MCPServerConfig = MCPServerConfig()
    mcp_external_rag: MCPServerConfig = MCPServerConfig()
    mcp_postgresql: MCPServerConfig = MCPServerConfig()

    # Infrastructure
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()

    # LLM (model-agnostic)
    llm: LLMConfig = LLMConfig()

    # Agents
    agent_defaults: AgentDefaults = AgentDefaults()

    # Write-back & RBAC (Phase 5)
    writeback: WriteBackConfig = WriteBackConfig()
    rbac: RBACConfig = RBACConfig()

    # Learning & Experience Ledger
    learning: LearningConfig = LearningConfig()

    # Security
    secret_key: SecretStr = SecretStr("insecure-default-change-in-production")

    # Observability
    logfire_token: str | None = None
    log_level: str = "INFO"


# Singleton — load once, reuse everywhere
settings = Settings()  # type: ignore[call-arg]
