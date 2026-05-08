"""Conflict Resolver — utility-based multi-agent negotiation.

Implements the 4-step resolution algorithm:
  1. Clarification — conflicting agents justify their position
  2. Amendment — agents may submit amended proposals
  3. Utility auction — supply awarded to higher-utility proposal
  4. Tiebreaker — weighted-random selection using business weights

The algorithm always terminates within max_rounds. Non-convergence
triggers NEGOTIATION_DEADLOCK → mandatory HITL review.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from axon.core.schema import (
    AgentProposal,
    Allocation,
    NegotiationRound,
    ProposalStatus,
)
from axon.core.telemetry import log_event, trace_negotiation_round

# =============================================================================
# Business Weights
# =============================================================================


@dataclass
class BusinessWeights:
    """Strategic weights set via the Control Tower. Must sum to 1.0."""

    cost: float = 0.3
    delivery: float = 0.3
    quality: float = 0.2
    sustainability: float = 0.1
    flexibility: float = 0.1

    def validate(self) -> bool:
        return (
            abs(
                sum([self.cost, self.delivery, self.quality, self.sustainability, self.flexibility])
                - 1.0
            )
            < 0.001
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "cost": self.cost,
            "delivery": self.delivery,
            "quality": self.quality,
            "sustainability": self.sustainability,
            "flexibility": self.flexibility,
        }


# =============================================================================
# Negotiation Config
# =============================================================================


@dataclass
class NegotiationConfig:
    max_rounds: int = 5
    clarification_char_limit: int = 250
    weights: BusinessWeights = field(default_factory=BusinessWeights)


# =============================================================================
# Utility Engine
# =============================================================================


def utility_score(
    proposal: AgentProposal,
    weights: BusinessWeights,
    demand: dict[str, float] | None = None,
) -> float:
    """Calculate U_i = Σ (w_k × s_ik) for an agent proposal.

    Uses heuristics based on proposal attributes when actual scoring
    dimensions aren't available (pre-LLM phase). In Phase 3 with live
    LLM agents, the agent provides its own utility_score.
    """
    if proposal.utility_score is not None:
        return proposal.utility_score

    # Heuristic fallback: score based on allocation properties
    if not proposal.allocations:
        return 0.25  # no allocations = low utility

    total_qty = sum(float(a.allocated_quantity) for a in proposal.allocations)
    fulfilled = sum(1 for a in proposal.allocations if a.status == "proposed")
    total = len(proposal.allocations) or 1

    # Simple heuristic: fill rate × base utility
    fill_rate = min(
        total_qty / (sum(float(a.demand.quantity) for a in proposal.allocations) or 1), 1.0
    )
    base = fill_rate * 0.5 + (fulfilled / total) * 0.5

    # Apply weight bias based on agent type
    agent_bias = {
        "sales": weights.delivery * 0.3 + weights.cost * 0.1,
        "production": weights.cost * 0.2 + weights.quality * 0.2,
        "procurement": weights.cost * 0.3 + weights.sustainability * 0.1,
        "warehouse": weights.cost * 0.1 + weights.flexibility * 0.1,
        "logistics": weights.delivery * 0.2 + weights.cost * 0.1,
        "finance": weights.cost * 0.4,
        "qa": weights.quality * 0.3 + weights.sustainability * 0.1,
        "qc": weights.quality * 0.3,
        "pd": weights.quality * 0.1 + weights.flexibility * 0.1,
        "maintenance": weights.flexibility * 0.2 + weights.quality * 0.1,
    }.get(proposal.agent_id, 0.15)

    return base + agent_bias


def global_utility(proposals: list[AgentProposal], weights: BusinessWeights) -> float:
    """Calculate U_total = Σ U_i for all proposals."""
    return sum(utility_score(p, weights) for p in proposals)


# =============================================================================
# Conflict Detection
# =============================================================================


def detect_conflicts(proposals: dict[str, AgentProposal]) -> list[tuple[str, str, Allocation]]:
    """Find conflicting allocations between agents.

    Two proposals conflict when they allocate the same supply to different
    demands, or allocate beyond available supply.

    Returns list of (agent_a, agent_b, conflicting_allocation).
    """
    supply_allocations: dict[str, list[tuple[str, Allocation]]] = {}

    for agent_id, proposal in proposals.items():
        for alloc in proposal.allocations:
            supply_key = str(alloc.supply.id)
            if supply_key not in supply_allocations:
                supply_allocations[supply_key] = []
            supply_allocations[supply_key].append((agent_id, alloc))

    conflicts: list[tuple[str, str, Allocation]] = []
    for _supply_key, entries in supply_allocations.items():
        if len(entries) < 2:
            continue
        # All entries consuming the same supply are conflicts
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                conflicts.append((entries[i][0], entries[j][0], entries[i][1]))

    return conflicts


# =============================================================================
# Tiebreaker
# =============================================================================


def resolve_tiebreaker(
    agent_a: str,
    agent_b: str,
    weights: BusinessWeights,
    seed: int | None = None,
) -> str:
    """Weighted-random selection between two agents.

    Uses business weights as probability distribution: an agent whose
    primary dimension has higher weight is more likely to win.
    """
    if seed is not None:
        random.seed(seed)

    weight_bias = {
        "sales": weights.delivery,
        "production": weights.cost + weights.quality,
        "procurement": weights.cost,
        "warehouse": weights.cost,
        "logistics": weights.delivery,
        "finance": weights.cost,
        "qa": weights.quality,
        "qc": weights.quality,
        "pd": weights.quality,
        "maintenance": weights.flexibility,
    }
    a_weight = weight_bias.get(agent_a, 0.1)
    b_weight = weight_bias.get(agent_b, 0.1)
    total = a_weight + b_weight
    return agent_a if random.random() < (a_weight / total) else agent_b


# =============================================================================
# Conflict Resolver
# =============================================================================


class ConflictResolver:
    """Resolves cross-departmental conflicts through multi-round negotiation."""

    def __init__(self, config: NegotiationConfig | None = None):
        self.config = config or NegotiationConfig()

    async def resolve(
        self,
        proposals: dict[str, AgentProposal],
        demand_context: dict[str, Any] | None = None,
    ) -> NegotiationRound:
        """Run negotiation rounds until convergence or max_rounds.

        Returns the final NegotiationRound with resolved=True or
        a NEGOTIATION_DEADLOCK round.
        """
        current_proposals = dict(proposals)
        last_round: NegotiationRound | None = None

        for round_num in range(1, self.config.max_rounds + 1):
            with trace_negotiation_round(round_num) as span:
                round_result = self._run_round(round_num, current_proposals, demand_context)
                span.set_attribute("conflicts", len(detect_conflicts(current_proposals)))
                span.set_attribute("global_utility", round_result.global_utility)
                span.set_attribute("resolved", round_result.resolved)
                last_round = round_result

                if round_result.resolved:
                    last_round.completed_at = datetime.now(UTC)
                    return last_round

        # Max rounds reached — deadlock
        log_event(
            "warn",
            "negotiation_deadlock",
            rounds=self.config.max_rounds,
            agent_count=len(proposals),
        )
        final = NegotiationRound(
            round_number=self.config.max_rounds,
            proposals=current_proposals,
            global_utility=global_utility(list(current_proposals.values()), self.config.weights),
            resolved=False,
            resolution="NEGOTIATION_DEADLOCK — max rounds reached, HITL required",
            completed_at=datetime.now(UTC),
        )
        return final

    # =========================================================================
    # Per-round logic
    # =========================================================================

    def _run_round(
        self,
        round_num: int,
        proposals: dict[str, AgentProposal],
        demand_context: dict[str, Any] | None = None,
    ) -> NegotiationRound:
        """Execute one negotiation round."""
        conflicts = detect_conflicts(proposals)

        if not conflicts:
            return NegotiationRound(
                round_number=round_num,
                proposals=dict(proposals),
                global_utility=global_utility(list(proposals.values()), self.config.weights),
                resolved=True,
                resolution="No conflicts detected",
                completed_at=datetime.now(UTC),
            )

        # Step 1 & 2: Clarification + Amendment (agents justify and may amend)
        for agent_id, _proposal in proposals.items():
            # Detect if this agent is in any conflict
            in_conflict = any(agent_id in (a, b) for a, b, _ in conflicts)
            if not in_conflict:
                continue

            # For now: auto-resolve via utility auction (steps 3+4)
            # In Phase 3 with live LLM agents, this triggers actual LLM calls

        # Step 3: Utility auction
        for agent_a, agent_b, conflict_alloc in conflicts:
            prop_a = proposals.get(agent_a)
            prop_b = proposals.get(agent_b)
            if not prop_a or not prop_b:
                continue

            u_a = utility_score(prop_a, self.config.weights)
            u_b = utility_score(prop_b, self.config.weights)

            if u_a > u_b:
                winner, loser = agent_a, agent_b
            elif u_b > u_a:
                winner, loser = agent_b, agent_a
            else:
                # Step 4: Tiebreaker
                winner = resolve_tiebreaker(agent_a, agent_b, self.config.weights)
                loser = agent_b if winner == agent_a else agent_a

            # Mark loser's conflicting allocation as rejected
            loser_prop = proposals.get(loser)
            if loser_prop:
                loser_prop.status = ProposalStatus.AMENDED
                loser_prop.amendments.append(
                    f"Conflict with {winner}: allocation {conflict_alloc.id} rejected via utility auction"
                )

        return NegotiationRound(
            round_number=round_num,
            proposals=dict(proposals),
            global_utility=global_utility(list(proposals.values()), self.config.weights),
            resolved=False,
            resolution=f"{len(conflicts)} conflict(s) resolved via auction",
        )
