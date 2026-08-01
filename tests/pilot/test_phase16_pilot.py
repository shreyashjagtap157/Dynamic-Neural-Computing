from __future__ import annotations

import pytest

from dnc.pilot.governance import (
    ApprovalRole,
    ExerciseKind,
    ExerciseRecord,
    OperationalReadiness,
    OutcomeObservation,
    PilotCriteria,
    PilotProgram,
    RolloutStage,
    WorkflowProfile,
)
from dnc.system import DNCSystem, DNCSystemConfig
from scripts.audits.phase16_pilot_readiness import build_local_readiness


def _program(*, minimum_observations: int = 2, minimum_duration_days: int = 2) -> PilotProgram:
    return PilotProgram(
        WorkflowProfile(
            workflow_id="invoice-review-assist",
            version="1",
            domain="accounts-payable",
            domain_owner="domain-owner",
            reversible=True,
            outcome_measurable=True,
            critical=False,
            system_fingerprint="sha256:dnc-profile",
            data_classification="internal",
            rollback_target="static-review-v3",
        ),
        PilotCriteria(
            baseline_value=0.5,
            minimum_business_value=0.6,
            maximum_failure_rate=0.1,
            maximum_p95_latency_ms=100,
            maximum_cost_per_case=2,
            minimum_observations=minimum_observations,
            minimum_duration_days=minimum_duration_days,
        ),
    )


def _outcome(identifier: str, stage: RolloutStage, day: int, *, external: bool) -> OutcomeObservation:
    return OutcomeObservation(
        observation_id=identifier,
        stage=stage,
        day=day,
        business_value=0.8,
        failed=False,
        latency_ms=80,
        cost=1,
        operator_feedback="useful and correctable",
        delayed_outcome=0.75,
        source="reference" if not external else "production-ledger",
        external=external,
    )


def _advance_to_canary(program: PilotProgram) -> None:
    program.record_outcome(_outcome("offline", RolloutStage.OFFLINE_REPLAY, 0, external=False))
    program.promote(RolloutStage.SHADOW)
    program.record_outcome(_outcome("shadow", RolloutStage.SHADOW, 0, external=False))
    program.promote(RolloutStage.LIMITED_CANARY)


def _complete_local_gates(program: PilotProgram) -> None:
    for kind in ExerciseKind:
        program.record_exercise(ExerciseRecord(kind, f"owner-{kind.value}", "evidence://run", True))
    program.set_operational_readiness(
        OperationalReadiness(
            capacity_plan="capacity-v1",
            cost_plan="cost-v1",
            support_model="support-v1",
            upgrade_policy="upgrade-v1",
            deprecation_policy="deprecation-v1",
            customer_documentation="customer-doc-v1",
        )
    )


def test_first_workflow_must_be_reversible_measurable_and_noncritical() -> None:
    with pytest.raises(ValueError, match="reversible, measurable, and noncritical"):
        WorkflowProfile("w", "1", "d", "o", False, True, False, "f", "internal", "static")


def test_success_threshold_must_exceed_the_frozen_baseline() -> None:
    with pytest.raises(ValueError, match="exceed the frozen baseline"):
        PilotCriteria(0.8, 0.8, 0.1, 100, 1, 1, 1)


def test_rollout_order_and_failed_stage_evidence_are_enforced() -> None:
    program = _program()
    with pytest.raises(ValueError, match="advance offline"):
        program.promote(RolloutStage.LIMITED_CANARY)
    failed = _outcome("failed", RolloutStage.OFFLINE_REPLAY, 0, external=False)
    program.record_outcome(OutcomeObservation(**{**failed.__dict__, "failed": True}))
    with pytest.raises(ValueError, match="successful evidence"):
        program.promote(RolloutStage.SHADOW)


def test_reference_evidence_cannot_be_misrepresented_as_e3() -> None:
    program = _program(minimum_observations=1, minimum_duration_days=1)
    _advance_to_canary(program)
    program.record_outcome(_outcome("local", RolloutStage.LIMITED_CANARY, 1, external=False))
    _complete_local_gates(program)
    review = program.review_general_availability()
    assert not review.approved
    assert "insufficient external canary observations" in review.reasons


def test_complete_e3_evidence_and_independent_approvals_are_required() -> None:
    program = _program()
    _advance_to_canary(program)
    program.record_outcome(_outcome("canary-1", RolloutStage.LIMITED_CANARY, 1, external=True))
    program.record_outcome(_outcome("canary-2", RolloutStage.LIMITED_CANARY, 2, external=True))
    _complete_local_gates(program)

    assert not program.review_general_availability().approved
    for role in ApprovalRole:
        program.approve(role, f"owner-{role.value}")
    review = program.review_general_availability()
    assert review.approved
    assert review.qualified_domain == "accounts-payable"
    assert program.stage is RolloutStage.GENERAL_AVAILABILITY
    assert program.review_general_availability().approved


def test_one_approver_cannot_fill_multiple_independent_roles() -> None:
    program = _program()
    program.approve(ApprovalRole.PRODUCT, "same-person")
    with pytest.raises(ValueError, match="independent approvers"):
        program.approve(ApprovalRole.DOMAIN, "same-person")


def test_new_evidence_invalidates_existing_approvals_and_rollback_is_safe() -> None:
    program = _program()
    _advance_to_canary(program)
    program.approve(ApprovalRole.PRODUCT, "product-owner")
    before = program.evidence_fingerprint
    program.record_outcome(_outcome("new", RolloutStage.LIMITED_CANARY, 1, external=True))
    assert program.evidence_fingerprint != before
    assert "missing product approval" in program.review_general_availability().reasons
    program.rollback()
    assert program.stage is RolloutStage.SHADOW


def test_snapshots_are_defensive_and_content_addressed() -> None:
    program = _program()
    snapshot = program.snapshot()
    fingerprint = program.evidence_fingerprint
    snapshot["workflow"]["domain"] = "tampered"
    assert program.workflow.domain == "accounts-payable"
    assert program.evidence_fingerprint == fingerprint


def test_pilot_can_bind_to_the_integrated_dnc_deployment_profile() -> None:
    reference = DNCSystem().deployment_profile_fingerprint()
    assert reference == DNCSystem().deployment_profile_fingerprint()
    assert reference != DNCSystem(
        config=DNCSystemConfig(enable_learning=False)
    ).deployment_profile_fingerprint()
    assert len(reference) == 64


def test_maintained_local_readiness_artifact_is_explicitly_no_go() -> None:
    _program, artifact = build_local_readiness()
    assert artifact["evidence_grade"] == "E2-local-controlled"
    assert artifact["decision"] == "NO-GO"
    assert "No external canary observations are present." in artifact["limitations"]
