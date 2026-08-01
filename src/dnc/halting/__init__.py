"""Attempt-level adaptive reasoning and inference halting."""

from dnc.halting.contracts import (
    AttemptRecord,
    BudgetStatus,
    HaltingContext,
    HaltingPolicyMode,
    InferenceAction,
    InferenceBudget,
    InferenceDecision,
)
from dnc.halting.evaluation import HaltingEvaluation, HaltingTrial, compare_matched_quality, evaluate_trials
from dnc.halting.policy import (
    AdaptiveHaltingPolicy,
    FixedAttemptPolicy,
    FixedRefinementPolicy,
    SelfConsistencyPolicy,
    budget_status,
)

__all__ = [
    "AdaptiveHaltingPolicy",
    "AttemptRecord",
    "BudgetStatus",
    "FixedAttemptPolicy",
    "FixedRefinementPolicy",
    "HaltingContext",
    "HaltingEvaluation",
    "HaltingPolicyMode",
    "HaltingTrial",
    "InferenceAction",
    "InferenceBudget",
    "InferenceDecision",
    "SelfConsistencyPolicy",
    "budget_status",
    "compare_matched_quality",
    "evaluate_trials",
]
