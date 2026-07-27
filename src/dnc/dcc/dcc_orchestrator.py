"""
DCCL Orchestrator — Phase 6 Interface Integration
Implements the complete DCCL control loop without full autonomous intelligence.
"""

from typing import List, Any, Optional, Tuple
from dnc.ir.graph import StructuralGraph
from dnc.ir.operations import IROperation
from dnc.transaction.manager import TransactionManager
from .dcc_contracts import DCCLControlContext, MutationProposal, AuthorizationDecision
from .dcc_generator import DeterministicComputationGenerator
from .dcc_controller import DeterministicStructuralController

class DCCLOrchestrator:
    """
    DCCL Control Loop Orchestrator (Phase 6).
    Connects DCCL interfaces to the proven structural transaction substrate.
    Demonstrates the complete macro-loop: INTERPRET → GENERATE → EVALUATE → AUTHORIZE → TRANSACT → ADAPT
    """
    def __init__(self, transaction_manager: Optional[TransactionManager] = None):
        self.transaction_manager = transaction_manager or TransactionManager()
        self.generator = DeterministicComputationGenerator()
        self.controller = DeterministicStructuralController()
        self.control_context = DCCLControlContext(
            current_graph_id="",
            current_version="v0.0.0-0"
        )

    def interpret(self, current_graph: StructuralGraph, execution_assessment: Any) -> None:
        """INTERPRET: Observe current system state and update control context."""
        self.control_context.current_graph_id = current_graph.graph_id.value
        self.control_context.current_version = str(current_graph.version)
        self.control_context.last_assessment = execution_assessment
        self.control_context.cycle_count += 1
        self.control_context.adaptation_active = True

    def generate(self, current_graph: StructuralGraph, observation: Any, adaptation_knowledge: Any = None) -> List[MutationProposal]:
        """GENERATE: Produce candidate structural mutation proposals."""
        return self.generator.propose(current_graph, observation, adaptation_knowledge)

    def evaluate(self, proposals: List[MutationProposal], current_graph: StructuralGraph) -> List[MutationProposal]:
        """EVALUATE: Filter and rank proposals (Phase 6: pass-through for deterministic generator)."""
        return proposals

    def authorize(self, proposal: MutationProposal) -> AuthorizationDecision:
        """AUTHORIZE: Controller evaluates and authorizes or rejects the proposal."""
        return self.controller.authorize(proposal)

    def transact(self, graph: StructuralGraph, operations: List[IROperation]) -> Tuple[bool, Any]:
        """TRANSACT: Execute authorized mutations via Transaction Manager."""
        success, ctx = self.transaction_manager.execute_transaction(graph, operations, base_version=graph.version)
        return success, ctx

    def adapt(self, success: bool, ctx: Any) -> bool:
        """ADAPT: Record adaptation outcome and update control state."""
        if success:
            self.control_context.adaptation_active = True
        else:
            self.control_context.adaptation_active = False
        return success

    def execute_control_cycle(self, current_graph: StructuralGraph, execution_assessment: Any = None, observation: Any = None) -> Tuple[bool, StructuralGraph, List[MutationProposal]]:
        """
        Executes one complete DCCL macro-loop cycle.
        Returns: (adaptation_success, updated_graph, generated_proposals)
        """
        # 1. INTERPRET
        self.interpret(current_graph, execution_assessment)

        # 2. GENERATE
        proposals = self.generate(current_graph, observation)

        # 3. EVALUATE
        evaluated_proposals = self.evaluate(proposals, current_graph)

        # 4. AUTHORIZE
        authorized_ops = []
        for proposal in evaluated_proposals:
            decision = self.authorize(proposal)
            if decision.authorized:
                authorized_ops.extend(proposal.candidate_operations)

        # 5. TRANSACT
        if authorized_ops:
            success, ctx = self.transact(current_graph, authorized_ops)
        else:
            success, ctx = True, None

        # 6. ADAPT
        self.adapt(success, ctx)

        return success, current_graph, proposals