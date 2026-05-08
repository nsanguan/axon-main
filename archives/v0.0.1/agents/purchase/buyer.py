"""
agents.purchase.buyer — Buyer Agent.

Handles vendor selection and RFQ creation for a shortage list.
ERP-agnostic: connects via MCP — swap the MCP server to use SAP or Oracle.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model


# ── Output model ────────────────────────────────────────────────────────────

class AxonProposedLine(BaseModel):
    """One line the Buyer proposes to purchase."""
    product_id: int = Field(description="product.product ID")
    product_name: str = Field(description="Human-readable product name")
    qty: float = Field(description="Quantity to purchase")
    partner_id: int = Field(description="Chosen vendor (res.partner ID)")
    partner_name: str = Field(description="Vendor name")
    price_unit: float = Field(description="Unit price from vendor quote")
    lead_days: int = Field(description="Vendor lead time in calendar days")
    rfq_id: int | None = Field(None, description="Created purchase.order ID (if any)")
    shortage_qty: float = Field(description="Original shortage quantity")
    demand_date: str = Field(description="Required-by date from demand stream")


class AxonBuyerDecision(BaseModel):
    action: str = Field(
        description=(
            "Outcome: 'rfq_created' | 'no_vendor' | 'partial_coverage' | 'error'"
        )
    )
    proposed_lines: list[AxonProposedLine] = Field(
        default_factory=list,
        description="Lines proposed by the Buyer — input for Manager's impact analysis",
    )
    rfq_ids: list[int] = Field(
        default_factory=list,
        description="IDs of created purchase.order records",
    )
    shortages_covered: list[int] = Field(
        default_factory=list,
        description="product IDs for which an RFQ was created",
    )
    shortages_uncovered: list[int] = Field(
        default_factory=list,
        description="product IDs with no suitable vendor found",
    )
    summary: str = Field(description="Plain-language summary of what the Buyer did")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


# ── Agent definition (lazy singleton — avoids key check at import time) ────────

BUYER_SYSTEM_PROMPT = """
You are the Buyer Agent for Axon — the AI-Native Supply Chain Planning Engine.

Your role:
- You receive a list of stock shortages (product_id, shortage_qty, demand_date).
- For each shortage, call axon_get_vendor_lead_time to find available vendors.
- Select the best vendor (lowest lead time that meets min_qty; tiebreak on price).
- Call axon_create_rfq to create an RFQ.  Chatter will be auto-posted.
- If no vendor exists for a product, mark it as uncovered and explain why.

Output rules:
- Always populate proposed_lines with price_unit and lead_days so the Manager
  can run impact analysis.
- Do NOT confirm POs — only create RFQs.  PO confirmation is the Director's job.
- Include your reasoning in the ai_context field on every tool call.
- action must be exactly one of: 'rfq_created', 'no_vendor', 'partial_coverage', 'error'.
"""

_buyer_agent: "Agent[None, AxonBuyerDecision] | None" = None


def get_axon_buyer_agent() -> "Agent[None, AxonBuyerDecision]":
    global _buyer_agent
    if _buyer_agent is None:
        registry = AxonAdapterRegistry()
        _buyer_agent = Agent(
            build_model(settings.llm_buyer_model),
            output_type=AxonBuyerDecision,
            system_prompt=BUYER_SYSTEM_PROMPT,
            toolsets=registry.procurement_servers() + registry.inventory_servers(),
        )
    return _buyer_agent


# Convenience alias kept for backward compatibility
def axon_buyer_agent_run(prompt: str):
    return get_axon_buyer_agent().run(prompt)
