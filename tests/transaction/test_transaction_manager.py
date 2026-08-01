from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.transaction.context import TransactionState
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.contracts import SideEffectContract
from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass

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


def test_transaction_commit_isolates_caller_owned_operation_payloads():
    graph = StructuralGraph(GraphID("isolated-payload"))
    unit = ComputationalUnit(
        UnitID("unit"), "Original", StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE,
    )

    success, _ = TransactionManager().execute_transaction(
        graph, [IROperation(OperationType.ADD_UNIT, {"unit": unit})]
    )
    assert success
    unit.name = "Caller mutation"
    unit.metadata["caller"] = True

    assert graph.units["unit"].name == "Original"
    assert "caller" not in graph.units["unit"].metadata


def test_failed_governed_transaction_leaves_active_graph_byte_identical():
    graph = StructuralGraph(GraphID("governed-rollback"))
    before = DNWIRSerializer.to_json(graph)
    unsafe_effect = SideEffectContract(
        SideEffectClass.COMPENSATABLE,
        frozenset({EffectType.FILE_WRITE}),
        "delete-file",
        IsolationGrade.I2_PROCESS_LOCAL,
    )
    unit = ComputationalUnit(
        UnitID("unsafe"), "Unsafe", StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE,
    )
    unit.contract.side_effects = unsafe_effect

    success, ctx = TransactionManager().execute_transaction(
        graph, [IROperation(OperationType.ADD_UNIT, {"unit": unit})]
    )

    assert not success
    assert ctx.state is TransactionState.ROLLED_BACK
    assert "INV_EFFECT_IDEMPOTENCY_REQUIRED" in ctx.error_message
    assert DNWIRSerializer.to_json(graph) == before


def test_uncopyable_operation_payload_rolls_back_without_raising_or_mutating():
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise RuntimeError("opaque handle cannot be copied")

    graph = StructuralGraph(GraphID("uncopyable-operation"))
    unit = ComputationalUnit(
        UnitID("opaque"), "Opaque", StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE,
        metadata={"handle": Uncopyable()},
    )
    before = DNWIRSerializer.to_json(graph)

    success, ctx = TransactionManager().execute_transaction(
        graph, [IROperation(OperationType.ADD_UNIT, {"unit": unit})]
    )

    assert not success
    assert ctx.state is TransactionState.ROLLED_BACK
    assert "Operation isolation failed" in ctx.error_message
    assert DNWIRSerializer.to_json(graph) == before
