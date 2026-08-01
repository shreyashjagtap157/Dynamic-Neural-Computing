"""Deterministic reference controller for first cognitive-runtime tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.cognition.calibration import CalibrationProfile, default_reference_calibration
from dnc.cognition.contracts import (
    CognitiveActionType,
    CognitiveDecision,
    CognitiveProposal,
    HaltingDecision,
    HaltingDecisionType,
    RiskClass,
)
from dnc.cognition.state import CognitiveState


RISK_ORDER: dict[RiskClass, int] = {
    RiskClass.LOW: 1,
    RiskClass.MEDIUM: 2,
    RiskClass.HIGH: 3,
    RiskClass.CRITICAL: 4,
}


@dataclass(frozen=True)
class CognitiveAuthorizationKernel:
    """Stable rule checks that learned policies must not bypass."""

    calibration: CalibrationProfile = field(default_factory=default_reference_calibration)

    def authorize(self, proposal: CognitiveProposal, state: CognitiveState) -> CognitiveDecision:
        """Authorize a cognitive proposal against task invariants and policy."""

        if proposal.task_id != state.task.task_id:
            return CognitiveDecision(
                proposal_id=proposal.proposal_id,
                authorized=False,
                rejection_reason="proposal task_id does not match cognitive state",
            )
        if RISK_ORDER[proposal.risk] > RISK_ORDER[state.task.policy.risk_class]:
            return CognitiveDecision(
                proposal_id=proposal.proposal_id,
                authorized=False,
                rejection_reason="proposal risk exceeds task policy risk class",
            )
        if proposal.action_type is CognitiveActionType.STOP and not _can_stop(
            state, self.calibration
        ):
            return CognitiveDecision(
                proposal_id=proposal.proposal_id,
                authorized=False,
                rejection_reason="STOP preconditions are not satisfied",
            )
        return CognitiveDecision(proposal_id=proposal.proposal_id, authorized=True)


@dataclass(frozen=True)
class ReferenceCognitiveController:
    """Minimal deterministic controller for the Cognitive Runtime profile."""

    calibration: CalibrationProfile = field(default_factory=default_reference_calibration)
    authorization: CognitiveAuthorizationKernel | None = None

    def __post_init__(self) -> None:
        if self.authorization is None:
            object.__setattr__(
                self,
                "authorization",
                CognitiveAuthorizationKernel(calibration=self.calibration),
            )

    def propose_next(self, state: CognitiveState) -> CognitiveProposal:
        """Propose the next cognitive action from semantic state only."""

        if state.unresolved_contradictions:
            return CognitiveProposal(
                proposal_id=f"{state.task.task_id}:verify-conflict",
                task_id=state.task.task_id,
                action_type=CognitiveActionType.VERIFY,
                rationale="unresolved contradictions require verification before stopping",
                evidence_requirements=state.unresolved_contradictions,
                risk=state.task.policy.risk_class,
            )
        if state.missing_information:
            return CognitiveProposal(
                proposal_id=f"{state.task.task_id}:ask-missing-info",
                task_id=state.task.task_id,
                action_type=CognitiveActionType.ASK,
                rationale="missing information dominates further internal reasoning",
                evidence_requirements=state.missing_information,
                risk=state.task.policy.risk_class,
            )
        if _can_stop(state, self.calibration):
            return CognitiveProposal(
                proposal_id=f"{state.task.task_id}:stop",
                task_id=state.task.task_id,
                action_type=CognitiveActionType.STOP,
                rationale="answer risk, verification, and information requirements are satisfied",
                risk=state.task.policy.risk_class,
            )
        if state.answer_state_id is not None:
            return CognitiveProposal(
                proposal_id=f"{state.task.task_id}:verify-answer",
                task_id=state.task.task_id,
                action_type=CognitiveActionType.VERIFY,
                rationale="answer exists but stopping evidence is insufficient",
                risk=state.task.policy.risk_class,
            )
        return CognitiveProposal(
            proposal_id=f"{state.task.task_id}:reason",
            task_id=state.task.task_id,
            action_type=CognitiveActionType.REASON,
            rationale="no answer state exists yet",
            risk=state.task.policy.risk_class,
        )

    def decide_next(self, state: CognitiveState) -> CognitiveDecision:
        """Select the deterministic next proposal if it passes stable authorization."""

        proposal = self.propose_next(state)
        decision = self.authorization.authorize(proposal, state)
        if not decision.authorized:
            return decision
        return CognitiveDecision(
            proposal_id=proposal.proposal_id,
            authorized=True,
            selected=True,
        )

    def halt(self, state: CognitiveState) -> HaltingDecision:
        """Return a task-level halting decision from current state."""

        if _can_stop(state, self.calibration):
            return HaltingDecision(
                task_id=state.task.task_id,
                decision=HaltingDecisionType.STOP,
                answer_state_id=state.answer_state_id,
                calibrated_risk=state.calibrated_risk,
                evidence_ids=state.evidence_ids,
                marginal_value_estimate=state.marginal_value_estimate,
                rationale="risk and verification policy satisfied",
            )
        if state.unresolved_contradictions:
            return HaltingDecision(
                task_id=state.task.task_id,
                decision=HaltingDecisionType.VERIFY,
                answer_state_id=state.answer_state_id,
                calibrated_risk=state.calibrated_risk,
                evidence_ids=state.evidence_ids,
                unresolved_contradictions=state.unresolved_contradictions,
                missing_information=state.missing_information,
                marginal_value_estimate=state.marginal_value_estimate,
                rationale="contradictions remain unresolved",
            )
        if state.missing_information:
            return HaltingDecision(
                task_id=state.task.task_id,
                decision=HaltingDecisionType.ASK,
                answer_state_id=state.answer_state_id,
                calibrated_risk=state.calibrated_risk,
                evidence_ids=state.evidence_ids,
                missing_information=state.missing_information,
                marginal_value_estimate=state.marginal_value_estimate,
                rationale="missing information remains",
            )
        return HaltingDecision(
            task_id=state.task.task_id,
            decision=HaltingDecisionType.VERIFY,
            answer_state_id=state.answer_state_id,
            calibrated_risk=state.calibrated_risk,
            evidence_ids=state.evidence_ids,
            marginal_value_estimate=state.marginal_value_estimate,
            rationale="stopping preconditions are not yet satisfied",
        )


def _can_stop(state: CognitiveState, calibration: CalibrationProfile) -> bool:
    if state.answer_state_id is None:
        return False
    if not state.has_mandatory_verification():
        return False
    if state.unresolved_contradictions or state.missing_information:
        return False
    if state.calibrated_risk is None:
        return False
    threshold = calibration.threshold_for(state.task.policy.risk_class)
    if state.calibrated_risk > threshold:
        return False
    if state.marginal_value_estimate is not None and state.marginal_value_estimate > 0:
        return False
    return True
