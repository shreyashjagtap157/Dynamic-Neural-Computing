"""Dependency cut analysis and typed stale propagation."""

from __future__ import annotations

from dataclasses import replace

from dnc.repair.contracts import ArtifactValidity, DependencyCut, RepairArtifact


def dependency_cut(
    artifacts: tuple[RepairArtifact, ...], root_ids: tuple[str, ...]
) -> DependencyCut:
    by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    if len(by_id) != len(artifacts):
        raise ValueError("repair artifacts MUST have unique IDs")
    missing = set(root_ids) - set(by_id)
    if missing:
        raise KeyError(f"unknown repair roots: {sorted(missing)}")
    affected = set(root_ids)
    changed = True
    while changed:
        changed = False
        for artifact in artifacts:
            if artifact.artifact_id not in affected and set(artifact.depends_on) & affected:
                affected.add(artifact.artifact_id)
                changed = True
    order = _topological_order(tuple(by_id[item] for item in affected))
    return DependencyCut(
        tuple(sorted(root_ids)),
        tuple(order),
        tuple(sorted(set(by_id) - affected)),
        tuple(order),
    )


def propagate_stale(
    artifacts: tuple[RepairArtifact, ...], cut: DependencyCut
) -> tuple[RepairArtifact, ...]:
    roots = set(cut.root_ids)
    affected = set(cut.affected_ids)
    return tuple(
        replace(
            artifact,
            validity=(
                ArtifactValidity.INVALID
                if artifact.artifact_id in roots
                else ArtifactValidity.STALE
            ),
        )
        if artifact.artifact_id in affected
        else artifact
        for artifact in artifacts
    )


def _topological_order(artifacts: tuple[RepairArtifact, ...]) -> list[str]:
    ids = {artifact.artifact_id for artifact in artifacts}
    dependencies = {
        artifact.artifact_id: set(artifact.depends_on) & ids for artifact in artifacts
    }
    ordered: list[str] = []
    while dependencies:
        ready = sorted(key for key, values in dependencies.items() if not values)
        if not ready:
            raise ValueError("repair dependency graph MUST be acyclic")
        ordered.extend(ready)
        for key in ready:
            dependencies.pop(key)
        for values in dependencies.values():
            values.difference_update(ready)
    return ordered
