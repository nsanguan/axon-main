"""ContextRetriever — enriches agent reasoning with RAG-sourced policies and SOPs.

Wraps PolicyServerClient to provide a simple async API for agents:
  - enrich_prompt() — injects relevant SOP text into an agent's prompt
  - check_plan() — validates a proposed plan against all applicable policies

Usage:
    from axon.connectors.mcp_external_rag.context_retriever import ContextRetriever

    retriever = ContextRetriever(client)
    enriched_context = await retriever.enrich_prompt(
        base_prompt="Create a production plan...",
        process_codes=["manufacturing.bolts", "quality.aerospace"],
    )
"""

from __future__ import annotations

from typing import Any

from axon.connectors.mcp_external_rag.client import PolicyServerClient
from axon.core.telemetry import log_event


class ContextRetriever:
    """High-level API for agents to consume RAG-sourced policies and SOPs.

    Agents call enrich_prompt() during the REASON phase and check_plan()
    during the APPROVE phase. All calls go through the PolicyServerClient
    which communicates with mcp-policy-server via MCP.
    """

    def __init__(self, client: PolicyServerClient):
        self._client = client

    async def enrich_prompt(
        self,
        base_prompt: str,
        process_codes: list[str],
        product_category: str | None = None,
    ) -> str:
        """Enrich a base agent prompt with relevant SOP context.

        Retrieves SOPs for each process code and appends them to the prompt
        as a "POLICIES" section the agent must follow.

        Args:
            base_prompt: The agent's core instruction
            process_codes: Process codes to retrieve SOPs for
            product_category: Optional category for regulatory requirements

        Returns:
            Enriched prompt string with policy context appended
        """
        enrichments: list[str] = []

        # Retrieve SOPs for each process
        for code in process_codes:
            try:
                sop = await self._client.get_sop(code)
                if sop and sop.get("content"):
                    enrichments.append(
                        f"### SOP: {sop.get('title', code)}\n"
                        f"Version: {sop.get('version', 'N/A')}\n"
                        f"{sop['content']}\n"
                    )
            except Exception as exc:
                log_event(
                    "warn",
                    "sop_retrieval_failed",
                    server_name="external_rag",
                    process_code=code,
                    error=str(exc),
                )

        # Retrieve regulatory requirements if category provided
        if product_category:
            try:
                regs = await self._client.get_regulatory_requirements(product_category)
                if regs and regs.get("requirements"):
                    req_text = "\n".join(f"- {r}" for r in regs["requirements"])
                    enrichments.append(
                        f"### Regulatory Requirements ({product_category})\n{req_text}\n"
                    )
            except Exception as exc:
                log_event(
                    "warn",
                    "regulatory_retrieval_failed",
                    server_name="external_rag",
                    category=product_category,
                    error=str(exc),
                )

        if not enrichments:
            log_event(
                "info",
                "no_enrichments",
                server_name="external_rag",
                process_codes=",".join(process_codes),
            )
            return base_prompt

        enriched = f"{base_prompt}\n\n## POLICIES (from mcp-policy-server)\n\n"
        enriched += "\n---\n".join(enrichments)

        log_event(
            "info",
            "prompt_enriched",
            server_name="external_rag",
            sop_count=len(process_codes),
            enrichment_count=len(enrichments),
        )
        return enriched

    async def check_plan(self, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Validate a proposed plan against all applicable policies.

        Called during the APPROVE phase before HITL or execution.

        Args:
            plan_data: The plan to validate, containing allocations,
                       item details, and timeline.

        Returns:
            {
                "compliant": bool,
                "violations": [{"rule": str, "severity": str, "detail": str}, ...],
                "recommendations": [str, ...]
            }
        """
        log_event(
            "info",
            "compliance_check_started",
            server_name="external_rag",
        )
        try:
            result = await self._client.check_compliance(plan_data)
            log_event(
                "info",
                "compliance_check_complete",
                server_name="external_rag",
                compliant=result.get("compliant", False),
                violation_count=len(result.get("violations", [])),
            )
            return result
        except Exception as exc:
            log_event(
                "error",
                "compliance_check_failed",
                server_name="external_rag",
                error=str(exc),
            )
            # Fail open: if RAG is down, return compliant with a warning
            return {
                "compliant": True,
                "violations": [],
                "recommendations": [],
                "_warning": f"Policy check skipped — RAG unavailable: {exc}",
                "policy_check": "skipped",
            }

    async def get_audit_context(
        self,
        process_code: str,
        item_id: str | None = None,
    ) -> str:
        """Retrieve audit history as context for the agent.

        Returns formatted text suitable for appending to a prompt.
        """
        try:
            findings = await self._client.get_audit_history(process_code, item_id)
            if not findings:
                return ""

            lines = [f"### Recent Audit Findings ({process_code})"]
            for f in findings[:5]:  # top 5 only
                lines.append(
                    f"- [{f.get('date', 'N/A')}] {f.get('finding', '')} "
                    f"(severity: {f.get('severity', 'N/A')})"
                )
            return "\n".join(lines)
        except Exception as exc:
            log_event(
                "warn",
                "audit_retrieval_failed",
                server_name="external_rag",
                process_code=process_code,
                error=str(exc),
            )
            return ""

    async def list_available_tools(self) -> list[dict[str, Any]]:
        """Return tools available from the policy server for tool registry."""
        return await self._client.list_tools()
