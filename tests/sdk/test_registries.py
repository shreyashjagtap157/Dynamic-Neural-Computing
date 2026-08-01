import pytest

from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.kernel.errors import DNCPolicyError, DNCValidationError
from dnc.persistence.object_store import ContentAddressedObjectStore
from dnc.registry import ArtifactRegistry, GraphRegistry


def test_artifact_registry_is_content_addressed_and_descriptor_immutable() -> None:
    registry = ArtifactRegistry()
    first = registry.register(
        b"payload",
        tenant_id="tenant-a",
        media_type="application/json",
        metadata={"kind": "evidence"},
    )
    second = registry.register(
        b"payload",
        tenant_id="tenant-a",
        media_type="application/json",
        metadata={"kind": "evidence"},
    )

    assert first == second
    assert first.content_ref.startswith("sha256:")
    assert registry.get(first.content_ref, tenant_id="tenant-a") == b"payload"
    with pytest.raises(DNCValidationError, match="conflicting descriptor"):
        registry.register(
            b"payload",
            tenant_id="tenant-a",
            media_type="text/plain",
        )


def test_artifact_registry_is_tenant_scoped_and_detects_corruption() -> None:
    store = ContentAddressedObjectStore()
    registry = ArtifactRegistry(store)
    record = registry.register(b"payload", tenant_id="tenant-a")

    with pytest.raises(KeyError, match="tenant-scoped"):
        registry.get(record.content_ref, tenant_id="tenant-b")
    store.corrupt_for_test(
        record.content_ref.removeprefix("sha256:"),
        tenant_id="tenant-a",
        data=b"tampered",
    )
    with pytest.raises(ValueError, match="integrity"):
        registry.get(record.content_ref, tenant_id="tenant-a")


def test_graph_registry_validates_roundtrips_and_enforces_tenant_scope(plain_graph) -> None:
    registry = GraphRegistry()
    record = registry.register(plain_graph, tenant_id="tenant-a")
    restored = registry.load(record.content_ref, tenant_id="tenant-a")

    assert restored.graph_id == plain_graph.graph_id
    assert record.graph_id == plain_graph.graph_id.value
    assert record.schema_version == "1.3.0"
    assert registry.register(plain_graph, tenant_id="tenant-a") == record
    with pytest.raises(KeyError, match="tenant-scoped"):
        registry.load(record.content_ref, tenant_id="tenant-b")


def test_graph_registry_rejects_invalid_graph_before_persistence() -> None:
    graph = StructuralGraph(GraphID("invalid"))
    graph.add_edge(Edge(UnitID("missing-a"), UnitID("missing-b"), EdgeType.DATA))
    registry = GraphRegistry()

    with pytest.raises(DNCValidationError, match="INV_EDGE_SOURCE_MISSING"):
        registry.register(graph, tenant_id="tenant-a")
    assert registry.all(tenant_id="tenant-a") == ()


def test_graph_registry_rejects_non_finite_metadata(plain_graph) -> None:
    plain_graph.metadata["non_finite"] = float("nan")

    with pytest.raises(DNCValidationError, match="finite JSON"):
        GraphRegistry().register(plain_graph, tenant_id="tenant-a")


def test_governed_graph_requires_matching_context_on_register_and_load(
    governed_graph,
    execution_context,
) -> None:
    registry = GraphRegistry()
    with pytest.raises(DNCPolicyError, match="require an ExecutionContext"):
        registry.register(governed_graph, tenant_id="tenant-a")
    with pytest.raises(DNCPolicyError, match="registry tenant"):
        registry.register(
            governed_graph,
            tenant_id="tenant-b",
            context=execution_context,
        )

    record = registry.register(
        governed_graph,
        tenant_id="tenant-a",
        context=execution_context,
    )
    with pytest.raises(DNCPolicyError, match="require an ExecutionContext"):
        registry.load(record.content_ref, tenant_id="tenant-a")
    assert (
        registry.load(
            record.content_ref,
            tenant_id="tenant-a",
            context=execution_context,
        ).graph_id
        == governed_graph.graph_id
    )


def test_graph_registry_revalidates_content_integrity_on_load(plain_graph) -> None:
    store = ContentAddressedObjectStore()
    registry = GraphRegistry(store)
    record = registry.register(plain_graph, tenant_id="tenant-a")
    store.corrupt_for_test(
        record.content_ref.removeprefix("sha256:"),
        tenant_id="tenant-a",
        data=b"{}",
    )

    with pytest.raises(ValueError, match="integrity"):
        registry.load(record.content_ref, tenant_id="tenant-a")
