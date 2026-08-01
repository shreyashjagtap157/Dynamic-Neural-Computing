"""Deterministic attempt-level baselines and adaptive halting policy."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.assurance.policy import RiskThresholdPolicy
from dnc.assurance.semantic import cluster_attempts
from dnc.halting.contracts import (
    BudgetStatus,
    HaltingContext,
    HaltingPolicyMode,
    InferenceAction,
    InferenceDecision,
)


def budget_status(context: HaltingContext) -> BudgetStatus:
    attempts = len(context.attempts)
    tokens = sum(attempt.tokens for attempt in context.attempts)
    cost = sum(attempt.cost for attempt in context.attempts)
    time_ms = sum(attempt.latency_ms for attempt in context.attempts)
    tails: list[str] = []
    for attempt in context.attempts:
        if context.budget.max_single_attempt_tokens is not None and attempt.tokens > context.budget.max_single_attempt_tokens:
            tails.append(f"TOKENS:{attempt.attempt_id}")
        if context.budget.max_single_attempt_cost is not None and attempt.cost > context.budget.max_single_attempt_cost:
            tails.append(f"COST:{attempt.attempt_id}")
        if context.budget.max_single_attempt_time_ms is not None and attempt.latency_ms > context.budget.max_single_attempt_time_ms:
            tails.append(f"TIME:{attempt.attempt_id}")
    exhausted = (
        attempts >= context.budget.max_attempts
        or tokens >= context.budget.max_tokens
        or cost >= context.budget.max_cost
        or time_ms >= context.budget.max_time_ms
        or bool(tails)
    )
    return BudgetStatus(attempts, tokens, cost, time_ms, exhausted, tuple(tails))


@dataclass(frozen=True)
class FixedAttemptPolicy:
    attempts: int

    def decide(self, context: HaltingContext) -> InferenceDecision:
        status = budget_status(context)
        if len(context.attempts) >= self.attempts:
            action = InferenceAction.STOP if _minimum_stop_checks(context) else InferenceAction.ABSTAIN
        else:
            action = InferenceAction.SAMPLE
        if status.exhausted and action is not InferenceAction.STOP:
            action = InferenceAction.ABSTAIN
        return InferenceDecision(action, ("FIXED_ATTEMPT_BASELINE",), status, policy_mode=HaltingPolicyMode.FIXED_ATTEMPT)


@dataclass(frozen=True)
class FixedRefinementPolicy:
    refinements: int

    def decide(self, context: HaltingContext) -> InferenceDecision:
        status = budget_status(context)
        if status.exhausted and len(context.attempts) <= self.refinements:
            action = InferenceAction.ABSTAIN
        else:
            if len(context.attempts) > self.refinements:
                action = (
                    InferenceAction.STOP
                    if _minimum_stop_checks(context)
                    else InferenceAction.ABSTAIN
                )
            else:
                action = InferenceAction.SAMPLE
        return InferenceDecision(action, ("FIXED_REFINEMENT_BASELINE",), status, policy_mode=HaltingPolicyMode.FIXED_REFINEMENT)


@dataclass(frozen=True)
class SelfConsistencyPolicy:
    attempts: int
    minimum_leading_fraction: float = 0.5

    def decide(self, context: HaltingContext) -> InferenceDecision:
        status = budget_status(context)
        clusters = cluster_attempts(tuple(attempt.semantic_attempt() for attempt in context.attempts))
        total = sum(cluster.independent_weight for cluster in clusters)
        fraction = clusters[0].independent_weight / total if total else 0.0
        if len(context.attempts) >= self.attempts:
            action = (
                InferenceAction.STOP
                if fraction >= self.minimum_leading_fraction and _minimum_stop_checks(context)
                else InferenceAction.ABSTAIN
            )
        else:
            action = InferenceAction.ABSTAIN if status.exhausted else InferenceAction.SAMPLE
        return InferenceDecision(
            action,
            ("SELF_CONSISTENCY_BASELINE",),
            status,
            cluster_count=len(clusters),
            leading_cluster_weight=fraction,
            policy_mode=HaltingPolicyMode.SELF_CONSISTENCY,
        )


@dataclass(frozen=True)
class AdaptiveHaltingPolicy:
    threshold_policy: RiskThresholdPolicy
    enabled: bool = False
    minimum_independent_groups: int = 2
    minimum_leading_fraction: float = 0.6
    fallback: FixedAttemptPolicy = FixedAttemptPolicy(3)

    def decide(self, context: HaltingContext) -> InferenceDecision:
        if not self.enabled:
            return self.fallback.decide(context)
        status = budget_status(context)
        clusters = cluster_attempts(tuple(attempt.semantic_attempt() for attempt in context.attempts))
        total_weight = sum(cluster.independent_weight for cluster in clusters)
        lead = clusters[0] if clusters else None
        fraction = lead.independent_weight / total_weight if lead and total_weight else 0.0
        alternatives = tuple(action for action in InferenceAction if action in context.available_actions)

        if context.ambiguous_fields and InferenceAction.ASK in context.available_actions:
            return self._decision(InferenceAction.ASK, "AMBIGUITY_REQUIRES_CLARIFICATION", status, clusters, fraction, alternatives)
        if context.missing_information and InferenceAction.RETRIEVE in context.available_actions:
            return self._decision(InferenceAction.RETRIEVE, "MISSING_INFORMATION", status, clusters, fraction, alternatives)
        if context.critical_contradictions and InferenceAction.VERIFY in context.available_actions:
            return self._decision(InferenceAction.VERIFY, "CRITICAL_CONTRADICTION", status, clusters, fraction, alternatives)
        if context.calibration_shifted:
            action = InferenceAction.DIVERSIFY if InferenceAction.DIVERSIFY in context.available_actions and not status.exhausted else InferenceAction.ABSTAIN
            return self._decision(action, "CALIBRATION_SHIFTED", status, clusters, fraction, alternatives)
        if status.exhausted:
            return self._decision(InferenceAction.ABSTAIN, "BUDGET_EXHAUSTED", status, clusters, fraction, alternatives)

        confidence = context.confidence
        threshold = self.threshold_policy.threshold_for(context.risk_class, context.domain)
        lower_bound = confidence.lower_bound if confidence is not None else None
        applicable = confidence is not None and confidence.applicability_status == "calibrated"
        independent_groups = len(lead.correlation_groups) if lead else 0
        stable = (
            lead is not None
            and fraction >= self.minimum_leading_fraction
            and independent_groups >= self.minimum_independent_groups
        )
        if (
            lead is not None
            and independent_groups < self.minimum_independent_groups
            and InferenceAction.DIVERSIFY in context.available_actions
        ):
            return InferenceDecision(
                InferenceAction.DIVERSIFY,
                ("INDEPENDENCE_INSUFFICIENT",),
                status,
                threshold,
                lower_bound,
                len(clusters),
                fraction,
                alternatives,
            )
        next_action, marginal_value, next_cost = self._best_next_action(context)
        may_stop = (
            context.mandatory_checks_passed
            and context.output_contract_satisfied
            and applicable
            and lower_bound is not None
            and lower_bound >= threshold
            and stable
            and marginal_value <= next_cost
        )
        if may_stop and InferenceAction.STOP in context.available_actions:
            return InferenceDecision(
                InferenceAction.STOP,
                ("MANDATORY_CHECKS_PASS", "CALIBRATED_BOUND_MET", "SEMANTIC_STABILITY", "MARGINAL_VALUE_EXHAUSTED"),
                status,
                threshold,
                lower_bound,
                len(clusters),
                fraction,
                alternatives,
            )
        if not applicable and InferenceAction.VERIFY in context.available_actions:
            next_action = InferenceAction.VERIFY
        if next_action not in context.available_actions or next_action in {InferenceAction.STOP, InferenceAction.ABSTAIN}:
            next_action = InferenceAction.SAMPLE
        return InferenceDecision(
            next_action,
            ("STOP_PRECONDITIONS_UNMET",),
            status,
            threshold,
            lower_bound,
            len(clusters),
            fraction,
            alternatives,
        )

    def _best_next_action(self, context: HaltingContext) -> tuple[InferenceAction, float, float]:
        candidates = [
            action for action in context.available_actions
            if action not in {InferenceAction.STOP, InferenceAction.ABSTAIN}
        ]
        if not candidates:
            return InferenceAction.ABSTAIN, 0.0, 0.0
        selected = max(
            candidates,
            key=lambda action: (
                context.expected_action_values.get(action, 0.0)
                - context.action_costs.get(action, 0.0),
                action.value,
            ),
        )
        return (
            selected,
            context.expected_action_values.get(selected, 0.0),
            context.action_costs.get(selected, 0.0),
        )

    @staticmethod
    def _decision(action, reason, status, clusters, fraction, alternatives):
        return InferenceDecision(
            action,
            (reason,),
            status,
            cluster_count=len(clusters),
            leading_cluster_weight=fraction,
            alternatives=alternatives,
        )


def _minimum_stop_checks(context: HaltingContext) -> bool:
    return (
        context.mandatory_checks_passed
        and context.output_contract_satisfied
        and not context.critical_contradictions
        and not context.missing_information
        and context.confidence is not None
        and context.confidence.applicability_status == "calibrated"
    )
