"""Contracts for logged decisions and immutable learned policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.cognition.canonical import canonical_hash
@dataclass(frozen=True)
class LoggedCandidate:
    action_id: str
    propensity: float
    predicted_cost: float = 0.0
    predicted_risk: float = 0.0

    def __post_init__(self) -> None:
        if not self.action_id or not 0 < self.propensity <= 1:
            raise ValueError("candidate action and propensity MUST be valid")
        if self.predicted_cost < 0 or not 0 <= self.predicted_risk <= 1:
            raise ValueError("candidate cost/risk MUST be bounded")


@dataclass(frozen=True)
class DecisionExample:
    decision_id: str
    task_fingerprint: str
    context_key: str
    candidates: tuple[LoggedCandidate, ...]
    selected_action_id: str
    policy_version: str
    outcome: float | None
    realized_cost: float | None
    constraint_violation: bool = False
    delayed_correction: float | None = None
    censored: bool = False
    split: str = "train"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def selected(self) -> LoggedCandidate:
        return next(item for item in self.candidates if item.action_id == self.selected_action_id)

    @property
    def corrected_outcome(self) -> float | None:
        return self.delayed_correction if self.delayed_correction is not None else self.outcome


@dataclass(frozen=True)
class Prediction:
    outcome: float
    cost: float
    risk: float


@dataclass(frozen=True)
class LearnedPolicyVersion:
    policy_id: str
    version: str
    training_data_hash: str
    model_hash: str
    maximum_risk: float
    maximum_cost: float
    exploration_epsilon: float = 0.0
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not all((self.policy_id, self.version, self.training_data_hash, self.model_hash)):
            raise ValueError("policy identity and lineage MUST be complete")
        if not 0 <= self.maximum_risk <= 1 or self.maximum_cost < 0:
            raise ValueError("policy constraints MUST be bounded")
        if not 0 <= self.exploration_epsilon <= 0.1:
            raise ValueError("exploration MUST remain within the safe envelope")
        expected = canonical_hash(
            {
                "policy_id": self.policy_id,
                "version": self.version,
                "training_data_hash": self.training_data_hash,
                "model_hash": self.model_hash,
                "maximum_risk": self.maximum_risk,
                "maximum_cost": self.maximum_cost,
                "exploration_epsilon": self.exploration_epsilon,
            }, namespace="dnc.learned-policy.v1"
        )
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("learned policy fingerprint mismatch")
        object.__setattr__(self, "fingerprint", expected)


@dataclass(frozen=True)
class PolicyDecision:
    action_id: str
    propensities: dict[str, float]
    used_learned_policy: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class OPEEstimate:
    ips: float
    self_normalized_ips: float
    doubly_robust: float
    effective_sample_size: float
    supported_fraction: float
    sensitivity_range: tuple[float, float]


class PolicyLifecycle(str, Enum):
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class PromotionEvidence:
    evidence_id: str
    policy_fingerprint: str
    estimate: OPEEstimate
    baseline_value: float
    calibration_error: float
    shadow_guardrail_regressions: int
    lower_confidence_bound: float


@dataclass(frozen=True)
class PolicyMonitor:
    regret: float
    constraint_violations: int
    delayed_outcome_fraction: float
    distribution_shift: float
    feedback_concentration: float

    @property
    def healthy(self) -> bool:
        return (
            self.regret <= 0.05
            and self.constraint_violations == 0
            and self.distribution_shift <= 0.1
            and self.feedback_concentration <= 0.8
        )
