import pytest

from dnc.cognition.contracts import SideEffectClass as CognitionSideEffectClass
from dnc.execution.snapshot import EffectType as SnapshotEffectType
from dnc.execution.snapshot import IsolationGrade as SnapshotIsolationGrade
from dnc.ir.contracts import (
    DataClassification,
    ExecutionContext,
    IdempotencyContract,
    IdempotencyMode,
    PlacementContract,
    PortContract,
    PortDirection,
    PortKind,
    SecurityContract,
    SideEffectContract,
)
from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    UnitContract,
    VisibilityDimension,
)
from dnc.ir.validator import DNCIRValidator
from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass
from dnc.projection.projector import StructuralProjector


SCHEMA = {"type": "string"}


def _unit(unit_id: str, contract: UnitContract | None = None) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
        contract=contract or UnitContract(),
    )


def _port(port_id: str, direction: PortDirection) -> PortContract:
    return PortContract(port_id, direction, PortKind.DATA, SCHEMA)


def _codes(graph: StructuralGraph) -> set[str]:
    return {error.code for error in DNCIRValidator().validate_graph(graph).errors}


def test_shared_effect_and_isolation_enums_keep_compatibility_imports() -> None:
    assert CognitionSideEffectClass is SideEffectClass
    assert SnapshotIsolationGrade is IsolationGrade
    assert SnapshotEffectType is EffectType


def test_effect_contracts_require_compensation_isolation_and_idempotency() -> None:
    with pytest.raises(ValueError, match="I0_NONE"):
        SideEffectContract(minimum_isolation=IsolationGrade.I1_GRAPH_ONLY)
    with pytest.raises(ValueError, match="cannot declare key_field"):
        IdempotencyContract(IdempotencyMode.NONE, key_field="request_id")
    with pytest.raises(ValueError, match="compensation_action"):
        SideEffectContract(
            SideEffectClass.REVERSIBLE,
            frozenset({EffectType.FILE_WRITE}),
            minimum_isolation=IsolationGrade.I2_PROCESS_LOCAL,
        )
    with pytest.raises(ValueError, match="recorded-external"):
        SideEffectContract(
            SideEffectClass.IRREVERSIBLE,
            frozenset({EffectType.DATABASE_WRITE}),
            minimum_isolation=IsolationGrade.I2_PROCESS_LOCAL,
        )

    effect = SideEffectContract(
        SideEffectClass.COMPENSATABLE,
        frozenset({EffectType.FILE_WRITE}),
        "delete-created-file",
        IsolationGrade.I2_PROCESS_LOCAL,
    )
    graph = StructuralGraph(
        GraphID("effect"),
        units={"effect": _unit("effect", UnitContract(side_effects=effect))},
    )
    assert "INV_EFFECT_IDEMPOTENCY_REQUIRED" in _codes(graph)


def test_irreversible_effect_requires_strong_duplication_control() -> None:
    effect = SideEffectContract(
        SideEffectClass.IRREVERSIBLE,
        frozenset({EffectType.DATABASE_WRITE}),
        minimum_isolation=IsolationGrade.I3_RECORDED_EXTERNALS,
    )
    graph = StructuralGraph(
        GraphID("irreversible"),
        units={
            "irreversible": _unit(
                "irreversible",
                UnitContract(
                    side_effects=effect,
                    idempotency=IdempotencyContract(IdempotencyMode.IDEMPOTENT),
                ),
            )
        },
    )
    assert "INV_IRREVERSIBLE_EFFECT_DUPLICATION_CONTROL" in _codes(graph)


def test_cross_edge_security_and_locality_conflicts_fail_closed() -> None:
    source = _unit(
        "source",
        UnitContract(
            ports=[_port("out", PortDirection.OUTPUT)],
            placement=PlacementContract(
                allowed_regions=frozenset({"IN"}),
                allowed_devices=frozenset({"cpu"}),
            ),
            security=SecurityContract(
                tenant_id="tenant-a",
                output_classification=DataClassification.RESTRICTED,
                allowed_residencies=frozenset({"IN"}),
                trust_zone="trusted-a",
            ),
        ),
    )
    target = _unit(
        "target",
        UnitContract(
            ports=[_port("in", PortDirection.INPUT)],
            placement=PlacementContract(
                allowed_regions=frozenset({"US"}),
                allowed_devices=frozenset({"gpu"}),
                requires_local_inputs=True,
            ),
            security=SecurityContract(
                tenant_id="tenant-b",
                maximum_input_classification=DataClassification.CONFIDENTIAL,
                allowed_residencies=frozenset({"US"}),
                accepted_trust_zones=frozenset({"trusted-b"}),
            ),
        ),
    )
    graph = StructuralGraph(GraphID("security"))
    graph.add_unit(source)
    graph.add_unit(target)
    graph.add_edge(
        Edge(
            source.unit_id,
            target.unit_id,
            EdgeType.DATA,
            source_port="out",
            target_port="in",
        )
    )

    assert {
        "INV_EDGE_TENANT_MISMATCH",
        "INV_EDGE_CLASSIFICATION_DOWNGRADE",
        "INV_EDGE_RESIDENCY_CONFLICT",
        "INV_EDGE_TRUST_ZONE_DENIED",
        "INV_EDGE_LOCALITY_CONFLICT",
    } <= _codes(graph)


def _governed_graph() -> StructuralGraph:
    effects = SideEffectContract(
        SideEffectClass.IRREVERSIBLE,
        frozenset({EffectType.PROVIDER_CALL}),
        minimum_isolation=IsolationGrade.I3_RECORDED_EXTERNALS,
    )
    contract = UnitContract(
        idempotency=IdempotencyContract(
            IdempotencyMode.KEY_REQUIRED, key_field="request_id"
        ),
        side_effects=effects,
        placement=PlacementContract(
            allowed_regions=frozenset({"IN", "US"}),
            allowed_devices=frozenset({"cpu"}),
            allowed_runtimes=frozenset({"python"}),
            required_capabilities=frozenset({"provider-recording"}),
            preferred_regions=("US",),
        ),
        security=SecurityContract(
            tenant_id="tenant-a",
            required_permissions=frozenset({"provider:invoke"}),
            allowed_residencies=frozenset({"IN", "US"}),
            trust_zone="enclave",
            accepted_trust_zones=frozenset({"enclave"}),
            confidential_compute_required=True,
        ),
    )
    return StructuralGraph(
        GraphID("governed"), units={"governed": _unit("governed", contract)}
    )


def _context(**changes) -> ExecutionContext:
    values = {
        "tenant_id": "tenant-a",
        "permissions": frozenset({"provider:invoke"}),
        "isolation_grade": IsolationGrade.I3_RECORDED_EXTERNALS,
        "region": "IN",
        "device": "cpu",
        "runtime": "python",
        "capabilities": frozenset({"provider-recording"}),
        "trust_zone": "enclave",
        "confidential_compute": True,
    }
    values.update(changes)
    return ExecutionContext(**values)


def test_projection_requires_and_propagates_satisfying_execution_context() -> None:
    graph = _governed_graph()
    projector = StructuralProjector()
    with pytest.raises(ValueError, match="without an ExecutionContext"):
        projector.project(graph)

    denied = DNCIRValidator().validate_execution_context(
        graph,
        _context(
            tenant_id="tenant-b",
            permissions=frozenset(),
            isolation_grade=IsolationGrade.I1_GRAPH_ONLY,
            region="EU",
            trust_zone="public",
            confidential_compute=False,
        ),
    )
    assert {
        "CTX_TENANT_MISMATCH",
        "CTX_PERMISSION_MISSING",
        "CTX_ISOLATION_INSUFFICIENT",
        "CTX_REGION_DENIED",
        "CTX_UNIT_TRUST_ZONE_MISMATCH",
        "CTX_RESIDENCY_DENIED",
        "CTX_CONFIDENTIAL_COMPUTE_REQUIRED",
    } <= {error.code for error in denied.errors}

    dag, warnings = projector.project(graph, _context())
    assert warnings == []
    assert dag.nodes["governed"].idempotency.mode is IdempotencyMode.KEY_REQUIRED
    assert dag.nodes["governed"].security.tenant_id == "tenant-a"
    assert dag.nodes["governed"].placement.preferred_regions == ("US",)


def test_governance_contracts_roundtrip_canonically() -> None:
    graph = _governed_graph()
    payload = DNWIRSerializer.to_json(graph)
    restored = DNWIRSerializer.from_json(payload)

    assert DNWIRSerializer.to_json(restored) == payload
    assert restored.units["governed"].contract == graph.units["governed"].contract
