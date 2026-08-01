from dnc.cognition import (
    CognitiveActionType,
    CognitiveProposal,
    CognitiveState,
    EpistemicItem,
    EpistemicStatus,
    EvidenceItem,
    GoalInvariant,
    HaltingDecisionType,
    PolicyContext,
    ReferenceCognitiveController,
    RiskClass,
    TaskSpec,
)
from dnc.cognition.controller import CognitiveAuthorizationKernel


def _task(risk: RiskClass = RiskClass.MEDIUM) -> TaskSpec:
    return TaskSpec(
        task_id="task-1",
        description="answer under a verification policy",
        goal=GoalInvariant(
            objective="return a verified answer",
            mandatory_verification=("verifier-1",),
        ),
        policy=PolicyContext(risk_class=risk),
    )


def test_controller_asks_when_information_is_missing() -> None:
    state = CognitiveState(task=_task()).with_epistemic_item(
        EpistemicItem(
            item_id="unknown-1",
            status=EpistemicStatus.UNKNOWN,
            content="source date is unknown",
        )
    )

    proposal = ReferenceCognitiveController().propose_next(state)
    halt = ReferenceCognitiveController().halt(state)

    assert proposal.action_type is CognitiveActionType.ASK
    assert halt.decision is HaltingDecisionType.ASK


def test_controller_verifies_when_contradictions_exist() -> None:
    state = CognitiveState(task=_task()).with_epistemic_item(
        EpistemicItem(
            item_id="conflict-1",
            status=EpistemicStatus.CONFLICT,
            content="two sources disagree",
        )
    )

    proposal = ReferenceCognitiveController().propose_next(state)
    halt = ReferenceCognitiveController().halt(state)

    assert proposal.action_type is CognitiveActionType.VERIFY
    assert halt.decision is HaltingDecisionType.VERIFY


def test_controller_stops_only_with_verification_and_calibrated_risk() -> None:
    state = CognitiveState(
        task=_task(),
        answer_state_id="answer-1",
        verified_answer=True,
        calibrated_risk=0.01,
        marginal_value_estimate=0.0,
    ).with_evidence(
        EvidenceItem(
            evidence_id="ev-1",
            source="deterministic-test",
            summary="answer passed verifier",
            verifier="verifier-1",
        )
    )

    controller = ReferenceCognitiveController()
    proposal = controller.propose_next(state)
    halt = controller.halt(state)

    assert proposal.action_type is CognitiveActionType.STOP
    assert halt.decision is HaltingDecisionType.STOP


def test_controller_does_not_stop_when_risk_exceeds_policy_threshold() -> None:
    state = CognitiveState(
        task=_task(risk=RiskClass.HIGH),
        answer_state_id="answer-1",
        verified_answer=True,
        calibrated_risk=0.02,
        marginal_value_estimate=0.0,
    ).with_evidence(
        EvidenceItem(
            evidence_id="ev-1",
            source="deterministic-test",
            summary="answer passed verifier",
            verifier="verifier-1",
        )
    )

    proposal = ReferenceCognitiveController().propose_next(state)

    assert proposal.action_type is CognitiveActionType.VERIFY


def test_authorization_rejects_cross_task_proposals() -> None:
    state = CognitiveState(task=_task())
    proposal = CognitiveProposal(
        proposal_id="proposal-1",
        task_id="other-task",
        action_type=CognitiveActionType.REASON,
        rationale="wrong task",
    )

    decision = CognitiveAuthorizationKernel().authorize(proposal, state)

    assert decision.authorized is False
    assert "task_id" in decision.rejection_reason
