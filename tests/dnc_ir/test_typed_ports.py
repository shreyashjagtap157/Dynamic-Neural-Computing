from dnc.ir.contracts import PortCardinality, PortContract, PortDirection, PortKind
from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    UnitContract,
    VisibilityDimension,
)
from dnc.ir.validator import DNCIRValidator
import pytest
from dnc.mutation.engine import MutationEngine
from dnc.projection.projector import StructuralProjector


JSON_STRING = {"type": "string"}


def _unit(unit_id: str, *ports: PortContract) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
        contract=UnitContract(ports=list(ports)),
    )


def _port(
    port_id: str,
    direction: PortDirection,
    kind: PortKind = PortKind.DATA,
    schema: dict | None = None,
    cardinality: PortCardinality = PortCardinality.EXACTLY_ONE,
) -> PortContract:
    return PortContract(
        port_id,
        direction,
        kind,
        JSON_STRING if schema is None else schema,
        cardinality,
    )


def _typed_graph(kind: PortKind = PortKind.DATA) -> StructuralGraph:
    graph = StructuralGraph(GraphID("typed"))
    source = _unit("source", _port("out", PortDirection.OUTPUT, kind))
    target = _unit("target", _port("in", PortDirection.INPUT, kind))
    graph.add_unit(source)
    graph.add_unit(target)
    graph.add_edge(
        Edge(
            source.unit_id,
            target.unit_id,
            EdgeType(kind.value),
            source_port="out",
            target_port="in",
        )
    )
    return graph


def _error_codes(graph: StructuralGraph) -> set[str]:
    return {error.code for error in DNCIRValidator().validate_graph(graph).errors}


def test_typed_data_edge_validates_roundtrips_and_projects_ports() -> None:
    graph = _typed_graph()

    assert DNCIRValidator().validate_graph(graph).is_valid
    restored = DNWIRSerializer.from_json(DNWIRSerializer.to_json(graph))
    assert restored.units["source"].contract.port("out") == graph.units["source"].contract.port("out")
    assert restored.edges[0].source_port == "out"
    projected, warnings = StructuralProjector().project(restored)
    assert warnings == []
    assert projected.edges[0].target_port == "in"

    document = DNWIRSerializer.to_dict(graph)
    document["units"]["source"]["contract"]["ports"][0]["schema"]["type"] = "integer"
    assert graph.units["source"].contract.port("out").schema == JSON_STRING


def test_canonical_serialization_orders_same_endpoint_edges_by_ports() -> None:
    source = _unit(
        "source",
        _port(
            "out-b",
            PortDirection.OUTPUT,
            cardinality=PortCardinality.ZERO_OR_MORE,
        ),
        _port(
            "out-a",
            PortDirection.OUTPUT,
            cardinality=PortCardinality.ZERO_OR_MORE,
        ),
    )
    target = _unit(
        "target",
        _port(
            "in-b",
            PortDirection.INPUT,
            cardinality=PortCardinality.ZERO_OR_MORE,
        ),
        _port(
            "in-a",
            PortDirection.INPUT,
            cardinality=PortCardinality.ZERO_OR_MORE,
        ),
    )
    first = StructuralGraph(GraphID("same-endpoint"))
    first.add_unit(source)
    first.add_unit(target)
    edge_a = Edge(
        source.unit_id,
        target.unit_id,
        EdgeType.DATA,
        source_port="out-a",
        target_port="in-a",
    )
    edge_b = Edge(
        source.unit_id,
        target.unit_id,
        EdgeType.DATA,
        source_port="out-b",
        target_port="in-b",
    )
    first.add_edge(edge_b)
    first.add_edge(edge_a)
    second = StructuralGraph(
        GraphID("same-endpoint"),
        units=dict(first.units),
        edges=[edge_a, edge_b],
    )

    assert DNCIRValidator().validate_graph(first).is_valid
    assert DNWIRSerializer.to_json(first) == DNWIRSerializer.to_json(second)


def test_resource_edges_are_typed_without_becoming_execution_dependencies() -> None:
    graph = _typed_graph(PortKind.RESOURCE)

    result = DNCIRValidator().validate_graph(graph)
    projected, warnings = StructuralProjector().project(graph)

    assert result.is_valid
    assert warnings == []
    assert projected.edges[0].edge_type == "RESOURCE"
    assert [unit.value for unit in projected.topological_order] == ["source", "target"]


@pytest.mark.parametrize("kind", list(PortKind))
def test_all_normative_typed_edge_kinds_validate(kind: PortKind) -> None:
    assert DNCIRValidator().validate_graph(_typed_graph(kind)).is_valid


def test_typed_units_require_complete_port_bindings() -> None:
    graph = _typed_graph()
    graph.edges[0] = Edge(UnitID("source"), UnitID("target"), EdgeType.DATA)

    assert "INV_EDGE_PORT_BINDING_REQUIRED" in _error_codes(graph)

    legacy = StructuralGraph(GraphID("partial"))
    legacy.add_unit(_unit("source"))
    legacy.add_unit(_unit("target"))
    legacy.add_edge(
        Edge(
            UnitID("source"), UnitID("target"), EdgeType.DATA,
            source_port="out", target_port=None,
        )
    )
    assert "INV_EDGE_PORT_BINDING_INCOMPLETE" in _error_codes(legacy)


def test_validator_rejects_missing_direction_kind_and_schema_mismatches() -> None:
    missing = _typed_graph()
    missing.edges[0] = Edge(
        UnitID("source"), UnitID("target"), EdgeType.DATA,
        source_port="unknown", target_port="in",
    )
    assert "INV_EDGE_PORT_MISSING" in _error_codes(missing)

    direction = StructuralGraph(GraphID("direction"))
    direction.add_unit(_unit("a", _port("in", PortDirection.INPUT)))
    direction.add_unit(_unit("b", _port("out", PortDirection.OUTPUT)))
    direction.add_edge(Edge(UnitID("a"), UnitID("b"), EdgeType.DATA, source_port="in", target_port="out"))
    assert "INV_EDGE_PORT_DIRECTION" in _error_codes(direction)

    kind = _typed_graph()
    kind.edges[0] = Edge(
        UnitID("source"), UnitID("target"), EdgeType.STATE,
        source_port="out", target_port="in",
    )
    assert "INV_EDGE_PORT_KIND" in _error_codes(kind)

    schema = _typed_graph()
    schema.units["target"].contract.ports[0] = _port(
        "in", PortDirection.INPUT, schema={"type": "integer"}
    )
    assert "INV_EDGE_SCHEMA_MISMATCH" in _error_codes(schema)


def test_validator_enforces_port_identity_and_cardinality() -> None:
    malformed = _unit("malformed")
    malformed.contract.ports.append({"port_id": "not-a-contract"})  # type: ignore[arg-type]
    graph = StructuralGraph(GraphID("malformed"), units={"malformed": malformed})
    assert "INV_PORT_CONTRACT_INVALID" in _error_codes(graph)

    duplicate = _unit(
        "duplicate",
        _port("same", PortDirection.INPUT, cardinality=PortCardinality.ZERO_OR_MORE),
        _port("same", PortDirection.INPUT, cardinality=PortCardinality.ZERO_OR_MORE),
    )
    graph = StructuralGraph(GraphID("duplicate"), units={"duplicate": duplicate})
    assert "INV_PORT_ID_DUPLICATE" in _error_codes(graph)

    graph = _typed_graph()
    graph.edges.clear()
    assert "INV_PORT_CARDINALITY" in _error_codes(graph)

    graph = _typed_graph()
    graph.edges.append(graph.edges[0])
    assert "INV_PORT_CARDINALITY" in _error_codes(graph)
    assert "INV_EDGE_DUPLICATE" in _error_codes(graph)


def test_mutation_preserves_port_identity_for_connect_disconnect_and_rewire() -> None:
    graph = StructuralGraph(GraphID("mutations"))
    for unit_id in ("source", "alternate", "target"):
        graph.add_unit(_unit(unit_id))
    engine = MutationEngine()
    connect = IROperation(
        OperationType.CONNECT_UNITS,
        {
            "source": UnitID("source"),
            "target": UnitID("target"),
            "edge_type": EdgeType.DATA,
            "source_port": "out",
            "target_port": "in",
        },
    )
    success, _, undo = engine.apply_operation(graph, connect)
    assert success and graph.edges[0].source_port == "out"
    engine.rollback(graph, undo)
    assert graph.edges == []

    graph.add_edge(Edge(UnitID("source"), UnitID("target"), EdgeType.DATA, source_port="out", target_port="in"))
    rewire = IROperation(
        OperationType.REWIRE_EDGE,
        {
            "old_source": UnitID("source"),
            "old_target": UnitID("target"),
            "new_source": UnitID("alternate"),
            "new_target": UnitID("target"),
        },
    )
    success, _, undo = engine.apply_operation(graph, rewire)
    assert success and graph.edges[0].source == UnitID("alternate")
    assert graph.edges[0].source_port == "out"
    engine.rollback(graph, undo)
    assert graph.edges[0].source == UnitID("source")
