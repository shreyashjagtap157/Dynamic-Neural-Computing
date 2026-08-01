"""Attempt-level adaptive inference and halting contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from dnc.assurance.semantic import SemanticAttempt
from dnc.cognition.contracts import ConfidenceEstimate, RiskClass


class InferenceAction(str, Enum):
    SAMPLE = "SAMPLE"
    DIVERSIFY = "DIVERSIFY"
    VERIFY = "VERIFY"
    RETRIEVE = "RETRIEVE"
    ASK = "ASK"
    STOP = "STOP"
    ABSTAIN = "ABSTAIN"


class HaltingPolicyMode(str, Enum):
    FIXED_ATTEMPT = "FIXED_ATTEMPT"
    FIXED_REFINEMENT = "FIXED_REFINEMENT"
    SELF_CONSISTENCY = "SELF_CONSISTENCY"
    ADAPTIVE = "ADAPTIVE"


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: str
    task_id: str
    conclusion: str
    atomic_claims: tuple[str, ...]
    model_fingerprint: str
    prompt_fingerprint: str
    seed_family: str
    retrieval_fingerprint: str = "none"
    verifier_result_ids: tuple[str, ...] = ()
    tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    completed: bool = True

    def __post_init__(self) -> None:
        if not all((self.attempt_id, self.task_id, self.model_fingerprint, self.prompt_fingerprint, self.seed_family)):
            raise ValueError("attempt identity and diversity fingerprints MUST be complete")
        if self.tokens < 0 or self.cost < 0 or self.latency_ms < 0:
            raise ValueError("attempt resource usage MUST be non-negative")

    @property
    def correlation_group(self) -> str:
        return ":".join(
            (
                self.model_fingerprint,
                self.prompt_fingerprint,
                self.seed_family,
                self.retrieval_fingerprint,
            )
        )

    def semantic_attempt(self) -> SemanticAttempt:
        return SemanticAttempt(
            self.attempt_id,
            self.conclusion,
            self.atomic_claims,
            self.correlation_group,
            verifier_coverage=1.0 if self.verifier_result_ids else 0.0,
        )


@dataclass(frozen=True)
class InferenceBudget:
    max_attempts: int
    max_tokens: int
    max_cost: float
    max_time_ms: int
    max_single_attempt_tokens: int | None = None
    max_single_attempt_cost: float | None = None
    max_single_attempt_time_ms: int | None = None

    def __post_init__(self) -> None:
        if self.max_attempts <= 0 or self.max_tokens < 0 or self.max_cost < 0 or self.max_time_ms < 0:
            raise ValueError("inference budget limits are invalid")


@dataclass(frozen=True)
class BudgetStatus:
    attempts: int
    tokens: int
    cost: float
    time_ms: int
    exhausted: bool
    tail_violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class HaltingContext:
    task_id: str
    domain: str
    risk_class: RiskClass
    attempts: tuple[AttemptRecord, ...]
    budget: InferenceBudget
    mandatory_checks_passed: bool
    output_contract_satisfied: bool
    confidence: ConfidenceEstimate | None = None
    critical_contradictions: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    ambiguous_fields: tuple[str, ...] = ()
    calibration_shifted: bool = False
    expected_action_values: dict[InferenceAction, float] = field(default_factory=dict)
    action_costs: dict[InferenceAction, float] = field(default_factory=dict)
    available_actions: frozenset[InferenceAction] = frozenset(InferenceAction)

    def __post_init__(self) -> None:
        if not self.task_id or not self.domain:
            raise ValueError("halting context task and domain MUST be non-empty")
        if any(attempt.task_id != self.task_id for attempt in self.attempts):
            raise ValueError("all attempts MUST belong to the active task")


@dataclass(frozen=True)
class InferenceDecision:
    action: InferenceAction
    reason_codes: tuple[str, ...]
    budget_status: BudgetStatus
    threshold: float | None = None
    calibrated_lower_bound: float | None = None
    cluster_count: int = 0
    leading_cluster_weight: float = 0.0
    alternatives: tuple[InferenceAction, ...] = ()
    policy_mode: HaltingPolicyMode = HaltingPolicyMode.ADAPTIVE
