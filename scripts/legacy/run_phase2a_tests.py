"""
Test runner for Phase 2A: Structural Graph -> Executable DAG Projection & Integration.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.projection.projector import StructuralProjector
from dnc.projection.projection_validator import ProjectionValidator
from dnc.runtime.runtime import DNCRuntime
from dnc.state.registry import ModuleRegistry
from dnc.modules.standard import StandardModule

def test_projector_determinism_and_immutability():
    g = StructuralGraph(graph_id=GraphID("g_proj"), version=GraphVersion(1, 0, 0, 1))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    g.add_unit(u2)
    g.add_edge(Edge(u1.unit_id, u2.unit_id, EdgeType.DATA))

    projector = StructuralProjector()
    dag1, w1 = projector.project(g)
    dag2, w2 = projector.project(g)

    assert len(w1) == 0
    assert dag1.graph_id == dag2.graph_id
    assert dag1.topological_order == dag2.topological_order
    assert len(dag1.nodes) == 2

    # Verify immutability
    assert len(g.units) == 2
    assert len(g.edges) == 1
    print("PASS: test_projector_determinism_and_immutability")

def test_projection_validator():
    g = StructuralGraph(graph_id=GraphID("g_val"))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)
    projector = StructuralProjector()
    dag, _ = projector.project(g)

    p_validator = ProjectionValidator()
    assert p_validator.validate(dag) is True
    print("PASS: test_projection_validator")

def test_ir_to_core_integration():
    g = StructuralGraph(graph_id=GraphID("g_integration"))
    u1 = ComputationalUnit(UnitID("mod_1"), "StandardModule", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    g.add_unit(u1)

    projector = StructuralProjector()
    dag, warnings = projector.project(g)
    assert dag is not None
    assert len(dag.topological_order) == 1

    registry = ModuleRegistry()
    registry.register("StandardModule", StandardModule)
    runtime = DNCRuntime(registry=registry)
    assert runtime is not None
    print("PASS: test_ir_to_core_integration")

if __name__ == "__main__":
    test_projector_determinism_and_immutability()
    test_projection_validator()
    test_ir_to_core_integration()
    print("\nALL PHASE 2A PROJECTION TESTS PASSED SUCCESSFULLY!")
