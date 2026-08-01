"""Supported off-policy evaluation estimators and sensitivity bounds."""

from __future__ import annotations

from math import fsum

from dnc.policy_learning.contracts import DecisionExample, OPEEstimate
from dnc.policy_learning.models import TabularShadowPredictor


def evaluate_off_policy(
    examples: tuple[DecisionExample, ...],
    target_propensities: dict[str, dict[str, float]],
    predictor: TabularShadowPredictor,
    *,
    maximum_weight: float = 20.0,
) -> OPEEstimate:
    rows = []
    for example in examples:
        if example.censored or example.corrected_outcome is None:
            continue
        target = target_propensities.get(example.decision_id, {})
        known_actions = {item.action_id for item in example.candidates}
        if set(target) - known_actions:
            raise ValueError("target policy references actions outside logged candidate support")
        if target and abs(fsum(target.values()) - 1.0) > 1e-6:
            raise ValueError("target policy propensities MUST sum to one")
        if any(probability < 0 or probability > 1 for probability in target.values()):
            raise ValueError("target policy propensities MUST be probabilities")
        selected_probability = target.get(example.selected_action_id, 0.0)
        if selected_probability <= 0:
            continue
        weight = min(selected_probability / example.selected.propensity, maximum_weight)
        target_model = fsum(
            probability * predictor.predict(example.context_key, action_id).outcome
            for action_id, probability in target.items()
        )
        logged_model = predictor.predict(example.context_key, example.selected_action_id).outcome
        outcome = float(example.corrected_outcome)
        rows.append((weight, outcome, target_model + weight * (outcome - logged_model)))
    if not rows:
        raise ValueError("off-policy evaluation has no supported uncensored rows")
    weights = [item[0] for item in rows]
    ips = fsum(weight * outcome for weight, outcome, _ in rows) / len(rows)
    weight_sum = fsum(weights)
    snips = fsum(weight * outcome for weight, outcome, _ in rows) / weight_sum
    dr = fsum(item[2] for item in rows) / len(rows)
    ess = weight_sum**2 / fsum(weight**2 for weight in weights)
    spread = max(ips, snips, dr) - min(ips, snips, dr)
    return OPEEstimate(
        ips, snips, dr, ess, len(rows) / len(examples),
        (min(ips, snips, dr) - spread, max(ips, snips, dr) + spread),
    )
