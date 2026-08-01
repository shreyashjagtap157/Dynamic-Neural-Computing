from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.transaction.context import TransactionState

def test_transaction_manager_commit():
    g = StructuralGraph(graph_id=GraphID("g_tx"), version=GraphVersion(1, 0, 0, 0))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    mgr = TransactionManager()
    ops = [
        IROperation(OperationType.ADD_UNIT, {"unit": u1}),
        IROperation(OperationType.ADD_UNIT, {"unit": u2}),
        IROperation(OperationType.CONNECT_UNITS, {"source": u1.unit_id, "target": u2.unit_id, "edge_type": EdgeType.DATA})
    ]

    success, ctx = mgr.execute_transaction(g, ops, base_version=g.version)
    assert success is True
    assert ctx.state == TransactionState.COMMITTED
    assert len(g.units) == 2
    assert len(g.edges) == 1
    assert g.version.sequence == 1  # Transaction-level version advance

def test_transaction_manager_occ_conflict():
    g = StructuralGraph(graph_id=GraphID("g_occ"), version=GraphVersion(1, 0, 0, 5))
    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    mgr = TransactionManager()
    ops = [IROperation(OperationType.ADD_UNIT, {"unit": u1})]

    # Attempt transaction with stale base version v1.0.0-0 instead of v1.0.0-5
    stale_version = GraphVersion(1, 0, 0, 0)
    success, ctx = mgr.execute_transaction(g, ops, base_version=stale_version)
    assert success is False
    assert ctx.state == TransactionState.FAILED
    assert "OCC Conflict" in ctx.error_message
    assert len(g.units) == 0  # Graph untouched
