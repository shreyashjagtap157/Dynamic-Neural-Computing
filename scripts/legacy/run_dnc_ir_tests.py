"""
Test runner for Phase 1: DNC-IR Reference Implementation and Validator.
"""

import sys
import os

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dnc.ir.identity import UnitID, GraphID, GraphVersion, IdentityRegistry
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension, Constraint, EnforcementTier
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.ir.validator import DNCIRValidator
from dnc.ir.serialization import DNWIRSerializer

def test_identity_immutability():
    uid = UnitID("unit_test_1")
    assert str(uid) == "unit_test_1"
    try:
        uid.value = "unit_test_2"
        raise AssertionError("Should have raised frozen dataclass error")
    except Exception:
        pass
    print("PASS: test_identity_immutability")

def test_identity_permanence_registry():
    registry = IdentityRegistry()
    uid = UnitID("unit_perm_1")
    registry.register_unit(uid)
    assert registry.is_active(uid)
    registry.retire_unit(uid)
    assert not registry.is_active(uid)
    assert registry.is_retired(uid)
    try:
        registry.register_unit(uid)
        raise AssertionError("Should have raised ValueError on retired ID reuse")
    except ValueError as e:
        assert "Identity Violation" in str(e)
    print("PASS: test_identity_permanence_registry")

def test_computational_unit_dimensions():
    uid = UnitID("unit_calc_1")
    unit = ComputationalUnit(
        unit_id=uid,
        name="Calculator",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    )
    assert unit.unit_id == uid
    assert unit.structure == StructureDimension.PRIMITIVE
    assert unit.validate_dimensions() is True
    print("PASS: test_computational_unit_dimensions")

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
    print("PASS: test_structural_graph_construction")

def test_validator():
    g = StructuralGraph(graph_id=GraphID("g_val"))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u1.constraints.append(Constraint("c1", EnforcementTier.INVARIANT, "x > 0", "Positive constraint"))
    g.add_unit(u1)
    validator = DNCIRValidator()
    res = validator.validate_graph(g)
    assert res.is_valid is True
    assert validator.evaluate_conformance_level(g) == 4

    # Test invalid edge target
    g2 = StructuralGraph(graph_id=GraphID("g_bad"))
    g2.add_unit(u1)
    g2.add_edge(Edge(source=u1.unit_id, target=UnitID("missing"), edge_type=EdgeType.DATA))
    res2 = validator.validate_graph(g2)
    assert res2.is_valid is False
    assert validator.evaluate_conformance_level(g2) == 0
    print("PASS: test_validator")

def test_serialization():
    g = StructuralGraph(graph_id=GraphID("g_ser"), version=GraphVersion(1, 0, 0, 2))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    g.add_unit(u2)
    g.add_edge(Edge(source=u1.unit_id, target=u2.unit_id, edge_type=EdgeType.DATA))
    
    json_str = DNWIRSerializer.to_json(g)
    g_restored = DNWIRSerializer.from_json(json_str)
    assert g_restored.graph_id.value == "g_ser"
    assert g_restored.version.sequence == 2
    assert len(g_restored.units) == 2
    assert len(g_restored.edges) == 1
    print("PASS: test_serialization")

if __name__ == "__main__":
    test_identity_immutability()
    test_identity_permanence_registry()
    test_computational_unit_dimensions()
    test_structural_graph_construction()
    test_validator()
    test_serialization()
    print("\nALL DNC-IR PHASE 1 TESTS PASSED SUCCESSFULLY!")
