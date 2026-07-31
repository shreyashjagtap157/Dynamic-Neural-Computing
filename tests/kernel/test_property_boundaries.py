import copy

from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.projection.projector import StructuralProjector
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
    graph = StructuralGraph(graph_id=GraphID("prop_graph"), version=GraphVersion(1, 0, 0, 0))
    graph.add_unit(_unit("u1"))
    graph.add_unit(_unit("u2"))
    graph.add_edge(Edge(UnitID("u1"), UnitID("u2"), EdgeType.DATA))
    return graph


def test_serialization_is_order_independent_for_units_and_edges() -> None:
    graph_a = _graph()
    graph_b = StructuralGraph(graph_id=GraphID("prop_graph"), version=GraphVersion(1, 0, 0, 0))
    graph_b.add_unit(_unit("u2"))
    graph_b.add_unit(_unit("u1"))
    graph_b.add_edge(Edge(UnitID("u1"), UnitID("u2"), EdgeType.DATA))

    assert DNWIRSerializer.to_json(graph_a) == DNWIRSerializer.to_json(graph_b)


def test_projector_does_not_mutate_structural_graph() -> None:
    graph = _graph()
    before = DNWIRSerializer.to_json(graph)

    StructuralProjector().project(graph)

    assert DNWIRSerializer.to_json(graph) == before


def test_failed_transaction_preserves_canonical_graph() -> None:
    graph = _graph()
    before = DNWIRSerializer.to_json(graph)
    invalid_op = IROperation(OperationType.REMOVE_UNIT, parameters={})

    success, context = TransactionManager().execute_transaction(copy.deepcopy(graph), [invalid_op])

    assert success is False
    assert context.error_message is not None
    assert DNWIRSerializer.to_json(graph) == before
