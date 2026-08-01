"""Semantic graph synthesis and causal experiment contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.cognition.contracts import CognitiveActionType, RiskClass, SideEffectClass
from dnc.ir.operations import IROperation
from dnc.ir.unit import ComputationalUnit, UnitContract


@dataclass(frozen=True)
class SemanticUnitTemplate:
    template_id: str
    version: str
    purpose: str
    action_type: CognitiveActionType
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_capability_id: str
    permissions: frozenset[str] = frozenset()
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    resource_limits: dict[str, float] = field(default_factory=dict)
    risk_class: RiskClass = RiskClass.MEDIUM
    side_effect_class: SideEffectClass = SideEffectClass.NONE

    def __post_init__(self) -> None:
        if not all((self.template_id, self.version, self.purpose, self.required_capability_id)):
            raise ValueError("semantic template identity, purpose, and capability MUST be complete")
        if not self.input_schema or not self.output_schema:
            raise ValueError("semantic templates MUST declare input and output schemas")

    def contract(self) -> UnitContract:
        return UnitContract(
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            preconditions=list(self.preconditions),
            postconditions=list(self.postconditions),
            resource_limits=dict(self.resource_limits),
        )


@dataclass(frozen=True)
class SemanticGraphCandidate:
    candidate_id: str
    task_id: str
    operations: tuple[IROperation, ...]
    units: tuple[ComputationalUnit, ...]
    semantic_justification: str
    predicted_evidence: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    capability_ids: tuple[str, ...]
    source_kinds: tuple[str, ...]
    hypothesis_ids: tuple[str, ...] = ()
    estimated_cost: float = 0.0
    required_isolation_grade: str = "I1_GRAPH_ONLY"
    semantic_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not all((self.candidate_id, self.task_id, self.semantic_justification, self.semantic_fingerprint)):
            raise ValueError("semantic candidate identity and justification MUST be complete")
        if not self.operations or not self.units:
            raise ValueError("semantic candidates MUST contain units and operations")
        if not self.predicted_evidence or not self.provenance_refs:
            raise ValueError("semantic candidates MUST predict evidence and declare provenance")
        if self.estimated_cost < 0:
            raise ValueError("semantic candidate cost MUST be non-negative")


class ExperimentOutcomeStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    FALSIFIED = "FALSIFIED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"


@dataclass(frozen=True)
class CausalValidity:
    intervention: str
    control: str | None
    confounders: tuple[str, ...]
    isolation_grade: str
    outcome_access: str
    randomized: bool = False

    @property
    def identifiable(self) -> bool:
        return bool(
            self.intervention
            and self.control
            and self.outcome_access
            and self.isolation_grade in {"I3_RECORDED_EXTERNALS", "I4_SANDBOXED_ENVIRONMENT"}
            and (self.randomized or not self.confounders)
        )


@dataclass(frozen=True)
class ExperimentProposal:
    experiment_id: str
    task_id: str
    hypothesis_id: str
    predicted_observations: tuple[str, ...]
    falsifier: str
    expected_information_gain: float
    expected_decision_value: float
    cost: float
    risk: float
    side_effect_class: SideEffectClass
    required_isolation_grade: str
    causal_validity: CausalValidity

    def __post_init__(self) -> None:
        if not all((self.experiment_id, self.task_id, self.hypothesis_id, self.falsifier)):
            raise ValueError("experiment identity and falsifier MUST be complete")
        if not self.predicted_observations:
            raise ValueError("experiments MUST declare predicted observations")
        if any(value < 0 for value in (self.expected_information_gain, self.expected_decision_value, self.cost, self.risk)):
            raise ValueError("experiment value, cost, and risk MUST be non-negative")
        isolation_order = {
            "I0_NONE": 0,
            "I1_GRAPH_ONLY": 1,
            "I2_PROCESS_LOCAL": 2,
            "I3_RECORDED_EXTERNALS": 3,
            "I4_SANDBOXED_ENVIRONMENT": 4,
        }
        if (
            self.side_effect_class is not SideEffectClass.NONE
            and isolation_order.get(self.required_isolation_grade, -1) < 3
        ):
            raise ValueError("effectful experiments require recorded-external isolation")


@dataclass(frozen=True)
class ExperimentOutcome:
    experiment_id: str
    hypothesis_id: str
    observation: str
    status: ExperimentOutcomeStatus
    matched_prediction: str | None
    causal_validity: CausalValidity
    evidence_ref: str
