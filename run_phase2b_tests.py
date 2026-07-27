"""
Test runner for Phase 2B: Mutation Engine & Rollback Compensation.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.mutation.engine import MutationEngine

def test_mutation_engine_comprehensive():
    g = StructuralGraph(graph_id=GraphID("g_mut_comp"))
    engine = MutationEngine()

    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    # ADD_UNIT U1
    success, _, undo1 = engine.apply_operation(g, IROperation(OperationType.ADD_UNIT, {"unit": u1}))
    assert success is True
    assert "u1" in g.units

    # ADD_UNIT U2
    success, _, undo2 = engine.apply_operation(g, IROperation(OperationType.ADD_UNIT, {"unit": u2}))
    assert success is True
    assert "u2" in g.units

    # CONNECT_UNITS
    success, _, undo3 = engine.apply_operation(g, IROperation(OperationType.CONNECT_UNITS, {"source": u1.unit_id, "target": u2.unit_id, "edge_type": EdgeType.DATA}))
    assert success is True
    assert len(g.edges) == 1

    # Rollback connect
    engine.rollback(g, undo3)
    assert len(g.edges) == 0

    # Rollback add u2
    engine.rollback(g, undo2)
    assert "u2" not in g.units
    assert len(g.units) == 1

    print("PASS: test_mutation_engine_comprehensive")

if __name__ == "__main__":
    test_mutation_engine_comprehensive()
    print("\nALL PHASE 2B MUTATION ENGINE TESTS PASSED SUCCESSFULLY!")
