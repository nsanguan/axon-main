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
    """Configuration for a single MCP server connection.

    Supports universal MCP integration across any MCP-compliant server
    (Oracle EBS, SAP, Odoo, custom), with configurable transport, auth,
    circuit breaking, and cache behaviour.
    """

    url: AnyHttpUrl = AnyHttpUrl("http://localhost:8001/mcp")
    api_key: SecretStr | None = None
    auth_token: SecretStr | None = None  # session token (e.g. X-EBS-Session-Token)
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_count: int = 1  # retries before marking as DEGRADED
    enabled: bool = True
    transport: str = "sse"  # "sse" | "streamable_http" — MCP 2024-11-05 spec
    health_path: str = "/health"  # health check endpoint on the MCP server
    circuit_breaker_threshold: int = 3  # consecutive failures to OPEN
    circuit_breaker_cooldown: int = 60  # seconds before HALF_OPEN probe


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


class MemoryConfig(BaseSettings):
    """LangGraph short-term (checkpointer) and long-term (store) memory configuration.

    Short-term memory uses PostgresSaver to persist graph checkpoints.
    Long-term memory uses PostgresStore (BaseStore) for cross-thread knowledge.
    """

    # Short-term (checkpointer)
    checkpoint_enabled: bool = True
    checkpoint_ttl_seconds: int = 604800  # 7 days
    checkpoint_prune_after_days: int = 30

    # Long-term (store)
    store_enabled: bool = True
    store_namespaces: list[str] = [
        "agent_insights",
        "negotiation_patterns",
        "plan_history",
        "business_weights",
    ]
    store_search_limit: int = 10


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

    # MCP Servers — each maps to a physical MCP server process
    # Oracle EBS domain servers (ports 8001-8004, 8101-8111)
    mcp_oracle_ebs: MCPServerConfig = MCPServerConfig()
    mcp_agent_buyer: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8001/mcp"),
    )
    mcp_agent_store: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8002/mcp"),
    )
    mcp_ebs_auth: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8101/mcp"),
        transport="streamable_http",
        enabled=False,
    )
    mcp_ebs_demand: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8102/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_supply: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8103/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_production: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8104/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_logistics: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8105/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_quality: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8106/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_asset: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8107/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_finance: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8108/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_engineering: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8109/mcp"),
        transport="streamable_http",
    )
    mcp_ebs_warehouse: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8111/mcp"),
        transport="streamable_http",
    )
    # SAP MCP connector
    mcp_sap: MCPServerConfig = MCPServerConfig()
    # Odoo MCP connector
    mcp_odoo: MCPServerConfig = MCPServerConfig()
    # LLMWiki — Company Policy Server (MCP, port 8000)
    mcp_llmwiki: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8000/sse"),
        transport="sse",
    )
    # PostgreSQL MCP server (optional)
    mcp_postgresql: MCPServerConfig = MCPServerConfig()
    # Excalidraw MCP server (optional, disabled by default)
    mcp_excalidraw: MCPServerConfig = MCPServerConfig(
        url=AnyHttpUrl("http://localhost:8089/mcp"),
        enabled=False,
    )

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

    # Memory (LangGraph short-term + long-term)
    memory: MemoryConfig = MemoryConfig()

    # Security
    secret_key: SecretStr = SecretStr("insecure-default-change-in-production")

    # Observability
    logfire_token: str | None = None
    log_level: str = "INFO"


# Singleton — load once, reuse everywhere
settings = Settings()
