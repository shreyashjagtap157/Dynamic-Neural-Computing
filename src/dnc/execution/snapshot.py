"""Snapshot manifests, isolation grades, and reference restore support."""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from dnc.cognition.canonical import canonical_data
from dnc.execution.execution_provider import ExecutionCapability, ExecutionProvider, ProviderResult
from dnc.kernel.errors import DNCCancellationError, DNCCleanupError, DNCExecutionError
from dnc.kernel.contracts import EffectType, IsolationGrade
from dnc.ir.graph import StructuralGraph
from dnc.ir.serialization import DNWIRSerializer


SNAPSHOT_SCHEMA_ID = "dnc.execution.snapshot_manifest"
SNAPSHOT_SCHEMA_VERSION = "0.1.0"


class ReproducibilityGrade(str, Enum):
    """Replay reproducibility grade for a snapshot or execution branch."""

    R0_NONE = "R0_NONE"
    R1_MANIFEST_ONLY = "R1_MANIFEST_ONLY"
    R2_DETERMINISTIC_CORE = "R2_DETERMINISTIC_CORE"
    R3_RECORDED_EXTERNALS = "R3_RECORDED_EXTERNALS"
    R4_ENVIRONMENT_REPLAY = "R4_ENVIRONMENT_REPLAY"


class SharedStateKind(str, Enum):
    """Mutable state source audited before replay or counterfactual execution."""

    GRAPH = "GRAPH"
    RUNTIME_STATE = "RUNTIME_STATE"
    COGNITIVE_STATE = "COGNITIVE_STATE"
    CAPABILITY_REGISTRY = "CAPABILITY_REGISTRY"
    MODEL_PARAMETERS = "MODEL_PARAMETERS"
    OPTIMIZER_STATE = "OPTIMIZER_STATE"
    SAMPLER_STATE = "SAMPLER_STATE"
    COMPILATION_STATE = "COMPILATION_STATE"
    RNG = "RNG"
    PROVIDER_RESPONSES = "PROVIDER_RESPONSES"
    CACHE = "CACHE"
    FILESYSTEM = "FILESYSTEM"
    DATABASE = "DATABASE"
    OBJECT_STORE = "OBJECT_STORE"
    QUEUE = "QUEUE"
    NETWORK = "NETWORK"
    ENVIRONMENT = "ENVIRONMENT"


class SharedStateAccess(str, Enum):
    """Allowed access mode for shared state in speculative execution."""

    ISOLATED = "ISOLATED"
    READ_ONLY = "READ_ONLY"
    RECORDED = "RECORDED"
    SHARED_MUTABLE = "SHARED_MUTABLE"


class ReplayMode(str, Enum):
    """Provider replay mode for deterministic campaigns."""

    LIVE = "LIVE"
    RECORD = "RECORD"
    REPLAY = "REPLAY"
    DENY_LIVE = "DENY_LIVE"


@dataclass(frozen=True)
class SharedStateDeclaration:
    """Declaration of a mutable state source and its isolation mode."""

    state_id: str
    kind: SharedStateKind
    access: SharedStateAccess
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            raise ValueError("state_id MUST be non-empty")
        if not isinstance(self.kind, SharedStateKind):
            raise TypeError("kind MUST be SharedStateKind")
        if not isinstance(self.access, SharedStateAccess):
            raise TypeError("access MUST be SharedStateAccess")


@dataclass(frozen=True)
class SandboxPolicy:
    """Reference sandbox policy for Phase 2 deterministic campaigns."""

    allow_network: bool = False
    writable_roots: tuple[str, ...] = ()
    allow_process_spawn: bool = False
    allow_live_providers: bool = False

    def validate_effect(self, effect: "EffectLedgerEntry") -> None:
        if effect.effect_type is EffectType.NETWORK_CALL and not self.allow_network:
            raise DNCExecutionError("network effects denied by sandbox policy")
        if effect.effect_type is EffectType.PROVIDER_CALL and not self.allow_live_providers:
            raise DNCExecutionError("live provider effects denied by sandbox policy")
        if effect.effect_type is EffectType.FILE_WRITE and not self._target_allowed(effect.target):
            raise DNCExecutionError("file write target denied by sandbox policy")

    def _target_allowed(self, target: str) -> bool:
        if not self.writable_roots:
            return False
        return any(
            target == root.rstrip("/") or target.startswith(f"{root.rstrip('/')}/")
            for root in self.writable_roots
            if root.rstrip("/")
        )


@dataclass(frozen=True)
class EffectLedgerEntry:
    """Declared side effect or cleanup record for a branch."""

    effect_id: str
    effect_type: EffectType
    target: str
    reversible: bool
    committed: bool = False
    compensated_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.effect_id:
            raise ValueError("effect_id MUST be non-empty")
        if not isinstance(self.effect_type, EffectType):
            raise TypeError("effect_type MUST be EffectType")
        if not self.target:
            raise ValueError("target MUST be non-empty")


@dataclass(frozen=True)
class ProviderRecording:
    """Recorded provider response for replayable external calls."""

    recording_id: str
    provider_id: str
    request_hash: str
    response: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.recording_id:
            raise ValueError("recording_id MUST be non-empty")
        if not self.provider_id:
            raise ValueError("provider_id MUST be non-empty")
        if not self.request_hash:
            raise ValueError("request_hash MUST be non-empty")


@dataclass(frozen=True)
class SnapshotManifest:
    """Versioned declaration of captured and uncaptured execution state."""

    snapshot_id: str
    source_state_id: str
    schema_id: str = SNAPSHOT_SCHEMA_ID
    schema_version: str = SNAPSHOT_SCHEMA_VERSION
    reproducibility_grade: ReproducibilityGrade = ReproducibilityGrade.R1_MANIFEST_ONLY
    isolation_grade: IsolationGrade = IsolationGrade.I1_GRAPH_ONLY
    graph_hash: str | None = None
    runtime_state_hash: str | None = None
    rng_state_hash: str | None = None
    provider_recording_ids: tuple[str, ...] = ()
    effect_ids: tuple[str, ...] = ()
    captured_state: tuple[str, ...] = ()
    uncaptured_state: tuple[str, ...] = ()
    cleanup_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id MUST be non-empty")
        if not self.source_state_id:
            raise ValueError("source_state_id MUST be non-empty")
        if not isinstance(self.reproducibility_grade, ReproducibilityGrade):
            raise TypeError("reproducibility_grade MUST be ReproducibilityGrade")
        if not isinstance(self.isolation_grade, IsolationGrade):
            raise TypeError("isolation_grade MUST be IsolationGrade")
        if self.schema_id != SNAPSHOT_SCHEMA_ID:
            raise ValueError("unsupported snapshot schema_id")
        if self.schema_version != SNAPSHOT_SCHEMA_VERSION:
            raise ValueError("unsupported snapshot schema_version")

    def declares_uncaptured_state(self) -> bool:
        """Return whether manifest truthfully declares uncaptured state."""

        return bool(self.uncaptured_state)


@dataclass(frozen=True)
class Snapshot:
    """Captured process-local state plus its manifest."""

    manifest: SnapshotManifest
    graph: StructuralGraph | None = None
    runtime_state: dict[str, Any] | None = None
    provider_recordings: tuple[ProviderRecording, ...] = ()
    effects: tuple[EffectLedgerEntry, ...] = ()


def reject_unsafe_shared_state(declarations: tuple[SharedStateDeclaration, ...]) -> None:
    """Reject shared mutable state before speculative execution."""

    unsafe = [
        declaration
        for declaration in declarations
        if declaration.access is SharedStateAccess.SHARED_MUTABLE
    ]
    if unsafe:
        names = ", ".join(declaration.state_id for declaration in unsafe)
        raise DNCExecutionError(f"shared mutable state is not allowed: {names}")


def default_mutable_state_audit() -> tuple[SharedStateDeclaration, ...]:
    """Return the Phase 2 default mutable-state audit checklist."""

    return (
        SharedStateDeclaration("graph", SharedStateKind.GRAPH, SharedStateAccess.ISOLATED),
        SharedStateDeclaration(
            "runtime_state", SharedStateKind.RUNTIME_STATE, SharedStateAccess.ISOLATED
        ),
        SharedStateDeclaration(
            "cognitive_state", SharedStateKind.COGNITIVE_STATE, SharedStateAccess.ISOLATED
        ),
        SharedStateDeclaration(
            "capability_registry",
            SharedStateKind.CAPABILITY_REGISTRY,
            SharedStateAccess.ISOLATED,
        ),
        SharedStateDeclaration(
            "model_parameters", SharedStateKind.MODEL_PARAMETERS, SharedStateAccess.ISOLATED
        ),
        SharedStateDeclaration(
            "optimizer_state", SharedStateKind.OPTIMIZER_STATE, SharedStateAccess.ISOLATED
        ),
        SharedStateDeclaration(
            "sampler_state", SharedStateKind.SAMPLER_STATE, SharedStateAccess.ISOLATED
        ),
        SharedStateDeclaration(
            "compilation_state", SharedStateKind.COMPILATION_STATE, SharedStateAccess.READ_ONLY
        ),
        SharedStateDeclaration("rng", SharedStateKind.RNG, SharedStateAccess.ISOLATED),
        SharedStateDeclaration(
            "provider_responses", SharedStateKind.PROVIDER_RESPONSES, SharedStateAccess.RECORDED
        ),
        SharedStateDeclaration("cache", SharedStateKind.CACHE, SharedStateAccess.READ_ONLY),
        SharedStateDeclaration("filesystem", SharedStateKind.FILESYSTEM, SharedStateAccess.READ_ONLY),
        SharedStateDeclaration("database", SharedStateKind.DATABASE, SharedStateAccess.READ_ONLY),
        SharedStateDeclaration(
            "object_store", SharedStateKind.OBJECT_STORE, SharedStateAccess.READ_ONLY
        ),
        SharedStateDeclaration("queue", SharedStateKind.QUEUE, SharedStateAccess.READ_ONLY),
        SharedStateDeclaration("network", SharedStateKind.NETWORK, SharedStateAccess.RECORDED),
        SharedStateDeclaration("environment", SharedStateKind.ENVIRONMENT, SharedStateAccess.READ_ONLY),
    )


@dataclass
class CancellationToken:
    """Simple cancellation token used by Phase 2 reference executors."""

    cancelled: bool = False
    reason: str = ""

    def cancel(self, reason: str = "") -> None:
        self.cancelled = True
        self.reason = reason

    def is_cancelled(self) -> bool:
        return self.cancelled

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise DNCCancellationError(self.reason or "operation cancelled")


@dataclass(frozen=True)
class ExecutionDeadline:
    """Wall-clock deadline for reference cancellation propagation."""

    deadline_ns: int

    @staticmethod
    def after_ms(milliseconds: int) -> "ExecutionDeadline":
        if milliseconds < 0:
            raise ValueError("milliseconds MUST be non-negative")
        return ExecutionDeadline(time.monotonic_ns() + milliseconds * 1_000_000)

    def expired(self) -> bool:
        return time.monotonic_ns() >= self.deadline_ns

    def raise_if_expired(self) -> None:
        if self.expired():
            raise DNCCancellationError("execution deadline expired")


@dataclass
class EffectLedger:
    """Idempotent in-memory effect ledger with compensation records."""

    _entries: dict[str, EffectLedgerEntry] = field(default_factory=dict)

    def add(self, entry: EffectLedgerEntry) -> None:
        existing = self._entries.get(entry.effect_id)
        if existing is not None and existing != entry:
            raise DNCExecutionError(f"conflicting effect id {entry.effect_id}")
        self._entries[entry.effect_id] = entry

    def committed(self) -> tuple[EffectLedgerEntry, ...]:
        return tuple(entry for entry in self._entries.values() if entry.committed)

    def uncompensated(self) -> tuple[EffectLedgerEntry, ...]:
        return tuple(
            entry
            for entry in self._entries.values()
            if entry.committed and entry.reversible and entry.compensated_by is None
        )

    def compensate(self, effect_id: str, cleanup_id: str) -> None:
        entry = self._entries[effect_id]
        cleanup = EffectLedgerEntry(
            effect_id=cleanup_id,
            effect_type=EffectType.CLEANUP,
            target=entry.target,
            reversible=False,
            committed=True,
            metadata={"compensates": effect_id},
        )
        self._entries[effect_id] = EffectLedgerEntry(
            effect_id=entry.effect_id,
            effect_type=entry.effect_type,
            target=entry.target,
            reversible=entry.reversible,
            committed=entry.committed,
            compensated_by=cleanup_id,
            metadata=dict(entry.metadata),
        )
        self._entries[cleanup_id] = cleanup

    def all(self) -> tuple[EffectLedgerEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))


class CleanupReconciler:
    """Reference cleanup reconciler for reversible committed effects."""

    def reconcile(self, ledger: EffectLedger) -> tuple[EffectLedgerEntry, ...]:
        for entry in ledger.uncompensated():
            ledger.compensate(entry.effect_id, f"cleanup:{entry.effect_id}")
        remaining = ledger.uncompensated()
        if remaining:
            raise DNCCleanupError("cleanup reconciliation left uncompensated effects")
        return ledger.all()


@dataclass
class IdempotencyRegistry:
    """Tracks idempotency keys and rejects conflicting duplicate effects."""

    _keys: dict[str, str] = field(default_factory=dict)

    def register(self, key: str, payload_hash: str) -> bool:
        if not key:
            raise ValueError("idempotency key MUST be non-empty")
        existing = self._keys.get(key)
        if existing is None:
            self._keys[key] = payload_hash
            return True
        if existing != payload_hash:
            raise DNCExecutionError(f"idempotency key {key} reused with different payload")
        return False


@dataclass
class ProviderReplayStore:
    """In-memory provider recording store."""

    _recordings: dict[str, ProviderRecording] = field(default_factory=dict)

    def add(self, recording: ProviderRecording) -> None:
        existing = self._recordings.get(recording.request_hash)
        if existing is not None and existing != recording:
            raise DNCExecutionError("conflicting provider recording for request hash")
        self._recordings[recording.request_hash] = recording

    def get(self, request_hash_value: str) -> ProviderRecording | None:
        return self._recordings.get(request_hash_value)

    def all(self) -> tuple[ProviderRecording, ...]:
        return tuple(self._recordings[key] for key in sorted(self._recordings))


class RecordingExecutionProvider:
    """ExecutionProvider wrapper that records, replays, or denies live calls."""

    def __init__(
        self,
        provider: ExecutionProvider,
        store: ProviderReplayStore,
        mode: ReplayMode = ReplayMode.RECORD,
    ) -> None:
        self.provider = provider
        self.store = store
        self.mode = mode

    @property
    def provider_id(self) -> str:
        return self.provider.provider_id

    @property
    def provider_version(self) -> str:
        return self.provider.provider_version

    @property
    def provider_metadata(self):
        return self.provider.provider_metadata

    def supports(self, capability: ExecutionCapability) -> bool:
        return self.provider.supports(capability)

    def get_capabilities(self):
        return self.provider.get_capabilities()

    def execute(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: dict[str, Any] | None = None,
    ) -> ProviderResult:
        req_hash = request_hash(
            self.provider_id,
            capability.name,
            {"input": input, "config": config or {}},
        )
        recording = self.store.get(req_hash)
        if self.mode is ReplayMode.REPLAY:
            if recording is None:
                return ProviderResult(
                    capability=capability,
                    output=None,
                    provider_id=self.provider_id,
                    latency_ms=0.0,
                    error=f"no provider recording for request {req_hash}",
                    metadata={"request_hash": req_hash, "replay": True},
                )
            return ProviderResult(
                capability=capability,
                output=copy.deepcopy(recording.response),
                provider_id=self.provider_id,
                latency_ms=0.0,
                metadata={"request_hash": req_hash, "replay": True},
            )
        if self.mode is ReplayMode.DENY_LIVE:
            return ProviderResult(
                capability=capability,
                output=None,
                provider_id=self.provider_id,
                latency_ms=0.0,
                error="live provider call denied by replay policy",
                metadata={"request_hash": req_hash},
            )
        result = self.provider.execute(capability, input, config)
        if self.mode is ReplayMode.RECORD and result.is_success:
            self.store.add(
                ProviderRecording(
                    recording_id=f"rec:{req_hash}",
                    provider_id=self.provider_id,
                    request_hash=req_hash,
                    response=copy.deepcopy(result.output),
                    metadata={"capability": capability.name},
                )
            )
        return result

    def estimate_cost(self, capability: ExecutionCapability, input: Any):
        return self.provider.estimate_cost(capability, input)


class ReferenceSnapshotManager:
    """Process-local snapshot manager for deterministic reference branches."""

    def capture_graph(
        self,
        graph: StructuralGraph,
        *,
        snapshot_id: str,
        source_state_id: str,
        runtime_state: dict[str, Any] | None = None,
    ) -> Snapshot:
        """Capture graph and optional runtime state without external effects."""

        graph_json = DNWIRSerializer.to_json(graph)
        runtime_hash = _hash_json(runtime_state) if runtime_state is not None else None
        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            source_state_id=source_state_id,
            reproducibility_grade=ReproducibilityGrade.R2_DETERMINISTIC_CORE,
            isolation_grade=IsolationGrade.I1_GRAPH_ONLY,
            graph_hash=_hash_text(graph_json),
            runtime_state_hash=runtime_hash,
            captured_state=("graph",) + (("runtime_state",) if runtime_state is not None else ()),
            uncaptured_state=(
                "provider_responses",
                "filesystem",
                "database",
                "network",
                "accelerator",
                "process_environment",
            ),
            cleanup_required=False,
        )
        return Snapshot(
            manifest=manifest,
            graph=copy.deepcopy(graph),
            runtime_state=copy.deepcopy(runtime_state),
        )

    def restore_graph(self, snapshot: Snapshot) -> StructuralGraph:
        """Restore a graph from a process-local snapshot."""

        if snapshot.graph is None:
            raise ValueError("snapshot does not include graph state")
        restored = copy.deepcopy(snapshot.graph)
        restored_hash = _hash_text(DNWIRSerializer.to_json(restored))
        if restored_hash != snapshot.manifest.graph_hash:
            raise ValueError("snapshot graph hash mismatch")
        expected_runtime_hash = snapshot.manifest.runtime_state_hash
        actual_runtime_hash = (
            _hash_json(snapshot.runtime_state) if snapshot.runtime_state is not None else None
        )
        if actual_runtime_hash != expected_runtime_hash:
            raise ValueError("snapshot runtime state hash mismatch")
        return restored


def run_with_guards(
    operation: Callable[[], Any],
    *,
    token: CancellationToken | None = None,
    deadline: ExecutionDeadline | None = None,
) -> Any:
    """Run an operation after checking cancellation and deadline guards."""

    if token is not None:
        token.raise_if_cancelled()
    if deadline is not None:
        deadline.raise_if_expired()
    result = operation()
    if token is not None:
        token.raise_if_cancelled()
    if deadline is not None:
        deadline.raise_if_expired()
    return result


def request_hash(provider_id: str, capability: str, payload: Any) -> str:
    """Return a stable request hash for provider recording/replay."""

    return _hash_json(
        {
            "provider_id": provider_id,
            "capability": capability,
            "payload": payload,
        }
    )


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_json(value: Any) -> str:
    return _hash_text(json.dumps(canonical_data(value), sort_keys=True, separators=(",", ":")))
