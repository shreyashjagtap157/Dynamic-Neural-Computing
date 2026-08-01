"""Dependency-aware localized repair and runtime recovery."""

from dnc.repair.analysis import dependency_cut, propagate_stale
from dnc.repair.contracts import (
    ArtifactKind,
    ArtifactValidity,
    DependencyCut,
    FailureSource,
    RepairAction,
    RepairArtifact,
    RepairCandidate,
    RepairOutcome,
    RuntimeFailure,
)
from dnc.repair.engine import (
    cognitive_artifacts,
    execute_localized_repair,
    generate_repair_candidates,
    recovery_action,
)
from dnc.repair.evaluation import RepairEvaluation, evaluate_repair

__all__ = [
    "ArtifactKind",
    "ArtifactValidity",
    "DependencyCut",
    "FailureSource",
    "RepairAction",
    "RepairArtifact",
    "RepairCandidate",
    "RepairEvaluation",
    "RepairOutcome",
    "RuntimeFailure",
    "cognitive_artifacts",
    "dependency_cut",
    "evaluate_repair",
    "execute_localized_repair",
    "generate_repair_candidates",
    "propagate_stale",
    "recovery_action",
]
