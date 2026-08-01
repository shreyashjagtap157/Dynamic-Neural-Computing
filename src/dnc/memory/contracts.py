"""Governed memory and reusable-skill contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.cognition.canonical import canonical_hash


class MemoryKind(str, Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    CALIBRATION = "CALIBRATION"
    AUDIT = "AUDIT"


class SkillLifecycle(str, Enum):
    DRAFT = "DRAFT"
    SANDBOXED = "SANDBOXED"
    EVALUATED = "EVALUATED"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    kind: MemoryKind
    tenant_id: str
    content: Any
    provenance: tuple[str, ...]
    security_labels: frozenset[str] = frozenset()
    trust: float = 0.0
    created_at_ns: int = 0
    expires_at_ns: int | None = None
    legal_hold: bool = False
    dependencies: tuple[str, ...] = ()
    domain: str = "general"
    model_fingerprint: str | None = None
    policy_fingerprint: str | None = None
    integrity_verified: bool = False
    deleted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.record_id or not self.tenant_id or not self.provenance:
            raise ValueError("memory identity, tenant, and provenance MUST be non-empty")
        if not 0 <= self.trust <= 1:
            raise ValueError("memory trust MUST be between 0 and 1")
        if self.expires_at_ns is not None and self.expires_at_ns < self.created_at_ns:
            raise ValueError("memory expiry MUST not precede creation")


@dataclass(frozen=True)
class Episode:
    episode_id: str
    tenant_id: str
    task_fingerprint: str
    actions: tuple[str, ...]
    outcome: float
    verified: bool
    evidence_ids: tuple[str, ...]
    negative: bool = False


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    version: str
    tenant_id: str
    name: str
    procedure: tuple[str, ...]
    permissions: frozenset[str]
    domains: frozenset[str]
    source_episode_ids: tuple[str, ...]
    negative_episode_ids: tuple[str, ...]
    lifecycle: SkillLifecycle = SkillLifecycle.DRAFT
    dependency_fingerprints: frozenset[str] = frozenset()
    evaluation_artifact_ids: tuple[str, ...] = ()
    parent_version: str | None = None
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not all((self.skill_id, self.version, self.tenant_id, self.name)):
            raise ValueError("skill identity fields MUST be non-empty")
        if not self.procedure or not self.source_episode_ids:
            raise ValueError("skill MUST have a procedure and verified source episodes")
        expected = canonical_hash(
            {
                "skill_id": self.skill_id,
                "version": self.version,
                "tenant_id": self.tenant_id,
                "procedure": self.procedure,
                "permissions": self.permissions,
                "domains": self.domains,
                "source_episode_ids": self.source_episode_ids,
                "negative_episode_ids": self.negative_episode_ids,
                "dependency_fingerprints": self.dependency_fingerprints,
            },
            namespace="dnc.memory.skill.v1",
        )
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("skill fingerprint does not match manifest content")
        object.__setattr__(self, "fingerprint", expected)


@dataclass(frozen=True)
class SkillEvaluation:
    artifact_id: str
    skill_fingerprint: str
    held_out_tasks: int
    baseline_success: float
    skill_success: float
    harmful_transfer_rate: float
    poisoning_detection_rate: float
    permission_violations: int = 0

    @property
    def promotable(self) -> bool:
        return (
            self.held_out_tasks > 0
            and self.skill_success > self.baseline_success
            and self.harmful_transfer_rate <= 0.05
            and self.poisoning_detection_rate >= 0.95
            and self.permission_violations == 0
        )


@dataclass(frozen=True)
class CompressionResult:
    record: MemoryRecord
    source_ids: tuple[str, ...]
    preserved_ids: tuple[str, ...]
    information_loss: float
