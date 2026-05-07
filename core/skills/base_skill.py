"""
BaseSkill — abstract base class for all core/skills/ modules.

Every skill class:
- Receives a shared OdooXMLRPCClient via constructor injection
- Exposes post_ai_reasoning() as a convenience delegation to CommunicationSkills
- Must NOT contain any tool/MCP definitions (those live in mcp_servers/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.odoo_client import OdooXMLRPCClient

if TYPE_CHECKING:
    from core.skills.communication_skills import CommunicationSkills


class BaseSkill:
    def __init__(
        self,
        client: OdooXMLRPCClient | None = None,
        comms: "CommunicationSkills | None" = None,
    ) -> None:
        self.client = client or OdooXMLRPCClient()
        # comms is injected lazily to avoid circular imports;
        # subclasses that need it should import and pass explicitly.
        self._comms = comms

    @property
    def comms(self) -> "CommunicationSkills":
        if self._comms is None:
            from core.skills.communication_skills import CommunicationSkills
            self._comms = CommunicationSkills(client=self.client)
        return self._comms

    def post_ai_reasoning(
        self,
        model: str,
        record_id: int,
        action_taken: str,
        ai_context: str,
        cycle_id: str | None = None,
        confidence: float | None = None,
    ) -> dict:
        """Shortcut: post AI reasoning note to a record's Chatter."""
        return self.comms.post_ai_reasoning(
            model=model,
            record_id=record_id,
            action_taken=action_taken,
            ai_context=ai_context,
            cycle_id=cycle_id,
            confidence=confidence,
        )
