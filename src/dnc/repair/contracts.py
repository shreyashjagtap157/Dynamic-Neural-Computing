"""Dependency cuts, repair candidates, recovery, and outcome contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArtifactKind(str, Enum):
    CLAIM = "CLAIM"
    PLAN = "PLAN"
    ACTION = "ACTION"
    OUTPUT = "OUTPUT"
    MEMORY = "MEMORY"
    SKILL = "SKILL"


class ArtifactValidity(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class RepairArtifact:
    artifact_id: str
    kind: ArtifactKind
    depends_on: tuple[str, ...] = ()
    validity: ArtifactValidity = ArtifactValidity.CURRENT
    payload: Any = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("repair artifact_id MUST be non-empty")
        if self.artifact_id in self.depends_on:
            raise ValueError("repair artifacts MUST NOT depend on themselves")


@dataclass(frozen=True)
class DependencyCut:
    root_ids: tuple[str, ...]
    affected_ids: tuple[str, ...]
    unaffected_ids: tuple[str, ...]
    topological_order: tuple[str, ...]


class RepairAction(str, Enum):
    LOCAL_REPAIR = "LOCAL_REPAIR"
    ROLLBACK = "ROLLBACK"
    RECOMPUTE = "RECOMPUTE"
    ASK = "ASK"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class RepairCandidate:
    candidate_id: str
    action: RepairAction
    target_ids: tuple[str, ...]
    rationale: str
    estimated_cost: float
    preserves_unaffected: bool
    requires_input: bool = False


@dataclass(frozen=True)
class RepairOutcome:
    success: bool
    action: RepairAction
    affected_ids: tuple[str, ...]
    reverified_ids: tuple[str, ...]
    preserved_ids: tuple[str, ...]
    snapshot_id: str
    reason_codes: tuple[str, ...]
    avoided_recomputation: int = 0


class FailureSource(str, Enum):
    WORKER = "WORKER"
    PROVIDER = "PROVIDER"
    TOOL = "TOOL"


@dataclass(frozen=True)
class RuntimeFailure:
    failure_id: str
    source: FailureSource
    retryable: bool
    state_corrupted: bool
    input_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
