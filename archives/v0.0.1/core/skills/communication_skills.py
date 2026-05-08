"""
AxonCommunicationSkills — AI→Human bridge via Odoo Chatter and Activities.

This is the most critical skill module. Every write operation in the system
routes through here to create a permanent, human-readable audit trail.

Two capabilities:
1. post_ai_reasoning()  — posts a [AI-ASCP] note to any record's Chatter
2. create_activity()    — creates a mail.activity for human review/approval (HITL gate)
3. check_activity_done() — polls whether a mail.activity has been marked done

Rules (from AGENT.md + PROJECT_PLAN.md):
- The target model MUST have mail.thread (Odoo Chatter mixin).
- Never post silently — every write elsewhere must call post_ai_reasoning().
- Use subtype_xmlid="mail.mt_note" for internal AI notes (not visible in portal).
"""

from __future__ import annotations

from core.odoo_client import AxonOdooXMLRPCClient
from core.skills.base_skill import AxonBaseSkill


class AxonCommunicationSkills(AxonBaseSkill):
    """
    Wraps Odoo mail.thread + mail.activity operations.
    Does NOT inherit post_ai_reasoning from AxonBaseSkill to avoid circular calls —
    it IS the implementation of post_ai_reasoning.
    """

    def __init__(self, client: AxonOdooXMLRPCClient | None = None) -> None:
        # Pass comms=self to avoid circular lazy import
        super().__init__(client=client, comms=self)

    # ── 1. Post AI Reasoning to Chatter ──────────────────────────────────────

    def post_ai_reasoning(
        self,
        model: str,
        record_id: int,
        action_taken: str,
        ai_context: str,
        cycle_id: str | None = None,
        confidence: float | None = None,
    ) -> dict:
        """
        Post a structured [AI-ASCP] internal note to the record's Chatter.

        The record's model MUST have mail.thread (Odoo Chatter mixin).
        Uses subtype 'mail.mt_note' so the note is internal-only (not emailed).

        Returns:
            {"message_id": int}
        """
        footer_parts: list[str] = []
        if cycle_id:
            footer_parts.append(f"Cycle: {cycle_id}")
        if confidence is not None:
            footer_parts.append(f"Confidence: {confidence:.2f}")

        footer_html = (
            f"<br/><small style='color:#888'>{' | '.join(footer_parts)}</small>"
            if footer_parts
            else ""
        )

        body = (
            f"<b>[AI-ASCP]</b> {action_taken}"
            f"<br/><i>Reason: {ai_context}</i>"
            f"{footer_html}"
        )

        message_id = self.client.call_method(
            model,
            "message_post",
            [record_id],
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {"message_id": message_id}

    # ── 2. Create mail.activity (HITL gate) ───────────────────────────────────

    def create_activity(
        self,
        model: str,
        record_id: int,
        summary: str,
        note: str,
        deadline: str,
        activity_type_xmlid: str = "mail.mail_activity_data_todo",
        assigned_user_id: int | None = None,
    ) -> dict:
        """
        Create a mail.activity on a record to request human approval.

        The workflow PAUSES here — LangGraph checks axon_check_activity_done()
        before resuming.

        Args:
            model:                Odoo model name (must have mail.activity.mixin)
            record_id:            ID of the record requiring human attention
            summary:              Short activity title visible in planner's inbox
            note:                 Full AI reasoning for the human to read
            deadline:             ISO date string (YYYY-MM-DD) for response
            activity_type_xmlid:  Defaults to "To-Do"; use
                                  "mail.mail_activity_data_warning" for urgent
            assigned_user_id:     Odoo user ID to assign to; None = current API user

        Returns:
            {"activity_id": int, "record_url": str}
        """
        # Resolve the activity type record ID from its XML ID
        activity_type_id = self._get_activity_type_id(activity_type_xmlid)

        # Build activity values
        values: dict = {
            "activity_type_id": activity_type_id,
            "summary": summary,
            "note": f"<p>{note}</p>",
            "date_deadline": deadline,
            "res_model": model,
            "res_id": record_id,
        }
        if assigned_user_id:
            values["user_id"] = assigned_user_id

        activity_id = self.client.create("mail.activity", values)

        record_url = (
            f"{self.client._url}/odoo/{model.replace('.', '-')}/{record_id}"
        )

        return {"activity_id": activity_id, "record_url": record_url}

    # ── 3. Check activity done (HITL resume probe) ────────────────────────────

    def check_activity_done(self, activity_id: int) -> dict:
        """
        Check whether a mail.activity has been marked done (feedback set).

        LangGraph's HITL checkpoint node calls this to decide whether to resume.

        Returns:
            {
                "exists": bool,        # False = activity was marked done and deleted
                "approved": bool,      # True when activity no longer exists (done)
                "feedback": str | None # Feedback text if available (from done activity log)
            }
        """
        records = self.client.search_read(
            "mail.activity",
            [("id", "=", activity_id)],
            ["id", "summary", "date_deadline"],
            limit=1,
        )

        if not records:
            # Activity no longer exists = it was marked done by the human
            return {"exists": False, "approved": True, "feedback": None}

        return {"exists": True, "approved": False, "feedback": None}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_activity_type_id(self, xmlid: str) -> int:
        """Resolve an XML ID to a record ID for mail.activity.type."""
        # xmlid format: "module.xml_id"
        module, xml_id = xmlid.split(".")
        refs = self.client.search_read(
            "ir.model.data",
            [("module", "=", module), ("name", "=", xml_id)],
            ["res_id"],
            limit=1,
        )
        if not refs:
            raise ValueError(f"Activity type XML ID not found: {xmlid}")
        return refs[0]["res_id"]
