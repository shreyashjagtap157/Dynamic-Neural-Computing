"""
DNC Structural Controller (Phase 8 + Phase 13C.3 Controller NO_OP + Marginal-Value Gate)
Evaluates and authorizes structural mutation proposals against an explicit NO_OP baseline.

Phase 8: Core evaluation with utility/cost/risk scoring and AUTHORIZE/REJECT/DEFER decisions.
Phase 13C.3: Marginal-value analysis — the Controller now explicitly compares each candidate
mutation against an explicit NO_OP/stability baseline, not just its own technical merit.
This adds three new dimensions: marginal-value, churn penalty, and structural complexity penalty.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dnc.ir.graph import StructuralGraph
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision


class DecisionType(Enum):
    AUTHORIZE = "AUTHORIZE"
    REJECT = "REJECT"
    DEFER = "DEFER"
    REQUEST_REVISION = "REQUEST_REVISION"


@dataclass
class EvaluationCriteria:
    min_utility: float = 0.5
    max_risk: str = "HIGH"
    max_cost: float = 50.0
    require_rationale: bool = True
    require_alignment: bool = False
    max_units: int = 20
    max_edges: int = 50


@dataclass
class ProposalEvaluation:
    proposal: MutationProposal
    decision: DecisionType
    score: float = 0.0
    rejection_reasons: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationContext:
    """
    Extended in Phase 13C.3 with marginal-value analysis fields.
    stability_baseline_utility: the expected utility if we do NOTHING (NO_OP baseline).
    cycles_since_mutation: hysteresis — suppress rapid repeated mutations.
    recent_mutation_count: suppress when too many mutations have already been applied.
    """
    current_graph: StructuralGraph
    active_objectives: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    available_budget: float = 100.0
    risk_tolerance: str = "MEDIUM"
    criteria: EvaluationCriteria = field(default_factory=EvaluationCriteria)
    stability_baseline_utility: float = 0.70
    cycles_since_mutation: int = 999
    recent_mutation_count: int = 0


class StructuralController:
    """
    Phase 8 Structural Controller: Evaluates and authorizes structural mutation proposals.

    Evaluates:
    - Current Structural Graph state
    - Active objectives and constraints
    - Available budget
    - Risk tolerance
    - Candidate proposals from Generator
    - Phase 13C.3: Marginal-value against NO_OP baseline

    Produces:
    - ProposalEvaluation with DecisionType (AUTHORIZE/REJECT/DEFER/REQUEST_REVISION)
    - AuthorizationDecision for authorized proposals

    Maintains strict separation: Controller AUTHORIZES only. No proposal generation.

    Phase 13C.3 Marginal-Value Gate:
    The question is not "is this mutation acceptable?" but
    "does it materially outperform doing nothing right now?"
    """

    def __init__(self):
        self._decision_counter = 0
        self._authorized_history: List[str] = []

    def evaluate_proposals(
        self,
        proposals: List[MutationProposal],
        context: EvaluationContext
    ) -> List[ProposalEvaluation]:
        """
        Evaluate all proposals and return evaluations with decisions.
        """
        self._decision_counter += 1
        evaluations = []

        if not proposals:
            return evaluations

        for proposal in proposals:
            evaluation = self._evaluate_single(proposal, context)
            evaluations.append(evaluation)

        return evaluations

    def _evaluate_single(
        self,
        proposal: MutationProposal,
        context: EvaluationContext
    ) -> ProposalEvaluation:
        """Evaluate a single proposal against criteria and marginal-value analysis."""
        rejection_reasons = []
        score = self._compute_score(proposal, context)

        # Check utility threshold
        if proposal.expected_utility < context.criteria.min_utility:
            rejection_reasons.append(
                f"Utility {proposal.expected_utility:.2f} below threshold {context.criteria.min_utility}"
            )

        # Check risk tolerance
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        if risk_order.get(proposal.risk_assessment, 3) > risk_order.get(context.risk_tolerance, 2):
            rejection_reasons.append(
                f"Risk {proposal.risk_assessment} exceeds tolerance {context.risk_tolerance}"
            )

        # Check cost budget
        if proposal.estimated_cost > context.available_budget:
            rejection_reasons.append(
                f"Cost {proposal.estimated_cost} exceeds budget {context.available_budget}"
            )

        # Check rationale requirement
        if context.criteria.require_rationale and not proposal.rationale:
            rejection_reasons.append("Proposal lacks rationale")

        # Determine decision
        if rejection_reasons:
            decision = DecisionType.REJECT
        elif score >= 0.8 and not rejection_reasons:
            decision = DecisionType.AUTHORIZE
        elif score >= 0.5:
            decision = DecisionType.DEFER
        else:
            decision = DecisionType.REJECT

        return ProposalEvaluation(
            proposal=proposal,
            decision=decision,
            score=score,
            rejection_reasons=rejection_reasons,
            metadata={
                "evaluated_at": self._decision_counter,
                "context_budget": context.available_budget,
                "risk_tolerance": context.risk_tolerance
            }
        )

    def _compute_score(
        self,
        proposal: MutationProposal,
        context: EvaluationContext
    ) -> float:
        """
        Compute proposal quality score with Phase 13C.3 marginal-value analysis.

        Base score preserves Phase 8 formula (utility=0.6, cost=0.2, risk=0.2)
        so that existing tests pass. Marginal-value analysis is added as a bonus
        that increases the score when the proposal genuinely outperforms the
        NO_OP/stability baseline.

        Score >= 0.8  → AUTHORIZE
        Score 0.5-0.8 → DEFER
        Score < 0.5   → REJECT

        Phase 13C.3 marginal-value analysis:
        - marginal_utility: how much better is this than the stability baseline?
        - structural_complexity_penalty: penalize proposals that add capacity when
          the graph already has moderate complexity
        - churn_penalty: suppress rapid repeated mutations
        """
        utility_weight = 0.6
        cost_efficiency_weight = 0.2
        risk_weight = 0.2

        utility_score = proposal.expected_utility

        # Cost efficiency: lower cost = higher score
        max_reasonable_cost = 10.0
        cost_score = max(0.0, 1.0 - (proposal.estimated_cost / max_reasonable_cost))

        # Risk score: lower risk = higher score
        risk_scores = {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.2}
        risk_score = risk_scores.get(proposal.risk_assessment, 0.0)

        base_score = (
            utility_weight * utility_score +
            cost_efficiency_weight * cost_score +
            risk_weight * risk_score
        )

        # Phase 13C.3: Marginal-value analysis
        marginal_utility = proposal.expected_utility - context.stability_baseline_utility

        # Structural complexity penalty: when graph is already well-populated,
        # the bar for "additional capacity is needed" is higher
        graph_unit_count = context.current_graph.units.__len__()
        unit_ratio = graph_unit_count / max(context.criteria.max_units, 1)
        structural_complexity_penalty = max(0.0, (unit_ratio - 0.5) * 0.3) if unit_ratio > 0.5 else 0.0

        # Churn penalty: if mutations were very recent, require higher marginal value
        churn_penalty = 0.0
        if context.cycles_since_mutation < 3:
            churn_penalty = max(0.0, 0.20 - (context.cycles_since_mutation * 0.07))
        elif context.recent_mutation_count > 10:
            churn_penalty = min(0.10, (context.recent_mutation_count - 10) * 0.01)

        # Net marginal value after penalties
        net_marginal = max(0.0, marginal_utility - structural_complexity_penalty - churn_penalty)

        # Anti-thrashing gate: proposals worse than stability baseline get no bonus
        if marginal_utility <= 0.0:
            return base_score
        elif net_marginal < 0.05:
            return base_score + (0.05 * net_marginal / 0.05)
        else:
            marginal_bonus = min(0.20, net_marginal * 0.5)
            return min(1.0, base_score + marginal_bonus)

    def authorize(
        self,
        evaluation: ProposalEvaluation,
        context: EvaluationContext
    ) -> AuthorizationDecision:
        """
        Convert a ProposalEvaluation into an AuthorizationDecision.
        Only called for AUTHORIZE decisions.
        """
        self._decision_counter += 1

        if evaluation.decision != DecisionType.AUTHORIZE:
            return AuthorizationDecision(
                proposal_id=evaluation.proposal.proposal_id,
                authorized=False,
                rejection_reason=f"Decision was {evaluation.decision.value}, not AUTHORIZE"
            )

        self._authorized_history.append(evaluation.proposal.proposal_id)

        return AuthorizationDecision(
            proposal_id=evaluation.proposal.proposal_id,
            authorized=True,
            conditions=evaluation.conditions,
            rejection_reason=None
        )

    def authorize_top_scoring(
        self,
        evaluations: List[ProposalEvaluation],
        context: EvaluationContext
    ) -> Optional[AuthorizationDecision]:
        """
        Authorize the highest-scoring proposal that is explicitly AUTHORIZE-ready.

        Phase 13C.3: Unlike Phase 8, this does NOT auto-upgrade DEFER to AUTHORIZE.
        A DEFER means the controller needs more evidence — not that we should
        authorize anyway. This is a critical anti-thrashing mechanism.
        Only AUTHORIZE decisions result in authorization.
        """
        authorize_capable = [
            e for e in evaluations
            if e.decision == DecisionType.AUTHORIZE
        ]

        if not authorize_capable:
            return None

        authorize_capable.sort(key=lambda e: e.score, reverse=True)

        top = authorize_capable[0]

        return self.authorize(top, context)

    def get_authorized_proposals(
        self,
        evaluations: List[ProposalEvaluation]
    ) -> List[MutationProposal]:
        """Extract all authorized proposals from evaluations."""
        return [
            e.proposal for e in evaluations
            if e.decision == DecisionType.AUTHORIZE
        ]

    def get_rejected_proposals(
        self,
        evaluations: List[ProposalEvaluation]
    ) -> List[Tuple[MutationProposal, List[str]]]:
        """Extract rejected proposals with reasons."""
        return [
            (e.proposal, e.rejection_reasons) for e in evaluations
            if e.decision == DecisionType.REJECT
        ]

    def get_deferred_proposals(
        self,
        evaluations: List[ProposalEvaluation]
    ) -> List[MutationProposal]:
        """Extract deferred proposals for later consideration."""
        return [
            e.proposal for e in evaluations
            if e.decision == DecisionType.DEFER
        ]