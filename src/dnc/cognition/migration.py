"""Import/export and migration fixtures for Phase 3 cognitive state."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from typing import Any

from dnc.cognition.canonical import COGNITIVE_SCHEMA_VERSION, canonical_data, canonical_json
from dnc.cognition.contracts import (
    ActionLifecycleState,
    CognitiveBudgets,
    EnforcementTier,
    EpistemicItem,
    EpistemicRelation,
    EpistemicStatus,
    EvidenceItem,
    EvidenceRef,
    EvidenceSourceType,
    GoalInvariant,
    Hypothesis,
    HypothesisStatus,
    InvalidationStatus,
    ObjectiveConstraint,
    PolicyContext,
    RelationType,
    RiskClass,
    SideEffectClass,
    TaskSpec,
)
from dnc.cognition.state import CognitiveState
from dnc.kernel.errors import DNCPolicyError


def export_cognitive_state(state: CognitiveState) -> str:
    """Export cognitive state as canonical JSON."""

    return canonical_json(state)


def import_cognitive_state(payload: str | dict[str, Any]) -> CognitiveState:
    """Import all canonical state fields, applying known schema migrations."""

    raw = json.loads(payload) if isinstance(payload, str) else dict(payload)
    version = raw.get("schema_version")
    if version not in {COGNITIVE_SCHEMA_VERSION, "phase3-draft-0"}:
        raise ValueError(f"unsupported cognitive state schema_version: {version}")
    if version == "phase3-draft-0":
        raw = migrate_phase3_draft_0(raw)

    task = _task_from_dict(raw["task"])
    epistemic_items = tuple(_epistemic_item_from_dict(item) for item in raw.get("epistemic_items", ()))
    evidence = tuple(_evidence_from_dict(item) for item in raw.get("evidence", ()))
    relations = tuple(_relation_from_dict(item) for item in raw.get("relations", ()))
    hypotheses = tuple(_hypothesis_from_dict(item) for item in raw.get("hypotheses", ()))
    action_states = {
        action_id: ActionLifecycleState(state)
        for action_id, state in raw.get("action_states", {}).items()
    }
    materialized_views = {
        view_id: tuple(dependencies)
        for view_id, dependencies in raw.get("materialized_views", {}).items()
    }
    return CognitiveState(
        task=task,
        schema_version=raw.get("schema_version", COGNITIVE_SCHEMA_VERSION),
        epistemic_items=epistemic_items,
        evidence=evidence,
        relations=relations,
        hypotheses=hypotheses,
        action_states=action_states,
        materialized_views=materialized_views,
        invalidated_views=tuple(raw.get("invalidated_views", ())),
        event_log=tuple(raw.get("event_log", ())),
        answer_state_id=raw.get("answer_state_id"),
        verified_answer=bool(raw.get("verified_answer", False)),
        calibrated_risk=raw.get("calibrated_risk"),
        marginal_value_estimate=raw.get("marginal_value_estimate"),
        metadata=raw.get("metadata", {}),
    )


def _task_from_dict(raw: dict[str, Any]) -> TaskSpec:
    goal_raw = raw["goal"]
    policy_raw = raw["policy"]
    return TaskSpec(
        task_id=raw["task_id"],
        description=raw["description"],
        goal=GoalInvariant(
            objective=goal_raw["objective"],
            success_criteria=tuple(goal_raw.get("success_criteria", ())),
            constraints=tuple(goal_raw.get("constraints", ())),
            authority=tuple(goal_raw.get("authority", ())),
            mandatory_verification=tuple(goal_raw.get("mandatory_verification", ())),
        ),
        policy=PolicyContext(
            risk_class=RiskClass(policy_raw["risk_class"]),
            budget=policy_raw.get("budget"),
            deadline=policy_raw.get("deadline"),
            data_boundaries=tuple(policy_raw.get("data_boundaries", ())),
            side_effect_boundaries=tuple(policy_raw.get("side_effect_boundaries", ())),
        ),
        parent_task_id=raw.get("parent_task_id"),
        tenant_id=raw.get("tenant_id", "tenant-default"),
        actor_id=raw.get("actor_id", "actor-default"),
        session_id=raw.get("session_id", "session-default"),
        expected_output_contract=raw.get("expected_output_contract", {}),
        constraints=tuple(
            ObjectiveConstraint(
                **{
                    **constraint,
                    "tier": EnforcementTier(constraint["tier"]),
                    "violation_severity": RiskClass(
                        constraint.get("violation_severity", RiskClass.MEDIUM.value)
                    ),
                }
            )
            for constraint in raw.get("constraints", ())
        ),
        prohibited_outcomes=tuple(raw.get("prohibited_outcomes", ())),
        soft_preferences=tuple(raw.get("soft_preferences", ())),
        domain=raw.get("domain", "general"),
        data_classification=raw.get("data_classification", "internal"),
        jurisdiction_tags=tuple(raw.get("jurisdiction_tags", ())),
        budgets=CognitiveBudgets(**raw.get("budgets", {})),
        required_evidence=tuple(raw.get("required_evidence", ())),
        acceptable_uncertainty=raw.get("acceptable_uncertainty"),
        abstention_rule=raw.get("abstention_rule", "abstain when required evidence is missing"),
        escalation_rule=raw.get(
            "escalation_rule", "escalate high-risk unresolved contradictions"
        ),
        side_effect_class=SideEffectClass(raw.get("side_effect_class", SideEffectClass.NONE.value)),
        retention_policy=raw.get("retention_policy", "default"),
        audit_policy=raw.get("audit_policy", "append-only"),
        user_sources=tuple(raw.get("user_sources", ())),
        system_sources=tuple(raw.get("system_sources", ())),
        retrieved_sources=tuple(raw.get("retrieved_sources", ())),
        security_labels=tuple(raw.get("security_labels", ())),
        schema_version=raw.get("schema_version", COGNITIVE_SCHEMA_VERSION),
        metadata=raw.get("metadata", {}),
    )


def _epistemic_item_from_dict(raw: dict[str, Any]) -> EpistemicItem:
    tuple_fields = {
        "evidence_ids", "support_ids", "contradiction_ids", "depends_on",
        "security_labels", "ir_unit_refs",
    }
    values = _known_fields(EpistemicItem, raw)
    for name in tuple_fields:
        values[name] = tuple(raw.get(name, ()))
    values["status"] = EpistemicStatus(raw["status"])
    values["invalidation_status"] = InvalidationStatus(
        raw.get("invalidation_status", InvalidationStatus.CURRENT.value)
    )
    return EpistemicItem(**values)


def _evidence_from_dict(raw: dict[str, Any]) -> EvidenceItem | EvidenceRef:
    if "artifact_hash" not in raw:
        values = _known_fields(EvidenceItem, raw)
        for name in ("supports", "contradicts"):
            values[name] = tuple(raw.get(name, ()))
        return EvidenceItem(**values)
    values = _known_fields(EvidenceRef, raw)
    for name in (
        "security_labels", "chain_of_custody", "transformation_lineage", "verifier_results",
        "supports", "contradicts", "retention_obligations", "deletion_obligations",
    ):
        values[name] = tuple(raw.get(name, ()))
    values["source_type"] = EvidenceSourceType(raw["source_type"])
    return EvidenceRef(**values)


def _relation_from_dict(raw: dict[str, Any]) -> EpistemicRelation:
    values = _known_fields(EpistemicRelation, raw)
    values["relation_type"] = RelationType(raw["relation_type"])
    values["evidence_ids"] = tuple(raw.get("evidence_ids", ()))
    values["security_labels"] = tuple(raw.get("security_labels", ()))
    return EpistemicRelation(**values)


def _hypothesis_from_dict(raw: dict[str, Any]) -> Hypothesis:
    values = _known_fields(Hypothesis, raw)
    for name in (
        "supporting_evidence", "contradicting_evidence", "assumptions", "depends_on",
        "predicted_observations", "discriminating_actions", "security_labels",
    ):
        values[name] = tuple(raw.get(name, ()))
    values["status"] = HypothesisStatus(raw.get("status", HypothesisStatus.PROPOSED.value))
    values["cost_of_being_wrong"] = RiskClass(
        raw.get("cost_of_being_wrong", RiskClass.MEDIUM.value)
    )
    return Hypothesis(**values)


def _known_fields(model: type[Any], raw: dict[str, Any]) -> dict[str, Any]:
    names = {item.name for item in fields(model)}
    return {key: value for key, value in raw.items() if key in names}


def migrate_phase3_draft_0(raw: dict[str, Any]) -> dict[str, Any]:
    """Migrate the initial Phase 3 fixture into the canonical schema version."""

    migrated = dict(raw)
    migrated["schema_version"] = COGNITIVE_SCHEMA_VERSION
    task = dict(migrated["task"])
    task.setdefault("tenant_id", "tenant-default")
    task.setdefault("actor_id", "actor-default")
    task.setdefault("session_id", "session-default")
    task.setdefault("security_labels", [])
    task.setdefault("expected_output_contract", {})
    task.setdefault("metadata", {})
    migrated["task"] = task
    migrated.setdefault("event_log", [])
    return migrated


def redacted_export(state: CognitiveState, allowed_labels: set[str]) -> str:
    """Export a state with records outside the allowed security labels removed."""

    if not set(state.task.security_labels) <= allowed_labels:
        raise DNCPolicyError("task security labels are outside the export scope")
    visible_item_ids = {
        item.item_id for item in state.epistemic_items if set(item.security_labels) <= allowed_labels
    }
    visible_evidence_ids = {
        item.evidence_id
        for item in state.evidence
        if set(getattr(item, "security_labels", ())) <= allowed_labels
    }
    visible_hypothesis_ids = {
        item.hypothesis_id
        for item in state.hypotheses
        if set(item.security_labels) <= allowed_labels
    }
    visible_relation_ids = {
        relation.relation_id
        for relation in state.relations
        if set(relation.security_labels) <= allowed_labels
        and relation.source_id in visible_item_ids
        and relation.target_id in visible_item_ids
    }
    hidden_ids = (
        {item.item_id for item in state.epistemic_items} - visible_item_ids
        | {item.evidence_id for item in state.evidence} - visible_evidence_ids
        | {item.hypothesis_id for item in state.hypotheses} - visible_hypothesis_ids
        | {item.relation_id for item in state.relations} - visible_relation_ids
    )
    safe_events = tuple(
        event for event in state.event_log
        if not _contains_hidden_identifier(event, hidden_ids)
    )
    redacted = replace(
        state,
        epistemic_items=tuple(
            item for item in state.epistemic_items if item.item_id in visible_item_ids
        ),
        evidence=tuple(item for item in state.evidence if item.evidence_id in visible_evidence_ids),
        relations=tuple(
            relation for relation in state.relations
            if relation.relation_id in visible_relation_ids
        ),
        hypotheses=tuple(
            hypothesis for hypothesis in state.hypotheses
            if hypothesis.hypothesis_id in visible_hypothesis_ids
        ),
        materialized_views={
            view_id: dependencies for view_id, dependencies in state.materialized_views.items()
            if set(dependencies) <= visible_item_ids
        },
        invalidated_views=tuple(
            view_id for view_id in state.invalidated_views
            if view_id in state.materialized_views
            and set(state.materialized_views[view_id]) <= visible_item_ids
        ),
        event_log=safe_events,
        action_states={},
        answer_state_id=(
            state.answer_state_id if state.answer_state_id in visible_item_ids else None
        ),
        metadata={},
    )
    return json.dumps(canonical_data(redacted), sort_keys=True, separators=(",", ":"))


def _contains_hidden_identifier(value: Any, hidden_ids: set[str]) -> bool:
    if isinstance(value, str):
        return value in hidden_ids
    if isinstance(value, dict):
        return any(_contains_hidden_identifier(item, hidden_ids) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_hidden_identifier(item, hidden_ids) for item in value)
    return False
