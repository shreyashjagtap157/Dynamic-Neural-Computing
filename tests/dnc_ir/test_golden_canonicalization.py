import hashlib

from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.kernel import DNC_IR_SCHEMA_ID, DNC_IR_SCHEMA_VERSION


def _golden_graph() -> StructuralGraph:
    graph = StructuralGraph(
        graph_id=GraphID("golden_graph"),
        version=GraphVersion(1, 1, 0, 7),
        metadata={"purpose": "phase1-golden", "platform": "independent"},
    )
    source = ComputationalUnit(
        UnitID("unit_source"),
        "Source",
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
        metadata={"role": "source"},
    )
    sink = ComputationalUnit(
        UnitID("unit_sink"),
        "Sink",
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
        metadata={"role": "sink"},
    )
    graph.add_unit(sink)
    graph.add_unit(source)
    graph.add_edge(
        Edge(
            source=source.unit_id,
            target=sink.unit_id,
            edge_type=EdgeType.DATA,
            metadata={"order": 1},
        )
    )
    return graph


def test_canonical_json_golden_vector_is_stable() -> None:
    payload = DNWIRSerializer.to_json(_golden_graph())

    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == (
        "2c48428e2aed240fcef304d120840ac0b1aa14b3fc91b6d7b3d6c642544a138f"
    )


def test_serialized_graph_carries_schema_version_header() -> None:
    data = DNWIRSerializer.to_dict(_golden_graph())

    assert data["schema_id"] == DNC_IR_SCHEMA_ID
    assert data["schema_version"] == DNC_IR_SCHEMA_VERSION


def test_legacy_serialized_graph_without_header_still_loads() -> None:
    data = DNWIRSerializer.to_dict(_golden_graph())
    data.pop("schema_id")
    data.pop("schema_version")
    data.pop("compatibility_version")

    restored = DNWIRSerializer.from_dict(data)

    assert restored.graph_id.value == "golden_graph"
    assert set(restored.units) == {"unit_source", "unit_sink"}
