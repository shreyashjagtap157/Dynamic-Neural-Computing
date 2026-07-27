"""
DCCL Interface Contracts and Minimal Reference Implementations (Phase 6)
Establishes DCCL interfaces without full autonomous intelligence.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from dnc.ir.operations import IROperation

@dataclass
class MutationProposal:
    proposal_id: str
    target_graph_id: str
    candidate_operations: List[IROperation]
    rationale: str = ""
    expected_utility: float = 0.0
    estimated_cost: float = 0.0
    risk_assessment: str = "MEDIUM"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AuthorizationDecision:
    proposal_id: str
    authorized: bool
    transaction_id: str | None = None
    rejection_reason: str | None = None
    conditions: List[str] = field(default_factory=list)

class ComputationGeneratorInterface:
    """
    DCCL Computation Generator interface.
    Generates candidate structural mutation proposals.
    Phase 6: Minimal reference implementation using deterministic rule-based generation.
    """
    def propose(self, current_graph_state: Any, observation: Any, adaptation_knowledge: Any) -> List[MutationProposal]:
        raise NotImplementedError("Subclass must implement generate_proposals()")

class StructuralControllerInterface:
    """
    DCCL Structural Controller interface.
    Evaluates and authorizes mutation proposals.
    Phase 6: Minimal reference implementation using deterministic policy.
    """
    def authorize(self, proposal: MutationProposal) -> AuthorizationDecision:
        raise NotImplementedError("Subclass must implement authorize()")

@dataclass
class DCCLControlContext:
    current_graph_id: str
    current_version: str
    cycle_count: int = 0
    last_assessment: Any = None
    adaptation_active: bool = False