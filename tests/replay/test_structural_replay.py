from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.replay.structural_replay import StructuralReplayEngine
from dnc.execution.snapshot import ReproducibilityGrade

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

    evidence = engine.replay_with_evidence(g0, [tx1, tx2])
    assert evidence.success
    assert evidence.reproducibility_grade is ReproducibilityGrade.R2_DETERMINISTIC_CORE
    assert len(evidence.canonical_hash) == 64


def test_structural_replay_verification_compares_canonical_content():
    g0 = StructuralGraph(graph_id=GraphID("content"), version=GraphVersion(1, 0, 0, 0))
    original = ComputationalUnit(
        UnitID("u1"), "Original", StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE,
    )
    operations = [[IROperation(OperationType.ADD_UNIT, {"unit": original})]]
    success, expected = StructuralReplayEngine().replay(g0, operations)
    assert success
    expected.units["u1"].name = "Tampered but same ID and count"

    assert not StructuralReplayEngine().verify_replay(g0, operations, expected)
