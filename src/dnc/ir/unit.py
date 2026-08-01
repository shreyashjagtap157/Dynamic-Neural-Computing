"""
DNC-IR Computational Unit Specification (SPEC-IR Section 4, 8, 9, 10, 11)
Implements ComputationalUnit, three orthogonal dimensions, contracts, capabilities, and constraints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Set
from dnc.kernel.contracts import SideEffectClass
from .contracts import (
    IdempotencyContract,
    PlacementContract,
    PortContract,
    SecurityContract,
    SideEffectContract,
)
from .identity import UnitID

class StructureDimension(str, Enum):
    PRIMITIVE = "PRIMITIVE"
    COMPOSITE = "COMPOSITE"

class VisibilityDimension(str, Enum):
    OPAQUE = "OPAQUE"
    INSPECTABLE = "INSPECTABLE"

class LifecycleDimension(str, Enum):
    BASE = "BASE"
    SPECIALIZED = "SPECIALIZED"

class EnforcementTier(str, Enum):
    INVARIANT = "INVARIANT"     # Absolute; violation halts or rejects immediately
    CONSTRAINT = "CONSTRAINT"   # Negotiable within operational bounds
    POLICY = "POLICY"           # Advisory / preference rule

@dataclass
class UnitContract:
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    ports: List[PortContract] = field(default_factory=list)
    idempotency: IdempotencyContract = field(default_factory=IdempotencyContract)
    side_effects: SideEffectContract = field(default_factory=SideEffectContract)
    placement: PlacementContract = field(default_factory=PlacementContract)
    security: SecurityContract = field(default_factory=SecurityContract)

    def port(self, port_id: str) -> PortContract | None:
        return next((port for port in self.ports if port.port_id == port_id), None)

    def validate_ports(self) -> bool:
        if not all(isinstance(port, PortContract) for port in self.ports):
            return False
        identifiers = [port.port_id for port in self.ports]
        return len(identifiers) == len(set(identifiers))

    def requires_execution_context(self) -> bool:
        return bool(
            self.side_effects.classification is not SideEffectClass.NONE
            or self.placement.allowed_regions
            or self.placement.allowed_devices
            or self.placement.allowed_runtimes
            or self.placement.required_capabilities
            or self.placement.requires_local_inputs
            or self.security.tenant_id
            or self.security.required_permissions
            or self.security.allowed_residencies
            or self.security.trust_zone
            or self.security.accepted_trust_zones
            or self.security.confidential_compute_required
        )

@dataclass
class MutationContract:
    allowed_mutations: Set[str] = field(default_factory=lambda: {"ADD", "REMOVE", "CONNECT", "DISCONNECT", "REWIRE"})
    max_children: int = 100
    is_immutable: bool = False

@dataclass
class Constraint:
    constraint_id: str
    tier: EnforcementTier
    expression: str
    description: str

@dataclass
class ComputationalUnit:
    unit_id: UnitID
    name: str
    structure: StructureDimension
    visibility: VisibilityDimension
    lifecycle: LifecycleDimension
    contract: UnitContract = field(default_factory=UnitContract)
    mutation_contract: MutationContract = field(default_factory=MutationContract)
    constraints: List[Constraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sub_units: List[UnitID] = field(default_factory=list)  # For COMPOSITE units

    def validate_dimensions(self) -> bool:
        if self.structure == StructureDimension.PRIMITIVE and len(self.sub_units) > 0:
            return False
        if self.structure == StructureDimension.COMPOSITE and len(self.sub_units) == 0:
            # Composite units may have sub-units or be empty pending composition
            pass
        return True
