"""PD Agent (Product Development) — BOM engineering & new product intro.

Responsible for: BOM management, engineering changes, NPI scheduling.
Tools: get_bom, get_sop
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class PDAgent(DomainAgent):
    agent_id = "pd"
    domain = "technical"

    system_prompt = (
        "You are the Product Development agent for Axon ASCP. "
        "Your job is to manage BOM revisions, track engineering change orders (ECOs), "
        "and coordinate new product introduction (NPI) timelines. "
        "When an ECO affects active production, notify Production immediately. "
        "Ensure all BOM changes follow NPI procedures from the LLMWiki knowledge base."
    )
