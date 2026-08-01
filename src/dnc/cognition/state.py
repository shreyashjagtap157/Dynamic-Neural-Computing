"""Reference cognitive state container for the DNC Cognitive Runtime profile."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from dnc.cognition.canonical import COGNITIVE_SCHEMA_VERSION, canonical_hash
from dnc.cognition.contracts import (
    ActionLifecycleState,
    EpistemicItem,
    EpistemicRelation,
    EpistemicStatus,
    EvidenceItem,
    EvidenceRef,
    Hypothesis,
    HypothesisStatus,
    InvalidationStatus,
    OutcomeLifecycleState,
    RelationType,
    TaskLifecycleState,
    TaskSpec,
)


_TASK_TRANSITIONS = {
    TaskLifecycleState.RECEIVED: {TaskLifecycleState.NORMALIZED, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED},
    TaskLifecycleState.NORMALIZED: {TaskLifecycleState.POLICY_BOUND, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED},
    TaskLifecycleState.POLICY_BOUND: {TaskLifecycleState.ACTIVE, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED, TaskLifecycleState.ESCALATED},
    TaskLifecycleState.ACTIVE: {
        TaskLifecycleState.WAITING_INPUT, TaskLifecycleState.WAITING_APPROVAL,
        TaskLifecycleState.WAITING_OUTCOME, TaskLifecycleState.PAUSED,
        TaskLifecycleState.COMPLETED, TaskLifecycleState.ABSTAINED,
        TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED, TaskLifecycleState.ESCALATED,
    },
    TaskLifecycleState.WAITING_INPUT: {TaskLifecycleState.ACTIVE, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED, TaskLifecycleState.ESCALATED},
    TaskLifecycleState.WAITING_APPROVAL: {TaskLifecycleState.ACTIVE, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED, TaskLifecycleState.ESCALATED},
    TaskLifecycleState.WAITING_OUTCOME: {TaskLifecycleState.ACTIVE, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED, TaskLifecycleState.ESCALATED},
    TaskLifecycleState.PAUSED: {TaskLifecycleState.ACTIVE, TaskLifecycleState.CANCELLED, TaskLifecycleState.FAILED},
}
_ACTION_SEQUENCE = (
    ActionLifecycleState.PROPOSED, ActionLifecycleState.VALIDATED,
    ActionLifecycleState.POLICY_CHECKED, ActionLifecycleState.AUTHORIZED,
    ActionLifecycleState.PREPARED, ActionLifecycleState.EXECUTING,
    ActionLifecycleState.OBSERVED, ActionLifecycleState.VERIFIED,
    ActionLifecycleState.ASSESSED, ActionLifecycleState.CLOSED,
)
_ACTION_ALTERNATIVE_TERMINALS = {
    ActionLifecycleState.REJECTED, ActionLifecycleState.CANCELLED,
    ActionLifecycleState.TIMED_OUT, ActionLifecycleState.FAILED,
    ActionLifecycleState.COMPENSATION_REQUIRED, ActionLifecycleState.QUARANTINED,
}
_HYPOTHESIS_TRANSITIONS = {
    HypothesisStatus.PROPOSED: {HypothesisStatus.ACTIVE, HypothesisStatus.RETIRED},
    HypothesisStatus.ACTIVE: {HypothesisStatus.TEST_PLANNED, HypothesisStatus.RETIRED},
    HypothesisStatus.TEST_PLANNED: {HypothesisStatus.OBSERVATION_RECEIVED, HypothesisStatus.RETIRED},
    HypothesisStatus.OBSERVATION_RECEIVED: {
        HypothesisStatus.SUPPORTED, HypothesisStatus.WEAKENED,
        HypothesisStatus.FALSIFIED, HypothesisStatus.UNRESOLVED,
    },
    HypothesisStatus.SUPPORTED: {HypothesisStatus.ACCEPTED_FOR_ACTION, HypothesisStatus.RETIRED, HypothesisStatus.ACTIVE},
    HypothesisStatus.WEAKENED: {HypothesisStatus.ACCEPTED_FOR_ACTION, HypothesisStatus.RETIRED, HypothesisStatus.ACTIVE},
    HypothesisStatus.FALSIFIED: {HypothesisStatus.RETIRED},
    HypothesisStatus.UNRESOLVED: {HypothesisStatus.ACCEPTED_FOR_ACTION, HypothesisStatus.RETIRED, HypothesisStatus.ACTIVE},
    HypothesisStatus.ACCEPTED_FOR_ACTION: {HypothesisStatus.RETIRED, HypothesisStatus.ACTIVE},
}
_OUTCOME_SEQUENCE = (
    OutcomeLifecycleState.PREDICTED, OutcomeLifecycleState.IMMEDIATE_OBSERVED,
    OutcomeLifecycleState.INTERIM_ASSESSED, OutcomeLifecycleState.DELAYED_PENDING,
    OutcomeLifecycleState.DELAYED_OBSERVED, OutcomeLifecycleState.CLOSED,
    OutcomeLifecycleState.LEARNING_ELIGIBLE,
)


def validate_task_transition(current: TaskLifecycleState | None, next_state: TaskLifecycleState) -> None:
    _validate_transition("task", current, next_state, _TASK_TRANSITIONS, TaskLifecycleState.RECEIVED)


def validate_action_transition(current: ActionLifecycleState | None, next_state: ActionLifecycleState) -> None:
    if current == next_state:
        return
    if current is None:
        allowed = {ActionLifecycleState.PROPOSED}
    elif current in _ACTION_ALTERNATIVE_TERMINALS or current is ActionLifecycleState.CLOSED:
        allowed = set()
    else:
        allowed = {_ACTION_SEQUENCE[_ACTION_SEQUENCE.index(current) + 1]} | _ACTION_ALTERNATIVE_TERMINALS
    if next_state not in allowed:
        raise ValueError(f"illegal action lifecycle transition: {current} -> {next_state}")


def validate_hypothesis_transition(current: HypothesisStatus | None, next_state: HypothesisStatus) -> None:
    _validate_transition("hypothesis", current, next_state, _HYPOTHESIS_TRANSITIONS, HypothesisStatus.PROPOSED)


def validate_outcome_transition(current: OutcomeLifecycleState | None, next_state: OutcomeLifecycleState) -> None:
    if current == next_state:
        return
    allowed = {OutcomeLifecycleState.PREDICTED} if current is None else (
        {_OUTCOME_SEQUENCE[_OUTCOME_SEQUENCE.index(current) + 1]}
        if current is not OutcomeLifecycleState.LEARNING_ELIGIBLE else set()
    )
    if next_state not in allowed:
        raise ValueError(f"illegal outcome lifecycle transition: {current} -> {next_state}")


def _validate_transition(name: str, current: Any, next_state: Any, transitions: dict[Any, set[Any]], initial: Any) -> None:
    if current == next_state:
        return
    allowed = {initial} if current is None else transitions.get(current, set())
    if next_state not in allowed:
        raise ValueError(f"illegal {name} lifecycle transition: {current} -> {next_state}")


@dataclass(frozen=True)
class CognitiveState:
    """Immutable task-level cognitive state.

    This state is intentionally semantic: it tracks task invariants, evidence,
    epistemic distinctions, and answer identity without exposing scratchpad
    reasoning or replacing the governed DNC-IR kernel state.
    """

    task: TaskSpec
    schema_version: str = COGNITIVE_SCHEMA_VERSION
    epistemic_items: tuple[EpistemicItem, ...] = ()
    epistemic_history: tuple[EpistemicItem, ...] = ()
    evidence: tuple[EvidenceItem | EvidenceRef, ...] = ()
    relations: tuple[EpistemicRelation, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    action_states: dict[str, ActionLifecycleState] = field(default_factory=dict)
    materialized_views: dict[str, tuple[str, ...]] = field(default_factory=dict)
    invalidated_views: tuple[str, ...] = ()
    event_log: tuple[dict[str, Any], ...] = ()
    answer_state_id: str | None = None
    verified_answer: bool = False
    calibrated_risk: float | None = None
    marginal_value_estimate: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.task, TaskSpec):
            raise TypeError("task MUST be TaskSpec")
        for item in self.epistemic_items:
            if item.tenant_id != self.task.tenant_id:
                raise ValueError("epistemic item tenant_id MUST match task tenant_id")
        for item in self.epistemic_history:
            if item.tenant_id != self.task.tenant_id:
                raise ValueError("epistemic history tenant_id MUST match task tenant_id")
        for evidence in self.evidence:
            if getattr(evidence, "tenant_id", self.task.tenant_id) != self.task.tenant_id:
                raise ValueError("evidence tenant_id MUST match task tenant_id")
        if self.calibrated_risk is not None and not 0.0 <= self.calibrated_risk <= 1.0:
            raise ValueError("calibrated_risk MUST be between 0 and 1")
        if self.marginal_value_estimate is not None and self.marginal_value_estimate < 0:
            raise ValueError("marginal_value_estimate MUST be non-negative")

    @property
    def unresolved_contradictions(self) -> tuple[str, ...]:
        """Return epistemic item IDs currently marked as conflicts."""

        return tuple(
            item.item_id
            for item in self.epistemic_items
            if item.status is EpistemicStatus.CONFLICT
        )

    @property
    def missing_information(self) -> tuple[str, ...]:
        """Return epistemic item IDs currently marked as unknowns or capability limits."""

        return tuple(
            item.item_id
            for item in self.epistemic_items
            if item.status in {EpistemicStatus.UNKNOWN, EpistemicStatus.CAPABILITY_LIMIT}
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return evidence IDs in insertion order."""

        return tuple(item.evidence_id for item in self.evidence)

    def canonical_hash(self) -> str:
        """Return the semantic cognitive-state hash, separate from DNC-IR."""

        return canonical_hash(self)

    @property
    def current_epistemic_items(self) -> tuple[EpistemicItem, ...]:
        """Return non-invalidated epistemic items."""

        return tuple(
            item
            for item in self.epistemic_items
            if item.invalidation_status is InvalidationStatus.CURRENT
        )

    def has_mandatory_verification(self) -> bool:
        """Return whether the state satisfies mandatory verification policy."""

        if not self.task.goal.mandatory_verification:
            return True
        if not self.verified_answer:
            return False
        verifiers = {item.verifier for item in self.evidence if item.verifier is not None}
        return all(verifier in verifiers for verifier in self.task.goal.mandatory_verification)

    def with_epistemic_item(self, item: EpistemicItem) -> "CognitiveState":
        """Return a new state with an added epistemic item."""

        if item.item_id in {existing.item_id for existing in self.epistemic_items}:
            raise ValueError(f"epistemic item already exists: {item.item_id}")
        return CognitiveState(
            task=self.task,
            epistemic_items=self.epistemic_items + (item,),
            epistemic_history=self.epistemic_history,
            evidence=self.evidence,
            relations=self.relations,
            hypotheses=self.hypotheses,
            action_states=dict(self.action_states),
            materialized_views=dict(self.materialized_views),
            invalidated_views=self.invalidated_views,
            event_log=self.event_log
            + (
                {
                    "event": "epistemic_item_appended",
                    "item_id": item.item_id,
                    "status": item.status.value,
                },
            ),
            answer_state_id=self.answer_state_id,
            verified_answer=self.verified_answer,
            calibrated_risk=self.calibrated_risk,
            marginal_value_estimate=self.marginal_value_estimate,
            metadata=dict(self.metadata),
        )

    def with_evidence(self, evidence: EvidenceItem | EvidenceRef) -> "CognitiveState":
        """Return a new state with an added evidence item."""

        if evidence.evidence_id in self.evidence_ids:
            raise ValueError(f"evidence already exists: {evidence.evidence_id}")
        return CognitiveState(
            task=self.task,
            epistemic_items=self.epistemic_items,
            epistemic_history=self.epistemic_history,
            evidence=self.evidence + (evidence,),
            relations=self.relations,
            hypotheses=self.hypotheses,
            action_states=dict(self.action_states),
            materialized_views=dict(self.materialized_views),
            invalidated_views=self.invalidated_views,
            event_log=self.event_log
            + ({"event": "evidence_appended", "evidence_id": evidence.evidence_id},),
            answer_state_id=self.answer_state_id,
            verified_answer=self.verified_answer,
            calibrated_risk=self.calibrated_risk,
            marginal_value_estimate=self.marginal_value_estimate,
            metadata=dict(self.metadata),
        )

    def with_relation(self, relation: EpistemicRelation) -> "CognitiveState":
        """Return a new state with a support/contradiction/dependency relation."""

        item_ids = {item.item_id for item in self.epistemic_items}
        if relation.source_id not in item_ids or relation.target_id not in item_ids:
            raise ValueError("relation endpoints MUST reference existing epistemic items")
        if relation.relation_id in {existing.relation_id for existing in self.relations}:
            raise ValueError(f"relation already exists: {relation.relation_id}")
        return replace(
            self,
            relations=self.relations + (relation,),
            event_log=self.event_log
            + (
                {
                    "event": "relation_appended",
                    "relation_id": relation.relation_id,
                    "relation_type": relation.relation_type.value,
                },
            ),
        )

    def with_hypothesis(self, hypothesis: Hypothesis) -> "CognitiveState":
        """Return a new state with an appended hypothesis."""

        if hypothesis.hypothesis_id in {existing.hypothesis_id for existing in self.hypotheses}:
            raise ValueError(f"hypothesis already exists: {hypothesis.hypothesis_id}")
        if hypothesis.tenant_id != self.task.tenant_id:
            raise ValueError("hypothesis tenant_id MUST match task tenant_id")
        return replace(
            self,
            hypotheses=self.hypotheses + (hypothesis,),
            event_log=self.event_log
            + ({"event": "hypothesis_appended", "hypothesis_id": hypothesis.hypothesis_id},),
        )

    def with_action_transition(
        self,
        action_id: str,
        next_state: ActionLifecycleState,
    ) -> "CognitiveState":
        """Record an idempotent action lifecycle transition."""

        if not action_id:
            raise ValueError("action_id MUST be non-empty")
        if not isinstance(next_state, ActionLifecycleState):
            raise TypeError("next_state MUST be ActionLifecycleState")
        action_states = dict(self.action_states)
        previous = action_states.get(action_id)
        if previous == next_state:
            return self
        validate_action_transition(previous, next_state)
        action_states[action_id] = next_state
        return replace(
            self,
            action_states=action_states,
            event_log=self.event_log
            + (
                {
                    "event": "action_transition",
                    "action_id": action_id,
                    "from": previous.value if previous else None,
                    "to": next_state.value,
                },
            ),
        )

    def invalidate_from(self, item_id: str, *, reason: str) -> "CognitiveState":
        """Invalidate an item and dependency descendants without deleting history."""

        item_ids = {item.item_id for item in self.epistemic_items}
        if item_id not in item_ids:
            raise KeyError(f"unknown epistemic item: {item_id}")
        invalid = {item_id}
        changed = True
        while changed:
            changed = False
            for item in self.epistemic_items:
                if item.item_id not in invalid and set(item.depends_on) & invalid:
                    invalid.add(item.item_id)
                    changed = True
            for relation in self.relations:
                if (
                    relation.relation_type is RelationType.DEPENDS_ON
                    and relation.target_id in invalid
                    and relation.source_id not in invalid
                ):
                    invalid.add(relation.source_id)
                    changed = True

        invalidated_items = tuple(
            replace(item, invalidation_status=InvalidationStatus.INVALID)
            if item.item_id in invalid and item.invalidation_status is InvalidationStatus.CURRENT
            else item
            for item in self.epistemic_items
        )
        invalidated_views = tuple(
            view_id
            for view_id, dependencies in self.materialized_views.items()
            if set(dependencies) & invalid
        )
        return replace(
            self,
            epistemic_items=invalidated_items,
            invalidated_views=tuple(sorted(set(self.invalidated_views) | set(invalidated_views))),
            event_log=self.event_log
            + (
                {
                    "event": "dependency_invalidation",
                    "root_item_id": item_id,
                    "invalidated_item_ids": tuple(sorted(invalid)),
                    "reason": reason,
                },
            ),
        )

    def with_materialized_view(self, view_id: str, dependency_item_ids: tuple[str, ...]) -> "CognitiveState":
        """Register a materialized view and its epistemic dependencies."""

        item_ids = {item.item_id for item in self.epistemic_items}
        missing = set(dependency_item_ids) - item_ids
        if missing:
            raise ValueError(f"view dependencies are unknown: {sorted(missing)}")
        views = dict(self.materialized_views)
        views[view_id] = dependency_item_ids
        return replace(self, materialized_views=views)
