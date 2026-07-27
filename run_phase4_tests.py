"""
Test runner for Phase 4: Structural Versioning + Provenance Integration.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.transaction.manager import TransactionManager
from dnc.transaction.context import TransactionState
from dnc.observability.provenance import ProvenanceLog, EventType

def test_structural_provenance_and_versioning():
    g = StructuralGraph(graph_id=GraphID("g_prov_v"), version=GraphVersion(1, 0, 0, 0))
    prov_log = ProvenanceLog(execution_id="exec_phase4_test")
    mgr = TransactionManager(provenance_log=prov_log)

    u1 = ComputationalUnit(UnitID("u1"), "U1", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)
    u2 = ComputationalUnit(UnitID("u2"), "U2", StructureDimension.PRIMITIVE, VisibilityDimension.INSPECTABLE, LifecycleDimension.BASE)

    ops = [
        IROperation(OperationType.ADD_UNIT, {"unit": u1}),
        IROperation(OperationType.ADD_UNIT, {"unit": u2}),
        IROperation(OperationType.CONNECT_UNITS, {"source": u1.unit_id, "target": u2.unit_id, "edge_type": EdgeType.DATA})
    ]

    success, ctx = mgr.execute_transaction(g, ops, base_version=g.version)
    assert success is True
    assert ctx.state == TransactionState.COMMITTED
    assert str(g.version) == "v1.0.0-1"

    # Verify provenance event types
    event_types = [e.event_type for e in prov_log]
    assert EventType.STRUCTURAL_TRANSACTION_BEGIN in event_types
    assert EventType.STRUCTURAL_MUTATION_APPLIED in event_types
    assert EventType.STRUCTURAL_TRANSACTION_COMMITTED in event_types
    assert EventType.STRUCTURAL_GRAPH_VERSION_CREATED in event_types

    # Verify hash chain integrity
    assert prov_log.verify_chain() is True
    print("PASS: test_structural_provenance_and_versioning")

if __name__ == "__main__":
    test_structural_provenance_and_versioning()
    print("\nALL PHASE 4 STRUCTURAL PROVENANCE & VERSIONING TESTS PASSED SUCCESSFULLY!")
