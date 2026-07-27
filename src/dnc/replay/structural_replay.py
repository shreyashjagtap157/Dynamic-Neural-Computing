"""
Structural Replay and Rollback Verification Engine (Phase 5)
Proves deterministic reconstruction of structural graph states from transaction history.
"""

import copy
from typing import List, Tuple
from dnc.ir.graph import StructuralGraph
from dnc.ir.operations import IROperation
from dnc.transaction.manager import TransactionManager

class StructuralReplayEngine:
    """
    Replays a sequence of committed transactions on top of an initial structural graph G_0
    to deterministically reproduce G_n.
    """
    def __init__(self, transaction_manager: Optional[TransactionManager] = None):
        self.transaction_manager = transaction_manager or TransactionManager()

    def replay(self, initial_graph: StructuralGraph, transaction_operations: List[List[IROperation]]) -> Tuple[bool, StructuralGraph]:
        """
        Replays a list of transaction operation batches sequentially.
        """
        current_graph = copy.deepcopy(initial_graph)
        
        for ops in transaction_operations:
            success, ctx = self.transaction_manager.execute_transaction(current_graph, ops, base_version=current_graph.version)
            if not success:
                return False, current_graph

        return True, current_graph

    def verify_replay(self, initial_graph: StructuralGraph, transaction_operations: List[List[IROperation]], expected_final_graph: StructuralGraph) -> bool:
        """
        Asserts that Replay(G_0, T_1...T_n) matches expected_final_graph structurally and version-wise.
      """
        success, replayed_graph = self.replay(initial_graph, transaction_operations)
        if not success:
            return False

        # Compare version, units count, edges count
        if replayed_graph.version != expected_final_graph.version:
            return False
        if set(replayed_graph.units.keys()) != set(expected_final_graph.units.keys()):
            return False
        if len(replayed_graph.edges) != len(expected_final_graph.edges):
            return False

        return True
