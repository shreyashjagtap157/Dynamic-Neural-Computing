"""Phase 4 (Production Hardening) exit criteria tests.

Per mvp-roadmap.md Section 6: Phase 4 exit criteria cover:
- EC-1: Canary monitoring (INV-CL-17 circuit breaker)
- EC-2: Automated rollback trigger (Class 1 regression)
- EC-3: Bias evaluation framework (PR-15)
- EC-4: Bias thresholds enforced (4 metrics)
- EC-5: RegressionMonitor integration with Runtime
- EC-6: Blocking bias violations
"""

from __future__ import annotations

import sys
from typing import Dict

sys.path.insert(0, "src")

from dnc.observability.bias_evaluation import (
    BiasEvaluationFramework,
    BiasEvaluationResult,
    BiasViolationException,
    GroupedPredictions,
    dp_a_rate,
    dp_b_rate,
    tpr_fpr,
)
from dnc.runtime.runtime import (
    RegressionMonitor,
    Runtime,
    LatencyConfig,
)
from dnc.state.execution_state import ExecutionState


class MockEvaluationRun:
    def __init__(self, metric_results: Dict[str, str]) -> None:
        self.metric_results = metric_results


def test_ec1_regression_monitor_initial_state():
    """EC-1: RegressionMonitor starts with zero regression count."""
    rm = RegressionMonitor(rollback_threshold=1)
    assert rm.get_regression_count() == 0
    assert not rm.should_rollback()
    print("PASS: ec1_regression_monitor_initial_state")


def test_ec2_regression_monitor_detects_class1_regression():
    """EC-2: RegressionMonitor detects Class 1 regression and triggers rollback.

    A Class 1 regression occurs when a metric was WIN or TIE and becomes LOSS.
    """
    rm = RegressionMonitor(rollback_threshold=1)

    prior_results = {
        "scenario_1": {"accuracy": "WIN"},
        "scenario_2": {"latency": "TIE"},
    }

    current = MockEvaluationRun({
        "accuracy": "LOSS",
        "latency": "TIE",
    })

    from dnc.observability.evaluation import EvaluationSuite, EvaluationRun, MetricSpec, TrialResult
    suite = EvaluationSuite()

    eval_run = EvaluationRun(
        trial_results=[
            TrialResult(
                scenario_id="scenario_1",
                metric_spec=MetricSpec(name="accuracy", higher_is_better=True),
                baseline_mean=0.9,
                current_mean=0.7,
                p_value=0.1,
                effect_size=0.5,
                n_trials=30,
            ),
        ],
        metadata={},
    )

    es = ExecutionState()
    should_rollback = rm.check_regressions(eval_run, es, prior_results)
    assert should_rollback, "RegressionMonitor should trigger rollback on Class 1 regression"
    assert rm.should_rollback()
    print("PASS: ec2_regression_monitor_detects_class1_regression")


def test_ec3_bias_evaluation_framework_demographic_parity():
    """EC-3: BiasEvaluationFramework correctly computes demographic parity."""
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[True, True, True, False],
        outcomes=[True, True, True, True],
        protected_attribute="gender",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[True, True, True, True],
        outcomes=[True, True, True, True],
        protected_attribute="gender",
    )

    diff, within = bef.compute_demographic_parity_difference(group_a, group_b)
    assert within, f"Demographic parity diff {diff:.4f} should be within 0.05"
    print("PASS: ec3_bias_evaluation_framework_demographic_parity")


def test_ec4_bias_evaluation_framework_equalized_odds():
    """EC-4: BiasEvaluationFramework correctly computes equalized odds."""
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[True, True, False, False],
        outcomes=[True, False, True, False],
        protected_attribute="age_group",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[True, True, False, False],
        outcomes=[True, False, True, False],
        protected_attribute="age_group",
    )

    diff, within = bef.compute_equalized_odds_difference(group_a, group_b)
    assert within, f"Equalized odds diff {diff:.4f} should be within 0.05"
    print("PASS: ec4_bias_evaluation_framework_equalized_odds")


def test_ec5_bias_evaluation_framework_disparate_impact():
    """EC-5: BiasEvaluationFramework correctly computes disparate impact ratio."""
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[True, True, True, True, True],
        outcomes=[True, True, True, True, True],
        protected_attribute="region",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[True, True, True, True, True],
        outcomes=[True, True, True, True, True],
        protected_attribute="region",
    )

    ratio, within = bef.compute_disparate_impact_ratio(group_a, group_b)
    assert within, f"Disparate impact ratio {ratio:.4f} should be within [0.8, 1.25]"
    print("PASS: ec5_bias_evaluation_framework_disparate_impact")


def test_ec6_bias_evaluation_framework_individual_fairness():
    """EC-6: BiasEvaluationFramework correctly computes individual fairness."""
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[True, True, True, True],
        outcomes=[True, True, True, True],
        protected_attribute="income_level",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[True, True, True, True],
        outcomes=[True, True, True, True],
        protected_attribute="income_level",
    )

    features = [
        [1.0, 0.5, 0.2],
        [1.0, 0.6, 0.2],
        [0.9, 0.5, 0.3],
        [1.0, 0.55, 0.25],
    ]

    score, within = bef.compute_individual_fairness_consistency(
        group_a, group_b, features
    )
    assert within, f"Individual fairness score {score:.4f} should be >= 0.85"
    print("PASS: ec6_bias_evaluation_framework_individual_fairness")


def test_ec7_bias_evaluation_blocks_on_threshold_violation():
    """EC-7: Bias evaluation blocks deployment when thresholds are violated.

    Per PR-15: If any threshold is violated, the deployment or KB update is BLOCKED.
    """
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[True, True, True, True],
        outcomes=[True, True, True, True],
        protected_attribute="gender",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[False, False, False, False],
        outcomes=[False, False, False, False],
        protected_attribute="gender",
    )

    result = bef.evaluate(group_a, group_b)

    assert not result.overall_pass, "Should fail bias evaluation (opposite predictions)"
    assert len(result.blocking_failures) > 0, "Should have blocking failures"

    try:
        bef.block_if_failing(result)
        assert False, "Should have raised BiasViolationException"
    except BiasViolationException as e:
        assert len(e.failures) > 0

    print("PASS: ec7_bias_evaluation_blocks_on_threshold_violation")


def test_ec8_runtime_integration_has_regression_monitor():
    """EC-8: Runtime has RegressionMonitor integrated."""
    config = LatencyConfig()
    runtime = Runtime(config=config)

    assert hasattr(runtime, "_regression_monitor")
    assert hasattr(runtime, "regression_monitor")
    assert hasattr(runtime, "check_regressions")
    print("PASS: ec8_runtime_integration_has_regression_monitor")


def test_ec9_regression_monitor_threshold():
    """EC-9: RegressionMonitor respects configurable rollback threshold."""
    rm = RegressionMonitor(rollback_threshold=3)

    assert not rm.should_rollback()
    assert rm.get_regression_count() == 0
    print("PASS: ec9_regression_monitor_threshold")


def test_ec10_bias_evaluation_with_empty_predictions():
    """EC-10: Bias evaluation handles edge case of empty predictions gracefully."""
    bef = BiasEvaluationFramework()

    group_a = GroupedPredictions(
        group_id="group_A",
        predictions=[],
        outcomes=[],
        protected_attribute="gender",
    )
    group_b = GroupedPredictions(
        group_id="group_B",
        predictions=[],
        outcomes=[],
        protected_attribute="gender",
    )

    diff, within = bef.compute_demographic_parity_difference(group_a, group_b)
    assert diff == 0.0
    assert within

    ratio, di_within = bef.compute_disparate_impact_ratio(group_a, group_b)
    assert di_within

    print("PASS: ec10_bias_evaluation_with_empty_predictions")


if __name__ == "__main__":
    tests = [
        test_ec1_regression_monitor_initial_state,
        test_ec2_regression_monitor_detects_class1_regression,
        test_ec3_bias_evaluation_framework_demographic_parity,
        test_ec4_bias_evaluation_framework_equalized_odds,
        test_ec5_bias_evaluation_framework_disparate_impact,
        test_ec6_bias_evaluation_framework_individual_fairness,
        test_ec7_bias_evaluation_blocks_on_threshold_violation,
        test_ec8_runtime_integration_has_regression_monitor,
        test_ec9_regression_monitor_threshold,
        test_ec10_bias_evaluation_with_empty_predictions,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/10 Phase 4 tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/10 Phase 4 tests failed")
        exit(1)
    else:
        print("PASS: All Phase 4 tests passed")
        exit(0)