import pytest

from dnc.cognition import (
    CognitiveActionType,
    CognitiveDecision,
    CognitiveProposal,
    CognitiveUnsupportedAction,
    EpistemicItem,
    EpistemicStatus,
    GoalInvariant,
    HaltingDecision,
    HaltingDecisionType,
    NoOpDecision,
    PolicyContext,
    RiskClass,
    TaskSpec,
)


def test_task_spec_preserves_goal_and_policy_context() -> None:
    goal = GoalInvariant(
        objective="answer with cited evidence",
        success_criteria=("correct answer",),
        constraints=("no external side effects",),
        authority=("read-only",),
        mandatory_verification=("deterministic verifier",),
    )
    policy = PolicyContext(risk_class=RiskClass.HIGH, budget=3.0)

    task = TaskSpec(
        task_id="task-1",
        description="evaluate a candidate answer",
        goal=goal,
        policy=policy,
    )

    assert task.goal.objective == "answer with cited evidence"
    assert task.policy.risk_class is RiskClass.HIGH


def test_epistemic_statuses_remain_distinct() -> None:
    assumption = EpistemicItem(
        item_id="e-1",
        status=EpistemicStatus.ASSUMPTION,
        content="the provider output is current",
    )
    observation = EpistemicItem(
        item_id="e-2",
        status=EpistemicStatus.OBSERVATION,
        content="the verifier returned pass",
    )

    assert assumption.status is not observation.status


def test_cognitive_proposal_rejects_untyped_actions() -> None:
    with pytest.raises(CognitiveUnsupportedAction):
        CognitiveProposal(
            proposal_id="p-1",
            task_id="task-1",
            action_type="STOP",
            rationale="string actions are not canonical",
        )


def test_selected_cognitive_decision_must_be_authorized() -> None:
    with pytest.raises(ValueError, match="MUST be authorized"):
        CognitiveDecision(proposal_id="p-1", authorized=False, selected=True)


def test_no_op_and_stop_are_separate_records() -> None:
    no_op = NoOpDecision(
        proposal_id="mut-1",
        source_state_id="state-1",
        accepted_no_op=True,
        isolation_grade="IR_ONLY",
        rationale="mutation did not beat preservation",
    )
    stop = HaltingDecision(
        task_id="task-1",
        decision=HaltingDecisionType.STOP,
        answer_state_id="answer-1",
        calibrated_risk=0.02,
        evidence_ids=("ev-1",),
        rationale="risk and verification policy satisfied",
    )

    assert no_op.accepted_no_op is True
    assert stop.decision is HaltingDecisionType.STOP


def test_stop_requires_calibrated_risk_and_no_open_gaps() -> None:
    with pytest.raises(ValueError, match="calibrated_risk"):
        HaltingDecision(
            task_id="task-1",
            decision=HaltingDecisionType.STOP,
            answer_state_id="answer-1",
            calibrated_risk=None,
            evidence_ids=("ev-1",),
        )

    with pytest.raises(ValueError, match="unresolved contradictions"):
        HaltingDecision(
            task_id="task-1",
            decision=HaltingDecisionType.STOP,
            answer_state_id="answer-1",
            calibrated_risk=0.02,
            evidence_ids=("ev-1",),
            unresolved_contradictions=("claim-7",),
        )


def test_supported_action_vocabulary_contains_active_inquiry_and_abstention() -> None:
    assert CognitiveActionType.RETRIEVE.value == "RETRIEVE"
    assert CognitiveActionType.OBSERVE_OR_TEST.value == "OBSERVE_OR_TEST"
    assert CognitiveActionType.ASK.value == "ASK"
    assert CognitiveActionType.ABSTAIN.value == "ABSTAIN"
