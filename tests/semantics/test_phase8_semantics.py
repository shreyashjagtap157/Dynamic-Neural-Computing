from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnc.capabilities import CapabilityCard, CapabilityRegistry
from dnc.cognition import (
    CognitiveActionType,
    CognitiveState,
    EpistemicItem,
    EpistemicStatus,
    GoalInvariant,
    Hypothesis,
    PolicyContext,
    RiskClass,
    SideEffectClass,
    TaskSpec,
)
from dnc.ir.operations import IROperation, OperationType
from dnc.semantics import (
    CausalValidity,
    ExperimentOutcomeStatus,
    ExperimentProposal,
    SemanticSynthesizer,
    SynthesisTrial,
    SemanticUnitTemplate,
    SynthesisRequest,
    assess_observation,
    assess_candidate_outcome,
    compare_synthesis,
    select_experiment,
    semantic_deduplicate,
    validate_semantic_candidate,
)
from dnc.system import DNCSystem


def _state() -> CognitiveState:
    state = CognitiveState(
        TaskSpec(
            task_id="task",
            tenant_id="tenant-a",
            description="Resolve an unknown and test competing explanations",
            goal=GoalInvariant("produce an evidence-grounded answer"),
            policy=PolicyContext(risk_class=RiskClass.HIGH),
        )
    ).with_epistemic_item(
        EpistemicItem("unknown", EpistemicStatus.UNKNOWN, "source value unknown", tenant_id="tenant-a")
    )
    return state.with_hypothesis(
        Hypothesis(
            "hypothesis-a", "A explains the observation",
            predicted_observations=("signal-a",), strongest_falsifier="signal-not-a",
            tenant_id="tenant-a",
        )
    ).with_hypothesis(
        Hypothesis(
            "hypothesis-b", "B explains the observation",
            predicted_observations=("signal-b",), strongest_falsifier="signal-not-b",
            tenant_id="tenant-a",
        )
    )


def _registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityCard(
            "semantic", "Semantic capability", "reference", "1", "semantic-v1",
            frozenset(
                {
                    CognitiveActionType.REASON,
                    CognitiveActionType.RETRIEVE,
                    CognitiveActionType.VERIFY,
                    CognitiveActionType.OBSERVE_OR_TEST,
                }
            ),
            RiskClass.HIGH,
            permissions=frozenset({"semantic:execute"}),
            fingerprint="semantic-v1",
        )
    )
    return registry


def _template(action: CognitiveActionType, *, side_effect=SideEffectClass.NONE, cost=0.1):
    return SemanticUnitTemplate(
        f"template-{action.value.casefold()}", "1", f"Perform {action.value}", action,
        {"type": "object"}, {"type": "object"}, "semantic",
        permissions=frozenset({"semantic:execute"}),
        resource_limits={"cost": cost}, side_effect_class=side_effect,
    )


def test_synthesis_is_task_conditioned_bounded_capability_bound_and_deduplicated() -> None:
    state = _state()
    templates = tuple(
        _template(action)
        for action in (
            CognitiveActionType.REASON,
            CognitiveActionType.RETRIEVE,
            CognitiveActionType.VERIFY,
            CognitiveActionType.OBSERVE_OR_TEST,
        )
    )
    request = SynthesisRequest(
        state, templates + (templates[0],), ("event:ingress",), 1,
        frozenset({"semantic:execute"}), max_hypothesis_branches=1,
        verifier_needs=("verifier-1",),
    )
    candidates = SemanticSynthesizer(_registry()).synthesize(request)
    assert len(candidates) == 4
    assert len({candidate.semantic_fingerprint for candidate in candidates}) == 4
    experiment = next(
        candidate for candidate in candidates
        if candidate.units[0].metadata["action_type"] == CognitiveActionType.OBSERVE_OR_TEST.value
    )
    assert experiment.hypothesis_ids == ("hypothesis-a",)
    assert experiment.predicted_evidence == ("signal-a",)
    assert semantic_deduplicate(candidates + candidates) == candidates


def test_semantic_validation_enforces_policy_provenance_permissions_and_isolation() -> None:
    state = _state()
    candidate = SemanticSynthesizer(_registry()).synthesize(
        SynthesisRequest(
            state,
            (_template(CognitiveActionType.OBSERVE_OR_TEST, side_effect=SideEffectClass.REVERSIBLE),),
            ("event:ingress",),
            1,
            max_hypothesis_branches=1,
        )
    )[0]
    denied = validate_semantic_candidate(
        candidate, _registry(), task_id="task", tenant_id="tenant-a",
        available_budget=0.05, granted_permissions=frozenset(),
        available_isolation_grade="I1_GRAPH_ONLY",
    )
    assert not denied.valid
    assert {reason.split(":")[0] for reason in denied.reason_codes} >= {
        "COST_BUDGET", "PERMISSION", "UNIT_PERMISSION", "ISOLATION_GRADE"
    }
    allowed = validate_semantic_candidate(
        candidate, _registry(), task_id="task", tenant_id="tenant-a",
        available_budget=1, granted_permissions=frozenset({"semantic:execute"}),
        available_isolation_grade="I3_RECORDED_EXTERNALS",
    )
    assert allowed.valid


def test_candidate_cannot_smuggle_non_semantic_mutation() -> None:
    state = _state()
    candidate = SemanticSynthesizer(_registry()).synthesize(
        SynthesisRequest(state, (_template(CognitiveActionType.REASON),), ("event",), 1)
    )[0]
    malicious = replace(
        candidate,
        operations=(IROperation(OperationType.REMOVE_UNIT, {"unit_id": candidate.units[0].unit_id}, "remove"),),
    )
    validation = validate_semantic_candidate(
        malicious, _registry(), task_id="task", tenant_id="tenant-a", available_budget=1,
        granted_permissions=frozenset({"semantic:execute"}), available_isolation_grade="I4_SANDBOXED_ENVIRONMENT",
    )
    assert not validation.valid
    assert "OPERATION_NOT_SEMANTIC:REMOVE_UNIT" in validation.reason_codes


def test_system_applies_semantic_candidate_transactionally_and_snapshot_restores() -> None:
    state, registry = _state(), _registry()
    system = DNCSystem(cognitive_state=state, capability_registry=registry)
    snapshot = system.capture_execution_snapshot("before-semantic")
    candidate = system.synthesize_semantic_graph(
        SynthesisRequest(state, (_template(CognitiveActionType.REASON),), ("event",), 1)
    )[0]
    committed, validation = system.apply_semantic_candidate(
        candidate, available_budget=1,
        granted_permissions=frozenset({"semantic:execute"}),
        available_isolation_grade="I1_GRAPH_ONLY",
    )
    assert committed and validation.valid
    assert candidate.units[0].unit_id.value in system.graph.units
    assert system.graph.units[candidate.units[0].unit_id.value].metadata["semantic_justification"]
    outcome = assess_candidate_outcome(
        candidate, candidate.predicted_evidence, evidence_refs=("evidence:result",)
    )
    assert outcome.measured
    assert outcome.matched_predictions == candidate.predicted_evidence
    assert system.synthesize_semantic_graph(
        SynthesisRequest(state, (_template(CognitiveActionType.REASON),), ("event",), 1)
    ) == ()
    duplicate_commit, duplicate_validation = system.apply_semantic_candidate(
        candidate, available_budget=1,
        granted_permissions=frozenset({"semantic:execute"}),
        available_isolation_grade="I1_GRAPH_ONLY",
    )
    assert not duplicate_commit
    assert duplicate_validation.reason_codes[0].startswith("SEMANTIC_TRANSPOSITION")
    system.restore_execution_snapshot(snapshot)
    assert candidate.units[0].unit_id.value not in system.graph.units


def _causal(*, identifiable=True) -> CausalValidity:
    return CausalValidity(
        "change input", "unchanged control" if identifiable else None,
        (), "I3_RECORDED_EXTERNALS", "recorded metric", randomized=True,
    )


def _experiment(identity, information, decision, cost, *, causal=None):
    return ExperimentProposal(
        identity, "task", "hypothesis-a", ("signal-a",), "signal-not-a",
        information, decision, cost, 0.01, SideEffectClass.REVERSIBLE,
        "I3_RECORDED_EXTERNALS", causal or _causal(),
    )


def test_experiment_selection_uses_information_decision_value_and_causal_validity() -> None:
    weak = _experiment("weak", 0.2, 0.1, 0.2)
    strong = _experiment("strong", 0.9, 0.8, 0.2)
    invalid = _experiment("invalid", 10, 10, 0.1, causal=_causal(identifiable=False))
    selection = select_experiment(
        (weak, strong, invalid), available_budget=1,
        available_isolation_grade="I3_RECORDED_EXTERNALS",
    )
    assert selection.selected == strong
    assert ("invalid", "NON_IDENTIFIABLE") in selection.rejected


@pytest.mark.parametrize(
    ("observation", "status"),
    (
        ("signal-a", ExperimentOutcomeStatus.SUPPORTED),
        ("signal-not-a", ExperimentOutcomeStatus.FALSIFIED),
        ("different", ExperimentOutcomeStatus.INCONCLUSIVE),
    ),
)
def test_predicted_observation_and_falsification_outcomes(observation, status) -> None:
    outcome = assess_observation(_experiment("experiment", 1, 1, 0.1), observation, evidence_ref="evidence")
    assert outcome.status is status
    assert outcome.evidence_ref == "evidence"


def test_non_identifiable_outcome_is_recorded_without_causal_claim() -> None:
    proposal = _experiment("invalid", 1, 1, 0.1, causal=_causal(identifiable=False))
    outcome = assess_observation(proposal, "signal-a", evidence_ref="observed")
    assert outcome.status is ExperimentOutcomeStatus.NON_IDENTIFIABLE
    assert not outcome.causal_validity.identifiable


def test_hidden_shift_fixture_prefers_inquiry_over_structural_heuristic() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "hidden_shift.json").read_text()
    )
    assert fixture["frozen"] is True
    templates = (
        _template(CognitiveActionType.REASON),
        _template(CognitiveActionType.RETRIEVE),
        _template(CognitiveActionType.OBSERVE_OR_TEST),
    )
    semantic_trials = []
    for task in fixture["tasks"]:
        state = _state()
        if task["id"] == "unknown-source":
            state = replace(state, hypotheses=())
        elif task["id"] == "competing-hypotheses":
            state = replace(state, epistemic_items=())
        generated = SemanticSynthesizer(_registry()).synthesize(
            SynthesisRequest(state, templates, ("event:hidden",), 1, max_hypothesis_branches=1)
        )
        actions = {candidate.units[0].metadata["action_type"] for candidate in generated}
        semantic_trials.append(
            SynthesisTrial(
                task["id"], "semantic", task["expected_action"] in actions,
                all(candidate.semantic_justification for candidate in generated),
                all(candidate.predicted_evidence for candidate in generated), True, 0.2,
            )
        )
    semantic = tuple(semantic_trials)
    heuristic = tuple(
        SynthesisTrial(
            task["id"], "structural-heuristic",
            task["expected_action"] == CognitiveActionType.REASON.value,
            False, False, False, 0.2,
        )
        for task in fixture["tasks"]
    )
    comparison = compare_synthesis(semantic, heuristic)
    assert comparison["semantic_improved"]
    assert comparison["inquiry_accuracy_delta"] == 1.0
