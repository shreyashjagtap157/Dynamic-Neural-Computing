import json

import pytest

from dnc.cognition import (
    ACTION_OUTCOME_SCHEMA,
    ActionLifecycleState,
    ClarificationRequest,
    CognitiveState,
    CONFIDENCE_ESTIMATE_SCHEMA,
    EpistemicItem,
    EpistemicRelation,
    EpistemicStatus,
    EPISTEMIC_RELATION_SCHEMA,
    EvidenceRef,
    EvidenceSourceType,
    EVIDENCE_REF_SCHEMA,
    GoalInvariant,
    Hypothesis,
    HypothesisStatus,
    HYPOTHESIS_SCHEMA,
    IRUnitReference,
    InvalidationStatus,
    OutcomeLifecycleState,
    PolicyContext,
    RelationType,
    RiskClass,
    RationaleCode,
    RATIONALE_CODE_SCHEMA,
    TaskSpec,
    ambiguous_task_fields,
    canonical_hash,
    export_cognitive_state,
    import_cognitive_state,
    redacted_export,
    task_fingerprint,
    validate_hypothesis_transition,
    validate_outcome_transition,
    validate_task_transition,
)
from dnc.cognition.contracts import (
    ActionOutcome,
    ConfidenceEstimate,
    EvidenceItem,
    TaskLifecycleState,
)
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import ComputationalUnit, LifecycleDimension, StructureDimension, VisibilityDimension
from dnc.system import DNCSystem


def _task(**kwargs: object) -> TaskSpec:
    return TaskSpec(
        task_id="task-1",
        tenant_id="tenant-a",
        actor_id="actor-a",
        session_id="session-a",
        description="  Answer   the question with evidence. ",
        goal=GoalInvariant(objective="  Answer the question with evidence. "),
        policy=PolicyContext(risk_class=RiskClass.HIGH),
        **kwargs,
    )


def test_task_normalization_and_clarification_workflow() -> None:
    task = _task()
    assert task.normalized_objective == "answer the question with evidence."
    assert task_fingerprint(
        objective="answer the question with evidence.",
        tenant_id=task.tenant_id,
        actor_id=task.actor_id,
        session_id=task.session_id,
    ) == task_fingerprint(
        objective="  ANSWER   THE QUESTION WITH EVIDENCE. ",
        tenant_id=task.tenant_id,
        actor_id=task.actor_id,
        session_id=task.session_id,
    )
    request = ClarificationRequest(
        request_id="clarify-1",
        task_id=task.task_id,
        question="What output format and evidence threshold should be used?",
        ambiguous_fields=ambiguous_task_fields(task),
        tenant_id=task.tenant_id,
    )
    assert "expected_output_contract" in request.ambiguous_fields


def test_canonical_hash_is_stable_and_separate_from_dnc_ir_hashes() -> None:
    graph = StructuralGraph(GraphID("graph-1"))
    graph.add_unit(
        ComputationalUnit(
            unit_id=UnitID("unit-1"),
            name="reason",
            structure=StructureDimension.PRIMITIVE,
            visibility=VisibilityDimension.INSPECTABLE,
            lifecycle=LifecycleDimension.BASE,
        )
    )
    before_ir_json = DNWIRSerializer.to_json(graph)
    before_ir_hash = canonical_hash(DNWIRSerializer.to_dict(graph), namespace="dnc.ir")

    item = EpistemicItem(
        item_id="claim-1",
        status=EpistemicStatus.MODEL_INFERENCE,
        content="Unit 1 produced a candidate answer.",
        tenant_id="tenant-a",
        ir_unit_refs=("unit-1",),
    )
    state = CognitiveState(task=_task()).with_epistemic_item(item)
    assert state.canonical_hash() == CognitiveState(task=_task()).with_epistemic_item(item).canonical_hash()
    assert DNWIRSerializer.to_json(graph) == before_ir_json
    assert canonical_hash(DNWIRSerializer.to_dict(graph), namespace="dnc.ir") == before_ir_hash


def test_append_only_evidence_relations_and_dependency_invalidation() -> None:
    root = EpistemicItem(
        item_id="claim-root",
        status=EpistemicStatus.RETRIEVED_CLAIM,
        content="The source says the value is 42.",
        tenant_id="tenant-a",
    )
    child = EpistemicItem(
        item_id="claim-child",
        status=EpistemicStatus.MODEL_INFERENCE,
        content="Therefore the answer should be 42.",
        tenant_id="tenant-a",
        depends_on=("claim-root",),
    )
    evidence = EvidenceRef(
        evidence_id="ev-1",
        artifact_hash="sha256:abc",
        source_type=EvidenceSourceType.RETRIEVED,
        source_identity="doc://source",
        acquired_at="2026-07-31T00:00:00Z",
        tenant_id="tenant-a",
        supports=("claim-root",),
        security_labels=("internal",),
    )
    state = (
        CognitiveState(task=_task())
        .with_epistemic_item(root)
        .with_epistemic_item(child)
        .with_evidence(evidence)
        .with_relation(
            EpistemicRelation(
                relation_id="rel-1",
                relation_type=RelationType.DEPENDS_ON,
                source_id="claim-child",
                target_id="claim-root",
                tenant_id="tenant-a",
            )
        )
        .with_materialized_view("answer-view", ("claim-child",))
    )

    invalidated = state.invalidate_from("claim-root", reason="source retracted")
    statuses = {item.item_id: item.invalidation_status for item in invalidated.epistemic_items}
    assert statuses["claim-root"] is InvalidationStatus.INVALID
    assert statuses["claim-child"] is InvalidationStatus.INVALID
    assert "answer-view" in invalidated.invalidated_views
    assert len(invalidated.epistemic_items) == 2


def test_hypothesis_falsifier_and_accepted_for_action_is_not_truth() -> None:
    hypothesis = Hypothesis(
        hypothesis_id="hyp-1",
        proposition="Implementation follows Phase 3 requirements.",
        status=HypothesisStatus.ACCEPTED_FOR_ACTION,
        posterior=0.82,
        predicted_observations=("schema import/export succeeds",),
        strongest_falsifier="canonical replay fails after migration",
        discriminating_actions=("run migration fixture",),
        accepted_for_action=True,
        tenant_id="tenant-a",
    )

    assert hypothesis.accepted_for_action is True
    assert hypothesis.status is HypothesisStatus.ACCEPTED_FOR_ACTION
    assert hypothesis.status is not HypothesisStatus.SUPPORTED


def test_action_lifecycle_outcome_confidence_and_rationale_records() -> None:
    state = CognitiveState(task=_task()).with_action_transition("act-1", ActionLifecycleState.PROPOSED)
    state = state.with_action_transition("act-1", ActionLifecycleState.VALIDATED)
    state = state.with_action_transition("act-1", ActionLifecycleState.POLICY_CHECKED)
    state = state.with_action_transition("act-1", ActionLifecycleState.AUTHORIZED)
    confidence = ConfidenceEstimate(
        estimate_id="conf-1",
        target_id="claim-1",
        target_type="atomic-claim",
        p_correct=0.91,
        lower_bound=0.8,
        upper_bound=0.97,
        method="deterministic-verifier",
        applicability_status="extrapolated",
    )
    outcome = ActionOutcome(
        outcome_id="out-1",
        action_id="act-1",
        attempt_id="attempt-1",
        trace_id="trace-1",
        lifecycle_state=OutcomeLifecycleState.IMMEDIATE_OBSERVED,
        execution_status="success",
        confidence_ref=confidence.estimate_id,
        cleanup_confirmed=True,
    )
    rationale = RationaleCode(code="REQ_EVIDENCE_MET", label="Required evidence was present")

    assert state.action_states["act-1"] is ActionLifecycleState.AUTHORIZED
    assert outcome.confidence_ref == "conf-1"
    assert rationale.code == "REQ_EVIDENCE_MET"
    with pytest.raises(ValueError, match="hidden chain-of-thought"):
        RationaleCode(code="BAD", label="hidden chain-of-thought trace")


def test_lifecycle_state_machines_reject_skips_and_terminal_mutation() -> None:
    state = CognitiveState(task=_task())
    with pytest.raises(ValueError, match="illegal action lifecycle"):
        state.with_action_transition("act-1", ActionLifecycleState.CLOSED)

    state = state.with_action_transition("act-1", ActionLifecycleState.PROPOSED)
    state = state.with_action_transition("act-1", ActionLifecycleState.REJECTED)
    with pytest.raises(ValueError, match="illegal action lifecycle"):
        state.with_action_transition("act-1", ActionLifecycleState.VALIDATED)

    validate_task_transition(None, TaskLifecycleState.RECEIVED)
    with pytest.raises(ValueError, match="illegal task lifecycle"):
        validate_task_transition(None, TaskLifecycleState.COMPLETED)
    validate_hypothesis_transition(None, HypothesisStatus.PROPOSED)
    with pytest.raises(ValueError, match="illegal hypothesis lifecycle"):
        validate_hypothesis_transition(HypothesisStatus.PROPOSED, HypothesisStatus.SUPPORTED)
    validate_outcome_transition(None, OutcomeLifecycleState.PREDICTED)
    with pytest.raises(ValueError, match="illegal outcome lifecycle"):
        validate_outcome_transition(None, OutcomeLifecycleState.CLOSED)


def test_import_export_migration_and_redaction_preserve_tenant_labels() -> None:
    public = EpistemicItem(
        item_id="public-claim",
        status=EpistemicStatus.DIRECT_OBSERVATION,
        content="Public observation",
        tenant_id="tenant-a",
        security_labels=("public",),
    )
    secret = EpistemicItem(
        item_id="secret-claim",
        status=EpistemicStatus.ASSUMPTION,
        content="Secret assumption",
        tenant_id="tenant-a",
        security_labels=("secret",),
    )
    state = CognitiveState(task=_task()).with_epistemic_item(public).with_epistemic_item(secret)
    restored = import_cognitive_state(export_cognitive_state(state))
    redacted = json.loads(redacted_export(restored, {"public"}))

    assert restored.task.tenant_id == "tenant-a"
    assert [item["item_id"] for item in redacted["epistemic_items"]] == ["public-claim"]
    assert "secret-claim" not in json.dumps(redacted)


def test_redaction_removes_hidden_identifiers_from_event_log() -> None:
    secret = EpistemicItem(
        item_id="secret-claim",
        status=EpistemicStatus.ASSUMPTION,
        content="Secret assumption",
        tenant_id="tenant-a",
        security_labels=("secret",),
    )
    state = CognitiveState(task=_task()).with_epistemic_item(secret)
    state = state.invalidate_from("secret-claim", reason="secret source retracted")

    payload = redacted_export(state, {"public"})

    assert "secret-claim" not in payload
    assert "secret source retracted" not in payload


def test_full_state_and_legacy_evidence_round_trip_without_loss() -> None:
    first = EpistemicItem(
        item_id="claim-a",
        status=EpistemicStatus.DIRECT_OBSERVATION,
        content="A",
        tenant_id="tenant-a",
    )
    second = EpistemicItem(
        item_id="claim-b",
        status=EpistemicStatus.MODEL_INFERENCE,
        content="B",
        tenant_id="tenant-a",
        depends_on=("claim-a",),
    )
    state = CognitiveState(task=_task(required_evidence=("source",), acceptable_uncertainty=0.1))
    state = state.with_epistemic_item(first).with_epistemic_item(second)
    state = state.with_evidence(EvidenceItem("legacy", "manual", "observed"))
    state = state.with_relation(
        EpistemicRelation(
            "relation", RelationType.DEPENDS_ON, "claim-b", "claim-a", "tenant-a"
        )
    )
    state = state.with_hypothesis(
        Hypothesis("hypothesis", "A predicts B", tenant_id="tenant-a")
    )
    state = state.with_action_transition("action", ActionLifecycleState.PROPOSED)
    state = state.with_materialized_view("answer", ("claim-b",))

    restored = import_cognitive_state(export_cognitive_state(state))

    assert restored.canonical_hash() == state.canonical_hash()
    assert isinstance(restored.evidence[0], EvidenceItem)


def test_set_canonicalization_is_order_independent() -> None:
    assert canonical_hash({"values": {"a", "b", "c"}}) == canonical_hash(
        {"values": {"c", "b", "a"}}
    )


def test_phase3_boundary_schemas_cover_all_canonical_record_types() -> None:
    schemas = (
        EVIDENCE_REF_SCHEMA,
        EPISTEMIC_RELATION_SCHEMA,
        HYPOTHESIS_SCHEMA,
        ACTION_OUTCOME_SCHEMA,
        CONFIDENCE_ESTIMATE_SCHEMA,
        RATIONALE_CODE_SCHEMA,
    )

    for schema in schemas:
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["required"]
        assert schema["properties"]["schema_version"]


def test_phase3_system_integration_does_not_mutate_graph_identity() -> None:
    state = CognitiveState(task=_task()).with_epistemic_item(
        EpistemicItem(
            item_id="claim-1",
            status=EpistemicStatus.UNKNOWN,
            content="Missing evidence",
            tenant_id="tenant-a",
        )
    )
    system = DNCSystem(execution_id="phase3", cognitive_state=state)
    before_graph = DNWIRSerializer.to_json(system.graph)
    snapshot = system.capture_execution_snapshot("snap-phase3")

    assert snapshot.runtime_state["cognitive_state_hash"] == state.canonical_hash()
    system.update_cognitive_state(state.with_materialized_view("view-1", ("claim-1",)))
    assert DNWIRSerializer.to_json(system.graph) == before_graph


def test_ir_unit_reference_is_semantic_not_truth_claim() -> None:
    ref = IRUnitReference(
        graph_id="graph-1",
        graph_version="v1.0.0-0",
        unit_id="unit-1",
        relation="produced_by",
        semantic_role="candidate_answer_source",
        tenant_id="tenant-a",
    )

    assert ref.unit_id == "unit-1"
    assert ref.semantic_role == "candidate_answer_source"
