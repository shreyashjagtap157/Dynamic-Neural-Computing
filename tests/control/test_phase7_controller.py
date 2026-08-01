from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnc.cognition import (
    ActionLifecycleState,
    CognitiveActionType,
    CognitiveProposal,
    CognitiveState,
    GoalInvariant,
    NoOpDecision,
    PolicyContext,
    RiskClass,
    TaskSpec,
)
from dnc.control import (
    ActionCandidate,
    CallbackCandidateGenerator,
    CandidateSource,
    ControllerContext,
    ControllerTrial,
    OutcomeVector,
    RuleCandidateGenerator,
    SemanticCognitiveController,
    compare_controller,
    pareto_prune,
)
from dnc.system import DNCSystem


def _state() -> CognitiveState:
    return CognitiveState(
        TaskSpec(
            task_id="task",
            description="choose the next cognitive action",
            goal=GoalInvariant("produce a verified answer"),
            policy=PolicyContext(risk_class=RiskClass.HIGH),
        )
    )


def _candidate(
    proposal_id: str,
    action: CognitiveActionType,
    vector: OutcomeVector,
    *,
    risk: RiskClass = RiskClass.MEDIUM,
    cost: float = 0.0,
    latency: int = 0,
    permissions: frozenset[str] = frozenset(),
    preconditions: bool = True,
    shadow: OutcomeVector | None = None,
) -> ActionCandidate:
    return ActionCandidate(
        CognitiveProposal(
            proposal_id, "task", action, f"candidate {proposal_id}",
            estimated_cost=cost, estimated_latency_ms=latency, risk=risk,
        ),
        CandidateSource.RULE,
        vector,
        required_permissions=permissions,
        preconditions_satisfied=preconditions,
        shadow_prediction=shadow,
    )


def test_rule_and_callback_generators_are_typed_and_source_checked() -> None:
    generated = RuleCandidateGenerator().generate(_state())
    assert {candidate.proposal.action_type for candidate in generated} >= {
        CognitiveActionType.REASON,
        CognitiveActionType.CONTINUE,
    }
    assert CognitiveActionType.ABSTAIN not in {
        candidate.proposal.action_type for candidate in generated
    }
    planner_candidate = replace(generated[0], source=CandidateSource.PLANNER)
    planner = CallbackCandidateGenerator(CandidateSource.PLANNER, lambda state: (planner_candidate,))
    assert planner.generate(_state()) == (planner_candidate,)
    with pytest.raises(ValueError, match="source"):
        CallbackCandidateGenerator(CandidateSource.MODEL, lambda state: (planner_candidate,)).generate(_state())


def test_hard_authorization_precedes_scoring() -> None:
    unsafe = _candidate(
        "unsafe", CognitiveActionType.OBSERVE_OR_TEST,
        OutcomeVector(quality_gain=100, information_gain=100),
        risk=RiskClass.CRITICAL, cost=10, latency=1000,
        permissions=frozenset({"dangerous:test"}), preconditions=False,
    )
    safe = _candidate("safe", CognitiveActionType.ASK, OutcomeVector(information_gain=0.3))
    decision = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (unsafe, safe), 1, 100)
    )
    assert decision.selected == safe
    rejection = next(item for item in decision.rejections if item.proposal_id == "unsafe")
    assert set(rejection.reason_codes) == {
        "RISK_LIMIT", "COST_BUDGET", "DEADLINE", "PERMISSION", "PRECONDITION"
    }


def test_stop_requires_separate_authorization_and_no_op_is_not_stop() -> None:
    stop = _candidate("stop", CognitiveActionType.STOP, OutcomeVector())
    restructure = _candidate("restructure", CognitiveActionType.RESTRUCTURE, OutcomeVector(quality_gain=0.2))
    denied = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (stop, restructure), 1, 100, stop_authorized=False)
    )
    assert denied.action_type is CognitiveActionType.RESTRUCTURE
    assert any(item.proposal_id == "stop" and "STOP_NOT_AUTHORIZED" in item.reason_codes for item in denied.rejections)
    allowed = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (stop,), 1, 100, stop_authorized=True)
    )
    assert allowed.action_type is CognitiveActionType.STOP
    assert restructure.proposal.action_type is not CognitiveActionType.STOP

    no_op = NoOpDecision("structural", "state", True, "I1_GRAPH_ONLY", "preserve graph")
    linked_restructure = replace(
        restructure,
        proposal=replace(restructure.proposal, metadata={"no_op_decision": no_op}),
    )
    linked = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (linked_restructure,), 1, 100)
    )
    assert linked.action_type is CognitiveActionType.RESTRUCTURE
    conflated_stop = replace(
        stop, proposal=replace(stop.proposal, metadata={"no_op_decision": no_op})
    )
    rejected = SemanticCognitiveController().select(
        ControllerContext(
            "task", RiskClass.HIGH, (conflated_stop,), 1, 100, stop_authorized=True
        )
    )
    assert rejected.selected is None
    assert "STOP_NO_OP_CONFLATION" in rejected.rejections[0].reason_codes


def test_pareto_pruning_and_lexicographic_risk_selection_are_deterministic() -> None:
    dominated = _candidate(
        "dominated", CognitiveActionType.REASON,
        OutcomeVector(quality_gain=0.2, monetary_cost=0.5, safety_risk=0.2),
    )
    efficient = _candidate(
        "efficient", CognitiveActionType.RETRIEVE,
        OutcomeVector(quality_gain=0.3, monetary_cost=0.2, safety_risk=0.1),
    )
    informative = _candidate(
        "informative", CognitiveActionType.ASK,
        OutcomeVector(information_gain=0.8, monetary_cost=0.1, safety_risk=0.0),
    )
    survivors = pareto_prune((dominated, efficient, informative))
    assert dominated not in survivors
    decision = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (dominated, efficient, informative), 1, 100)
    )
    assert decision.selected == informative
    assert decision.pareto_survivors


def test_shadow_predictions_are_logged_but_do_not_select() -> None:
    deterministic_best = _candidate(
        "deterministic", CognitiveActionType.VERIFY,
        OutcomeVector(quality_gain=0.5, safety_risk=0.0),
        shadow=OutcomeVector(quality_gain=0.0, safety_risk=10),
    )
    other = _candidate(
        "other", CognitiveActionType.REASON,
        OutcomeVector(quality_gain=0.1, safety_risk=0.1),
        shadow=OutcomeVector(quality_gain=100),
    )
    decision = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (deterministic_best, other), 1, 100)
    )
    assert decision.selected == deterministic_best
    assert len(decision.shadow_log) == 2


def test_every_typed_action_can_be_authorized_and_enters_lifecycle() -> None:
    for action in CognitiveActionType:
        candidate = _candidate(action.value, action, OutcomeVector())
        system = DNCSystem(cognitive_state=_state())
        decision = system.select_cognitive_action(
            ControllerContext(
                "task", RiskClass.HIGH, (candidate,), 1, 100,
                stop_authorized=action is CognitiveActionType.STOP,
            )
        )
        assert decision.action_type is action
        assert system.cognitive_state.action_states[action.value] is ActionLifecycleState.AUTHORIZED
        before = system.cognitive_state
        system.select_cognitive_action(
            ControllerContext(
                "task", RiskClass.HIGH, (candidate,), 1, 100,
                stop_authorized=action is CognitiveActionType.STOP,
            )
        )
        assert system.cognitive_state == before


def test_duplicate_and_cross_task_candidates_are_rejected_with_audit() -> None:
    candidate = _candidate("candidate", CognitiveActionType.REASON, OutcomeVector())
    duplicate = replace(candidate, proposal=replace(candidate.proposal, proposal_id="duplicate"))
    wrong_task = replace(candidate, proposal=replace(candidate.proposal, proposal_id="wrong", task_id="other"))
    decision = SemanticCognitiveController().select(
        ControllerContext("task", RiskClass.HIGH, (candidate, duplicate, wrong_task), 1, 100)
    )
    assert decision.selected == candidate
    assert decision.audit_record_id
    assert {item.proposal_id for item in decision.rejections} == {"duplicate", "wrong"}


def test_hidden_multi_action_fixture_improves_quality_cost_risk_frontier() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "hidden_multi_action.json").read_text()
    )
    assert fixture["frozen"] is True
    controller_trials = []
    for task in fixture["tasks"]:
        expected = CognitiveActionType(task["expected"])
        expected_candidate = _candidate(
            f"{task['id']}:expected", expected,
            OutcomeVector(quality_gain=1, safety_risk=task["controller_risk"]),
        )
        distractor = _candidate(
            f"{task['id']}:distractor", CognitiveActionType.REASON,
            OutcomeVector(quality_gain=0.1, safety_risk=task["baseline_risk"]),
        )
        decision = SemanticCognitiveController().select(
            ControllerContext(
                "task", RiskClass.HIGH, (expected_candidate, distractor), 1, 100,
                stop_authorized=expected is CognitiveActionType.STOP,
            )
        )
        controller_trials.append(
            ControllerTrial(
                task["id"], "semantic-controller", decision.action_type is expected,
                decision.selected is not None, bool(decision.audit_record_id),
                task["controller_cost"], task["controller_risk"],
            )
        )
    controller = tuple(controller_trials)
    baseline = tuple(
        ControllerTrial(
            task["id"], "fixed-agent-loop",
            CognitiveActionType.REASON is CognitiveActionType(task["expected"]), True, True,
            task["baseline_cost"], task["baseline_risk"],
        )
        for task in fixture["tasks"]
    )
    comparison = compare_controller(controller, baseline)
    assert comparison["pareto_improved"]
    assert comparison["authorization_complete"]
    assert comparison["trace_complete"]
