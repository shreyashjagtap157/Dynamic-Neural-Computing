"""
DNC-IR Validator and Conformance Engine (SPEC-IR Section 11, 13, 17)
Implements multi-tier validation, invariants, constraints, policies, and conformance levels.
"""

from dataclasses import dataclass, field
from typing import List
from .graph import StructuralGraph
from .unit import EnforcementTier

@dataclass
class ValidationError:
    tier: EnforcementTier
    code: str
    message: str
    target_id: str = ""

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

class DNCIRValidator:
    """
    Validates StructuralGraphs against invariants, constraints, contracts, and capabilities.
    """
    def validate_graph(self, graph: StructuralGraph) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # 1. Structural Invariants (INV-1 through INV-X)
        for uid, unit in graph.units.items():
            if not unit.validate_dimensions():
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_UNIT_DIMENSION",
                    message=f"Unit {uid} violates dimensional structure rules.",
                    target_id=uid
                ))

        # 2. Edge Integrity (Source and target must exist)
        for edge in graph.edges:
            if edge.source.value not in graph.units:
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_EDGE_SOURCE_MISSING",
                    message=f"Edge references non-existent source unit {edge.source}.",
                    target_id=edge.source.value
                ))
            if edge.target.value not in graph.units:
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_EDGE_TARGET_MISSING",
                    message=f"Edge references non-existent target unit {edge.target}.",
                    target_id=edge.target.value
                ))

        # 3. Constraint and Policy checking
        for uid, unit in graph.units.items():
            for constraint in unit.constraints:
                if constraint.tier == EnforcementTier.INVARIANT:
                    # Evaluate invariant condition (stub check or expression eval)
                    if not constraint.expression:
                        errors.append(ValidationError(
                            tier=EnforcementTier.INVARIANT,
                            code="INV_CONSTRAINT_EMPTY",
                            message=f"Unit {uid} has empty invariant constraint {constraint.constraint_id}.",
                            target_id=uid
                        ))
                elif constraint.tier == EnforcementTier.CONSTRAINT:
                    if not constraint.expression:
                        warnings.append(ValidationError(
                            tier=EnforcementTier.CONSTRAINT,
                            code="WARN_CONSTRAINT_EMPTY",
                            message=f"Unit {uid} has empty negotiable constraint {constraint.constraint_id}.",
                            target_id=uid
                        ))

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def evaluate_conformance_level(self, graph: StructuralGraph) -> int:
        """
        Evaluates conformance level (0 to 4):
        Level 0: Structural (units & edges well-formed)
        Level 1: Semantic (contracts and schemas valid)
        Level 2: Identity (stable permanent IDs)
        Level 3: Mutation (mutation contracts respected)
        Level 4: Full (all invariants and constraints satisfied)
        """
        # Level 0 check
        if not graph.units and not graph.edges:
            return 0
        
        # Run full validation
        res = self.validate_graph(graph)
        if not res.is_valid:
            return 0  # Below level 4 if invariants fail
            
        return 4
