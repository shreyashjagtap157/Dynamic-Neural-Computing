"""Calibration, shift, shadow, and online monitoring calculations."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.policy_learning.contracts import DecisionExample, PolicyMonitor
from dnc.policy_learning.models import TabularShadowPredictor


@dataclass(frozen=True)
class PredictionEvaluation:
    outcome_calibration_error: float
    cost_error: float
    risk_error: float
    unseen_context_fraction: float


@dataclass(frozen=True)
class ShadowComparison:
    decisions: int
    agreement: float
    learned_value: float
    deterministic_value: float
    guardrail_regressions: int


def evaluate_predictions(
    predictor: TabularShadowPredictor,
    examples: tuple[DecisionExample, ...],
    *,
    training_contexts: frozenset[str],
) -> PredictionEvaluation:
    usable = [item for item in examples if not item.censored and item.corrected_outcome is not None]
    if not usable:
        raise ValueError("prediction evaluation requires uncensored outcomes")
    predictions = [predictor.predict(item.context_key, item.selected_action_id) for item in usable]
    return PredictionEvaluation(
        sum(abs(pred.outcome - float(item.corrected_outcome)) for pred, item in zip(predictions, usable)) / len(usable),
        sum(abs(pred.cost - float(item.realized_cost or 0)) for pred, item in zip(predictions, usable)) / len(usable),
        sum(abs(pred.risk - float(item.constraint_violation)) for pred, item in zip(predictions, usable)) / len(usable),
        sum(item.context_key not in training_contexts for item in usable) / len(usable),
    )


def compare_shadow(
    learned_actions: tuple[str, ...],
    deterministic_actions: tuple[str, ...],
    learned_values: tuple[float, ...],
    deterministic_values: tuple[float, ...],
    guardrail_regressions: tuple[bool, ...],
) -> ShadowComparison:
    lengths = {len(learned_actions), len(deterministic_actions), len(learned_values), len(deterministic_values), len(guardrail_regressions)}
    if len(lengths) != 1 or not learned_actions:
        raise ValueError("shadow comparison inputs MUST be aligned and non-empty")
    count = len(learned_actions)
    return ShadowComparison(
        count,
        sum(left == right for left, right in zip(learned_actions, deterministic_actions)) / count,
        sum(learned_values) / count,
        sum(deterministic_values) / count,
        sum(guardrail_regressions),
    )


def calculate_policy_monitor(
    *,
    learned_values: tuple[float, ...],
    oracle_values: tuple[float, ...],
    constraint_violations: tuple[bool, ...],
    delayed_outcomes: tuple[bool, ...],
    shifted_contexts: tuple[bool, ...],
    action_counts: tuple[int, ...],
) -> PolicyMonitor:
    lengths = {
        len(learned_values), len(oracle_values), len(constraint_violations),
        len(delayed_outcomes), len(shifted_contexts), len(action_counts), sum(action_counts),
    }
    if len(lengths) != 1 or not learned_values or not action_counts:
        raise ValueError("monitor inputs MUST be aligned and non-empty")
    count = len(learned_values)
    return PolicyMonitor(
        sum(max(0.0, oracle - learned) for oracle, learned in zip(oracle_values, learned_values)) / count,
        sum(constraint_violations),
        sum(delayed_outcomes) / count,
        sum(shifted_contexts) / count,
        max(action_counts) / count,
    )
