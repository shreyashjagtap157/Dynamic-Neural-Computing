from dataclasses import replace

import pytest

from dnc.cognition import RiskClass
from dnc.policy_learning import (
    DecisionExample,
    LearnedPolicyRegistry,
    LearnedPolicyVersion,
    LoggedCandidate,
    OPEEstimate,
    PolicyLifecycle,
    PolicyMonitor,
    PromotionEvidence,
    TabularShadowPredictor,
    calculate_policy_monitor,
    compare_shadow,
    evaluate_off_policy,
    evaluate_predictions,
    select_action,
    validate_decision_dataset,
)
from dnc.system import DNCSystem


def _example(index, action, outcome, *, split="train", task=None, censored=False):
    return DecisionExample(
        decision_id=f"d{index}", task_fingerprint=task or f"task-{index}",
        context_key="context", candidates=(LoggedCandidate("safe", 0.5), LoggedCandidate("fast", 0.5)),
        selected_action_id=action, policy_version="deterministic-v1", outcome=outcome,
        realized_cost=0.1 if action == "safe" else 0.2, censored=censored, split=split,
    )


def _training():
    return tuple(
        _example(index, "safe" if index % 2 == 0 else "fast", 0.6 if index % 2 == 0 else 0.9)
        for index in range(20)
    )


def _policy(predictor, epsilon=0.0):
    return LearnedPolicyVersion(
        "controller", "1.0.0", predictor.training_hash, predictor.model_hash,
        maximum_risk=0.2, maximum_cost=0.5, exploration_epsilon=epsilon,
    )


def _evidence(policy, *, estimate=None):
    return PromotionEvidence(
        "e1", policy.fingerprint,
        estimate or OPEEstimate(0.8, 0.79, 0.81, 20, 1, (0.7, 0.9)),
        baseline_value=0.6, calibration_error=0.02,
        shadow_guardrail_regressions=0, lower_confidence_bound=0.7,
    )


def test_dataset_schema_validates_candidate_sets_propensities_outcomes_and_hash() -> None:
    result = validate_decision_dataset(_training())
    assert result.valid and result.minimum_propensity == 0.5 and result.supported_fraction == 1
    bad = replace(_training()[0], candidates=(LoggedCandidate("safe", 0.4), LoggedCandidate("fast", 0.4)))
    result = validate_decision_dataset((bad,))
    assert not result.valid and any("PROPENSITY_SUM" in item for item in result.errors)


def test_dataset_rejects_task_split_leakage_missing_outcome_and_duplicates() -> None:
    train = _example(1, "safe", 1, task="same")
    evaluation = _example(2, "safe", None, split="evaluation", task="same")
    result = validate_decision_dataset((train, evaluation, train))
    assert not result.valid
    assert any("TASK_SPLIT_LEAKAGE" in item for item in result.errors)
    assert any("MISSING_OUTCOME" in item for item in result.errors)
    assert any("DUPLICATE_DECISION" in item for item in result.errors)


def test_shadow_predictor_uses_delayed_corrections_and_reports_lineage() -> None:
    corrected = replace(_example(1, "safe", 0.1), delayed_correction=0.8)
    predictor = TabularShadowPredictor()
    predictor.fit((corrected, _example(2, "fast", 0.9)))
    assert predictor.predict("context", "safe").outcome == 0.8
    assert predictor.training_hash and predictor.model_hash


def test_constrained_policy_selects_value_only_inside_safety_envelope() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    policy = _policy(predictor)
    decision = select_action(
        policy=policy, predictor=predictor, context_key="context",
        candidate_ids=("safe", "fast"), deterministic_action_id="safe",
        safe_action_ids=frozenset({"safe", "fast"}), canary_allowed=True,
    )
    assert decision.action_id == "fast" and decision.used_learned_policy
    fallback = select_action(
        policy=policy, predictor=predictor, context_key="context",
        candidate_ids=("fast",), deterministic_action_id="safe",
        safe_action_ids=frozenset({"safe"}), canary_allowed=True,
    )
    assert fallback.action_id == "safe" and not fallback.used_learned_policy


def test_safe_exploration_propensities_are_logged_and_bounded() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    decision = select_action(
        policy=_policy(predictor, 0.1), predictor=predictor, context_key="context",
        candidate_ids=("safe", "fast"), deterministic_action_id="safe",
        safe_action_ids=frozenset({"safe", "fast"}), canary_allowed=True,
    )
    assert sum(decision.propensities.values()) == pytest.approx(1)
    assert all(value > 0 for value in decision.propensities.values())


def test_ope_computes_ips_snips_dr_support_and_sensitivity() -> None:
    examples = _training()
    predictor = TabularShadowPredictor()
    predictor.fit(examples)
    targets = {item.decision_id: {"safe": 0.2, "fast": 0.8} for item in examples}
    estimate = evaluate_off_policy(examples, targets, predictor)
    assert estimate.effective_sample_size > 0
    assert estimate.supported_fraction == 1
    assert estimate.sensitivity_range[0] <= estimate.doubly_robust <= estimate.sensitivity_range[1]


def test_ope_rejects_no_support() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    with pytest.raises(ValueError, match="no supported"):
        evaluate_off_policy(_training(), {}, predictor)


def test_ope_rejects_malformed_or_out_of_support_target_policy() -> None:
    examples = _training()
    predictor = TabularShadowPredictor()
    predictor.fit(examples)
    malformed = {item.decision_id: {"safe": 0.8, "fast": 0.8} for item in examples}
    with pytest.raises(ValueError, match="sum to one"):
        evaluate_off_policy(examples, malformed, predictor)
    unsupported = {item.decision_id: {"unknown": 1.0} for item in examples}
    with pytest.raises(ValueError, match="outside logged"):
        evaluate_off_policy(examples, unsupported, predictor)


def test_promotion_rejects_estimator_disagreement_and_support_failure() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    policy = _policy(predictor)
    registry = LearnedPolicyRegistry()
    registry.register(policy)
    discordant = OPEEstimate(0.9, 0.5, 0.7, 5, 0.5, (0.2, 1.0))
    registry.record_evidence(_evidence(policy, estimate=discordant))
    with pytest.raises(ValueError, match="insufficient or discordant"):
        registry.promote_canary(policy.fingerprint)


def test_shadow_canary_active_low_risk_kill_switch_and_rollback() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    policy = _policy(predictor)
    registry = LearnedPolicyRegistry()
    registry.register(policy)
    registry.record_evidence(_evidence(policy))
    registry.promote_canary(policy.fingerprint)
    assert registry.can_execute(policy.fingerprint, RiskClass.LOW)
    assert not registry.can_execute(policy.fingerprint, RiskClass.HIGH)
    registry.promote_active(policy.fingerprint)
    registry.kill_switch = True
    assert not registry.can_execute(policy.fingerprint, RiskClass.LOW)
    registry.rollback(policy.fingerprint)
    assert registry.lifecycle(policy.fingerprint) is PolicyLifecycle.ROLLED_BACK


def test_monitor_covers_regret_constraints_delays_shift_and_feedback() -> None:
    monitor = calculate_policy_monitor(
        learned_values=(0.9, 0.9), oracle_values=(0.91, 0.91),
        constraint_violations=(False, False), delayed_outcomes=(False, True),
        shifted_contexts=(False, False), action_counts=(1, 1),
    )
    assert monitor.healthy
    assert not PolicyMonitor(0.01, 1, 0.2, 0.05, 0.5).healthy
    assert not PolicyMonitor(0.01, 0, 0.2, 0.2, 0.5).healthy


def test_prediction_calibration_shift_and_shadow_comparison_are_computed() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    evaluation = evaluate_predictions(
        predictor, (_example(30, "fast", 0.9, split="evaluation"),),
        training_contexts=frozenset({"context"}),
    )
    assert evaluation.outcome_calibration_error == pytest.approx(0)
    assert evaluation.unseen_context_fraction == 0
    shadow = compare_shadow(
        ("fast", "safe"), ("safe", "safe"), (0.9, 0.6), (0.6, 0.6), (False, False)
    )
    assert shadow.agreement == 0.5
    assert shadow.learned_value > shadow.deterministic_value


def test_system_snapshot_restores_learned_policy_independently() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    policy = _policy(predictor)
    system = DNCSystem()
    system.learned_policy_registry.register(policy)
    snapshot = system.capture_execution_snapshot("phase11")
    system.learned_policy_registry.kill_switch = True
    system.learned_policy_registry.rollback(policy.fingerprint)
    system.restore_execution_snapshot(snapshot)
    assert system.learned_policy_registry.lifecycle(policy.fingerprint) is PolicyLifecycle.SHADOW
    assert not system.learned_policy_registry.kill_switch


def test_system_learned_action_api_preserves_deterministic_authority_until_low_risk_canary() -> None:
    predictor = TabularShadowPredictor()
    predictor.fit(_training())
    policy = _policy(predictor)
    system = DNCSystem()
    system.learned_policy_registry.register(policy)
    shadow = system.select_learned_action(
        policy=policy, predictor=predictor, risk_class=RiskClass.LOW,
        context_key="context", candidate_ids=("safe", "fast"),
        deterministic_action_id="safe", safe_action_ids=frozenset({"safe", "fast"}),
    )
    assert shadow.action_id == "safe" and not shadow.used_learned_policy
    system.learned_policy_registry.record_evidence(_evidence(policy))
    system.learned_policy_registry.promote_canary(policy.fingerprint)
    canary = system.select_learned_action(
        policy=policy, predictor=predictor, risk_class=RiskClass.LOW,
        context_key="context", candidate_ids=("safe", "fast"),
        deterministic_action_id="safe", safe_action_ids=frozenset({"safe", "fast"}),
    )
    assert canary.action_id == "fast" and canary.used_learned_policy
    high_risk = system.select_learned_action(
        policy=policy, predictor=predictor, risk_class=RiskClass.HIGH,
        context_key="context", candidate_ids=("safe", "fast"),
        deterministic_action_id="safe", safe_action_ids=frozenset({"safe", "fast"}),
    )
    assert high_risk.action_id == "safe" and not high_risk.used_learned_policy
