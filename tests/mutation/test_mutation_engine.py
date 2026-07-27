import pytest
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.mutation.engine import MutationEngine

def test_mutation_engine_add_and_connect():
    g = StructuralGraph(graph_id=GraphID("g_mut"))
    engine = MutationEngine()

    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    # 1. Add U1
    success, warns, undo = engine.apply_operation(g, IROperation(OperationType.ADD_UNIT, {"unit": u1}))
    assert success is True
    assert len(g.units) == 1
    assert g.version.sequence == 1

    # 2. Add U2
    success, warns, undo2 = engine.apply_operation(g, IROperation(OperationType.ADD_UNIT, {"unit": u2}))
    assert success is True
    assert len(g.units) == 2
    assert g.version.sequence == 2

    # 3. Connect U1 -> U2
    success, warns, undo3 = engine.apply_operation(g, IROperation(OperationType.CONNECT_UNITS, {"source": u1.unit_id, "target": u2.unit_id, "edge_type": EdgeType.DATA}))
    assert success is True
    assert len(g.edges) == 1
    assert g.version.sequence == 3

    # 4. Test Rollback
    engine.rollback(g, undo3)
    assert len(g.edges) == 0

    engine.rollback(g, undo2)
    assert len(g.units) == 1
