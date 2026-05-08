"""
agents.sales.demand_forecasting — Demand Forecasting Agent.

Reads confirmed sales orders, historical movement, and the current demand
forecast from the Sales MCP server. Produces an AxonDemandStream for the
Planning Agent to consume.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.demand import AxonDemandStream

DEMAND_FORECAST_SYSTEM_PROMPT = """
You are the Demand Forecasting Agent for Axon — the AI-Native Supply Chain Planning Engine.

Your role:
- Call axon_get_demand_forecast to retrieve the statistical forecast from the ERP.
- Call axon_get_confirmed_orders to capture confirmed sales orders with their dates.
- Merge both into a single AxonDemandStream (higher of forecast vs booked wins).
- Flag any demand spikes > 30 % above the 30-day rolling average.
- Post a Chatter summary to each flagged sales order via axon_post_comment.
- Return the consolidated AxonDemandStream for the Planning Agent.

Rules:
- Do NOT modify any ERP records directly — use only read + comment tools.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonDemandStream] | None" = None


def get_axon_demand_forecast_agent() -> "Agent[None, AxonDemandStream]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_sales_model),
            output_type=AxonDemandStream,
            system_prompt=DEMAND_FORECAST_SYSTEM_PROMPT,
            toolsets=registry.sales_servers(),
        )
    return _agent
