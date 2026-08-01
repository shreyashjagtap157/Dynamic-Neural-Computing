import pytest

from dnc.assurance import RiskThresholdPolicy
from dnc.cognition import ConfidenceEstimate, RiskClass
from dnc.halting import (
    AdaptiveHaltingPolicy,
    AttemptRecord,
    FixedAttemptPolicy,
    FixedRefinementPolicy,
    HaltingContext,
    HaltingPolicyMode,
    HaltingTrial,
    InferenceAction,
    InferenceBudget,
    SelfConsistencyPolicy,
    budget_status,
    compare_matched_quality,
    evaluate_trials,
)
from dnc.kernel.errors import DNCCapabilityError
from dnc.system import DNCSystem, DNCSystemConfig


def _thresholds() -> RiskThresholdPolicy:
    return RiskThresholdPolicy(
        "phase6", "1", "general",
        {
            RiskClass.LOW: 0.60,
            RiskClass.MEDIUM: 0.70,
            RiskClass.HIGH: 0.80,
            RiskClass.CRITICAL: 0.90,
        },
        "reviewer", "approval-phase6",
    )


def _attempt(identity: str, *, conclusion: str = "Paris", group: str | None = None, **usage: object) -> AttemptRecord:
    group = group or identity
    return AttemptRecord(
        identity, "task", conclusion, (f"capital={conclusion}",),
        f"model-{group}", f"prompt-{group}", f"seed-{group}",
        verifier_result_ids=(f"verify-{identity}",), **usage,
    )


def _confidence(lower: float = 0.85, status: str = "calibrated") -> ConfidenceEstimate:
    return ConfidenceEstimate(
        "confidence", "answer", "answer", p_correct=0.9, lower_bound=lower,
        method="held-out-logistic", calibration_model="artifact", calibration_dataset="held-out",
        domain="general", risk_class=RiskClass.HIGH, applicability_status=status,
    )


def _context(**changes: object) -> HaltingContext:
    values = {
        "task_id": "task",
        "domain": "general",
        "risk_class": RiskClass.HIGH,
        "attempts": (_attempt("a"), _attempt("b")),
        "budget": InferenceBudget(5, 5000, 5.0, 5000, 2000, 2.0, 2000),
        "mandatory_checks_passed": True,
        "output_contract_satisfied": True,
        "confidence": _confidence(),
        "expected_action_values": {InferenceAction.SAMPLE: 0.01},
        "action_costs": {InferenceAction.SAMPLE: 0.02},
    }
    values.update(changes)
    return HaltingContext(**values)


def _adaptive() -> AdaptiveHaltingPolicy:
    return AdaptiveHaltingPolicy(_thresholds(), enabled=True)


def test_easy_task_stops_only_when_all_preconditions_hold() -> None:
    decision = _adaptive().decide(_context())
    assert decision.action is InferenceAction.STOP
    assert decision.calibrated_lower_bound == 0.85
    assert decision.threshold == 0.80
    assert decision.leading_cluster_weight == 1.0


def test_hard_task_continues_when_marginal_value_exceeds_cost() -> None:
    decision = _adaptive().decide(
        _context(
            expected_action_values={InferenceAction.SAMPLE: 0.2},
            action_costs={InferenceAction.SAMPLE: 0.01},
        )
    )
    assert decision.action is InferenceAction.SAMPLE


@pytest.mark.parametrize(
    ("changes", "expected"),
    (
        ({"ambiguous_fields": ("output_format",)}, InferenceAction.ASK),
        ({"missing_information": ("source",)}, InferenceAction.RETRIEVE),
        ({"critical_contradictions": ("conflict",)}, InferenceAction.VERIFY),
        ({"calibration_shifted": True}, InferenceAction.DIVERSIFY),
        ({"confidence": None}, InferenceAction.VERIFY),
    ),
)
def test_adaptive_policy_selects_non_sampling_actions(changes, expected) -> None:
    assert _adaptive().decide(_context(**changes)).action is expected


def test_budget_and_tail_exhaustion_abstain_without_claiming_correctness() -> None:
    context = _context(
        attempts=(_attempt("a", tokens=3000),),
        budget=InferenceBudget(5, 5000, 5, 5000, max_single_attempt_tokens=2000),
    )
    status = budget_status(context)
    decision = _adaptive().decide(context)
    assert status.exhausted and status.tail_violations == ("TOKENS:a",)
    assert decision.action is InferenceAction.ABSTAIN


def test_correlated_agreement_does_not_satisfy_independence_gate() -> None:
    context = _context(attempts=(_attempt("a", group="same"), _attempt("b", group="same")))
    assert _adaptive().decide(context).action is InferenceAction.SAMPLE


def test_fixed_baselines_and_opt_in_system_gate_remain_available() -> None:
    context = _context(attempts=(_attempt("a"),))
    assert FixedAttemptPolicy(2).decide(context).action is InferenceAction.SAMPLE
    assert FixedRefinementPolicy(0).decide(context).action is InferenceAction.STOP
    self_consistency = SelfConsistencyPolicy(1).decide(context)
    assert self_consistency.policy_mode is HaltingPolicyMode.SELF_CONSISTENCY

    policy = _adaptive()
    default_system = DNCSystem(inference_policy=policy)
    assert default_system.decide_inference(context).policy_mode is HaltingPolicyMode.FIXED_ATTEMPT
    adaptive_system = DNCSystem(
        config=DNCSystemConfig(enable_adaptive_halting=True), inference_policy=policy
    )
    assert adaptive_system.decide_inference(_context()).action is InferenceAction.STOP
    with pytest.raises(DNCCapabilityError):
        DNCSystem().decide_inference(context)


def test_matched_quality_evaluation_reports_savings_and_false_stops() -> None:
    baseline = tuple(
        HaltingTrial(f"task-{index}", "fixed", True, True, index == 3, 3, 300, 0.3, 300)
        for index in range(4)
    )
    adaptive = tuple(
        HaltingTrial(f"task-{index}", "adaptive", True, True, index == 3, 2, 200, 0.2, 200)
        for index in range(4)
    )
    comparison = compare_matched_quality(adaptive, baseline)
    evaluation = evaluate_trials(adaptive, seed=9)
    assert comparison["quality_matched"]
    assert comparison["attempt_reduction"] == 1
    assert comparison["critical_false_stop_delta"] == 0
    assert evaluation.attempt_savings_interval == (2.0, 2.0)
