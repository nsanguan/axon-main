"""
BuyerAgent — handles supplier selection and RFQ creation for a list of shortages.

Responsibilities:
  1. Receive shortage list from Supervisor state.
  2. Query vendor lead times (ascp_get_vendor_lead_time) for each shortage item.
  3. Select the best vendor (fastest lead time that meets minimum qty).
  4. Create RFQs (ascp_create_rfq) — Chatter posted automatically by the skill.
  5. Return BuyerDecision with proposed lines (price_unit, lead_days) so the
     Manager Agent can perform Impact Analysis.

This agent does NOT confirm POs — that is deferred to the Director after
the Manager's impact analysis clears (or HITL approves).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from core.config import settings
from core.model_factory import build_model


# ── Output model ────────────────────────────────────────────────────────────

class ProposedLine(BaseModel):
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


class BuyerDecision(BaseModel):
    action: str = Field(
        description=(
            "Outcome: 'rfq_created' | 'no_vendor' | 'partial_coverage' | 'error'"
        )
    )
    proposed_lines: list[ProposedLine] = Field(
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
You are the Buyer Agent for EraOwl ASCP — an AI-native supply chain planning system.

Your role:
- You receive a list of stock shortages (product_id, shortage_qty, demand_date).
- For each shortage, call ascp_get_vendor_lead_time to find available vendors.
- Select the best vendor (lowest lead time that meets min_qty; tiebreak on price).
- Call ascp_create_rfq to create an RFQ.  Chatter will be auto-posted.
- If no vendor exists for a product, mark it as uncovered and explain why.

Output rules:
- Always populate proposed_lines with price_unit and lead_days so the Manager
  can run impact analysis.
- Do NOT confirm POs — only create RFQs.  PO confirmation is the Director's job.
- Include your reasoning in the ai_context field on every tool call.
- action must be exactly one of: 'rfq_created', 'no_vendor', 'partial_coverage', 'error'.
"""

_buyer_agent: "Agent[None, BuyerDecision] | None" = None


def get_buyer_agent() -> "Agent[None, BuyerDecision]":
    global _buyer_agent
    if _buyer_agent is None:
        mcp_procurement = MCPServerSSE(
            f"http://localhost:{settings.mcp_procurement_port}/sse"
        )
        _buyer_agent = Agent(
            build_model(settings.llm_buyer_model),
            output_type=BuyerDecision,
            system_prompt=BUYER_SYSTEM_PROMPT,
            toolsets=[mcp_procurement],
        )
    return _buyer_agent


# Convenience alias kept for backward compatibility
def buyer_agent_run(prompt: str):
    return get_buyer_agent().run(prompt)
