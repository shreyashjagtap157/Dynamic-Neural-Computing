"""Authorization-first Pareto semantic controller."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from dnc.cognition.canonical import canonical_json
from dnc.cognition.contracts import (
    ActionLifecycleState,
    CognitiveActionType,
    NoOpDecision,
    RiskClass,
)
from dnc.cognition.state import CognitiveState
from dnc.control.contracts import (
    ActionCandidate,
    CandidateRejection,
    ControllerContext,
    ControllerDecision,
    OutcomeVector,
)


_RISK_ORDER = {RiskClass.LOW: 1, RiskClass.MEDIUM: 2, RiskClass.HIGH: 3, RiskClass.CRITICAL: 4}


@dataclass(frozen=True)
class SemanticCognitiveController:
    """Select one authorized action using deterministic non-learned policy."""

    def select(self, context: ControllerContext) -> ControllerDecision:
        unique, duplicate_rejections = self._validate_and_deduplicate(context.candidates)
        authorized: list[ActionCandidate] = []
        rejections = list(duplicate_rejections)
        for candidate in unique:
            reasons = self._authorization_reasons(candidate, context)
            if reasons:
                rejections.append(CandidateRejection(candidate.proposal.proposal_id, tuple(reasons)))
            else:
                authorized.append(candidate)
        survivors = pareto_prune(tuple(authorized))
        selected = min(survivors, key=_lexicographic_key) if survivors else None
        alternatives = tuple(
            candidate for candidate in sorted(authorized, key=_lexicographic_key)
            if candidate is not selected
        )
        survivor_ids = {candidate.proposal.proposal_id for candidate in survivors}
        rejections.extend(
            CandidateRejection(candidate.proposal.proposal_id, ("PARETO_DOMINATED",))
            for candidate in authorized
            if candidate.proposal.proposal_id not in survivor_ids
        )
        shadow_log = tuple(
            (candidate.proposal.proposal_id, candidate.shadow_prediction)
            for candidate in unique
            if candidate.shadow_prediction is not None
        )
        audit_payload = {
            "task_id": context.task_id,
            "selected": selected.proposal.proposal_id if selected else None,
            "survivors": [candidate.proposal.proposal_id for candidate in survivors],
            "rejections": [(item.proposal_id, item.reason_codes) for item in rejections],
        }
        audit_id = hashlib.sha256(canonical_json(audit_payload).encode()).hexdigest()
        return ControllerDecision(
            selected,
            alternatives,
            tuple(rejections),
            tuple(candidate.proposal.proposal_id for candidate in survivors),
            ("LEXICOGRAPHIC_RISK_SELECTION",) if selected else ("NO_AUTHORIZED_CANDIDATE",),
            audit_id,
            shadow_log,
        )

    def authorize_lifecycle(
        self, state: CognitiveState, decision: ControllerDecision
    ) -> CognitiveState:
        if decision.selected is None:
            return state
        action_id = decision.selected.proposal.proposal_id
        current = state.action_states.get(action_id)
        lifecycle_sequence = (
            ActionLifecycleState.PROPOSED,
            ActionLifecycleState.VALIDATED,
            ActionLifecycleState.POLICY_CHECKED,
            ActionLifecycleState.AUTHORIZED,
        )
        if current is ActionLifecycleState.AUTHORIZED:
            return state
        start = lifecycle_sequence.index(current) + 1 if current in lifecycle_sequence else 0
        updated = state
        for lifecycle in lifecycle_sequence[start:]:
            updated = updated.with_action_transition(action_id, lifecycle)
        return updated

    @staticmethod
    def _validate_and_deduplicate(
        candidates: tuple[ActionCandidate, ...],
    ) -> tuple[tuple[ActionCandidate, ...], tuple[CandidateRejection, ...]]:
        unique: list[ActionCandidate] = []
        seen_ids: set[str] = set()
        seen_semantics: set[tuple[object, ...]] = set()
        rejected: list[CandidateRejection] = []
        for candidate in candidates:
            proposal = candidate.proposal
            semantic_key = (
                proposal.task_id,
                proposal.action_type,
                tuple(sorted(proposal.preconditions)),
                tuple(sorted(proposal.expected_effects)),
                tuple(sorted(proposal.evidence_requirements)),
                proposal.risk,
                proposal.reversible,
                tuple(sorted(candidate.required_permissions)),
            )
            if proposal.proposal_id in seen_ids or semantic_key in seen_semantics:
                rejected.append(CandidateRejection(proposal.proposal_id, ("DUPLICATE",)))
                continue
            seen_ids.add(proposal.proposal_id)
            seen_semantics.add(semantic_key)
            unique.append(candidate)
        return tuple(unique), tuple(rejected)

    @staticmethod
    def _authorization_reasons(
        candidate: ActionCandidate, context: ControllerContext
    ) -> list[str]:
        proposal = candidate.proposal
        reasons: list[str] = []
        if proposal.task_id != context.task_id:
            reasons.append("TASK_MISMATCH")
        if proposal.action_type not in context.allowed_actions:
            reasons.append("ACTION_NOT_ALLOWED")
        if _RISK_ORDER[proposal.risk] > _RISK_ORDER[context.risk_class]:
            reasons.append("RISK_LIMIT")
        if proposal.estimated_cost > context.available_budget:
            reasons.append("COST_BUDGET")
        if proposal.estimated_latency_ms > context.deadline_remaining_ms:
            reasons.append("DEADLINE")
        if not candidate.required_permissions.issubset(context.granted_permissions):
            reasons.append("PERMISSION")
        if not candidate.preconditions_satisfied:
            reasons.append("PRECONDITION")
        if proposal.action_type is CognitiveActionType.STOP and not context.stop_authorized:
            reasons.append("STOP_NOT_AUTHORIZED")
        no_op = proposal.metadata.get("no_op_decision")
        if proposal.action_type is CognitiveActionType.STOP and no_op is not None:
            reasons.append("STOP_NO_OP_CONFLATION")
        if proposal.action_type is CognitiveActionType.RESTRUCTURE and no_op is not None:
            if not isinstance(no_op, NoOpDecision):
                reasons.append("INVALID_NO_OP_DECISION")
        return reasons


def pareto_prune(candidates: tuple[ActionCandidate, ...]) -> tuple[ActionCandidate, ...]:
    return tuple(
        candidate for candidate in candidates
        if not any(_dominates(other.prediction, candidate.prediction) for other in candidates if other is not candidate)
    )


def _dominates(left: OutcomeVector, right: OutcomeVector) -> bool:
    left_values = _objectives(left)
    right_values = _objectives(right)
    return all(a >= b for a, b in zip(left_values, right_values)) and any(
        a > b for a, b in zip(left_values, right_values)
    )


def _objectives(vector: OutcomeVector) -> tuple[float, ...]:
    return (
        vector.quality_gain,
        vector.information_gain,
        vector.confidence_gain,
        -vector.monetary_cost,
        -vector.compute_cost,
        -vector.latency_ms,
        -vector.epistemic_risk,
        -vector.safety_risk,
        -vector.privacy_risk,
        vector.reversibility,
        -vector.side_effect_magnitude,
    )


def _lexicographic_key(candidate: ActionCandidate) -> tuple[object, ...]:
    vector = candidate.prediction
    return (
        vector.safety_risk,
        vector.privacy_risk,
        vector.epistemic_risk + candidate.uncertainty,
        vector.side_effect_magnitude,
        -vector.reversibility,
        -(vector.quality_gain + vector.information_gain + vector.confidence_gain),
        vector.monetary_cost,
        vector.compute_cost,
        vector.latency_ms,
        candidate.proposal.proposal_id,
    )
