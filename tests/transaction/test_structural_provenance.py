from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.transaction.context import TransactionState
from dnc.observability.provenance import ProvenanceLog, EventType

def test_structural_provenance_integration():
    g = StructuralGraph(graph_id=GraphID("g_prov"), version=GraphVersion(1, 0, 0, 0))
    prov_log = ProvenanceLog(execution_id="exec_structural_test")
    mgr = TransactionManager(provenance_log=prov_log)

    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    ops = [IROperation(OperationType.ADD_UNIT, {"unit": u1})]

    success, ctx = mgr.execute_transaction(g, ops, base_version=g.version)
    assert success is True
    assert ctx.state == TransactionState.COMMITTED

    # Verify provenance log contains structural events
    event_types = [e.event_type for e in prov_log]
    assert EventType.STRUCTURAL_TRANSACTION_BEGIN in event_types
    assert EventType.STRUCTURAL_MUTATION_APPLIED in event_types
    assert EventType.STRUCTURAL_TRANSACTION_COMMITTED in event_types
    assert EventType.STRUCTURAL_GRAPH_VERSION_CREATED in event_types

    # Verify hash chain integrity
    assert prov_log.verify_chain() is True
