"""Semantic cognitive-controller candidates, predictions, and decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnc.cognition.contracts import CognitiveActionType, CognitiveProposal, RiskClass


class CandidateSource(str, Enum):
    RULE = "RULE"
    PLANNER = "PLANNER"
    MODEL = "MODEL"
    SKILL = "SKILL"
    VERIFIER = "VERIFIER"
    HYPOTHESIS = "HYPOTHESIS"


@dataclass(frozen=True)
class OutcomeVector:
    quality_gain: float = 0.0
    information_gain: float = 0.0
    confidence_gain: float = 0.0
    monetary_cost: float = 0.0
    compute_cost: float = 0.0
    latency_ms: float = 0.0
    epistemic_risk: float = 0.0
    safety_risk: float = 0.0
    privacy_risk: float = 0.0
    reversibility: float = 1.0
    side_effect_magnitude: float = 0.0

    def __post_init__(self) -> None:
        for value in self.__dict__.values():
            if value < 0:
                raise ValueError("outcome vector values MUST be non-negative")


@dataclass(frozen=True)
class ActionCandidate:
    proposal: CognitiveProposal
    source: CandidateSource
    prediction: OutcomeVector
    uncertainty: float = 0.0
    required_permissions: frozenset[str] = frozenset()
    preconditions_satisfied: bool = True
    shadow_prediction: OutcomeVector | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.uncertainty <= 1:
            raise ValueError("candidate uncertainty MUST be between 0 and 1")


@dataclass(frozen=True)
class ControllerContext:
    task_id: str
    risk_class: RiskClass
    candidates: tuple[ActionCandidate, ...]
    available_budget: float
    deadline_remaining_ms: int
    granted_permissions: frozenset[str] = frozenset()
    allowed_actions: frozenset[CognitiveActionType] = frozenset(CognitiveActionType)
    stop_authorized: bool = False
    tenant_id: str = "tenant-default"

    def __post_init__(self) -> None:
        if not self.task_id or not self.tenant_id:
            raise ValueError("controller task and tenant identity MUST be non-empty")
        if self.available_budget < 0 or self.deadline_remaining_ms < 0:
            raise ValueError("controller budget and deadline MUST be non-negative")


@dataclass(frozen=True)
class CandidateRejection:
    proposal_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ControllerDecision:
    selected: ActionCandidate | None
    alternatives: tuple[ActionCandidate, ...]
    rejections: tuple[CandidateRejection, ...]
    pareto_survivors: tuple[str, ...]
    reason_codes: tuple[str, ...]
    audit_record_id: str
    shadow_log: tuple[tuple[str, OutcomeVector], ...] = ()

    @property
    def action_type(self) -> CognitiveActionType | None:
        return self.selected.proposal.action_type if self.selected else None
