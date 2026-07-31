import pytest

from dnc.execution.snapshot import (
    CancellationToken,
    CleanupReconciler,
    EffectLedger,
    EffectLedgerEntry,
    EffectType,
    ExecutionDeadline,
    IdempotencyRegistry,
    IsolationGrade,
    ProviderReplayStore,
    RecordingExecutionProvider,
    ReferenceSnapshotManager,
    ReproducibilityGrade,
    ReplayMode,
    SandboxPolicy,
    SharedStateAccess,
    SharedStateDeclaration,
    SharedStateKind,
    SnapshotManifest,
    default_mutable_state_audit,
    reject_unsafe_shared_state,
    request_hash,
    run_with_guards,
)
from dnc import DNCSystem
from dnc.execution.execution_provider import ExecutionCapability, ReferenceExecutionProvider
from dnc.kernel.errors import DNCCancellationError, DNCExecutionError
from dnc.execution.torch_snapshot import PyTorchSnapshotManager, torch_available
from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)


def _unit(unit_id: str) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )


def _graph() -> StructuralGraph:
    graph = StructuralGraph(GraphID("snapshot_graph"), GraphVersion(1, 0, 0, 0))
    graph.add_unit(_unit("u1"))
    graph.add_unit(_unit("u2"))
    graph.add_edge(Edge(UnitID("u1"), UnitID("u2"), EdgeType.DATA))
    return graph


def test_snapshot_manifest_declares_grades_and_uncaptured_state() -> None:
    manifest = SnapshotManifest(
        snapshot_id="snap-1",
        source_state_id="state-1",
        reproducibility_grade=ReproducibilityGrade.R2_DETERMINISTIC_CORE,
        isolation_grade=IsolationGrade.I2_PROCESS_LOCAL,
        uncaptured_state=("network",),
    )

    assert manifest.declares_uncaptured_state()
    assert manifest.schema_id == "dnc.execution.snapshot_manifest"


def test_reference_snapshot_restore_preserves_graph_and_source_can_diverge() -> None:
    graph = _graph()
    manager = ReferenceSnapshotManager()
    snapshot = manager.capture_graph(
        graph,
        snapshot_id="snap-1",
        source_state_id="state-1",
        runtime_state={"cycle": 3},
    )

    graph.add_unit(_unit("u3"))
    restored = manager.restore_graph(snapshot)

    assert "u3" in graph.units
    assert "u3" not in restored.units
    assert DNWIRSerializer.to_json(restored) == DNWIRSerializer.to_json(snapshot.graph)
    assert snapshot.manifest.isolation_grade is IsolationGrade.I2_PROCESS_LOCAL
    assert snapshot.manifest.reproducibility_grade is ReproducibilityGrade.R2_DETERMINISTIC_CORE


def test_effect_ledger_entry_tracks_reversibility_and_commit_state() -> None:
    effect = EffectLedgerEntry(
        effect_id="effect-1",
        effect_type=EffectType.FILE_WRITE,
        target="artifact://candidate-output",
        reversible=True,
        committed=False,
    )

    assert effect.reversible is True
    assert effect.committed is False


def test_request_hash_is_stable_for_equivalent_payloads() -> None:
    first = request_hash("provider", "CAP_REASONING", {"b": 2, "a": 1})
    second = request_hash("provider", "CAP_REASONING", {"a": 1, "b": 2})

    assert first == second


def test_dnc_system_can_capture_and_restore_process_local_snapshot() -> None:
    system = DNCSystem(execution_id="phase2")
    snapshot = system.capture_execution_snapshot("snap-system-1")

    system.graph.add_unit(_unit("after_snapshot"))
    assert "after_snapshot" in system.graph.units

    system.restore_execution_snapshot(snapshot)

    assert "after_snapshot" not in system.graph.units
    assert snapshot.manifest.graph_hash is not None
    assert snapshot.manifest.declares_uncaptured_state()


def test_recording_provider_records_and_replays_without_live_call() -> None:
    store = ProviderReplayStore()
    provider = RecordingExecutionProvider(
        ReferenceExecutionProvider(capabilities={ExecutionCapability.CAP_REASONING}),
        store,
        mode=ReplayMode.RECORD,
    )

    live = provider.execute(ExecutionCapability.CAP_REASONING, "hello", {"temperature": 0})
    replay = RecordingExecutionProvider(provider.provider, store, mode=ReplayMode.REPLAY).execute(
        ExecutionCapability.CAP_REASONING,
        "hello",
        {"temperature": 0},
    )

    assert live.is_success
    assert replay.is_success
    assert replay.output == live.output
    assert replay.metadata["replay"] is True


def test_replay_mode_rejects_missing_recording() -> None:
    replay = RecordingExecutionProvider(
        ReferenceExecutionProvider(capabilities={ExecutionCapability.CAP_REASONING}),
        ProviderReplayStore(),
        mode=ReplayMode.REPLAY,
    ).execute(ExecutionCapability.CAP_REASONING, "missing")

    assert replay.is_success is False
    assert "no provider recording" in replay.error


def test_deny_live_mode_blocks_provider_call() -> None:
    result = RecordingExecutionProvider(
        ReferenceExecutionProvider(capabilities={ExecutionCapability.CAP_REASONING}),
        ProviderReplayStore(),
        mode=ReplayMode.DENY_LIVE,
    ).execute(ExecutionCapability.CAP_REASONING, "blocked")

    assert result.is_success is False
    assert result.error == "live provider call denied by replay policy"


def test_effect_ledger_and_cleanup_reconciler_compensate_reversible_effects() -> None:
    ledger = EffectLedger()
    ledger.add(
        EffectLedgerEntry(
            effect_id="write-1",
            effect_type=EffectType.FILE_WRITE,
            target="artifact://tmp",
            reversible=True,
            committed=True,
        )
    )

    entries = CleanupReconciler().reconcile(ledger)

    assert not ledger.uncompensated()
    assert any(entry.effect_type is EffectType.CLEANUP for entry in entries)


def test_effect_ledger_rejects_conflicting_duplicate_effect_ids() -> None:
    ledger = EffectLedger()
    ledger.add(
        EffectLedgerEntry("effect-1", EffectType.FILE_WRITE, "artifact://a", True)
    )

    try:
        ledger.add(
            EffectLedgerEntry("effect-1", EffectType.FILE_WRITE, "artifact://b", True)
        )
    except DNCExecutionError as exc:
        assert "conflicting effect id" in str(exc)
    else:
        raise AssertionError("conflicting duplicate effect id must fail")


def test_idempotency_registry_rejects_conflicting_payload_reuse() -> None:
    registry = IdempotencyRegistry()

    assert registry.register("key-1", "hash-a") is True
    assert registry.register("key-1", "hash-a") is False

    try:
        registry.register("key-1", "hash-b")
    except DNCExecutionError as exc:
        assert "reused with different payload" in str(exc)
    else:
        raise AssertionError("conflicting idempotency key reuse must fail")


def test_cancellation_and_deadline_guards_fail_before_work() -> None:
    token = CancellationToken(cancelled=True, reason="user stop")

    try:
        run_with_guards(lambda: "never", token=token)
    except DNCCancellationError as exc:
        assert "user stop" in str(exc)
    else:
        raise AssertionError("cancelled operation must fail")

    expired = ExecutionDeadline.after_ms(0)
    try:
        run_with_guards(lambda: "maybe", deadline=expired)
    except DNCCancellationError:
        pass
    else:
        raise AssertionError("expired deadline must fail")


def test_failed_restore_does_not_mutate_active_system_graph() -> None:
    system = DNCSystem(execution_id="restore-fail")
    snapshot = system.capture_execution_snapshot("snap-bad")
    bad_manifest = SnapshotManifest(
        snapshot_id=snapshot.manifest.snapshot_id,
        source_state_id=snapshot.manifest.source_state_id,
        reproducibility_grade=snapshot.manifest.reproducibility_grade,
        isolation_grade=snapshot.manifest.isolation_grade,
        graph_hash="bad-hash",
    )
    bad_snapshot = type(snapshot)(
        manifest=bad_manifest,
        graph=snapshot.graph,
        runtime_state=snapshot.runtime_state,
    )
    before = DNWIRSerializer.to_json(system.graph)

    try:
        system.restore_execution_snapshot(bad_snapshot)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("bad snapshot restore must fail")

    assert DNWIRSerializer.to_json(system.graph) == before


def test_shared_mutable_state_is_rejected() -> None:
    declarations = (
        SharedStateDeclaration("cache", SharedStateKind.CACHE, SharedStateAccess.SHARED_MUTABLE),
    )

    try:
        reject_unsafe_shared_state(declarations)
    except DNCExecutionError as exc:
        assert "shared mutable state" in str(exc)
    else:
        raise AssertionError("shared mutable state must be rejected")


def test_default_mutable_state_audit_has_no_shared_mutable_entries() -> None:
    declarations = default_mutable_state_audit()

    reject_unsafe_shared_state(declarations)
    assert {declaration.kind for declaration in declarations} >= {
        SharedStateKind.GRAPH,
        SharedStateKind.RNG,
        SharedStateKind.PROVIDER_RESPONSES,
        SharedStateKind.FILESYSTEM,
        SharedStateKind.DATABASE,
        SharedStateKind.NETWORK,
        SharedStateKind.MODEL_PARAMETERS,
        SharedStateKind.OPTIMIZER_STATE,
        SharedStateKind.SAMPLER_STATE,
        SharedStateKind.COMPILATION_STATE,
        SharedStateKind.OBJECT_STORE,
        SharedStateKind.QUEUE,
    }


def test_sandbox_policy_denies_network_live_provider_and_disallowed_file_write() -> None:
    policy = SandboxPolicy(writable_roots=("artifact://allowed/",))

    for effect in (
        EffectLedgerEntry("net", EffectType.NETWORK_CALL, "https://example.test", False),
        EffectLedgerEntry("provider", EffectType.PROVIDER_CALL, "provider://openai", False),
        EffectLedgerEntry("file", EffectType.FILE_WRITE, "artifact://denied/out", True),
    ):
        try:
            policy.validate_effect(effect)
        except DNCExecutionError:
            pass
        else:
            raise AssertionError(f"{effect.effect_type} should be denied")

    policy.validate_effect(
        EffectLedgerEntry("allowed-file", EffectType.FILE_WRITE, "artifact://allowed/out", True)
    )
    with pytest.raises(DNCExecutionError):
        SandboxPolicy(writable_roots=("artifact://allowed",)).validate_effect(
            EffectLedgerEntry(
                "confusable-file", EffectType.FILE_WRITE, "artifact://allowed-evil/out", True
            )
        )


def test_pytorch_snapshot_manager_reports_unavailable_when_torch_missing() -> None:
    if torch_available():
        import torch

        manager = PyTorchSnapshotManager()
        module = torch.nn.Linear(2, 1)
        optimizer = torch.optim.SGD(module.parameters(), lr=0.1)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1)

        class Sampler:
            position = 7

        sampler = Sampler()
        snapshot = manager.capture_module(
            module,
            optimizer=optimizer,
            scheduler=scheduler,
            sampler=sampler,
            code_fingerprint="code-v1",
            config_fingerprint="config-v1",
        )
        with torch.no_grad():
            module.weight.add_(1)
        sampler.position = 99
        manager.restore_module(
            module,
            snapshot,
            optimizer=optimizer,
            scheduler=scheduler,
            sampler=sampler,
        )
        assert snapshot.cpu_rng_state is not None
        assert sampler.position == 7
        assert snapshot.optimizer_state is not None
        assert snapshot.scheduler_state is not None
    else:
        try:
            PyTorchSnapshotManager()
        except RuntimeError as exc:
            assert "not installed" in str(exc)
        else:
            raise AssertionError("PyTorchSnapshotManager must report missing torch")
