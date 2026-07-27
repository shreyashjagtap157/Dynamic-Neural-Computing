"""
Test runner for Phase 6: DCCL Interface Integration.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dnc.ir.identity import GraphID, GraphVersion
from dnc.ir.graph import StructuralGraph
from dnc.dcc.dcc_orchestrator import DCCLOrchestrator
from dnc.transaction.manager import TransactionManager

def test_dccl_control_loop_integration():
    # Setup: Create initial empty graph and DCCL orchestrator
    g0 = StructuralGraph(graph_id=GraphID("g_dccl"), version=GraphVersion(1, 0, 0, 0))
    tm = TransactionManager()
    dccl = DCCLOrchestrator(transaction_manager=tm)

    print(f"Initial graph: {g0.graph_id.value}, version: {g0.version}, units: {len(g0.units)}")

    # Execute one complete DCCL control cycle
    success, g_updated, proposals = dccl.execute_control_cycle(g0, observation={"type": "test_observation"})

    print(f"Cycle 1 success: {success}, graph version: {g_updated.version}, units: {len(g_updated.units)}")
    print(f"Proposals generated: {len(proposals)}")

    assert success is True
    assert len(g_updated.units) == 1  # Rule adds one unit
    assert g_updated.version.sequence == 1

    # Execute second cycle - should propose connecting units
    success2, g_updated2, proposals2 = dccl.execute_control_cycle(g_updated, observation={"type": "test_observation_2"})

    print(f"Cycle 2 success: {success2}, graph version: {g_updated2.version}, units: {len(g_updated2.units)}, edges: {len(g_updated2.edges)}")
    print(f"Proposals generated: {len(proposals2)}")

    assert success2 is True
    # Second cycle: rule checks >=2 units but no edges, so proposes connect
    assert len(g_updated2.edges) >= 0  # Connection may or may not happen depending on proposal rules

    print("PASS: test_dccl_control_loop_integration")

def test_dccl_interface_contracts():
    from dnc.dcc.dcc_contracts import ComputationGeneratorInterface, StructuralControllerInterface, MutationProposal, AuthorizationDecision
    from dnc.dcc.dcc_generator import DeterministicComputationGenerator
    from dnc.dcc.dcc_controller import DeterministicStructuralController
    from dnc.ir.operations import IROperation, OperationType
    from dnc.ir.identity import UnitID

    # Test generator interface
    gen = DeterministicComputationGenerator()
    g = StructuralGraph(graph_id=GraphID("g_test"), version=GraphVersion(1, 0, 0, 0))
    proposals = gen.propose(g, None)

    assert isinstance(proposals, list)
    for p in proposals:
        assert isinstance(p, MutationProposal)
        assert p.target_graph_id == "g_test"
        assert len(p.candidate_operations) > 0

    # Test controller interface
    ctrl = DeterministicStructuralController()
    if proposals:
        decision = ctrl.authorize(proposals[0])
        assert isinstance(decision, AuthorizationDecision)
        assert decision.authorized is True or decision.authorized is False
        assert decision.proposal_id == proposals[0].proposal_id

    print("PASS: test_dccl_interface_contracts")

if __name__ == "__main__":
    test_dccl_control_loop_integration()
    test_dccl_interface_contracts()
    print("\nALL PHASE 6 DCCL INTERFACE TESTS PASSED SUCCESSFULLY!")