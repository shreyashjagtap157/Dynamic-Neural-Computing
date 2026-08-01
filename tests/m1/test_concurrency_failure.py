"""Thread-concurrency and injected-failure coverage for M1 authorities."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from dnc.ir.contracts import SideEffectContract
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass
from dnc.kernel.errors import DNCCapabilityError, DNCValidationError
from dnc.mutation.engine import MutationEngine
from dnc.persistence.object_store import ContentAddressedObjectStore
from dnc.plugins import PluginLoadPolicy, PluginManifest, PluginRegistry
from dnc.registry import ArtifactRegistry, GraphRegistry
from dnc.transaction.context import TransactionState
from dnc.transaction.manager import TransactionManager


def _unit(unit_id: str) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )


def _graph() -> StructuralGraph:
    return StructuralGraph(
        GraphID("concurrent-graph"),
        units={"base": _unit("base")},
    )


def _manifest() -> PluginManifest:
    return PluginManifest(
        plugin_id="concurrent.plugin",
        plugin_version="1.0.0",
        entry_point="concurrent_plugin:create",
        capabilities=frozenset({"provider"}),
    )


def test_content_and_descriptor_registries_are_safe_under_concurrent_access() -> None:
    store = ContentAddressedObjectStore()
    artifacts = ArtifactRegistry(store)
    payloads = [f"payload-{index % 8}".encode() for index in range(64)]

    def register(payload: bytes):
        record = artifacts.register(payload, tenant_id="tenant-a", media_type="text/plain")
        assert artifacts.get(record.content_ref, tenant_id="tenant-a") == payload
        return record.content_ref

    with ThreadPoolExecutor(max_workers=12) as executor:
        references = tuple(executor.map(register, payloads))

    assert len(set(references)) == 8
    assert len(artifacts.all(tenant_id="tenant-a")) == 8
    assert len(store.snapshot()) == 8


def test_graph_and_plugin_reads_are_safe_under_concurrent_access() -> None:
    graph_registry = GraphRegistry()
    graph = _graph()

    with ThreadPoolExecutor(max_workers=8) as executor:
        records = tuple(
            executor.map(
                lambda _: graph_registry.register(graph, tenant_id="tenant-a"),
                range(32),
            )
        )
    assert len({record.content_ref for record in records}) == 1
    reference = records[0].content_ref

    with ThreadPoolExecutor(max_workers=8) as executor:
        loaded = tuple(
            executor.map(
                lambda _: graph_registry.load(reference, tenant_id="tenant-a"),
                range(32),
            )
        )
    assert all(item.graph_id == graph.graph_id for item in loaded)

    manifest = _manifest()
    plugins = PluginRegistry(PluginLoadPolicy.trust(manifest))
    plugins.register(manifest)

    class Plugin:
        def __init__(self) -> None:
            self.manifest = manifest

        def activate(self, runtime: object) -> None:
            self.runtime = runtime

    with ThreadPoolExecutor(max_workers=8) as executor:
        instances = tuple(
            executor.map(
                lambda _: plugins.load(
                    manifest.plugin_id,
                    resolver=lambda entry_point: Plugin,
                ),
                range(32),
            )
        )
    assert all(instance.manifest == manifest for instance in instances)


def test_concurrent_transactions_with_one_base_version_have_one_winner() -> None:
    graph = StructuralGraph(GraphID("concurrent-transaction"), GraphVersion())
    base_version = graph.version

    def transact(index: int):
        return TransactionManager().execute_transaction(
            graph,
            [IROperation(OperationType.ADD_UNIT, {"unit": _unit(f"unit-{index}")})],
            base_version=base_version,
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = tuple(executor.map(transact, range(24)))

    assert sum(success for success, _ in results) == 1
    assert len(graph.units) == 1
    assert graph.version.sequence == 1
    assert sum(context.state is TransactionState.FAILED for _, context in results) == 23


class _RollbackFailureEngine(MutationEngine):
    def rollback(self, graph, undo_log) -> None:
        raise RuntimeError("injected rollback failure")


def test_staging_rollback_failure_is_reported_without_active_graph_mutation() -> None:
    graph = StructuralGraph(GraphID("rollback-failure"))
    before = DNWIRSerializer.to_json(graph)
    invalid = _unit("invalid")
    invalid.contract.side_effects = SideEffectContract(
        SideEffectClass.COMPENSATABLE,
        frozenset({EffectType.FILE_WRITE}),
        "delete-file",
        IsolationGrade.I2_PROCESS_LOCAL,
    )

    success, context = TransactionManager(
        mutation_engine=_RollbackFailureEngine()
    ).execute_transaction(
        graph,
        [IROperation(OperationType.ADD_UNIT, {"unit": invalid})],
    )

    assert not success
    assert context.state is TransactionState.FAILED
    assert "staging rollback failed: injected rollback failure" in context.error_message
    assert DNWIRSerializer.to_json(graph) == before


class _PutFailureStore(ContentAddressedObjectStore):
    def put(self, data: bytes, *, tenant_id: str) -> str:
        raise OSError("injected put failure")


class _MalformedDigestStore(ContentAddressedObjectStore):
    def put(self, data: bytes, *, tenant_id: str) -> str:
        return "not-a-sha256-digest"


class _MalformedReadStore(ContentAddressedObjectStore):
    malformed = False

    def get(self, digest: str, *, tenant_id: str) -> bytes:
        if self.malformed:
            return b"{not-json"
        return super().get(digest, tenant_id=tenant_id)


@pytest.mark.parametrize("registry_factory", [ArtifactRegistry, GraphRegistry])
def test_registry_put_failures_leave_no_descriptor(registry_factory) -> None:
    registry = registry_factory(_PutFailureStore())
    with pytest.raises(OSError, match="injected put failure"):
        if isinstance(registry, ArtifactRegistry):
            registry.register(b"payload", tenant_id="tenant-a")
        else:
            registry.register(_graph(), tenant_id="tenant-a")
    assert registry.all(tenant_id="tenant-a") == ()


@pytest.mark.parametrize("registry_factory", [ArtifactRegistry, GraphRegistry])
def test_registry_rejects_malformed_backend_digest(registry_factory) -> None:
    registry = registry_factory(_MalformedDigestStore())
    with pytest.raises(DNCValidationError, match="sha256"):
        if isinstance(registry, ArtifactRegistry):
            registry.register(b"payload", tenant_id="tenant-a")
        else:
            registry.register(_graph(), tenant_id="tenant-a")
    assert registry.all(tenant_id="tenant-a") == ()


def test_graph_registry_wraps_malformed_storage_reads() -> None:
    store = _MalformedReadStore()
    registry = GraphRegistry(store)
    record = registry.register(_graph(), tenant_id="tenant-a")
    store.malformed = True

    with pytest.raises(DNCValidationError, match="valid DNC-IR JSON"):
        registry.load(record.content_ref, tenant_id="tenant-a")


def test_invalid_object_store_restore_is_atomic() -> None:
    store = ContentAddressedObjectStore()
    digest = store.put(b"original", tenant_id="tenant-a")
    before = store.snapshot()

    with pytest.raises(ValueError, match="integrity"):
        store.restore({("tenant-a", "0" * 64): b"tampered"})

    assert store.snapshot() == before
    assert store.get(digest, tenant_id="tenant-a") == b"original"


def test_plugin_resolution_and_factory_failures_use_capability_taxonomy() -> None:
    manifest = _manifest()
    registry = PluginRegistry(PluginLoadPolicy.trust(manifest))
    registry.register(manifest)

    def resolution_failure(entry_point: str):
        raise ImportError("injected import failure")

    def factory_failure():
        raise RuntimeError("injected factory failure")

    with pytest.raises(DNCCapabilityError, match="resolution failed"):
        registry.load(manifest.plugin_id, resolver=resolution_failure)
    with pytest.raises(DNCCapabilityError, match="factory failed"):
        registry.load(manifest.plugin_id, resolver=lambda entry_point: factory_failure)

    class BrokenContract:
        @property
        def manifest(self):
            raise RuntimeError("injected inspection failure")

        def activate(self, runtime: object) -> None:
            pass

    with pytest.raises(DNCCapabilityError, match="inspection failed"):
        registry.load(
            manifest.plugin_id,
            resolver=lambda entry_point: BrokenContract,
        )
    assert registry.manifest(manifest.plugin_id) == manifest


def test_non_operation_transaction_entry_rolls_back_without_raising() -> None:
    graph = StructuralGraph(GraphID("invalid-operation-entry"))
    before = DNWIRSerializer.to_json(graph)

    success, context = TransactionManager().execute_transaction(
        graph,
        [IROperation(OperationType.ADD_UNIT, {"unit": _unit("staged")}), object()],
    )

    assert not success
    assert context.state is TransactionState.ROLLED_BACK
    assert "Operation validation failed" in context.error_message
    assert DNWIRSerializer.to_json(graph) == before
