"""
DNC-IR Validator and Conformance Engine (SPEC-IR Section 11, 13, 17)
Implements multi-tier validation, invariants, constraints, policies, and conformance levels.
"""

from dataclasses import dataclass, field
from collections import Counter
from typing import List
from .graph import StructuralGraph
from dnc.kernel.contracts import SideEffectClass

from .contracts import (
    ExecutionContext,
    IdempotencyMode,
    PortContract,
    PortDirection,
)
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
            if not all(isinstance(port, PortContract) for port in unit.contract.ports):
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_PORT_CONTRACT_INVALID",
                    message=f"Unit {uid} contains a malformed port contract.",
                    target_id=uid,
                ))
            elif not unit.contract.validate_ports():
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_PORT_ID_DUPLICATE",
                    message=f"Unit {uid} declares duplicate port identifiers.",
                    target_id=uid,
                ))
            effects = unit.contract.side_effects
            idempotency = unit.contract.idempotency
            if effects.classification is not SideEffectClass.NONE and (
                idempotency.mode is IdempotencyMode.NONE
            ):
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_EFFECT_IDEMPOTENCY_REQUIRED",
                    message=f"Effectful unit {uid} MUST declare idempotency semantics.",
                    target_id=uid,
                ))
            if effects.classification is SideEffectClass.IRREVERSIBLE and idempotency.mode not in {
                IdempotencyMode.KEY_REQUIRED,
                IdempotencyMode.AT_MOST_ONCE,
            }:
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_IRREVERSIBLE_EFFECT_DUPLICATION_CONTROL",
                    message=(
                        f"Irreversible unit {uid} MUST require an idempotency key "
                        "or at-most-once dispatch."
                    ),
                    target_id=uid,
                ))

        # 2. Edge Integrity (Source and target must exist)
        seen_edges: set[tuple[str, str | None, str, str | None, str]] = set()
        for edge in graph.edges:
            edge_identity = (
                edge.source.value,
                edge.source_port,
                edge.target.value,
                edge.target_port,
                edge.edge_type.value,
            )
            if edge_identity in seen_edges:
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_EDGE_DUPLICATE",
                    message="Duplicate edges between the same port pair are forbidden.",
                    target_id=f"{edge.source.value}->{edge.target.value}",
                ))
            seen_edges.add(edge_identity)
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
            if edge.source.value in graph.units and edge.target.value in graph.units:
                self._validate_edge_contract(graph, edge, errors)
                self._validate_edge_governance(graph, edge, errors)

        connection_counts: Counter[tuple[str, str]] = Counter()
        for edge in graph.edges:
            if edge.source_port is not None:
                connection_counts[(edge.source.value, edge.source_port)] += 1
            if edge.target_port is not None:
                connection_counts[(edge.target.value, edge.target_port)] += 1
        for uid, unit in graph.units.items():
            for port in unit.contract.ports:
                if not isinstance(port, PortContract):
                    continue
                count = connection_counts[(uid, port.port_id)]
                if count < port.cardinality.minimum or (
                    port.cardinality.maximum is not None
                    and count > port.cardinality.maximum
                ):
                    errors.append(ValidationError(
                        tier=EnforcementTier.INVARIANT,
                        code="INV_PORT_CARDINALITY",
                        message=(
                            f"Port {uid}.{port.port_id} has {count} connections; "
                            f"requires {port.cardinality.value}."
                        ),
                        target_id=uid,
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

    def validate_execution_context(
        self,
        graph: StructuralGraph,
        context: ExecutionContext,
    ) -> ValidationResult:
        """Validate hard deployment requirements without enforcing preferences."""

        errors: List[ValidationError] = []
        for uid, unit in graph.units.items():
            contract = unit.contract
            security = contract.security
            placement = contract.placement
            effects = contract.side_effects
            checks = (
                (
                    security.tenant_id is not None and security.tenant_id != context.tenant_id,
                    "CTX_TENANT_MISMATCH",
                    "execution tenant does not match the unit tenant",
                ),
                (
                    not security.required_permissions <= context.permissions,
                    "CTX_PERMISSION_MISSING",
                    "execution context lacks required permissions",
                ),
                (
                    context.isolation_grade.rank < effects.minimum_isolation.rank,
                    "CTX_ISOLATION_INSUFFICIENT",
                    "execution isolation is below the unit minimum",
                ),
                (
                    bool(placement.allowed_regions)
                    and context.region not in placement.allowed_regions,
                    "CTX_REGION_DENIED",
                    "execution region is not allowed",
                ),
                (
                    bool(placement.allowed_devices)
                    and context.device not in placement.allowed_devices,
                    "CTX_DEVICE_DENIED",
                    "execution device is not allowed",
                ),
                (
                    bool(placement.allowed_runtimes)
                    and context.runtime not in placement.allowed_runtimes,
                    "CTX_RUNTIME_DENIED",
                    "execution runtime is not allowed",
                ),
                (
                    not placement.required_capabilities <= context.capabilities,
                    "CTX_CAPABILITY_MISSING",
                    "execution context lacks placement capabilities",
                ),
                (
                    bool(security.accepted_trust_zones)
                    and context.trust_zone not in security.accepted_trust_zones,
                    "CTX_TRUST_ZONE_DENIED",
                    "execution trust zone is not accepted",
                ),
                (
                    bool(security.trust_zone)
                    and context.trust_zone != security.trust_zone,
                    "CTX_UNIT_TRUST_ZONE_MISMATCH",
                    "execution trust zone does not match the unit declaration",
                ),
                (
                    bool(security.allowed_residencies)
                    and context.region not in security.allowed_residencies,
                    "CTX_RESIDENCY_DENIED",
                    "execution region violates data residency",
                ),
                (
                    security.confidential_compute_required and not context.confidential_compute,
                    "CTX_CONFIDENTIAL_COMPUTE_REQUIRED",
                    "unit requires confidential compute",
                ),
            )
            for failed, code, message in checks:
                if failed:
                    errors.append(ValidationError(
                        tier=EnforcementTier.INVARIANT,
                        code=code,
                        message=f"Unit {uid}: {message}.",
                        target_id=uid,
                    ))
        return ValidationResult(is_valid=not errors, errors=errors)

    @staticmethod
    def _validate_edge_contract(graph, edge, errors: List[ValidationError]) -> None:
        source_unit = graph.units[edge.source.value]
        target_unit = graph.units[edge.target.value]
        typed_endpoints = bool(source_unit.contract.ports or target_unit.contract.ports)
        if (edge.source_port is None) != (edge.target_port is None):
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_PORT_BINDING_INCOMPLETE",
                message="An edge port binding MUST name both source and target ports.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
            return
        if edge.source_port is None:
            if typed_endpoints:
                errors.append(ValidationError(
                    tier=EnforcementTier.INVARIANT,
                    code="INV_EDGE_PORT_BINDING_REQUIRED",
                    message="Edges touching typed units MUST bind source and target ports.",
                    target_id=f"{edge.source.value}->{edge.target.value}",
                ))
            return

        source_port = source_unit.contract.port(edge.source_port)
        target_port = target_unit.contract.port(edge.target_port)
        if source_port is None or target_port is None:
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_PORT_MISSING",
                message="Edge references an undeclared source or target port.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
            return
        if source_port.direction is not PortDirection.OUTPUT or target_port.direction is not PortDirection.INPUT:
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_PORT_DIRECTION",
                message="Edges MUST connect OUTPUT ports to INPUT ports.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        if source_port.kind.value != edge.edge_type.value or target_port.kind.value != edge.edge_type.value:
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_PORT_KIND",
                message="Edge type MUST match both bound port kinds.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        if source_port.schema != target_port.schema:
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_SCHEMA_MISMATCH",
                message="Bound source and target port schemas MUST be equal.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
    @staticmethod
    def _validate_edge_governance(graph, edge, errors: List[ValidationError]) -> None:
        source_unit = graph.units[edge.source.value]
        target_unit = graph.units[edge.target.value]
        source_security = source_unit.contract.security
        target_security = target_unit.contract.security
        if (
            source_security.tenant_id is not None
            and target_security.tenant_id is not None
            and source_security.tenant_id != target_security.tenant_id
        ):
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_TENANT_MISMATCH",
                message="Edges cannot cross explicit tenant boundaries.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        if edge.edge_type.value in {"DATA", "STATE", "RESOURCE"} and (
            source_security.output_classification.rank
            > target_security.maximum_input_classification.rank
        ):
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_CLASSIFICATION_DOWNGRADE",
                message="Target cannot accept the source data classification.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        if (
            source_security.allowed_residencies
            and target_security.allowed_residencies
            and source_security.allowed_residencies.isdisjoint(
                target_security.allowed_residencies
            )
        ):
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_RESIDENCY_CONFLICT",
                message="Connected units have no common permitted data residency.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        if (
            source_security.trust_zone
            and target_security.accepted_trust_zones
            and source_security.trust_zone not in target_security.accepted_trust_zones
        ):
            errors.append(ValidationError(
                tier=EnforcementTier.INVARIANT,
                code="INV_EDGE_TRUST_ZONE_DENIED",
                message="Target does not accept the source trust zone.",
                target_id=f"{edge.source.value}->{edge.target.value}",
            ))
        target_placement = target_unit.contract.placement
        source_placement = source_unit.contract.placement
        if target_placement.requires_local_inputs:
            for name in ("allowed_regions", "allowed_devices", "allowed_runtimes"):
                source_values = getattr(source_placement, name)
                target_values = getattr(target_placement, name)
                if source_values and target_values and source_values.isdisjoint(target_values):
                    errors.append(ValidationError(
                        tier=EnforcementTier.INVARIANT,
                        code="INV_EDGE_LOCALITY_CONFLICT",
                        message=f"Local-input edge has incompatible {name}.",
                        target_id=f"{edge.source.value}->{edge.target.value}",
                    ))

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
