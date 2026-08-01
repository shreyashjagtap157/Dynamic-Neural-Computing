from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnc.cognition import (
    CognitiveState,
    EpistemicItem,
    EpistemicStatus,
    GoalInvariant,
    PolicyContext,
    RiskClass,
    TaskSpec,
    export_cognitive_state,
    import_cognitive_state,
)
from dnc.ir.serialization import DNWIRSerializer
from dnc.repair import (
    ArtifactKind,
    ArtifactValidity,
    FailureSource,
    RepairAction,
    RepairArtifact,
    RuntimeFailure,
    cognitive_artifacts,
    dependency_cut,
    evaluate_repair,
    generate_repair_candidates,
    propagate_stale,
    recovery_action,
)
from dnc.system import DNCSystem


def _state() -> CognitiveState:
    state = CognitiveState(
        TaskSpec(
            task_id="task", tenant_id="tenant-a", description="repair stale evidence",
            goal=GoalInvariant("produce corrected output"),
            policy=PolicyContext(risk_class=RiskClass.HIGH),
        )
    )
    state = state.with_epistemic_item(
        EpistemicItem("root", EpistemicStatus.RETRIEVED_CLAIM, "old root", tenant_id="tenant-a")
    )
    state = state.with_epistemic_item(
        EpistemicItem(
            "child", EpistemicStatus.MODEL_INFERENCE, "old child",
            tenant_id="tenant-a", depends_on=("root",),
        )
    )
    state = state.with_epistemic_item(
        EpistemicItem("independent", EpistemicStatus.VERIFIED_FACT, "keep me", tenant_id="tenant-a")
    )
    return state.with_materialized_view("answer", ("child",))


def test_dependency_cut_propagates_across_all_typed_artifact_kinds() -> None:
    artifacts = (
        RepairArtifact("claim", ArtifactKind.CLAIM),
        RepairArtifact("plan", ArtifactKind.PLAN, ("claim",)),
        RepairArtifact("action", ArtifactKind.ACTION, ("plan",)),
        RepairArtifact("output", ArtifactKind.OUTPUT, ("action",)),
        RepairArtifact("memory", ArtifactKind.MEMORY, ("claim",)),
        RepairArtifact("skill", ArtifactKind.SKILL, ("memory",)),
        RepairArtifact("independent", ArtifactKind.CLAIM),
    )
    cut = dependency_cut(artifacts, ("claim",))
    assert set(cut.affected_ids) == {"claim", "plan", "action", "output", "memory", "skill"}
    assert cut.unaffected_ids == ("independent",)
    stale = {item.artifact_id: item.validity for item in propagate_stale(artifacts, cut)}
    assert stale["claim"] is ArtifactValidity.INVALID
    assert all(stale[item] is ArtifactValidity.STALE for item in ("plan", "action", "output", "memory", "skill"))
    assert stale["independent"] is ArtifactValidity.CURRENT


def test_repair_candidates_cover_local_rollback_recompute_ask_and_abstain() -> None:
    cut = dependency_cut(cognitive_artifacts(_state()), ("root",))
    actions = {
        candidate.action
        for candidate in generate_repair_candidates(
            cut, input_available=False, snapshot_available=True
        )
    }
    assert actions == set(RepairAction)


def test_localized_repair_matches_full_recompute_and_preserves_independent_state() -> None:
    system = DNCSystem(cognitive_state=_state())
    graph_before = DNWIRSerializer.to_json(system.graph)
    independent_before = next(
        item for item in system.cognitive_state.epistemic_items if item.item_id == "independent"
    )

    outcome = system.repair_cognitive_state(
        "root",
        lambda item: replace(item, content=f"corrected {item.item_id}"),
        lambda item: item.content.startswith("corrected"),
    )

    assert outcome.success
    assert set(outcome.affected_ids) == {"root", "child", "answer"}
    assert set(outcome.reverified_ids) == set(outcome.affected_ids)
    assert outcome.avoided_recomputation == 1
    assert DNWIRSerializer.to_json(system.graph) == graph_before
    independent_after = next(
        item for item in system.cognitive_state.epistemic_items if item.item_id == "independent"
    )
    assert independent_after == independent_before
    values = {item.item_id: item.content for item in system.cognitive_state.epistemic_items}
    full = {"root": "corrected root", "child": "corrected child", "independent": "keep me"}
    evaluation = evaluate_repair(
        localized_values=values,
        full_recompute_values=full,
        affected_ids=("root", "child"),
        original_values={"root": "old root", "child": "old child", "independent": "keep me"},
    )
    assert evaluation.correctness_matches_full
    assert evaluation.repair_precision == 1
    assert evaluation.unaffected_preservation == 1
    assert evaluation.avoided_recomputation_fraction == pytest.approx(1 / 3)
    history = system.cognitive_state.epistemic_history
    assert [(item.item_id, item.content) for item in history] == [
        ("root", "old root"),
        ("child", "old child"),
    ]
    assert all(item.invalidation_status.value == "INVALID" for item in history)
    restored = import_cognitive_state(export_cognitive_state(system.cognitive_state))
    assert restored.epistemic_history == history


def test_failed_reverification_rolls_back_everything() -> None:
    system = DNCSystem(cognitive_state=_state())
    before_hash = system.cognitive_state.canonical_hash()
    graph_before = DNWIRSerializer.to_json(system.graph)
    outcome = system.repair_cognitive_state(
        "root",
        lambda item: replace(item, content="corrupt"),
        lambda item: item.item_id != "child",
    )
    assert not outcome.success
    assert outcome.action is RepairAction.ROLLBACK
    assert system.cognitive_state.canonical_hash() == before_hash
    assert DNWIRSerializer.to_json(system.graph) == graph_before


def test_adversarial_cross_tenant_recompute_is_rejected_and_rolled_back() -> None:
    system = DNCSystem(cognitive_state=_state())
    before = system.cognitive_state.canonical_hash()
    outcome = system.repair_cognitive_state(
        "root",
        lambda item: replace(item, tenant_id="attacker"),
        lambda item: True,
    )
    assert not outcome.success
    assert system.cognitive_state.canonical_hash() == before
    assert any("tenant" in reason for reason in outcome.reason_codes)


def test_frozen_stale_evidence_fixture_repairs_only_dependency_cut() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "stale_evidence.json").read_text(encoding="utf-8")
    )
    system = DNCSystem(cognitive_state=_state())
    outcome = system.repair_cognitive_state(
        fixture["root_id"],
        lambda item: replace(item, content=f"{fixture['replacement_prefix']} {item.item_id}"),
        lambda item: item.content.startswith(fixture["replacement_prefix"]),
    )
    assert outcome.success
    assert set(outcome.affected_ids) == set(fixture["affected_ids"])
    assert set(outcome.preserved_ids) == set(fixture["preserved_ids"])


@pytest.mark.parametrize(
    ("failure", "expected"),
    (
        (RuntimeFailure("worker", FailureSource.WORKER, True, False), RepairAction.RECOMPUTE),
        (RuntimeFailure("provider", FailureSource.PROVIDER, False, True), RepairAction.ROLLBACK),
        (RuntimeFailure("tool", FailureSource.TOOL, False, False, True), RepairAction.ASK),
        (RuntimeFailure("fatal", FailureSource.PROVIDER, False, False), RepairAction.ABSTAIN),
    ),
)
def test_runtime_failure_recovery_policy(failure, expected) -> None:
    assert recovery_action(failure) is expected


def test_dependency_cycles_and_unknown_roots_are_rejected() -> None:
    with pytest.raises(ValueError, match="acyclic"):
        dependency_cut(
            (
                RepairArtifact("a", ArtifactKind.CLAIM, ("b",)),
                RepairArtifact("b", ArtifactKind.CLAIM, ("a",)),
            ),
            ("a",),
        )
    with pytest.raises(KeyError, match="unknown"):
        dependency_cut((RepairArtifact("a", ArtifactKind.CLAIM),), ("missing",))
