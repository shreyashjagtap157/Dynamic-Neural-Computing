"""
Structural Replay and Rollback Verification Engine (Phase 5)
Proves deterministic reconstruction of structural graph states from transaction history.
"""

import copy
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple
from dnc.execution.snapshot import ReproducibilityGrade
from dnc.ir.graph import StructuralGraph
from dnc.ir.operations import IROperation
from dnc.ir.serialization import DNWIRSerializer
from dnc.transaction.manager import TransactionManager


@dataclass(frozen=True)
class StructuralReplayResult:
    success: bool
    graph: StructuralGraph
    reproducibility_grade: ReproducibilityGrade
    canonical_hash: str
    failed_transaction_index: int | None = None
    failure_reason: str | None = None

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
        result = self.replay_with_evidence(initial_graph, transaction_operations)
        return result.success, result.graph

    def replay_with_evidence(
        self,
        initial_graph: StructuralGraph,
        transaction_operations: List[List[IROperation]],
    ) -> StructuralReplayResult:
        """Replay transactions and report truthful deterministic-core evidence."""

        current_graph = copy.deepcopy(initial_graph)
        for index, ops in enumerate(transaction_operations):
            success, ctx = self.transaction_manager.execute_transaction(
                current_graph, ops, base_version=current_graph.version
            )
            if not success:
                return StructuralReplayResult(
                    False,
                    current_graph,
                    ReproducibilityGrade.R2_DETERMINISTIC_CORE,
                    self._canonical_hash(current_graph),
                    failed_transaction_index=index,
                    failure_reason=ctx.error_message,
                )
        return StructuralReplayResult(
            True,
            current_graph,
            ReproducibilityGrade.R2_DETERMINISTIC_CORE,
            self._canonical_hash(current_graph),
        )

    def verify_replay(self, initial_graph: StructuralGraph, transaction_operations: List[List[IROperation]], expected_final_graph: StructuralGraph) -> bool:
        """
        Asserts that Replay(G_0, T_1...T_n) matches expected_final_graph structurally and version-wise.
      """
        success, replayed_graph = self.replay(initial_graph, transaction_operations)
        if not success:
            return False

        return DNWIRSerializer.to_json(replayed_graph) == DNWIRSerializer.to_json(
            expected_final_graph
        )

    @staticmethod
    def _canonical_hash(graph: StructuralGraph) -> str:
        payload = DNWIRSerializer.to_json(graph).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
