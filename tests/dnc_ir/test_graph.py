from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, Edge, EdgeType

def test_structural_graph_construction():
    g = StructuralGraph(graph_id=GraphID("g_1"))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    
    g.add_unit(u1)
    g.add_unit(u2)
    
    edge = Edge(source=u1.unit_id, target=u2.unit_id, edge_type=EdgeType.DATA)
    g.add_edge(edge)
    
    assert len(g.units) == 2
    assert len(g.edges) == 1
    
    proj_g, warnings = g.project_to_executable_dag()
    assert proj_g is not None
    assert len(warnings) == 0
