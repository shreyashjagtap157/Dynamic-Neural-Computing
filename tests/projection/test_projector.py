import pytest
from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.projection.projector import StructuralProjector
from dnc.projection.executable_graph import ExecutableDAG

def test_structural_projector_deterministic():
    g = StructuralGraph(graph_id=GraphID("g_proj"), version=GraphVersion(1, 0, 0, 1))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    g.add_unit(u2)
    g.add_edge(Edge(u1.unit_id, u2.unit_id, EdgeType.DATA))

    projector = StructuralProjector()
    dag1, warnings1 = projector.project(g)
    dag2, warnings2 = projector.project(g)

    assert len(warnings1) == 0
    assert dag1.graph_id == dag2.graph_id
    assert dag1.source_version == dag2.source_version
    assert dag1.topological_order == dag2.topological_order
    assert len(dag1.nodes) == len(dag2.nodes)
    assert len(dag1.edges) == len(dag2.edges)

    # Verify Structural Graph remains unchanged (immutability invariant)
    assert len(g.units) == 2
    assert len(g.edges) == 1
