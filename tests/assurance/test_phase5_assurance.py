import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from dnc.assurance import (
    AssuranceCalibrationRegistry,
    CalibrationArtifact,
    CalibrationKey,
    CalibrationStatus,
    CallbackVerifierAdapter,
    CascadePolicy,
    FunctionalVerifier,
    OutcomeLabel,
    OutcomeLabelStatus,
    OutcomeLabelStore,
    RiskThresholdPolicy,
    SemanticAttempt,
    VerificationStatus,
    VerifierClaim,
    VerifierDescriptor,
    VerifierKind,
    VerifierRegistry,
    arithmetic_check,
    bootstrap_interval,
    calibrated_lower_bound,
    cluster_attempts,
    conformal_error_bound,
    detect_contradictions,
    evaluate_calibration,
    fit_isotonic,
    fit_logistic,
    fit_temperature,
    format_check,
    issue_confidence,
    population_shift,
    schema_check,
    subgroup_analysis,
)
from dnc.cognition import EpistemicItem, EpistemicRelation, EpistemicStatus, RelationType, RiskClass
from dnc.capabilities import CapabilityCard, CapabilityRegistry, CapabilityRequirement
from dnc.cognition import CognitiveActionType, CognitiveState, GoalInvariant, PolicyContext, TaskSpec
from dnc.kernel.errors import DNCCalibrationError, DNCPolicyError, DNCVerificationError
from dnc.halting import AdaptiveHaltingPolicy, AttemptRecord, HaltingContext, InferenceAction, InferenceBudget
from dnc.system import DNCSystem, DNCSystemConfig


def _descriptor(
    verifier_id: str,
    *,
    scope: str = "format",
    cost: float = 0.0,
    group: str = "deterministic",
    kind: VerifierKind = VerifierKind.DETERMINISTIC,
    maximum_risk: RiskClass = RiskClass.CRITICAL,
    human: bool = False,
) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        kind=kind,
        scopes=frozenset({scope}),
        domains=frozenset({"*"}),
        maximum_risk=maximum_risk,
        cost=cost,
        independence_group=group,
        fingerprint=f"{verifier_id}-fp",
        requires_human_approval=human,
    )


def _claim(value: object, *, scope: str = "format", risk: RiskClass = RiskClass.HIGH) -> VerifierClaim:
    return VerifierClaim("claim-1", "answer-1", scope, value, risk_class=risk, tenant_id="tenant-a")


def test_deterministic_format_schema_and_arithmetic_verifiers_are_scoped() -> None:
    format_verifier = FunctionalVerifier(_descriptor("format"), format_check(pattern=r"[A-Z]{2}"))
    schema_verifier = FunctionalVerifier(
        _descriptor("schema", scope="schema"),
        schema_check({"type": "object", "required": ["answer"], "properties": {"answer": {"type": "integer"}}}),
    )
    arithmetic_verifier = FunctionalVerifier(
        _descriptor("arithmetic", scope="arithmetic"), arithmetic_check(14)
    )

    assert format_verifier.verify(_claim("OK")).status is VerificationStatus.PASS
    assert format_verifier.verify(_claim("wrong")).status is VerificationStatus.FAIL
    assert schema_verifier.verify(_claim({"answer": 7}, scope="schema")).status is VerificationStatus.PASS
    assert arithmetic_verifier.verify(_claim("2 + 3 * 4", scope="arithmetic")).status is VerificationStatus.PASS
    assert arithmetic_verifier.verify(_claim("__import__('os')", scope="arithmetic")).status is VerificationStatus.ERROR
    assert arithmetic_verifier.verify(_claim("2 ** 1000000", scope="arithmetic")).status is VerificationStatus.ERROR
    assert schema_verifier.verify(_claim({"answer": True}, scope="schema")).status is VerificationStatus.FAIL


def test_callback_adapter_requires_external_model_or_human_kind() -> None:
    adapter = CallbackVerifierAdapter(
        _descriptor("external", kind=VerifierKind.EXTERNAL), format_check()
    )
    assert adapter.verify(_claim("answer")).status is VerificationStatus.PASS
    with pytest.raises(ValueError, match="external"):
        CallbackVerifierAdapter(_descriptor("deterministic"), format_check())


def test_cascade_rejects_cross_tenant_or_forged_adapter_results() -> None:
    legitimate = FunctionalVerifier(_descriptor("external", kind=VerifierKind.EXTERNAL), format_check())

    class ForgedAdapter:
        descriptor = legitimate.descriptor

        def verify(self, claim: VerifierClaim):
            return replace(legitimate.verify(claim), tenant_id="different-tenant")

    registry = VerifierRegistry()
    registry.register(ForgedAdapter())
    with pytest.raises(DNCVerificationError, match="identity or claim scope"):
        DNCSystem(verifier_registry=registry).verify_claim(_claim("answer"))


def test_cascade_orders_by_cost_and_requires_independent_evidence() -> None:
    registry = VerifierRegistry()
    registry.register(FunctionalVerifier(_descriptor("same-a", cost=0.1, group="model-family"), format_check()))
    registry.register(FunctionalVerifier(_descriptor("same-b", cost=0.2, group="model-family"), format_check()))
    registry.register(FunctionalVerifier(_descriptor("independent", cost=0.3, group="exact-tool"), format_check()))

    result = DNCSystem(verifier_registry=registry).verify_claim(
        _claim("answer"),
        CascadePolicy(required_passes=2, required_independence_groups=2),
    )

    assert result.satisfied
    assert tuple(item.verifier_id for item in result.results) == ("same-a", "same-b", "independent")
    assert result.total_cost == pytest.approx(0.6)


def test_cascade_enforces_scope_risk_budget_human_and_kill_switch() -> None:
    registry = VerifierRegistry()
    registry.register(FunctionalVerifier(_descriptor("low-risk", maximum_risk=RiskClass.LOW), format_check()))
    registry.register(FunctionalVerifier(_descriptor("human", cost=2, group="human", kind=VerifierKind.HUMAN, human=True), format_check()))
    budget_limited = DNCSystem(verifier_registry=registry).verify_claim(
        _claim("x"), CascadePolicy(maximum_cost=1)
    )
    assert not budget_limited.satisfied
    assert budget_limited.reason == "assurance requirements unmet"
    result = DNCSystem(verifier_registry=registry).verify_claim(
        _claim("x"), CascadePolicy(require_human_approval=True, maximum_cost=2)
    )
    assert result.satisfied
    registry.disable("human")
    with pytest.raises(DNCVerificationError):
        DNCSystem(verifier_registry=registry).verify_claim(_claim("x"))


def test_delayed_outcomes_are_append_only_idempotent_and_tenant_scoped() -> None:
    store = OutcomeLabelStore()
    first = OutcomeLabel("l1", "answer", False, 1, "test", tenant_id="a")
    corrected = OutcomeLabel(
        "l2", "answer", True, 2, "delayed-observation", tenant_id="a",
        status=OutcomeLabelStatus.CORRECTED, supersedes="l1",
    )
    store.ingest(first)
    store.ingest(first)
    store.ingest(corrected)
    assert store.history("answer", tenant_id="a") == (first, corrected)
    assert store.current("answer", tenant_id="a") == corrected
    assert store.current("answer", tenant_id="b") is None
    with pytest.raises(ValueError, match="same tenant"):
        store.ingest(OutcomeLabel("l3", "answer", True, 3, "bad", tenant_id="b", supersedes="l1"))
    with pytest.raises(ValueError, match="MUST NOT precede"):
        store.ingest(
            OutcomeLabel(
                "l4", "answer", True, 0, "bad", tenant_id="a",
                status=OutcomeLabelStatus.CORRECTED, supersedes="l1",
            )
        )


def _artifact(status: CalibrationStatus = CalibrationStatus.CALIBRATED) -> CalibrationArtifact:
    metrics = evaluate_calibration([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], bins=2)
    return CalibrationArtifact(
        "artifact-1", "1", CalibrationKey("general", RiskClass.HIGH, "model-1", "prompt-1", "decode-1", ("verifier-1-fp",), "tasks-v1"),
        "logistic", (1.0, 0.0), "labels-v1", "held-out", metrics, status=status,
        assumptions=("held-out labels representative",),
    )


def test_calibration_metrics_registry_lifecycle_and_applicability() -> None:
    artifact = _artifact()
    registry = AssuranceCalibrationRegistry()
    registered = registry.register(artifact)
    assert registered.content_hash
    assert registry.require_applicable(artifact.key).artifact_id == "artifact-1"
    assert calibrated_lower_bound(registered, 0.9) < 0.9
    assert registry.invalidate_fingerprint("model-1", "model changed") == ("artifact-1",)
    with pytest.raises(DNCCalibrationError, match="no applicable"):
        registry.require_applicable(artifact.key)


def test_shifted_or_unheld_calibration_cannot_issue_confidence() -> None:
    shifted = _artifact(CalibrationStatus.SHIFTED)
    with pytest.raises(DNCCalibrationError, match="inapplicable"):
        calibrated_lower_bound(shifted, 0.8)
    with pytest.raises(DNCCalibrationError, match="held-out"):
        AssuranceCalibrationRegistry().register(
            CalibrationArtifact(
                "bad", "1", shifted.key, "logistic", (), "data", "training", shifted.metrics,
                status=CalibrationStatus.CALIBRATED,
            )
        )


def test_calibration_artifacts_are_immutable_and_shift_downgrades_applicability() -> None:
    registry = AssuranceCalibrationRegistry()
    artifact = registry.register(_artifact())
    with pytest.raises(DNCCalibrationError, match="cannot be replaced"):
        registry.register(
            CalibrationArtifact(
                artifact.artifact_id, "2", artifact.key, artifact.method, artifact.parameters,
                artifact.dataset_id, artifact.split, artifact.metrics,
                status=CalibrationStatus.CALIBRATED,
            )
        )
    shifted = registry.assess_shift(
        artifact.artifact_id, [0.1, 0.2, 0.3], [0.8, 0.9, 1.0], threshold=0.1
    )
    assert shifted.status is CalibrationStatus.SHIFTED
    assert registry.applicable(artifact.key) is None


def test_phase4_model_change_automatically_invalidates_phase5_calibration() -> None:
    capabilities = CapabilityRegistry()
    calibrations = AssuranceCalibrationRegistry()
    artifact = calibrations.register(_artifact())
    system = DNCSystem(
        capability_registry=capabilities,
        assurance_calibrations=calibrations,
    )
    card = CapabilityCard(
        "model", "Model", "provider", "1", "model-v1",
        frozenset({CognitiveActionType.REASON}), RiskClass.HIGH,
        fingerprint="model-1",
    )
    capabilities.register(card)
    capabilities.register(
        CapabilityCard(
            "model", "Model", "provider", "2", "model-v2",
            frozenset({CognitiveActionType.REASON}), RiskClass.HIGH,
            fingerprint="model-2",
        )
    )
    assert system.assurance_calibrations.applicable(artifact.key) is None


def test_confidence_is_issued_only_from_applicable_artifact() -> None:
    estimate = issue_confidence("estimate-1", "answer-1", "answer", 0.9, _artifact())
    assert estimate.applicability_status == "calibrated"
    assert estimate.lower_bound < estimate.p_correct
    assert estimate.calibration_split == "held-out"
    with pytest.raises(DNCCalibrationError):
        issue_confidence("bad", "answer", "answer", 0.9, _artifact(CalibrationStatus.SHIFTED))


def test_metrics_bootstrap_subgroups_and_shift_are_deterministic() -> None:
    metrics = evaluate_calibration([0.1, 0.4, 0.6, 0.9], [0, 0, 1, 1], bins=2)
    assert 0 <= metrics.brier_score <= 1
    assert math.isfinite(metrics.log_loss)
    assert len(metrics.selective_risk) == 4
    assert bootstrap_interval([1, 2, 3], samples=100, seed=7) == bootstrap_interval([1, 2, 3], samples=100, seed=7)
    groups = subgroup_analysis([0.1, 0.9], [0, 1], ["a", "b"])
    assert set(groups) == {"a", "b"}
    assert population_shift([0.1, 0.2], [0.8, 0.9]) > population_shift([0.1, 0.2], [0.1, 0.2])


def test_calibration_fitters_and_conformal_bound() -> None:
    weight, bias = fit_logistic([-2, -1, 1, 2], [0, 0, 1, 1], steps=200)
    assert weight > 0 and abs(bias) < 0.1
    assert fit_temperature([-2, -1, 1, 2], [0, 0, 1, 1]) > 0
    isotonic = fit_isotonic([0.1, 0.2, 0.8, 0.9], [0, 1, 0, 1])
    assert all(left[1] <= right[1] for left, right in zip(isotonic, isotonic[1:]))
    assert conformal_error_bound([0.1, 0.2, 0.3], alpha=0.2) == 0.3


def test_semantic_clusters_discount_correlated_attempts() -> None:
    clusters = cluster_attempts(
        (
            SemanticAttempt("a", "Paris is the capital", ("Paris is capital",), "same-model", 1),
            SemanticAttempt("b", "Paris is the capital", ("Paris is capital",), "same-model", 1),
            SemanticAttempt("c", "Paris is the capital", ("Paris is capital",), "independent", 1),
            SemanticAttempt("d", "Lyon is the capital", ("Lyon is capital",), "other", 0),
        )
    )
    assert len(clusters) == 2
    assert clusters[0].independent_weight == 2
    assert clusters[0].attempt_ids == ("a", "b", "c")


def test_structured_and_explicit_contradictions_are_detected() -> None:
    left = EpistemicItem("a", EpistemicStatus.FACT, "sky blue", subject="sky", predicate="color", object="blue")
    right = EpistemicItem("b", EpistemicStatus.FACT, "sky green", subject="sky", predicate="color", object="green")
    relation = EpistemicRelation("r", RelationType.CONTRADICTS, "a", "b")
    contradictions = detect_contradictions((left, right), (relation,))
    assert len(contradictions) == 1
    assert contradictions[0].critical


def test_risk_thresholds_require_approval_and_are_domain_specific() -> None:
    thresholds = {risk: 0.5 for risk in RiskClass}
    with pytest.raises(DNCPolicyError, match="approval"):
        RiskThresholdPolicy("p", "1", "medical", thresholds, "", "")
    policy = RiskThresholdPolicy("p", "1", "medical", thresholds, "reviewer", "approval-1")
    assert policy.threshold_for(RiskClass.HIGH, "medical") == 0.5
    with pytest.raises(DNCPolicyError, match="inapplicable"):
        policy.threshold_for(RiskClass.HIGH, "finance")


def test_frozen_held_out_fixture_meets_declared_reference_risk_coverage_targets() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "held_out_calibration.json").read_text()
    )
    assert fixture["frozen"] is True
    metrics = evaluate_calibration(fixture["probabilities"], fixture["labels"], bins=4)
    acceptance = fixture["acceptance"]
    assert metrics.brier_score <= acceptance["maximum_brier"]
    assert metrics.expected_calibration_error <= acceptance["maximum_ece"]
    half_coverage_risk = metrics.selective_risk[len(metrics.selective_risk) // 2 - 1][1]
    assert half_coverage_risk <= acceptance["maximum_risk_at_half_coverage"]


def test_phases1_to6_operate_as_one_governed_system() -> None:
    capabilities = CapabilityRegistry()
    card = CapabilityCard(
        "model", "Model", "provider", "1", "model-v1",
        frozenset({CognitiveActionType.REASON}), RiskClass.HIGH,
        fingerprint="model-1",
    )
    capabilities.register(card)
    verifiers = VerifierRegistry()
    verifiers.register(FunctionalVerifier(_descriptor("verifier-1"), format_check()))
    calibrations = AssuranceCalibrationRegistry()
    artifact = calibrations.register(_artifact())
    cognitive_state = CognitiveState(
        TaskSpec(
            task_id="task",
            tenant_id="tenant-a",
            actor_id="actor",
            session_id="session",
            description="Produce a verified answer",
            goal=GoalInvariant(
                "Produce a verified answer", mandatory_verification=("verifier-1",)
            ),
            policy=PolicyContext(risk_class=RiskClass.HIGH),
        )
    )
    system = DNCSystem(
        execution_id="phase1-5-manual",
        config=DNCSystemConfig(enable_adaptive_halting=True),
        cognitive_state=cognitive_state,
        capability_registry=capabilities,
        verifier_registry=verifiers,
        assurance_calibrations=calibrations,
        inference_policy=AdaptiveHaltingPolicy(
            RiskThresholdPolicy(
                "phase6", "1", "general", {risk: 0.5 for risk in RiskClass},
                "reviewer", "approval-phase6",
            ),
            enabled=True,
        ),
    )
    graph_identity = system.graph.graph_id
    snapshot = system.capture_execution_snapshot("phase1-5-snapshot")

    selection = system.select_capability(
        CapabilityRequirement(CognitiveActionType.REASON, RiskClass.HIGH)
    )
    assert selection.satisfied and selection.selected == card
    verification = system.verify_claim(_claim("verified answer"))
    assert verification.satisfied
    system.record_outcome_label(
        OutcomeLabel("immediate", "answer-1", True, 1, "format", tenant_id="tenant-a")
    )
    confidence = system.issue_calibrated_confidence(
        "confidence", "answer-1", "answer", 0.9, artifact.key,
        semantic_cluster_count=2, correlation_groups=("model", "exact-tool"),
    )
    assert confidence.applicability_status == "calibrated"
    attempts = tuple(
        AttemptRecord(
            attempt_id,
            "task",
            "verified answer",
            ("answer is verified",),
            f"model-{attempt_id}",
            f"prompt-{attempt_id}",
            f"seed-{attempt_id}",
            verifier_result_ids=(verification.results[0].result_id,),
        )
        for attempt_id in ("a", "b")
    )
    halt = system.decide_inference(
        HaltingContext(
            "task", "general", RiskClass.HIGH, attempts,
            InferenceBudget(3, 1000, 1, 1000), True, True,
            confidence=confidence,
            expected_action_values={InferenceAction.SAMPLE: 0.01},
            action_costs={InferenceAction.SAMPLE: 0.02},
        )
    )
    assert halt.action is InferenceAction.STOP

    verifiers.disable("verifier-1")
    with pytest.raises(DNCCalibrationError, match="verifier fingerprints"):
        system.issue_calibrated_confidence(
            "disabled-verifier", "answer-1", "answer", 0.9, artifact.key
        )
    verifiers.enable("verifier-1")

    system.update_cognitive_state(cognitive_state.with_materialized_view("answer", ()))
    capabilities.disable("model")
    system.restore_execution_snapshot(snapshot)
    assert system.graph.graph_id == graph_identity
    assert system.cognitive_state == cognitive_state
    assert not capabilities.is_disabled("model")
    assert system.outcome_labels.current("answer-1", tenant_id="tenant-a") is not None

    capabilities.register(
        CapabilityCard(
            "model", "Model", "provider", "2", "model-v2",
            frozenset({CognitiveActionType.REASON}), RiskClass.HIGH,
            fingerprint="model-2",
        )
    )
    with pytest.raises(DNCCalibrationError, match="capability fingerprint"):
        system.issue_calibrated_confidence("stale", "answer-1", "answer", 0.9, artifact.key)
    assert system.assurance_calibrations.applicable(artifact.key) is None
