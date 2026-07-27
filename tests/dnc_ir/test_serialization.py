from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.ir.serialization import DNWIRSerializer

def test_serialization_roundtrip():
    g = StructuralGraph(graph_id=GraphID("g_ser"), version=GraphVersion(1, 0, 0, 2))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    g.add_unit(u2)
    g.add_edge(Edge(source=u1.unit_id, target=u2.unit_id, edge_type=EdgeType.DATA))
    
    json_str = DNWIRSerializer.to_json(g)
    assert isinstance(json_str, str)
    
    g_restored = DNWIRSerializer.from_json(json_str)
    assert g_restored.graph_id.value == "g_ser"
    assert g_restored.version.sequence == 2
    assert len(g_restored.units) == 2
    assert len(g_restored.edges) == 1
    assert "u1" in g_restored.units
    assert "u2" in g_restored.units
