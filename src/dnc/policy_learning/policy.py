"""Constrained learned selection inside a deterministic safety envelope."""

from __future__ import annotations

from dnc.policy_learning.contracts import LearnedPolicyVersion, PolicyDecision
from dnc.policy_learning.models import TabularShadowPredictor


def select_action(
    *,
    policy: LearnedPolicyVersion,
    predictor: TabularShadowPredictor,
    context_key: str,
    candidate_ids: tuple[str, ...],
    deterministic_action_id: str,
    safe_action_ids: frozenset[str],
    canary_allowed: bool,
    exploration_index: int = 0,
) -> PolicyDecision:
    eligible = []
    for action_id in candidate_ids:
        prediction = predictor.predict(context_key, action_id)
        if (
            action_id in safe_action_ids
            and prediction.risk <= policy.maximum_risk
            and prediction.cost <= policy.maximum_cost
        ):
            eligible.append((action_id, prediction.outcome - prediction.cost))
    if not canary_allowed or not eligible:
        return PolicyDecision(
            deterministic_action_id, {deterministic_action_id: 1.0}, False,
            ("DETERMINISTIC_GUARDRAIL",),
        )
    eligible.sort(key=lambda item: (-item[1], item[0]))
    best = eligible[0][0]
    epsilon = policy.exploration_epsilon
    actions = [item[0] for item in eligible]
    propensities = {item: epsilon / len(actions) for item in actions}
    propensities[best] += 1 - epsilon
    selected = best
    if epsilon and exploration_index % max(1, round(1 / epsilon)) == 0:
        selected = actions[exploration_index % len(actions)]
    return PolicyDecision(selected, propensities, True, ("LEARNED_CONSTRAINED",))
