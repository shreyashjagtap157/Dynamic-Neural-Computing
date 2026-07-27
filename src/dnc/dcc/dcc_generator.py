"""
DCCL Computation Generator — Minimal Deterministic Reference Implementation (Phase 6)
Implements rule-based structural proposal generation for interface verification.
"""

from typing import List, Any
import uuid
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.identity import UnitID
from dnc.ir.graph import StructuralGraph
from .dcc_contracts import ComputationGeneratorInterface, MutationProposal

class DeterministicComputationGenerator(ComputationGeneratorInterface):
    """
    Minimal rule-based generator for Phase 6 DCCL interface verification.
    Produces structural proposals based on explicit rule patterns, not learned intelligence.
    """
    def __init__(self):
        self._proposal_count = 0

    def propose(self, current_graph_state: StructuralGraph, observation: Any, adaptation_knowledge: Any = None) -> List[MutationProposal]:
        proposals = []
        
        # Rule-based proposal 1: If no units exist, propose adding a base unit
        if not current_graph_state.units:
            self._proposal_count += 1
            u1 = UnitID("generated_unit_1")
            proposals.append(MutationProposal(
                proposal_id=f"prop_gen_{self._proposal_count}_{uuid.uuid4().hex[:8]}",
                target_graph_id=current_graph_state.graph_id.value,
                candidate_operations=[
                    IROperation(OperationType.ADD_UNIT, {
                        "unit": self._create_base_unit(u1, "BaseUnit_1")
                    })
                ],
                rationale="Initial unit addition for empty graph",
                expected_utility=1.0,
                estimated_cost=1.0,
                risk_assessment="LOW"
            ))

        # Rule-based proposal 2: If units exist but no edges, propose connecting them
        if len(current_graph_state.units) >= 2 and not current_graph_state.edges:
            unit_ids = list(current_graph_state.units.keys())
            self._proposal_count += 1
            proposals.append(MutationProposal(
                proposal_id=f"prop_gen_{self._proposal_count}_{uuid.uuid4().hex[:8]}",
                target_graph_id=current_graph_state.graph_id.value,
                candidate_operations=[
                    IROperation(OperationType.CONNECT_UNITS, {
                        "source": UnitID(unit_ids[0]),
                        "target": UnitID(unit_ids[1]),
                        "edge_type": "DATA"
                    })
                ],
                rationale="Connect isolated units in graph",
                expected_utility=0.8,
                estimated_cost=0.5,
                risk_assessment="LOW"
            ))

        return proposals

    def _create_base_unit(self, unit_id: UnitID, name: str):
        from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
        return ComputationalUnit(
            unit_id=unit_id,
            name=name,
            structure=StructureDimension.PRIMITIVE,
            visibility=VisibilityDimension.INSPECTABLE,
            lifecycle=LifecycleDimension.BASE
        )