"""Fail-closed pilot promotion and general-availability governance."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable


class RolloutStage(str, Enum):
    OFFLINE_REPLAY = "offline_replay"
    SHADOW = "shadow"
    LIMITED_CANARY = "limited_canary"
    GENERAL_AVAILABILITY = "general_availability"


class ExerciseKind(str, Enum):
    INCIDENT = "incident"
    PROVIDER_CHANGE = "provider_change"
    MODEL_CHANGE = "model_change"
    POLICY_CHANGE = "policy_change"
    SKILL_ROLLBACK = "skill_rollback"
    DISASTER_RECOVERY = "disaster_recovery"


class ApprovalRole(str, Enum):
    PRODUCT = "product"
    DOMAIN = "domain"
    RESEARCH = "research"
    SECURITY = "security"
    PRIVACY = "privacy"
    OPERATIONS = "operations"
    ARCHITECTURE = "architecture"


REQUIRED_EXERCISES = frozenset(ExerciseKind)
REQUIRED_APPROVAL_ROLES = frozenset(ApprovalRole)


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class WorkflowProfile:
    workflow_id: str
    version: str
    domain: str
    domain_owner: str
    reversible: bool
    outcome_measurable: bool
    critical: bool
    system_fingerprint: str
    data_classification: str
    rollback_target: str

    def __post_init__(self) -> None:
        required = (
            self.workflow_id,
            self.version,
            self.domain,
            self.domain_owner,
            self.system_fingerprint,
            self.data_classification,
            self.rollback_target,
        )
        if not all(value.strip() for value in required):
            raise ValueError("workflow profile fields must be non-empty")
        if not self.reversible or not self.outcome_measurable or self.critical:
            raise ValueError("first pilot must be reversible, measurable, and noncritical")


@dataclass(frozen=True)
class PilotCriteria:
    baseline_value: float
    minimum_business_value: float
    maximum_failure_rate: float
    maximum_p95_latency_ms: float
    maximum_cost_per_case: float
    minimum_observations: int
    minimum_duration_days: int
    require_delayed_outcomes: bool = True
    require_operator_feedback: bool = True

    def __post_init__(self) -> None:
        if self.minimum_observations <= 0 or self.minimum_duration_days <= 0:
            raise ValueError("sustained evidence thresholds must be positive")
        if not 0 <= self.maximum_failure_rate <= 1:
            raise ValueError("maximum_failure_rate must be between zero and one")
        if self.maximum_p95_latency_ms <= 0 or self.maximum_cost_per_case <= 0:
            raise ValueError("SLO and cost limits must be positive")
        if self.minimum_business_value <= self.baseline_value:
            raise ValueError("minimum business value must exceed the frozen baseline")


@dataclass(frozen=True)
class OutcomeObservation:
    observation_id: str
    stage: RolloutStage
    day: int
    business_value: float
    failed: bool
    latency_ms: float
    cost: float
    operator_feedback: str | None
    delayed_outcome: float | None
    source: str
    external: bool

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.source.strip():
            raise ValueError("observation identity and source are required")
        if self.day < 0 or self.latency_ms < 0 or self.cost < 0:
            raise ValueError("observation measurements cannot be negative")


@dataclass(frozen=True)
class ExerciseRecord:
    kind: ExerciseKind
    exercised_by: str
    evidence_uri: str
    passed: bool


@dataclass(frozen=True)
class OperationalReadiness:
    capacity_plan: str
    cost_plan: str
    support_model: str
    upgrade_policy: str
    deprecation_policy: str
    customer_documentation: str

    def complete(self) -> bool:
        return all(value.strip() for value in asdict(self).values())


@dataclass(frozen=True)
class Approval:
    role: ApprovalRole
    approver: str
    workflow_fingerprint: str
    evidence_fingerprint: str
    approved: bool


@dataclass(frozen=True)
class GAReview:
    approved: bool
    reasons: tuple[str, ...]
    workflow_fingerprint: str
    evidence_fingerprint: str
    qualified_domain: str


class PilotProgram:
    """Append-only evidence ledger with ordered, fail-closed promotion gates."""

    def __init__(self, workflow: WorkflowProfile, criteria: PilotCriteria) -> None:
        self.workflow = workflow
        self.criteria = criteria
        self._stage = RolloutStage.OFFLINE_REPLAY
        self._observations: list[OutcomeObservation] = []
        self._exercises: dict[ExerciseKind, ExerciseRecord] = {}
        self._readiness: OperationalReadiness | None = None
        self._approvals: dict[ApprovalRole, Approval] = {}

    @property
    def stage(self) -> RolloutStage:
        return self._stage

    @property
    def workflow_fingerprint(self) -> str:
        return _digest(asdict(self.workflow))

    @property
    def evidence_fingerprint(self) -> str:
        evidence = self.snapshot(include_approvals=False)
        evidence.pop("stage")
        return _digest(evidence)

    def record_outcome(self, observation: OutcomeObservation) -> None:
        if observation.stage is not self._stage:
            raise ValueError("outcome stage must match the active rollout stage")
        if any(item.observation_id == observation.observation_id for item in self._observations):
            raise ValueError("observation_id must be unique")
        self._observations.append(copy.deepcopy(observation))
        self._approvals.clear()

    def record_exercise(self, record: ExerciseRecord) -> None:
        if not record.exercised_by.strip() or not record.evidence_uri.strip():
            raise ValueError("exercise owner and evidence are required")
        self._exercises[record.kind] = copy.deepcopy(record)
        self._approvals.clear()

    def set_operational_readiness(self, readiness: OperationalReadiness) -> None:
        if not readiness.complete():
            raise ValueError("all operational readiness fields are required")
        self._readiness = copy.deepcopy(readiness)
        self._approvals.clear()

    def promote(self, target: RolloutStage) -> None:
        transitions = {
            RolloutStage.OFFLINE_REPLAY: RolloutStage.SHADOW,
            RolloutStage.SHADOW: RolloutStage.LIMITED_CANARY,
        }
        if transitions.get(self._stage) is not target:
            raise ValueError("rollout stages must advance offline, shadow, then canary")
        current = [item for item in self._observations if item.stage is self._stage]
        if not current or any(item.failed for item in current):
            raise ValueError("stage promotion requires successful evidence in the active stage")
        self._stage = target
        self._approvals.clear()

    def rollback(self) -> None:
        self._stage = RolloutStage.SHADOW
        self._approvals.clear()

    def approve(self, role: ApprovalRole, approver: str, *, approved: bool = True) -> Approval:
        if not approver.strip():
            raise ValueError("approver identity is required")
        if any(item.approver == approver and item.role is not role for item in self._approvals.values()):
            raise ValueError("required approval roles must have independent approvers")
        approval = Approval(
            role=role,
            approver=approver,
            workflow_fingerprint=self.workflow_fingerprint,
            evidence_fingerprint=self.evidence_fingerprint,
            approved=approved,
        )
        self._approvals[role] = approval
        return approval

    def review_general_availability(self) -> GAReview:
        reasons = list(self._evidence_failures())
        evidence_fingerprint = self.evidence_fingerprint
        for role in sorted(REQUIRED_APPROVAL_ROLES, key=lambda item: item.value):
            approval = self._approvals.get(role)
            if approval is None:
                reasons.append(f"missing {role.value} approval")
            elif not approval.approved:
                reasons.append(f"{role.value} approval denied")
            elif (
                approval.workflow_fingerprint != self.workflow_fingerprint
                or approval.evidence_fingerprint != evidence_fingerprint
            ):
                reasons.append(f"stale {role.value} approval")
        approved = not reasons
        if approved:
            self._stage = RolloutStage.GENERAL_AVAILABILITY
        return GAReview(
            approved=approved,
            reasons=tuple(reasons),
            workflow_fingerprint=self.workflow_fingerprint,
            evidence_fingerprint=evidence_fingerprint,
            qualified_domain=self.workflow.domain,
        )

    def _evidence_failures(self) -> Iterable[str]:
        if self._stage not in {
            RolloutStage.LIMITED_CANARY,
            RolloutStage.GENERAL_AVAILABILITY,
        }:
            yield "pilot has not reached limited canary"
            return
        canary = [item for item in self._observations if item.stage is RolloutStage.LIMITED_CANARY]
        external = [item for item in canary if item.external]
        if len(external) < self.criteria.minimum_observations:
            yield "insufficient external canary observations"
        if not external:
            return
        duration = max(item.day for item in external) - min(item.day for item in external) + 1
        if duration < self.criteria.minimum_duration_days:
            yield "canary evidence is not sustained for the required duration"
        failure_rate = sum(item.failed for item in external) / len(external)
        if failure_rate > self.criteria.maximum_failure_rate:
            yield "canary failure rate exceeds criterion"
        mean_value = sum(item.business_value for item in external) / len(external)
        if mean_value < self.criteria.minimum_business_value:
            yield "business value does not exceed the declared threshold"
        ordered_latency = sorted(item.latency_ms for item in external)
        p95_index = max(0, int(0.95 * len(ordered_latency) + 0.999999) - 1)
        if ordered_latency[p95_index] > self.criteria.maximum_p95_latency_ms:
            yield "p95 latency exceeds SLO"
        if sum(item.cost for item in external) / len(external) > self.criteria.maximum_cost_per_case:
            yield "mean cost exceeds criterion"
        if self.criteria.require_delayed_outcomes and any(
            item.delayed_outcome is None for item in external
        ):
            yield "delayed business outcomes are incomplete"
        if self.criteria.require_operator_feedback and any(
            not (item.operator_feedback or "").strip() for item in external
        ):
            yield "operator feedback is incomplete"
        missing = REQUIRED_EXERCISES - {
            kind for kind, record in self._exercises.items() if record.passed
        }
        if missing:
            yield "required incident/change/rollback/recovery exercises are incomplete"
        if self._readiness is None or not self._readiness.complete():
            yield "operational readiness package is incomplete"

    def snapshot(self, *, include_approvals: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "workflow": asdict(self.workflow),
            "criteria": asdict(self.criteria),
            "stage": self._stage.value,
            "observations": [asdict(item) for item in self._observations],
            "exercises": [
                asdict(self._exercises[kind])
                for kind in sorted(self._exercises, key=lambda item: item.value)
            ],
            "readiness": asdict(self._readiness) if self._readiness is not None else None,
        }
        if include_approvals:
            data["approvals"] = [
                asdict(self._approvals[role])
                for role in sorted(self._approvals, key=lambda item: item.value)
            ]
        return copy.deepcopy(data)
