"""Generate the local Phase 16 pilot-readiness decision artifact."""

from __future__ import annotations

import json
from pathlib import Path

from dnc.pilot import (
    ExerciseKind,
    OperationalReadiness,
    OutcomeObservation,
    PilotCriteria,
    PilotProgram,
    RolloutStage,
    WorkflowProfile,
)
from dnc.pilot.governance import ExerciseRecord
from dnc.system import DNCSystem


ARTIFACT = Path("docs/pilot/artifacts/phase16-local-readiness.json")


def build_local_readiness() -> tuple[PilotProgram, dict[str, object]]:
    system = DNCSystem()
    program = PilotProgram(
        WorkflowProfile(
            workflow_id="reference-document-review",
            version="1",
            domain="controlled-reference",
            domain_owner="unassigned-external-owner",
            reversible=True,
            outcome_measurable=True,
            critical=False,
            system_fingerprint=system.deployment_profile_fingerprint(),
            data_classification="synthetic",
            rollback_target="static-reference-review-v1",
        ),
        PilotCriteria(
            baseline_value=0.5,
            minimum_business_value=0.6,
            maximum_failure_rate=0.05,
            maximum_p95_latency_ms=1000,
            maximum_cost_per_case=5,
            minimum_observations=30,
            minimum_duration_days=14,
        ),
    )
    for identifier, stage in (
        ("offline-reference", RolloutStage.OFFLINE_REPLAY),
        ("shadow-reference", RolloutStage.SHADOW),
    ):
        program.record_outcome(
            OutcomeObservation(
                observation_id=identifier,
                stage=stage,
                day=0,
                business_value=0.8,
                failed=False,
                latency_ms=10,
                cost=0.1,
                operator_feedback="local test operator",
                delayed_outcome=0.8,
                source="deterministic-local-reference",
                external=False,
            )
        )
        program.promote(
            RolloutStage.SHADOW
            if stage is RolloutStage.OFFLINE_REPLAY
            else RolloutStage.LIMITED_CANARY
        )
    for kind in ExerciseKind:
        program.record_exercise(
            ExerciseRecord(
                kind=kind,
                exercised_by="local-test-harness",
                evidence_uri=f"local://phase16/{kind.value}",
                passed=True,
            )
        )
    program.set_operational_readiness(
        OperationalReadiness(
            capacity_plan="docs/pilot/PHASE16-PILOT-PLAN.md#capacity-and-cost",
            cost_plan="docs/pilot/PHASE16-PILOT-PLAN.md#capacity-and-cost",
            support_model="docs/pilot/PHASE16-PILOT-PLAN.md#support",
            upgrade_policy="docs/pilot/PHASE16-PILOT-PLAN.md#lifecycle",
            deprecation_policy="docs/pilot/PHASE16-PILOT-PLAN.md#lifecycle",
            customer_documentation="docs/pilot/PHASE16-PILOT-PLAN.md#operator-boundary",
        )
    )
    review = program.review_general_availability()
    artifact = {
        "evidence_grade": "E2-local-controlled",
        "decision": "GO" if review.approved else "NO-GO",
        "review": {
            "approved": review.approved,
            "reasons": list(review.reasons),
            "qualified_domain": review.qualified_domain,
            "workflow_fingerprint": review.workflow_fingerprint,
            "evidence_fingerprint": review.evidence_fingerprint,
        },
        "program": program.snapshot(),
        "limitations": [
            "No external canary observations are present.",
            "No human owner approvals are present.",
            "Local exercises validate control mechanics, not production operations.",
        ],
    }
    return program, artifact


def main() -> int:
    _program, artifact = build_local_readiness()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{artifact['decision']}: wrote {ARTIFACT}")
    return 0 if artifact["decision"] == "NO-GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
