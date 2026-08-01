import pytest

from dnc.cognition import (
    CalibrationProfile,
    CognitiveState,
    EvidenceItem,
    GoalInvariant,
    PolicyContext,
    ReferenceCognitiveController,
    RiskClass,
    TaskSpec,
)


def test_calibration_profile_requires_every_risk_class() -> None:
    with pytest.raises(ValueError, match="every RiskClass"):
        CalibrationProfile(
            profile_id="partial",
            domain="unit-test",
            policy_version="1",
            risk_thresholds={RiskClass.LOW: 0.1},
        )


def test_controller_uses_injected_calibration_profile_for_stop() -> None:
    task = TaskSpec(
        task_id="task-1",
        description="answer under custom calibration",
        goal=GoalInvariant(objective="return answer", mandatory_verification=("verifier-1",)),
        policy=PolicyContext(risk_class=RiskClass.HIGH),
    )
    state = CognitiveState(
        task=task,
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
    permissive = CalibrationProfile(
        profile_id="permissive-test",
        domain="unit-test",
        policy_version="1",
        risk_thresholds={
            RiskClass.LOW: 0.10,
            RiskClass.MEDIUM: 0.05,
            RiskClass.HIGH: 0.03,
            RiskClass.CRITICAL: 0.001,
        },
    )

    halt = ReferenceCognitiveController(calibration=permissive).halt(state)

    assert halt.decision.value == "STOP"
