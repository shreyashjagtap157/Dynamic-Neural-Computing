from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.replay.structural_replay import StructuralReplayEngine

def test_structural_replay_determinism():
    g0 = StructuralGraph(graph_id=GraphID("g_replay"), version=GraphVersion(1, 0, 0, 0))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    tx1 = [IROperation(OperationType.ADD_UNIT, {"unit": u1})]
    tx2 = [
        IROperation(OperationType.ADD_UNIT, {"unit": u2}),
        IROperation(OperationType.CONNECT_UNITS, {"source": u1.unit_id, "target": u2.unit_id, "edge_type": EdgeType.DATA})
    ]

    mgr = TransactionManager()
    engine = StructuralReplayEngine(mgr)

    success, g_final = engine.replay(g0, [tx1, tx2])
    assert success is True
    assert len(g_final.units) == 2
    assert len(g_final.edges) == 1
    assert g_final.version.sequence == 2  # Two committed transactions

    # Verify replay verification helper
    g_expected = StructuralGraph(graph_id=GraphID("g_replay"), version=GraphVersion(1, 0, 0, 0))
    mgr.execute_transaction(g_expected, tx1)
    mgr.execute_transaction(g_expected, tx2)

    assert engine.verify_replay(g0, [tx1, tx2], g_expected) is True
