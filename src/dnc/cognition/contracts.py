"""Typed contracts for the DNC Cognitive Runtime profile.

These contracts intentionally model cognitive control separately from the
existing DCCL structural-mutation contracts.  In particular, ``NO_OP`` is a
kernel-level mutation decision, while ``STOP`` is a task-level halting decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.kernel.contracts import SideEffectClass

from dnc.cognition.canonical import COGNITIVE_SCHEMA_VERSION, canonical_hash, normalize_text


class RiskClass(str, Enum):
    """Risk class used to choose verification and halting requirements."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EpistemicStatus(str, Enum):
    """Status of an epistemic item in task state."""

    VERIFIED_FACT = "VERIFIED_FACT"
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    RETRIEVED_CLAIM = "RETRIEVED_CLAIM"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    FACT = "FACT"
    OBSERVATION = "OBSERVATION"
    ASSUMPTION = "ASSUMPTION"
    PREDICTION = "PREDICTION"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"
    CAPABILITY_LIMIT = "CAPABILITY_LIMIT"
    UNVERIFIABLE = "UNVERIFIABLE"
    RETRACTED = "RETRACTED"


class CognitiveActionType(str, Enum):
    """Normative cognitive action vocabulary from RFC-0001."""

    REASON = "REASON"
    CONTINUE = "CONTINUE"
    BRANCH = "BRANCH"
    VERIFY = "VERIFY"
    RETRIEVE = "RETRIEVE"
    OBSERVE_OR_TEST = "OBSERVE_OR_TEST"
    ASK = "ASK"
    REPAIR = "REPAIR"
    REUSE_SKILL = "REUSE_SKILL"
    RESTRUCTURE = "RESTRUCTURE"
    ESCALATE = "ESCALATE"
    RESUME = "RESUME"
    STOP = "STOP"
    ABSTAIN = "ABSTAIN"


class HaltingDecisionType(str, Enum):
    """Task-level decision after considering evidence and marginal value."""

    STOP = "STOP"
    CONTINUE = "CONTINUE"
    ABSTAIN = "ABSTAIN"
    ASK = "ASK"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    ESCALATE = "ESCALATE"


class CognitiveUnsupportedAction(ValueError):
    """Raised when an unsupported action is supplied to a cognitive contract."""


class EnforcementTier(str, Enum):
    INVARIANT = "INVARIANT"
    CONSTRAINT = "CONSTRAINT"
    POLICY = "POLICY"
    PREFERENCE = "PREFERENCE"


class EvidenceSourceType(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"
    SYSTEM = "SYSTEM"
    RETRIEVED = "RETRIEVED"
    TOOL = "TOOL"
    MODEL = "MODEL"
    HUMAN = "HUMAN"


class RelationType(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    INVALIDATES = "INVALIDATES"


class InvalidationStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALID = "INVALID"
    SUPERSEDED = "SUPERSEDED"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    TEST_PLANNED = "TEST_PLANNED"
    OBSERVATION_RECEIVED = "OBSERVATION_RECEIVED"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    FALSIFIED = "FALSIFIED"
    UNRESOLVED = "UNRESOLVED"
    ACCEPTED_FOR_ACTION = "ACCEPTED_FOR_ACTION"
    RETIRED = "RETIRED"


class TaskLifecycleState(str, Enum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    POLICY_BOUND = "POLICY_BOUND"
    ACTIVE = "ACTIVE"
    WAITING_INPUT = "WAITING_INPUT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_OUTCOME = "WAITING_OUTCOME"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABSTAINED = "ABSTAINED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class ActionLifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    POLICY_CHECKED = "POLICY_CHECKED"
    AUTHORIZED = "AUTHORIZED"
    PREPARED = "PREPARED"
    EXECUTING = "EXECUTING"
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    ASSESSED = "ASSESSED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"
    COMPENSATION_REQUIRED = "COMPENSATION_REQUIRED"
    QUARANTINED = "QUARANTINED"


class OutcomeLifecycleState(str, Enum):
    PREDICTED = "PREDICTED"
    IMMEDIATE_OBSERVED = "IMMEDIATE_OBSERVED"
    INTERIM_ASSESSED = "INTERIM_ASSESSED"
    DELAYED_PENDING = "DELAYED_PENDING"
    DELAYED_OBSERVED = "DELAYED_OBSERVED"
    CLOSED = "CLOSED"
    LEARNING_ELIGIBLE = "LEARNING_ELIGIBLE"


class ClarificationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    ANSWERED = "ANSWERED"


@dataclass(frozen=True)
class ClarificationRequest:
    request_id: str
    task_id: str
    question: str
    ambiguous_fields: tuple[str, ...]
    status: ClarificationStatus = ClarificationStatus.REQUIRED
    tenant_id: str = "tenant-default"
    schema_version: str = COGNITIVE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.request_id or not self.task_id:
            raise ValueError("clarification request IDs MUST be non-empty")
        if not self.question:
            raise ValueError("clarification question MUST be non-empty")
        if not self.ambiguous_fields:
            raise ValueError("clarification requests MUST name ambiguous fields")


@dataclass(frozen=True)
class RationaleCode:
    code: str
    label: str
    evidence_ids: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    thresholds: dict[str, float] = field(default_factory=dict)
    schema_version: str = COGNITIVE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.code or not self.label:
            raise ValueError("rationale code and label MUST be non-empty")
        normalized_label = self.label.casefold().replace("-", "_")
        if "chain_of_thought" in normalized_label or "hidden reasoning" in normalized_label:
            raise ValueError("rationale codes MUST NOT encode hidden chain-of-thought")


@dataclass(frozen=True)
class ConfidenceEstimate:
    estimate_id: str
    target_id: str
    target_type: str
    p_correct: float | None = None
    failure_probability: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    method: str = "unavailable"
    calibration_model: str | None = None
    calibration_dataset: str | None = None
    calibration_split: str | None = None
    calibration_version: str | None = None
    domain: str = "general"
    risk_class: RiskClass = RiskClass.MEDIUM
    capability_fingerprint: str | None = None
    prompt_fingerprint: str | None = None
    verifier_fingerprints: tuple[str, ...] = ()
    sample_count: int = 0
    semantic_cluster_count: int = 0
    correlation_groups: tuple[str, ...] = ()
    held_out_metrics: dict[str, float] = field(default_factory=dict)
    shift_indicators: dict[str, float] = field(default_factory=dict)
    applicability_status: str = "unavailable"
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.estimate_id or not self.target_id or not self.target_type:
            raise ValueError("confidence estimate IDs MUST be non-empty")
        for name in ("p_correct", "failure_probability", "lower_bound", "upper_bound"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} MUST be between 0 and 1")
        numeric = (self.p_correct, self.failure_probability, self.lower_bound, self.upper_bound)
        if any(value is not None for value in numeric) and self.applicability_status not in {
            "calibrated",
            "extrapolated",
        }:
            raise ValueError("numeric confidence requires applicable calibration evidence")
        if self.sample_count < 0 or self.semantic_cluster_count < 0:
            raise ValueError("confidence sample and cluster counts MUST be non-negative")


@dataclass(frozen=True)
class ActionOutcome:
    outcome_id: str
    action_id: str
    attempt_id: str
    trace_id: str
    lifecycle_state: OutcomeLifecycleState
    execution_status: str
    observations: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    provider_fingerprint: str | None = None
    snapshot_id: str | None = None
    replay_grade: str | None = None
    isolation_grade: str | None = None
    realized_costs: dict[str, float] = field(default_factory=dict)
    side_effect_refs: tuple[str, ...] = ()
    compensation_status: str = "none"
    verifier_results: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    confidence_ref: str | None = None
    predicted_realized_deltas: dict[str, float] = field(default_factory=dict)
    cleanup_confirmed: bool = False
    tenant_id: str = "tenant-default"
    security_labels: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.outcome_id or not self.action_id or not self.attempt_id or not self.trace_id:
            raise ValueError("outcome/action/attempt/trace IDs MUST be non-empty")
        if not isinstance(self.lifecycle_state, OutcomeLifecycleState):
            raise TypeError("lifecycle_state MUST be OutcomeLifecycleState")


@dataclass(frozen=True)
class ObjectiveConstraint:
    constraint_id: str
    predicate: str
    label: str
    tier: EnforcementTier
    scope: str = "task"
    activation_condition: str = "always"
    violation_severity: RiskClass = RiskClass.MEDIUM
    detector_version: str = "manual-v1"
    override_authority: str | None = None
    override_forbidden: bool = False
    remediation: str = "escalate"

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise ValueError("constraint_id MUST be non-empty")
        if not self.predicate:
            raise ValueError("predicate MUST be non-empty")
        if not self.label:
            raise ValueError("label MUST be non-empty")
        if not isinstance(self.tier, EnforcementTier):
            raise TypeError("tier MUST be EnforcementTier")


@dataclass(frozen=True)
class CognitiveBudgets:
    tokens: int | None = None
    money: float | None = None
    wall_time_ms: int | None = None
    accelerator_time_ms: int | None = None
    tool_calls: int | None = None
    branch_count: int | None = None
    attempt_count: int | None = None

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if value is not None and value < 0:
                raise ValueError(f"{name} MUST be non-negative when provided")


@dataclass(frozen=True)
class GoalInvariant:
    """Goal-preserving constraints that cognitive policies may not alter."""

    objective: str
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    authority: tuple[str, ...] = ()
    mandatory_verification: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.objective:
            raise ValueError("objective MUST be non-empty")


@dataclass(frozen=True)
class PolicyContext:
    """Policy envelope for a task-level cognitive run."""

    risk_class: RiskClass
    budget: float | None = None
    deadline: str | None = None
    data_boundaries: tuple[str, ...] = ()
    side_effect_boundaries: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.risk_class, RiskClass):
            raise TypeError("risk_class MUST be RiskClass")
        if self.budget is not None and self.budget < 0:
            raise ValueError("budget MUST be non-negative when provided")


@dataclass(frozen=True)
class TaskSpec:
    """Task identity and immutable task-level invariants."""

    task_id: str
    description: str
    goal: GoalInvariant
    policy: PolicyContext
    parent_task_id: str | None = None
    tenant_id: str = "tenant-default"
    actor_id: str = "actor-default"
    session_id: str = "session-default"
    expected_output_contract: dict[str, Any] = field(default_factory=dict)
    constraints: tuple[ObjectiveConstraint, ...] = ()
    prohibited_outcomes: tuple[str, ...] = ()
    soft_preferences: tuple[str, ...] = ()
    domain: str = "general"
    data_classification: str = "internal"
    jurisdiction_tags: tuple[str, ...] = ()
    budgets: CognitiveBudgets = field(default_factory=CognitiveBudgets)
    required_evidence: tuple[str, ...] = ()
    acceptable_uncertainty: float | None = None
    abstention_rule: str = "abstain when required evidence is missing"
    escalation_rule: str = "escalate high-risk unresolved contradictions"
    side_effect_class: SideEffectClass = SideEffectClass.NONE
    retention_policy: str = "default"
    audit_policy: str = "append-only"
    user_sources: tuple[str, ...] = ()
    system_sources: tuple[str, ...] = ()
    retrieved_sources: tuple[str, ...] = ()
    security_labels: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id MUST be non-empty")
        if not self.description:
            raise ValueError("description MUST be non-empty")
        if not isinstance(self.goal, GoalInvariant):
            raise TypeError("goal MUST be GoalInvariant")
        if not isinstance(self.policy, PolicyContext):
            raise TypeError("policy MUST be PolicyContext")
        if not self.tenant_id:
            raise ValueError("tenant_id MUST be non-empty")
        if not self.actor_id:
            raise ValueError("actor_id MUST be non-empty")
        if not self.session_id:
            raise ValueError("session_id MUST be non-empty")
        if self.acceptable_uncertainty is not None and not 0.0 <= self.acceptable_uncertainty <= 1.0:
            raise ValueError("acceptable_uncertainty MUST be between 0 and 1")

    @property
    def normalized_objective(self) -> str:
        return normalize_text(self.goal.objective)

    def canonical_hash(self) -> str:
        return canonical_hash(self)


@dataclass(frozen=True)
class EvidenceItem:
    """Evidence item supporting or contradicting an epistemic item."""

    evidence_id: str
    source: str
    summary: str
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    verifier: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id MUST be non-empty")
        if not self.source:
            raise ValueError("source MUST be non-empty")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence MUST be between 0 and 1")


@dataclass(frozen=True)
class EvidenceRef:
    """Content-addressed evidence record for cognitive state."""

    evidence_id: str
    artifact_hash: str
    source_type: EvidenceSourceType
    source_identity: str
    acquired_at: str
    tenant_id: str = "tenant-default"
    security_labels: tuple[str, ...] = ()
    freshness: str | None = None
    trust_policy: str = "unverified"
    authority_level: str = "none"
    independence_group: str = "default"
    chain_of_custody: tuple[str, ...] = ()
    transformation_lineage: tuple[str, ...] = ()
    prompt_injection_untrusted: bool = False
    signature: str | None = None
    verifier_results: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    retention_obligations: tuple[str, ...] = ()
    deletion_obligations: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id MUST be non-empty")
        if not self.artifact_hash:
            raise ValueError("artifact_hash MUST be non-empty")
        if not isinstance(self.source_type, EvidenceSourceType):
            raise TypeError("source_type MUST be EvidenceSourceType")
        if not self.source_identity:
            raise ValueError("source_identity MUST be non-empty")
        if not self.acquired_at:
            raise ValueError("acquired_at MUST be non-empty")
        if not self.tenant_id:
            raise ValueError("tenant_id MUST be non-empty")


@dataclass(frozen=True)
class EpistemicItem:
    """Fact, observation, assumption, prediction, conflict, unknown, or limit."""

    item_id: str
    status: EpistemicStatus
    content: str
    tenant_id: str = "tenant-default"
    normalized_claim: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    scope: str = "task"
    temporal_validity: str | None = None
    confidence_ref: str | None = None
    evidence_ids: tuple[str, ...] = ()
    support_ids: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    independence_group: str = "default"
    freshness: str | None = None
    expires_at: str | None = None
    invalidation_status: InvalidationStatus = InvalidationStatus.CURRENT
    security_labels: tuple[str, ...] = ()
    ir_unit_refs: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id MUST be non-empty")
        if not isinstance(self.status, EpistemicStatus):
            raise TypeError("status MUST be EpistemicStatus")
        if not self.content:
            raise ValueError("content MUST be non-empty")
        if not self.tenant_id:
            raise ValueError("tenant_id MUST be non-empty")

    @property
    def canonical_claim(self) -> str:
        return self.normalized_claim or normalize_text(self.content)


@dataclass(frozen=True)
class EpistemicRelation:
    relation_id: str
    relation_type: RelationType
    source_id: str
    target_id: str
    tenant_id: str = "tenant-default"
    evidence_ids: tuple[str, ...] = ()
    security_labels: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.relation_id:
            raise ValueError("relation_id MUST be non-empty")
        if not isinstance(self.relation_type, RelationType):
            raise TypeError("relation_type MUST be RelationType")
        if not self.source_id or not self.target_id:
            raise ValueError("relation endpoints MUST be non-empty")


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    proposition: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    scope: str = "task"
    prior: float | None = None
    posterior: float | None = None
    qualitative_uncertainty: str = "unknown"
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    predicted_observations: tuple[str, ...] = ()
    strongest_falsifier: str = ""
    discriminating_actions: tuple[str, ...] = ()
    decision_relevance: str = "unspecified"
    cost_of_being_wrong: RiskClass = RiskClass.MEDIUM
    accepted_for_action: bool = False
    tenant_id: str = "tenant-default"
    security_labels: tuple[str, ...] = ()
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id MUST be non-empty")
        if not self.proposition:
            raise ValueError("proposition MUST be non-empty")
        if not isinstance(self.status, HypothesisStatus):
            raise TypeError("status MUST be HypothesisStatus")
        for name in ("prior", "posterior"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} MUST be between 0 and 1")
        if self.accepted_for_action and self.status is not HypothesisStatus.ACCEPTED_FOR_ACTION:
            raise ValueError("accepted_for_action requires ACCEPTED_FOR_ACTION status")


@dataclass(frozen=True)
class IRUnitReference:
    """Semantic reference to DNC-IR without changing graph identity."""

    graph_id: str
    graph_version: str
    unit_id: str
    relation: str
    semantic_role: str
    tenant_id: str = "tenant-default"
    schema_version: str = COGNITIVE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.graph_id or not self.graph_version or not self.unit_id:
            raise ValueError("IR references MUST include graph_id, graph_version, and unit_id")


@dataclass(frozen=True)
class CognitiveProposal:
    """Governed proposal for one cognitive action."""

    proposal_id: str
    task_id: str
    action_type: CognitiveActionType
    rationale: str
    preconditions: tuple[str, ...] = ()
    expected_effects: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0
    risk: RiskClass = RiskClass.MEDIUM
    reversible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id MUST be non-empty")
        if not self.task_id:
            raise ValueError("task_id MUST be non-empty")
        if not isinstance(self.action_type, CognitiveActionType):
            raise CognitiveUnsupportedAction("action_type MUST be CognitiveActionType")
        if not self.rationale:
            raise ValueError("rationale MUST be non-empty")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost MUST be non-negative")
        if self.estimated_latency_ms < 0:
            raise ValueError("estimated_latency_ms MUST be non-negative")
        if not isinstance(self.risk, RiskClass):
            raise TypeError("risk MUST be RiskClass")


@dataclass(frozen=True)
class CognitiveDecision:
    """Authorization and selection result for a cognitive proposal."""

    proposal_id: str
    authorized: bool
    selected: bool = False
    rejection_reason: str | None = None
    conditions: tuple[str, ...] = ()
    audit_record_id: str | None = None

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id MUST be non-empty")
        if self.selected and not self.authorized:
            raise ValueError("selected cognitive decisions MUST be authorized")


@dataclass(frozen=True)
class NoOpDecision:
    """Structural mutation decision comparing a proposal to state preservation."""

    proposal_id: str
    source_state_id: str
    accepted_no_op: bool
    isolation_grade: str
    rationale: str
    uncaptured_state: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id MUST be non-empty")
        if not self.source_state_id:
            raise ValueError("source_state_id MUST be non-empty")
        if not self.isolation_grade:
            raise ValueError("isolation_grade MUST be non-empty")
        if not self.rationale:
            raise ValueError("rationale MUST be non-empty")


@dataclass(frozen=True)
class HaltingDecision:
    """Task-level halting decision distinct from structural ``NO_OP``."""

    task_id: str
    decision: HaltingDecisionType
    answer_state_id: str | None
    calibrated_risk: float | None
    evidence_ids: tuple[str, ...]
    unresolved_contradictions: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    marginal_value_estimate: float | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id MUST be non-empty")
        if not isinstance(self.decision, HaltingDecisionType):
            raise TypeError("decision MUST be HaltingDecisionType")
        if self.calibrated_risk is not None and not 0.0 <= self.calibrated_risk <= 1.0:
            raise ValueError("calibrated_risk MUST be between 0 and 1")
        if self.marginal_value_estimate is not None and self.marginal_value_estimate < 0:
            raise ValueError("marginal_value_estimate MUST be non-negative")
        if self.decision is HaltingDecisionType.STOP:
            if self.answer_state_id is None:
                raise ValueError("STOP decisions MUST identify an answer_state_id")
            if self.calibrated_risk is None:
                raise ValueError("STOP decisions MUST include calibrated_risk")
            if self.unresolved_contradictions:
                raise ValueError("STOP decisions MUST NOT have unresolved contradictions")
            if self.missing_information:
                raise ValueError("STOP decisions MUST NOT have missing information")
