"""PolicyServer client backed by EraOwl-LLMWiki — Company Policy MCP Server.

Connects to the LLMWiki MCP server (port 8000 by default) which exposes
24 tools for policy retrieval, compliance checking, procurement validation,
and strategic review against the company's policy vault.

The MCP server supports three transport modes; Axon uses SSE (default
for Docker deployments) for consistent compatibility with the rest
of the connector layer.

Tool mapping (Axon API → LLMWiki MCP tools):
  - get_sop                      → read_policy / search_policy_keywords
  - check_compliance             → policy_consultant / compliance_harness
  - get_audit_history            → ask_policy
  - get_regulatory_requirements  → search_policy_keywords

Usage:
    from axon.connectors.mcp_llmwiki.client import PolicyServerClient

    async with PolicyServerClient(settings.mcp_llmwiki) as client:
        sop = await client.get_sop("Financial Controls")
        result = await client.check_compliance(plan_data)
"""

from __future__ import annotations

from typing import Any

from axon.connectors.base import BaseMCPConnector
from axon.core.config import MCPServerConfig
from axon.core.telemetry import trace_mcp_call


class PolicyServerClient(BaseMCPConnector):
    """MCP client for the EraOwl-LLMWiki Company Policy Server.

    Extends BaseMCPConnector to inherit circuit breaker, cache, retry,
    and dual-transport (SSE / Streamable HTTP) support. Connects to the
    LLMWiki MCP server to retrieve company policies, run compliance
    checks, and get regulatory guidance.
    """

    server_name = "llmwiki"

    # Tool name mapping: Axon agent tool name → LLMWiki MCP tool name
    _tool_map: dict[str, str] = {
        "get_sop": "read_policy",
        "check_compliance": "policy_consultant",
        "get_audit_history": "ask_policy",
        "get_regulatory_requirements": "search_policy_keywords",
    }

    # Tool name → argument mapping: remap args for the target tool
    _arg_map: dict[str, dict[str, str]] = {
        "get_sop": {"process_code": "title"},
        "get_regulatory_requirements": {"product_category": "keywords"},
        "get_audit_history": {"process_code": "question"},
    }

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)

    # =========================================================================
    # Tool name mapping — agents call Axon names, we map to LLMWiki tools
    # =========================================================================

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        use_cache: bool = True,
    ) -> Any:
        """Intercept agent tool calls and map to LLMWiki MCP tool names.

        Agent tools use Axon-standard names (get_sop, check_compliance, etc.)
        while the LLMWiki MCP server exposes its own tool names (read_policy,
        policy_consultant, etc.). This override maps transparently.

        Args not in _tool_map pass through unchanged to the base _call_tool.
        """
        mapped_tool = self._tool_map.get(tool_name)
        if mapped_tool is not None:
            # Remap arguments to the target tool's parameter names
            arg_remap = self._arg_map.get(tool_name, {})
            mapped_args: dict[str, Any] = {}
            for src_key, value in arguments.items():
                dst_key = arg_remap.get(src_key, src_key)
                mapped_args[dst_key] = value
            return await super()._call_tool(mapped_tool, mapped_args, use_cache=use_cache)

        return await super()._call_tool(tool_name, arguments, use_cache=use_cache)

    # =========================================================================
    # Tool wrappers — mapped to LLMWiki MCP tools
    # =========================================================================

    async def get_sop(self, process_code: str) -> dict[str, Any]:
        """Retrieve a policy article from the LLMWiki vault.

        Maps to the LLMWiki ``read_policy`` tool, which reads a full policy
        article with YAML frontmatter metadata.

        Args:
            process_code: Policy title or keyword (e.g. "Financial Controls",
                          "IT Security", "HR Policy", "Procurement")

        Returns:
            {"process_code": str, "title": str, "content": str, "version": str,
             "status": str, "tags": list[str]}
        """
        with trace_mcp_call(self.server_name, "read_policy") as span:
            span.set_attribute("process_code", process_code)

            # Try direct read_policy first (title-based lookup)
            try:
                raw = await self._call_tool("read_policy", {"title": process_code})
                parsed = self._parse_policy_markdown(raw, process_code)
                span.set_attribute("found", True)
                return parsed
            except Exception:
                pass

            # Fallback: keyword search
            try:
                raw = await self._call_tool(
                    "search_policy_keywords",
                    {"keywords": process_code},
                )
                span.set_attribute("found", True)
                span.set_attribute("method", "keyword_search")
                return {
                    "process_code": process_code,
                    "title": process_code,
                    "content": (
                        str(raw)
                        if not isinstance(raw, dict)
                        else raw.get("content", str(raw))
                    ),
                    "version": "llmwiki",
                }
            except Exception:
                span.set_attribute("found", False)
                return {}

    async def check_compliance(self, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Verify a plan against company policies via the LLMWiki policy_consultant.

        Maps to the LLMWiki ``policy_consultant`` tool, which checks a
        business request against the Approval Matrix and Procurement Rules.

        Falls back to ``compliance_harness`` for cross-reference authorization
        checks when a requester_role and department are provided.

        Args:
            plan_data: Plan context with items, quantities, timelines.
                       May include "action", "requester_role", "department"
                       for richer compliance checks.

        Returns:
            {"compliant": bool, "violations": list[dict], "recommendations": list[str]}
        """
        with trace_mcp_call(self.server_name, "policy_consultant") as span:
            action = plan_data.get("action", "")
            if not action:
                # Build a human-readable request from plan data
                demands = plan_data.get("demands", [])
                cost = plan_data.get("cost_impact", 0)
                action = f"Plan with {len(demands)} demands, cost impact ${cost:,.0f}"

            try:
                raw = await self._call_tool(
                    "policy_consultant",
                    {"request": action},
                )
                result = self._parse_compliance_result(raw, plan_data)
                span.set_attribute("compliant", result["compliant"])
                return result
            except Exception:
                # Fallback: try compliance_harness if role/department provided
                requester_role = plan_data.get("requester_role", "")
                department = plan_data.get("department", "")
                if requester_role:
                    try:
                        raw = await self._call_tool(
                            "compliance_harness",
                            {
                                "action": action,
                                "requester_role": requester_role,
                                "department": department,
                            },
                        )
                        result = self._parse_compliance_result(raw, plan_data)
                        span.set_attribute("compliant", result["compliant"])
                        span.set_attribute("method", "compliance_harness")
                        return result
                    except Exception:
                        pass

                # Both failed
                return {
                    "compliant": True,
                    "violations": [],
                    "recommendations": [],
                    "_warning": "Policy check skipped — LLMWiki unreachable",
                    "policy_check": "skipped",
                }

    async def get_audit_history(
        self, process_code: str | None = None, item_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Query the LLMWiki for audit and compliance history via ask_policy.

        Maps to the LLMWiki ``ask_policy`` tool, which answers natural-language
        questions against the policy vault.

        Returns:
            List of audit finding dicts with date, finding, severity, source.
        """
        with trace_mcp_call(self.server_name, "ask_policy") as span:
            question_parts: list[str] = []
            if process_code:
                question_parts.append(f"policy '{process_code}'")
            if item_id:
                question_parts.append(f"item '{item_id}'")
            if not question_parts:
                question_parts.append("compliance and audit history")

            question = (
                "Summarise recent audit findings and compliance history "
                f"for {' '.join(question_parts)}."
            )
            try:
                raw = await self._call_tool("ask_policy", {"question": question})
                findings = self._parse_audit_result(raw)
                span.set_attribute("finding_count", len(findings))
                return findings
            except Exception:
                span.set_attribute("finding_count", 0)
                return []

    async def get_regulatory_requirements(self, product_category: str) -> dict[str, Any]:
        """Search the LLMWiki for regulations applicable to a product category.

        Maps to the LLMWiki ``search_policy_keywords`` tool for keyword-based
        policy search, and ``get_approval_matrix`` for spending limits.

        Returns:
            {"product_category": str, "requirements": list[str], "source": str}
        """
        with trace_mcp_call(self.server_name, "search_policy_keywords") as span:
            span.set_attribute("category", product_category)
            requirements: list[str] = []

            # Keyword search for category-relevant policies
            try:
                raw = await self._call_tool(
                    "search_policy_keywords",
                    {"keywords": product_category},
                )
                requirements.append(
                    f"Policy matches for '{product_category}':\n{self._truncate(str(raw), 2000)}"
                )
            except Exception:
                requirements.append(
                    "Core policies: Financial Controls, IT Security, Code of Conduct, "
                    "Data Privacy — see LLMWiki vault for full text"
                )

            # Also get the approval matrix for spending thresholds
            try:
                raw = await self._call_tool("get_approval_matrix", {})
                requirements.append(
                    f"Approval Matrix (spending limits):\n{self._truncate(str(raw), 1000)}"
                )
            except Exception:
                pass

            return {
                "product_category": product_category,
                "requirements": requirements,
                "source": "llmwiki-policy-server",
            }

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the tools exposed by this policy client (for tool registry)."""
        return [
            {"name": "get_sop",
             "description": "Retrieve policy from LLMWiki vault"},
            {"name": "check_compliance",
             "description": "Verify plan via LLMWiki policy_consultant"},
            {"name": "get_audit_history",
             "description": "Query compliance history via ask_policy"},
            {"name": "get_regulatory_requirements",
             "description": "Search LLMWiki for regulations"},
        ]

    # =========================================================================
    # Response parsers (LLMWiki tools return text, sometimes JSON-in-text)
    # =========================================================================

    @staticmethod
    def _parse_policy_markdown(raw: Any, process_code: str) -> dict[str, Any]:
        """Parse a read_policy response (markdown with YAML frontmatter)."""
        text = str(raw) if not isinstance(raw, str) else raw

        # Extract title from first heading
        title = process_code
        status = "unknown"
        tags: list[str] = []
        for line in text.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
            if line.lower().startswith("status:"):
                status = line.split(":", 1)[1].strip()
            if line.lower().startswith("tags:"):
                tags = [t.strip() for t in line.split(":", 1)[1].split(",")]

        return {
            "process_code": process_code,
            "title": title,
            "content": text,
            "version": "llmwiki",
            "status": status,
            "tags": tags,
        }

    @staticmethod
    def _parse_compliance_result(raw: Any, plan_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a policy_consultant / compliance_harness response.

        The LLMWiki tools return JSON strings like:
        {"is_compliant": true/false, "reason": "...", "reference": "[[Article]]", ...}
        """
        text = str(raw) if not isinstance(raw, str) else raw

        # Try to parse as JSON
        import json

        try:
            data = json.loads(text)
            is_compliant = data.get("is_compliant", data.get("compliant", True))
            violations: list[dict[str, Any]] = []
            if not is_compliant:
                violations.append({
                    "rule": data.get("reference", "policy_violation"),
                    "severity": "high",
                    "detail": str(
                        data.get("reason",
                                 data.get("output", "Policy violation detected"))
                    ),
                })
            return {
                "compliant": is_compliant,
                "violations": violations,
                "recommendations": (
                    [data["suggested_next_step"]] if data.get("suggested_next_step") else []
                ),
            }
        except (json.JSONDecodeError, TypeError):
            pass

        # Text-based parsing — check for PASS / FAIL indicators
        text_lower = text.lower()
        if "pass" in text_lower and "compliance" in text_lower and "fail" not in text_lower:
            return {"compliant": True, "violations": [], "recommendations": []}
        if "fail" in text_lower or "violation" in text_lower:
            return {
                "compliant": False,
                "violations": [{
                    "rule": "policy_violation",
                    "severity": "high",
                    "detail": text[:500],
                }],
                "recommendations": [],
            }

        return {"compliant": True, "violations": [], "recommendations": []}

    @staticmethod
    def _parse_audit_result(raw: Any) -> list[dict[str, Any]]:
        """Parse ask_policy response into structured audit findings."""
        text = str(raw) if not isinstance(raw, str) else raw
        findings: list[dict[str, Any]] = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                findings.append({
                    "date": "2026-05-22",
                    "finding": line[2:].strip(),
                    "severity": "info",
                    "source": "llmwiki/ask_policy",
                })
        if not findings and text:
            findings.append({
                "date": "2026-05-22",
                "finding": text[:500],
                "severity": "info",
                "source": "llmwiki/ask_policy",
            })
        return findings

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text to max_len characters."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."
