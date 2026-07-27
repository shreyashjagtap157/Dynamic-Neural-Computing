from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension, Constraint, EnforcementTier
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.ir.validator import DNCIRValidator

def test_validator_valid_graph():
    g = StructuralGraph(graph_id=GraphID("g_val"))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u1.constraints.append(Constraint("c1", EnforcementTier.INVARIANT, "x > 0", "Must be positive"))
    g.add_unit(u1)
    
    validator = DNCIRValidator()
    res = validator.validate_graph(g)
    assert res.is_valid is True
    assert validator.evaluate_conformance_level(g) == 4

def test_validator_missing_edge_target():
    g = StructuralGraph(graph_id=GraphID("g_bad"))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    
    # Edge referencing non-existent target u2
    edge = Edge(source=u1.unit_id, target=UnitID("u2"), edge_type=EdgeType.DATA)
    g.add_edge(edge)
    
    validator = DNCIRValidator()
    res = validator.validate_graph(g)
    assert res.is_valid is False
    assert len(res.errors) > 0
    assert validator.evaluate_conformance_level(g) == 0
