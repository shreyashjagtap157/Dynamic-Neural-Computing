"""
DCCL Structural Controller — Minimal Deterministic Reference Implementation (Phase 6)
Implements rule-based authorization for DCCL interface verification.
"""

import uuid
from .dcc_contracts import StructuralControllerInterface, MutationProposal, AuthorizationDecision

class DeterministicStructuralController(StructuralControllerInterface):
    """
    Minimal rule-based controller for Phase 6 DCCL interface verification.
    Authorizes proposals based on deterministic safety and cost policies.
    """
    def __init__(self):
        self._authorization_count = 0

    def authorize(self, proposal: MutationProposal) -> AuthorizationDecision:
        self._authorization_count += 1
        
        # Deterministic authorization policy for Phase 6:
        # 1. Always authorize low-risk proposals
        # 2. Reject if expected_utility <= 0
        # 3. Reject if estimated_cost > 10.0 (cost budget threshold)
        
        if proposal.risk_assessment == "LOW" and proposal.expected_utility > 0 and proposal.estimated_cost <= 10.0:
            return AuthorizationDecision(
                proposal_id=proposal.proposal_id,
                authorized=True,
                transaction_id=f"auth_tx_{uuid.uuid4().hex[:12]}",
                rejection_reason=None,
                conditions=[]
            )
        
        return AuthorizationDecision(
            proposal_id=proposal.proposal_id,
            authorized=False,
            transaction_id=None,
            rejection_reason=f"Policy rejection: utility={proposal.expected_utility}, cost={proposal.estimated_cost}, risk={proposal.risk_assessment}",
            conditions=[]
        )