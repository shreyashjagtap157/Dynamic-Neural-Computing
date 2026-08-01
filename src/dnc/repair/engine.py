"""Transactional localized cognitive repair and recovery policy."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, TYPE_CHECKING

from dnc.cognition.contracts import EpistemicItem, InvalidationStatus
from dnc.cognition.state import CognitiveState
from dnc.repair.analysis import dependency_cut
from dnc.repair.contracts import (
    ArtifactKind,
    FailureSource,
    RepairAction,
    RepairArtifact,
    RepairCandidate,
    RepairOutcome,
    RuntimeFailure,
)

if TYPE_CHECKING:
    from dnc.system import DNCSystem


def cognitive_artifacts(state: CognitiveState) -> tuple[RepairArtifact, ...]:
    artifacts = [
        RepairArtifact(item.item_id, ArtifactKind.CLAIM, item.depends_on, payload=item)
        for item in state.epistemic_items
    ]
    artifacts.extend(
        RepairArtifact(view_id, ArtifactKind.OUTPUT, tuple(dependencies), payload=view_id)
        for view_id, dependencies in state.materialized_views.items()
    )
    return tuple(artifacts)


def generate_repair_candidates(
    cut,
    *,
    input_available: bool,
    snapshot_available: bool,
) -> tuple[RepairCandidate, ...]:
    candidates = [
        RepairCandidate("local", RepairAction.LOCAL_REPAIR, cut.affected_ids, "recompute dependency cut", len(cut.affected_ids), True),
        RepairCandidate("recompute", RepairAction.RECOMPUTE, cut.affected_ids, "recompute affected closure", len(cut.affected_ids) * 1.2, True),
        RepairCandidate("abstain", RepairAction.ABSTAIN, cut.affected_ids, "avoid unsupported output", 0, True),
    ]
    if snapshot_available:
        candidates.append(RepairCandidate("rollback", RepairAction.ROLLBACK, cut.affected_ids, "restore checkpoint", 0.5, False))
    if not input_available:
        candidates.append(RepairCandidate("ask", RepairAction.ASK, cut.affected_ids, "request missing repair evidence", 0.1, True, True))
    return tuple(candidates)


def execute_localized_repair(
    system: "DNCSystem",
    root_item_id: str,
    recompute: Callable[[EpistemicItem], EpistemicItem],
    verify: Callable[[EpistemicItem], bool],
) -> RepairOutcome:
    if system.cognitive_state is None:
        raise ValueError("localized repair requires cognitive state")
    original = system.cognitive_state
    artifacts = cognitive_artifacts(original)
    cut = dependency_cut(artifacts, (root_item_id,))
    affected_claim_ids = tuple(
        artifact_id for artifact_id in cut.topological_order
        if artifact_id in {item.item_id for item in original.epistemic_items}
    )
    snapshot_id = f"repair:{root_item_id}:{system.snapshot().cycle}"
    snapshot = system.capture_execution_snapshot(snapshot_id)
    try:
        repaired_by_id = {}
        original_by_id = {item.item_id: item for item in original.epistemic_items}
        for item_id in affected_claim_ids:
            repaired = recompute(original_by_id[item_id])
            if repaired.item_id != item_id or repaired.tenant_id != original.task.tenant_id:
                raise ValueError("recomputed item identity or tenant changed")
            repaired = replace(repaired, invalidation_status=InvalidationStatus.CURRENT)
            if not verify(repaired):
                raise ValueError(f"reverification failed: {item_id}")
            repaired_by_id[item_id] = repaired
        repaired_items = tuple(repaired_by_id.get(item.item_id, item) for item in original.epistemic_items)
        repaired_item_ids = {
            item.item_id for item in repaired_items
            if item.invalidation_status is InvalidationStatus.CURRENT
        }
        affected_view_ids = tuple(
            view_id for view_id in cut.topological_order
            if view_id in original.materialized_views
        )
        for view_id in affected_view_ids:
            if not set(original.materialized_views[view_id]).issubset(repaired_item_ids):
                raise ValueError(f"repair closure incomplete: {view_id}")
        repaired_views = tuple(
            view_id for view_id in original.invalidated_views
            if view_id not in cut.affected_ids
        )
        system.cognitive_state = replace(
            original,
            epistemic_items=repaired_items,
            invalidated_views=repaired_views,
            event_log=original.event_log + ({"event": "localized_repair", "root": root_item_id, "affected": cut.affected_ids},),
        )
    except Exception as exc:
        system.restore_execution_snapshot(snapshot)
        return RepairOutcome(
            False,
            RepairAction.ROLLBACK,
            cut.affected_ids,
            (),
            cut.unaffected_ids,
            snapshot_id,
            (type(exc).__name__, str(exc)),
        )
    return RepairOutcome(
        True,
        RepairAction.LOCAL_REPAIR,
        cut.affected_ids,
        affected_claim_ids + affected_view_ids,
        cut.unaffected_ids,
        snapshot_id,
        ("REPAIR_CLOSURE_VERIFIED",),
        avoided_recomputation=len(cut.unaffected_ids),
    )


def recovery_action(failure: RuntimeFailure) -> RepairAction:
    if failure.input_required:
        return RepairAction.ASK
    if failure.state_corrupted:
        return RepairAction.ROLLBACK
    if failure.retryable and failure.source in {FailureSource.WORKER, FailureSource.PROVIDER, FailureSource.TOOL}:
        return RepairAction.RECOMPUTE
    return RepairAction.ABSTAIN
