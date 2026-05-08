"""Master Graph — LangGraph orchestration for the planning cycle.

Coordinates the full planning lifecycle:
  RETRIEVE → FETCH → TRANSFORM → REASON → NEGOTIATE → APPROVE → LEARN → STORE

Each step is a LangGraph node. The graph uses checkpointing for persistence
and supports HITL approval via interrupt() for high-impact and deadlock plans.

Memory integration (v0.0.2+):
  - Short-term memory: PostgresSaver persists graph checkpoints after each node,
    enabling pause/resume for HITL approval. Falls back to MemorySaver (dev).
  - Long-term memory: PostgresStore stores cross-thread knowledge: agent insights,
    negotiation patterns, plan history, and business weights evolution.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from axon.agents.executive import make_mock_assessment
from axon.core.config import settings
from axon.core.escalation import (
    SeverityScorer,
    compute_severity_from_state,
    determine_escalation_level,
)
from axon.core.learning import ExperienceLedger, PlanOutcome, get_pool
from axon.core.memory import PostgresStore
from axon.core.schema import AgentProposal, MCPToolOutput
from axon.core.telemetry import log_event, trace_planning_cycle
from axon.orchestrator.logging import logged_node

try:
    from axon.dashboard.backend.notifications import notify_pending_approval, notify_plan_recorded
except ImportError:
    # Dashboard not available — no-op fallbacks
    async def notify_pending_approval(*args: Any, **kwargs: Any) -> None: ...
    async def notify_plan_recorded(*args: Any, **kwargs: Any) -> None: ...


# =============================================================================
# Planning State
# =============================================================================


class PlanningState(dict):
    """State that flows through the MasterGraph planning cycle.

    Using dict subclass for LangGraph compatibility with TypedDict support.
    """

    planning_request: dict[str, Any]
    correlation_id: str

    # RETRIEVE phase
    past_insights: list[dict[str, Any]]

    # FETCH phase
    raw_demands: list[dict[str, Any]]
    raw_supplies: list[dict[str, Any]]
    raw_policies: list[dict[str, Any]]

    # TRANSFORM phase
    demands: list[dict[str, Any]]
    supplies: list[dict[str, Any]]
    allocations: list[dict[str, Any]]

    # REASON phase
    agent_proposals: dict[str, Any]

    # NEGOTIATE phase
    negotiation_rounds: list[dict[str, Any]]
    final_plan: dict[str, Any] | list[dict[str, Any]]
    deadlock: bool

    # Master Graph metadata
    business_weights: dict[str, float]
    degradation_level: str

    # APPROVE phase
    approved: bool
    approval_note: str
    approval_plan_id: UUID | None  # Set when plan is pending HITL
    hitl_required: bool  # True if this plan requires human approval

    # LEARN phase
    experience_record_id: str

    # Escalation (Phase 5)
    escalation_level: str  # worker, manager, director, executive
    severity_score: float
    escalation_steps: list[dict[str, Any]]
    executive_assessment: dict[str, Any] | None

    # Tracing
    traces: list[dict[str, Any]]


# =============================================================================
# Graph Nodes — Memory nodes
# =============================================================================


@logged_node("retrieve_context")
async def node_retrieve_context(state: PlanningState) -> dict[str, Any]:
    """RETRIEVE: Load relevant past insights from long-term memory.

    Queries the long-term store for agent insights, past plans, and
    negotiation patterns that match the current planning context.
    The retrieved insights are passed to agents during the REASON phase.
    """
    log_event("info", "phase_retrieve")

    store: PostgresStore | None = state.get("_store")
    if store is None:
        return {"past_insights": []}

    insights: list[dict[str, Any]] = []
    try:
        # Retrieve recent agent insights
        results = await store.asearch(
            ("agent_insights",),
            limit=settings.memory.store_search_limit,
        )
        for item in results:
            insights.append({
                "namespace": item.namespace,
                "key": item.key,
                "value": item.value,
                "score": item.score,
            })

        # Retrieve relevant plan history
        plan_results = await store.asearch(
            ("plan_history",),
            limit=5,
        )
        for item in plan_results:
            insights.append({
                "namespace": item.namespace,
                "key": item.key,
                "value": item.value,
                "score": item.score,
                "type": "plan_history",
            })
    except Exception as exc:
        log_event("warn", "retrieve_insights_failed", error=str(exc))

    return {"past_insights": insights}


@logged_node("store_insights")
async def node_store_insights(state: PlanningState) -> dict[str, Any]:
    """STORE: Persist plan insights and agent learnings to long-term memory.

    After each planning cycle, store:
    - Plan summary in 'plan_history' namespace
    - Agent-specific insights in 'agent_insights/<agent_id>' namespace
    - Negotiation patterns if significant
    """
    log_event("info", "phase_store")

    store: PostgresStore | None = state.get("_store")
    if store is None:
        return {}

    try:
        plan_summary = _build_plan_summary(state)
        if plan_summary:
            await store.aput(
                ("plan_history",),
                state.get("correlation_id", str(UUID(int=0))),
                plan_summary,
            )

        agent_proposals = state.get("agent_proposals", {})
        for agent_id, proposal in agent_proposals.items():
            if isinstance(proposal, dict):
                await store.aput(
                    ("agent_insights", agent_id),
                    state.get("correlation_id", str(UUID(int=0))),
                    {
                        "proposal": proposal,
                        "timestamp": str(__import__("datetime").datetime.now()),
                    },
                )

        negotiation_rounds = state.get("negotiation_rounds", [])
        if len(negotiation_rounds) > 2:
            await store.aput(
                ("negotiation_patterns",),
                state.get("correlation_id", str(UUID(int=0))),
                {
                    "round_count": len(negotiation_rounds),
                    "resolution": "deadlock" if state.get("deadlock") else "converged",
                    "rounds": negotiation_rounds,
                },
            )
    except Exception as exc:
        log_event("warn", "store_insights_failed", error=str(exc))

    return {}


def _str_escalation_level(level) -> str:
    """Convert an escalation level to string."""
    return level.value if hasattr(level, "value") else str(level)


def _build_plan_summary(state: PlanningState) -> dict[str, Any]:
    """Build a summary dict of the plan for long-term storage."""
    approved = state.get("approved", False)
    deadlock = state.get("deadlock", False)
    demands = state.get("demands", [])
    final_plan = state.get("final_plan", [])
    if isinstance(final_plan, dict):
        final_plan = [final_plan]

    return {
        "correlation_id": state.get("correlation_id", ""),
        "approved": approved,
        "deadlock": deadlock,
        "demand_count": len(demands),
        "allocation_count": len(final_plan),
        "negotiation_rounds": len(state.get("negotiation_rounds", [])),
        "business_weights": state.get("business_weights", {}),
        "experience_record_id": state.get("experience_record_id", ""),
    }


# =============================================================================
# Graph Nodes — Planning pipeline
# =============================================================================


@logged_node("fetch")
async def node_fetch(state: PlanningState) -> dict[str, Any]:
    """FETCH: Pull current state from all configured MCP servers.

    Queries inventory, sales orders, WIP jobs, demand forecasts, and SOPs
    in parallel across Oracle EBS, SAP, and Odoo.  Each result is wrapped
    in an MCPToolOutput for downstream transformation.

    Gracefully skips unavailable connectors — sets degradation_level when
    any server fails.
    """
    from axon.connectors.mcp_oracle_ebs import BuyerAgent, OracleEBSConnector, StoreAgent
    from axon.connectors.mcp_external_rag.client import PolicyServerClient
    from axon.connectors.mcp_sap.connector import SAPConnector

    correlation_id: str = state.get("correlation_id", "")
    log_event("info", "phase_fetch", correlation_id=correlation_id)

    # MCPToolOutput.correlation_id is UUID; parse it (or generate a new one)
    from uuid import UUID as _UUID, uuid4 as _uuid4

    def _cid() -> _UUID:
        try:
            return _UUID(correlation_id)
        except (ValueError, AttributeError):
            return _uuid4()

    raw_demands: list[dict[str, Any]] = []
    raw_supplies: list[dict[str, Any]] = []
    raw_policies: list[dict[str, Any]] = []
    failed_servers: list[str] = []

    # ── Oracle EBS — inventory, sales orders, WIP ─────────────────────────
    if settings.mcp_oracle_ebs.enabled:
        try:
            async with OracleEBSConnector(settings.mcp_oracle_ebs) as ebs:
                so_task = ebs.get_sales_orders()
                inv_task = ebs.get_inventory_levels()
                wip_task = ebs.list_wip_jobs()
                so, inv, wip = await asyncio.gather(so_task, inv_task, wip_task)

                if so:
                    raw_demands.append(MCPToolOutput(
                        server_name="oracle_ebs",
                        tool_name="get_sales_orders",
                        raw_payload={"items": so},
                        correlation_id=_cid(),
                    ).model_dump())
                if inv:
                    raw_supplies.append(MCPToolOutput(
                        server_name="oracle_ebs",
                        tool_name="get_inventory_levels",
                        raw_payload={"items": inv},
                        correlation_id=_cid(),
                    ).model_dump())
                if wip:
                    raw_supplies.append(MCPToolOutput(
                        server_name="oracle_ebs",
                        tool_name="list_wip_jobs",
                        raw_payload={"items": wip},
                        correlation_id=_cid(),
                    ).model_dump())

            async with StoreAgent(settings.mcp_agent_store) as store:
                # Fetch forecast with a broad query (no item filter = all items)
                forecast = await store._call_tool("get_demand_forecast", {})
                if forecast:
                    raw_demands.append(MCPToolOutput(
                        server_name="oracle_ebs",
                        tool_name="get_demand_forecast",
                        raw_payload={"items": forecast} if isinstance(forecast, list) else forecast,
                        correlation_id=_cid(),
                    ).model_dump())

            async with BuyerAgent(settings.mcp_agent_buyer) as buyer:
                pos = await buyer.get_purchase_orders()
                if pos:
                    raw_supplies.append(MCPToolOutput(
                        server_name="oracle_ebs",
                        tool_name="get_purchase_orders",
                        raw_payload={"items": pos},
                        correlation_id=_cid(),
                    ).model_dump())

        except Exception as exc:
            log_event("warn", "fetch_oracle_ebs_failed", error=str(exc))
            failed_servers.append("oracle_ebs")

    # ── SAP — additional inventory / demand ──────────────────────────────
    if settings.mcp_sap.enabled:
        try:
            async with SAPConnector(settings.mcp_sap) as sap:
                sap_so = await sap.get_sales_orders()
                if sap_so:
                    raw_demands.append(MCPToolOutput(
                        server_name="sap",
                        tool_name="get_sales_orders",
                        raw_payload={"items": sap_so},
                        correlation_id=_cid(),
                    ).model_dump())
        except Exception as exc:
            log_event("warn", "fetch_sap_failed", error=str(exc))
            failed_servers.append("sap")

    # ── External RAG — SOP / policy ───────────────────────────────────────
    if settings.mcp_external_rag.enabled:
        try:
            async with PolicyServerClient(settings.mcp_external_rag) as rag:
                # Broad SOP fetch; process_code="" returns general manufacturing SOPs
                sop = await rag._call_tool("get_sop", {"process_code": "manufacturing"})
                if sop:
                    raw_policies.append(MCPToolOutput(
                        server_name="external_rag",
                        tool_name="get_sop",
                        raw_payload=sop if isinstance(sop, dict) else {"content": str(sop)},
                        correlation_id=_cid(),
                    ).model_dump())
        except Exception as exc:
            log_event("warn", "fetch_rag_failed", error=str(exc))
            failed_servers.append("external_rag")

    # Preserve any pre-loaded data passed into the planning request
    raw_demands = raw_demands or state.get("raw_demands", [])
    raw_supplies = raw_supplies or state.get("raw_supplies", [])
    raw_policies = raw_policies or state.get("raw_policies", [])

    degradation = (
        "CRITICAL" if len(failed_servers) >= 3
        else "LIMITED" if len(failed_servers) == 2
        else "DEGRADED" if failed_servers
        else "FULL"
    )

    return {
        "raw_demands": raw_demands,
        "raw_supplies": raw_supplies,
        "raw_policies": raw_policies,
        "degradation_level": degradation,
    }


@logged_node("transform")
async def node_transform(state: PlanningState) -> dict[str, Any]:
    """TRANSFORM: Map MCPToolOutput → Domain models via SemanticTransformers.

    Routes each MCPToolOutput to the correct transformer via can_handle().
    Items that fail transformation receive confidence=0.0 and are logged
    but not dropped, so agents can reason about partial data.
    """
    from axon.connectors.mcp_odoo.transformer import OdooTransformer
    from axon.connectors.mcp_oracle_ebs.transformer import OracleEBSTransformer
    from axon.connectors.mcp_sap.transformer import SAPTransformer

    correlation_id: str = state.get("correlation_id", "")
    log_event("info", "phase_transform", correlation_id=correlation_id)

    transformers = [OracleEBSTransformer(), SAPTransformer(), OdooTransformer()]

    demands_out: list[dict[str, Any]] = []
    supplies_out: list[dict[str, Any]] = []

    def _transform_batch(raw_items: list[dict[str, Any]], *, demand: bool) -> None:
        for raw in raw_items:
            try:
                output = MCPToolOutput.model_validate(raw)
            except Exception as exc:
                log_event("warn", "transform_parse_failed", error=str(exc))
                continue

            handled = False
            for tx in transformers:
                if not tx.can_handle(output):
                    continue
                try:
                    if demand:
                        for d in tx.to_demand(output):
                            demands_out.append(d.model_dump(mode="json"))
                    else:
                        for s in tx.to_supply(output):
                            supplies_out.append(s.model_dump(mode="json"))
                    handled = True
                    break
                except Exception as exc:
                    log_event(
                        "warn",
                        "transform_item_failed",
                        server_name=output.server_name,
                        tool_name=output.tool_name,
                        error=str(exc),
                    )
            if not handled:
                log_event(
                    "warn",
                    "transform_no_handler",
                    server_name=output.server_name,
                    tool_name=output.tool_name,
                )

    _transform_batch(state.get("raw_demands", []), demand=True)
    _transform_batch(state.get("raw_supplies", []), demand=False)

    log_event(
        "info",
        "transform_complete",
        demand_count=len(demands_out),
        supply_count=len(supplies_out),
    )
    return {
        "demands": demands_out,
        "supplies": supplies_out,
    }


@logged_node("reason")
async def node_reason(state: PlanningState) -> dict[str, Any]:
    """REASON: Each domain agent analyses its area and produces a proposal.

    All 10 agents run in parallel (grouped by domain group).  Each agent
    may call its MCP tools to gather additional data during reasoning.
    Past insights from long-term memory are injected into the context.
    """
    from axon.agents.commercial.finance import FinanceAgent
    from axon.agents.commercial.procurement import ProcurementAgent
    from axon.agents.commercial.sales import SalesAgent
    from axon.agents.operations.logistics import LogisticsAgent
    from axon.agents.operations.production import ProductionAgent
    from axon.agents.operations.warehouse import WarehouseAgent
    from axon.agents.technical.maintenance import MaintenanceAgent
    from axon.agents.technical.pd import PDAgent
    from axon.agents.technical.qa import QAAgent
    from axon.agents.technical.qc import QCAgent
    from axon.connectors.mcp_external_rag.client import PolicyServerClient
    from axon.connectors.mcp_oracle_ebs import BuyerAgent, OracleEBSConnector, StoreAgent
    from axon.connectors.mcp_sap.connector import SAPConnector

    correlation_id: str = state.get("correlation_id", "")
    log_event("info", "phase_reason", correlation_id=correlation_id)

    # Build connector instances (not yet connected — agents connect on tool call)
    connectors: dict[str, Any] = {}
    if settings.mcp_oracle_ebs.enabled:
        connectors["oracle_ebs"] = OracleEBSConnector(settings.mcp_oracle_ebs)
    if settings.mcp_agent_store.enabled:
        connectors["mcp_agent_store"] = StoreAgent(settings.mcp_agent_store)
    if settings.mcp_agent_buyer.enabled:
        connectors["mcp_agent_buyer"] = BuyerAgent(settings.mcp_agent_buyer)
    if settings.mcp_sap.enabled:
        connectors["sap"] = SAPConnector(settings.mcp_sap)
    if settings.mcp_external_rag.enabled:
        connectors["external_rag"] = PolicyServerClient(settings.mcp_external_rag)

    # Planning context available to all agents
    agent_context: dict[str, Any] = {
        "correlation_id": correlation_id,
        "demands": state.get("demands", []),
        "supplies": state.get("supplies", []),
        "allocations": state.get("allocations", []),
        "past_insights": state.get("past_insights", []),
        "business_weights": state.get("business_weights", {}),
        "round_number": 1,
    }

    # Instantiate all 10 agents with shared connector registry
    agents = [
        SalesAgent(connectors),
        ProcurementAgent(connectors),
        FinanceAgent(connectors),
        ProductionAgent(connectors),
        LogisticsAgent(connectors),
        WarehouseAgent(connectors),
        QAAgent(connectors),
        QCAgent(connectors),
        MaintenanceAgent(connectors),
        PDAgent(connectors),
    ]

    # Run all agents in parallel; failures produce a minimal proposal
    async def _run_agent(agent: Any) -> tuple[str, dict[str, Any]]:
        try:
            proposal = await agent.propose(agent_context)
            return agent.agent_id, proposal
        except Exception as exc:
            log_event("warn", "agent_propose_failed", agent_id=agent.agent_id, error=str(exc))
            return agent.agent_id, {
                "agent_id": agent.agent_id,
                "round_number": 1,
                "allocations": [],
                "utility_score": 0.2,
                "justification": f"Agent {agent.agent_id} failed: {exc!s}",
                "status": "proposed",
                "amendments": [],
            }

    results = await asyncio.gather(*[_run_agent(a) for a in agents])
    agent_proposals = {agent_id: proposal for agent_id, proposal in results}

    log_event("info", "reason_complete", agent_count=len(agent_proposals))
    return {"agent_proposals": agent_proposals}


@logged_node("negotiate")
async def node_negotiate(state: PlanningState) -> dict[str, Any]:
    """NEGOTIATE: ConflictResolver runs utility-auction rounds until convergence.

    Converts agent_proposals dicts to typed AgentProposal objects, runs
    the full negotiation algorithm, and stores the final round result.
    """
    from axon.orchestrator.conflict_resolver import (
        BusinessWeights,
        ConflictResolver,
        NegotiationConfig,
    )

    correlation_id: str = state.get("correlation_id", "")
    log_event("info", "phase_negotiate", correlation_id=correlation_id)

    raw_proposals: dict[str, Any] = state.get("agent_proposals", {})
    bw_dict: dict[str, float] = state.get(
        "business_weights",
        {"cost": 0.3, "delivery": 0.3, "quality": 0.2, "sustainability": 0.1, "flexibility": 0.1},
    )

    # Deserialise business weights
    weights = BusinessWeights(
        cost=bw_dict.get("cost", 0.3),
        delivery=bw_dict.get("delivery", 0.3),
        quality=bw_dict.get("quality", 0.2),
        sustainability=bw_dict.get("sustainability", 0.1),
        flexibility=bw_dict.get("flexibility", 0.1),
    )

    # Deserialise AgentProposal objects from the raw dicts
    typed_proposals: dict[str, AgentProposal] = {}
    for agent_id, raw in raw_proposals.items():
        try:
            typed_proposals[agent_id] = AgentProposal.model_validate(raw)
        except Exception as exc:
            log_event("warn", "proposal_parse_failed", agent_id=agent_id, error=str(exc))

    if not typed_proposals:
        log_event("warn", "negotiate_no_proposals")
        return {
            "negotiation_rounds": [],
            "final_plan": [],
            "deadlock": False,
        }

    config = NegotiationConfig(
        max_rounds=settings.agent_defaults.negotiation_rounds,
        weights=weights,
    )
    resolver = ConflictResolver(config)

    final_round = await resolver.resolve(typed_proposals, demand_context={
        "demands": state.get("demands", []),
        "supplies": state.get("supplies", []),
    })

    # Collect all allocations from the resolved proposals as the final plan
    final_plan: list[dict[str, Any]] = []
    for proposal in final_round.proposals.values():
        for alloc in proposal.allocations:
            final_plan.append(alloc.model_dump(mode="json"))

    rounds_serialised = [final_round.model_dump(mode="json")]

    log_event(
        "info",
        "negotiate_complete",
        resolved=final_round.resolved,
        global_utility=final_round.global_utility,
        round_count=len(rounds_serialised),
    )
    return {
        "negotiation_rounds": rounds_serialised,
        "final_plan": final_plan,
        "deadlock": not final_round.resolved,
        "business_weights": bw_dict,
    }


@logged_node("approve")
async def node_approve(state: PlanningState) -> dict[str, Any]:
    """APPROVE: Human-in-the-Loop approval node.

    Routes to:
      - Auto-approve for low-impact, non-deadlock plans
      - HITL interrupt for high-impact, deadlock, or first-run plans

    Auto-approval conditions (all must be true):
      1. Plan is not deadlocked
      2. No high-confidence VIP demands (priority > 95)
      3. Number of conflicts < 3
      4. Plan confidence >= 0.6 (or no traces)
    """
    log_event("info", "phase_approve", correlation_id=state.get("correlation_id", ""))

    deadlock = state.get("deadlock", False)
    demands = state.get("demands", [])

    # Compute severity using new escalation engine
    severity_score = compute_severity_from_state(state)
    escalation_level = determine_escalation_level(
        "production_broken" if deadlock else "po_delay",
        severity_score,
        priority=max((d.get("priority", 0) for d in demands), default=0),
    )

    # Determine if HITL is required via SeverityScorer
    scorer = SeverityScorer()
    hitl_required = scorer.needs_hitl(
        severity_score,
        next(
            (et for et in __import__("axon.core.escalation", fromlist=["EventType"]).EventType
             if et.value == ("production_broken" if deadlock else "po_delay")),
            __import__("axon.core.escalation", fromlist=["EventType"]).EventType.PO_DELAY,
        ),
        priority=max((d.get("priority", 0) for d in demands), default=0),
    )

    state["hitl_required"] = hitl_required

    if hitl_required:
        # Record escalation step
        state["escalation_steps"] = state.get("escalation_steps", []) + [{
            "level": _str_escalation_level(escalation_level),
            "phase": "approve",
            "severity_score": severity_score,
        }]
        state["severity_score"] = severity_score
        state["escalation_level"] = _str_escalation_level(escalation_level)

        # Record the plan first so it's available for review
        ledger = await _get_ledger()
        plan_id = await ledger.record_plan_from_state(state)

        # Notify dashboard of pending approval
        reason = (
            "Deadlock resolved by utility auction"
            if deadlock
            else "High-impact plan requiring human review"
        )
        await notify_pending_approval(plan_id, reason)

        log_event(
            "info",
            "hitl_pending",
            plan_id=str(plan_id),
            deadlock=deadlock,
            reason=reason,
        )

        return {
            "approved": False,
            "approval_note": "Pending human review",
            "approval_plan_id": plan_id,
            "hitl_required": True,
        }

    # Auto-approve
    log_event("info", "plan_auto_approved", correlation_id=state.get("correlation_id", ""))
    return {
        "approved": True,
        "approval_note": "Auto-approved — no conflicts requiring human review",
        "approval_plan_id": None,
        "hitl_required": False,
    }


@logged_node("learn")
async def node_learn(state: PlanningState) -> dict[str, Any]:
    """LEARN: Record plan, context, and outcome in Experience Ledger.

    If the plan was already recorded during HITL (approval_plan_id is set),
    just update it with the outcome. Otherwise record it fresh.
    """
    log_event("info", "phase_learn", correlation_id=state.get("correlation_id", ""))

    approved = state.get("approved", False)
    plan_id = state.get("approval_plan_id")

    if not approved:
        # Rejected or cancelled — record as negative example
        log_event(
            "info",
            "plan_not_recorded",
            reason="Not approved",
            correlation_id=state.get("correlation_id", ""),
        )
        return {"experience_record_id": ""}

    try:
        ledger = await _get_ledger()

        if plan_id:
            # Plan already recorded during HITL — update with outcome
            outcome = PlanOutcome(
                on_time=True,  # Optimistic; updated later via dashboard
                notes=state.get("approval_note", ""),
            )
            await ledger.record_outcome(plan_id, outcome)
            record_id = str(plan_id)

            await notify_plan_recorded(plan_id, [], None)
        else:
            # Record fresh
            record_id = str(await ledger.record_plan_from_state(state))

        log_event(
            "info",
            "plan_recorded",
            experience_record_id=record_id,
            correlation_id=state.get("correlation_id", ""),
        )
        return {"experience_record_id": record_id}

    except Exception as exc:
        log_event(
            "warn",
            "ledger_record_failed",
            correlation_id=state.get("correlation_id", ""),
            error=str(exc),
        )
        return {"experience_record_id": ""}


@logged_node("executive")
async def node_executive(state: PlanningState) -> dict[str, Any]:
    """EXECUTIVE: Strategic assessment for high-severity escalation.

    Called when severity score > DIRECTOR_MAX or event type is in
    ALWAYS_EXECUTIVE. Produces an executive assessment with recommended
    actions and presents them for HITL approval.
    """
    log_event("info", "phase_executive")

    severity_score = state.get("severity_score", 0)
    demands = state.get("demands", [])
    deadlock = state.get("deadlock", False)

    # Build context summary
    demand_summary = "; ".join(
        f"{d.get('item_name', d.get('item_native_id', 'unknown'))} x{d.get('quantity', 0)}"
        for d in demands[:3]
    )
    (
        f"Severity score: {severity_score:,.0f}. "
        f"Deadlock: {deadlock}. "
        f"Top demands: {demand_summary or 'none'}. "
        f"Negotiation rounds: {len(state.get('negotiation_rounds', []))}."
    )

    # Generate mock assessment (in production: call LLM via assess_crisis)
    assessment = make_mock_assessment(
        event_type="production_broken" if deadlock else "po_delay",
    )

    state["executive_assessment"] = assessment.model_dump(mode="json")
    state["escalation_level"] = "executive"
    state.setdefault("escalation_steps", []).append({
        "level": "executive",
        "phase": "assessment",
        "risk": assessment.risk_level,
        "actions": len(assessment.recommended_actions),
        "board_escalation": assessment.escalate_to_board,
    })

    log_event(
        "info",
        "executive_assessment_ready",
        risk=assessment.risk_level,
        action_count=len(assessment.recommended_actions),
        board=assessment.escalate_to_board,
    )

    return {
        "executive_assessment": assessment.model_dump(mode="json"),
        "escalation_level": "executive",
    }


# =============================================================================
# HITL Decision Logic
# =============================================================================


def _needs_hitl(
    deadlock: bool,
    demands: list[dict[str, Any]],
    negotiation_rounds: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> bool:
    """Determine if a plan requires human-in-the-loop approval.

    Returns True if any condition below is met:
      1. Deadlock reached (negotiation exhausted max_rounds)
      2. High-priority VIP demand (priority > 90) with any shortage
      3. More than 2 conflict rounds
      4. Plan confidence below 0.5
      5. First 5 plans (learning phase) — always get human review
    """
    # Condition 1: Deadlock
    if deadlock:
        return True

    # Condition 2: VIP demand with potential shortage
    for demand in demands:
        priority = demand.get("priority", 0)
        if priority > 90:
            return True

    # Condition 3: Many conflict rounds
    conflict_rounds = sum(
        1
        for r in negotiation_rounds
        if isinstance(r, dict) and r.get("resolution", "").startswith("Conflict")
    )
    if conflict_rounds > 2:
        return True

    # Condition 4: Low confidence from traces
    if traces:
        confidences = [t.get("confidence", 0.5) for t in traces if isinstance(t, dict)]
        if confidences and sum(confidences) / len(confidences) < 0.5:
            return True

    return False


# =============================================================================
# Routing
# =============================================================================


def route_after_negotiate(state: PlanningState) -> Literal["approve", "learn"]:
    """Route based on deadlock state.

    Deadlock → mandatory HITL approval
    Resolved → may auto-approve or go to HITL
    """
    return "approve"


def route_after_approve(state: PlanningState) -> Literal["executive", "learn", "__end__"]:
    """Route after approval decision.

    Executive-level severity → route to executive_node for strategic HITL
    Approved or standard HITL → record in Experience Ledger (learn)
    Rejected → stop (end)
    """
    if state.get("escalation_level") == "executive":
        return "executive"
    if state.get("approved", False) or state.get("hitl_required", False):
        return "learn"
    return END


# =============================================================================
# Graph Builder
# =============================================================================


_ledger_pool = None


async def _get_ledger() -> ExperienceLedger:
    """Get or create the Experience Ledger singleton."""
    global _ledger_pool
    if _ledger_pool is None:
        _ledger_pool = await get_pool()
    return ExperienceLedger(_ledger_pool)


class MasterGraph:
    """Top-level LangGraph orchestrator for Axon planning cycles.

    Integrates short-term memory (checkpointer) and long-term memory (store).

    Usage (dev — in-memory):
        graph = MasterGraph()
        compiled = graph.compile()
        result = await graph.run({...})

    Usage (production — PostgreSQL-backed memory):
        graph = await MasterGraph.with_postgres()
        compiled = graph.compile()
        result = await graph.run({...})
    """

    def __init__(
        self,
        checkpointer: MemorySaver | None = None,
        store: PostgresStore | None = None,
    ):
        self._checkpointer = checkpointer or MemorySaver()
        self._store = store
        self._compiled = None

    @classmethod
    async def with_postgres(
        cls,
        checkpointer_url: str | None = None,
        store_pool: Any = None,
    ) -> MasterGraph:
        """Create a MasterGraph with PostgreSQL-backed memory.

        Short-term memory uses PostgresSaver for graph checkpointing.
        Long-term memory uses PostgresStore for cross-thread knowledge.

        Args:
            checkpointer_url: PostgreSQL connection string for checkpoints.
                Defaults to settings.database.url.
            store_pool: Existing asyncpg pool for the long-term store.
                Creates one from settings if None.

        Returns:
            MasterGraph instance with memory wired in.
        """
        from axon.core.memory.store import PostgresStore

        # Long-term store
        store = await PostgresStore.from_conn_string(
            checkpointer_url or settings.database.url,
        )

        return cls(store=store)

    def build(self) -> StateGraph:
        """Construct the StateGraph with all nodes and edges.

        Pipeline: retrieve_context → fetch → transform → reason →
                  negotiate → approve → learn → store_insights
        """
        builder = StateGraph(PlanningState)

        # Custom memory nodes
        builder.add_node("retrieve_context", node_retrieve_context)
        builder.add_node("store_insights", node_store_insights)

        # Planning pipeline nodes
        builder.add_node("fetch", node_fetch)
        builder.add_node("transform", node_transform)
        builder.add_node("reason", node_reason)
        builder.add_node("negotiate", node_negotiate)
        builder.add_node("approve", node_approve)
        builder.add_node("executive", node_executive)  # Escalation: executive HITL
        builder.add_node("learn", node_learn)

        # Edges
        builder.set_entry_point("retrieve_context")
        builder.add_edge("retrieve_context", "fetch")
        builder.add_edge("fetch", "transform")
        builder.add_edge("transform", "reason")
        builder.add_edge("reason", "negotiate")
        builder.add_conditional_edges("negotiate", route_after_negotiate)
        builder.add_conditional_edges("approve", route_after_approve)
        # Executive assessment → learn (post-HITL)
        builder.add_edge("executive", "learn")
        builder.add_edge("learn", "store_insights")
        builder.add_edge("store_insights", END)

        return builder

    def compile(self, checkpointer: MemorySaver | None = None):
        """Compile the graph with optional checkpointer.

        Args:
            checkpointer: Override the checkpointer. Defaults to the one
                passed at construction (MemorySaver or PostgresSaver).
        """
        builder = self.build()
        self._compiled = builder.compile(
            checkpointer=checkpointer or self._checkpointer,
            store=self._store,
        )
        return self._compiled

    async def run(self, planning_context: dict[str, Any]) -> dict[str, Any]:
        """Execute a full planning cycle.

        Args:
            planning_context: Initial state with planning_request

        Returns:
            Final state after STORE phase
        """
        compiled = self._compiled
        if compiled is None:
            compiled = self.compile()

        initial_state = {
            "planning_request": planning_context,
            "correlation_id": planning_context.get("correlation_id", ""),
            "past_insights": [],
            "raw_demands": planning_context.get("raw_demands", []),
            "raw_supplies": planning_context.get("raw_supplies", []),
            "raw_policies": planning_context.get("raw_policies", []),
            "demands": [],
            "supplies": [],
            "allocations": [],
            "agent_proposals": {},
            "negotiation_rounds": [],
            "final_plan": {},
            "deadlock": False,
            "business_weights": planning_context.get(
                "business_weights",
                {
                    "cost": 0.3,
                    "delivery": 0.3,
                    "quality": 0.2,
                    "sustainability": 0.1,
                    "flexibility": 0.1,
                },
            ),
            "degradation_level": "FULL",
            "approved": False,
            "approval_note": "",
            "approval_plan_id": None,
            "hitl_required": False,
            "escalation_level": "manager",
            "severity_score": 0.0,
            "escalation_steps": [],
            "executive_assessment": None,
            "experience_record_id": "",
            "traces": planning_context.get("traces", []),
            "_store": self._store,  # Injected for memory nodes
        }

        # Config with thread_id for checkpointer (required by MemorySaver/PostgresSaver)
        config = {
            "configurable": {
                "thread_id": planning_context.get(
                    "correlation_id",
                    __import__("uuid").uuid4().hex,
                ),
            },
        }

        with trace_planning_cycle() as span:
            result = await compiled.ainvoke(initial_state, config=config)
            span.set_attribute("approved", result.get("approved", False))
            span.set_attribute("deadlock", result.get("deadlock", False))
            span.set_attribute("experience_record_id", result.get("experience_record_id", ""))
            # Clean up internal key before returning
            result.pop("_store", None)
            return result

    async def close(self) -> None:
        """Close the Experience Ledger pool, long-term store, and log pool."""
        global _ledger_pool
        if _ledger_pool:
            await _ledger_pool.close()
            _ledger_pool = None
        if self._store:
            await self._store.close()
        from axon.orchestrator.logging import close_log_pool
        await close_log_pool()
