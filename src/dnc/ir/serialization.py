"""
DNC-IR Deterministic Serialization (SPEC-IR Section 14, 15)
Implements canonical JSON / dict export and import for StructuralGraph.
"""

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Any
from dnc.kernel.errors import DNCValidationError
from dnc.kernel.versioning import schema_header
from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass
from dnc.ir.schema import validate_ir_document
from .graph import StructuralGraph, Edge, EdgeType
from .identity import GraphID, GraphVersion, UnitID
from .unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension, UnitContract, MutationContract, Constraint, EnforcementTier
from .contracts import (
    DataClassification,
    IdempotencyContract,
    IdempotencyMode,
    IdempotencyScope,
    PlacementContract,
    PortCardinality,
    PortContract,
    PortDirection,
    PortKind,
    SecurityContract,
    SideEffectContract,
)

class DNWIRSerializer:
    """
    Provides deterministic serialization of DNC-IR graphs.
    """
    @staticmethod
    def to_dict(graph: StructuralGraph) -> Dict[str, Any]:
        data = {
            **schema_header(),
            "graph_id": graph.graph_id.value,
            "version": {
                "major": graph.version.major,
                "minor": graph.version.minor,
                "patch": graph.version.patch,
                "sequence": graph.version.sequence
            },
            "units": {},
            "edges": [],
            "metadata": graph.metadata
        }
        
        # Sort units by ID for determinism
        sorted_unit_ids = sorted(graph.units.keys())
        for uid in sorted_unit_ids:
            u = graph.units[uid]
            data["units"][uid] = {
                "unit_id": u.unit_id.value,
                "name": u.name,
                "structure": u.structure.value,
                "visibility": u.visibility.value,
                "lifecycle": u.lifecycle.value,
                "contract": {
                    "input_schema": deepcopy(u.contract.input_schema),
                    "output_schema": deepcopy(u.contract.output_schema),
                    "preconditions": deepcopy(u.contract.preconditions),
                    "postconditions": deepcopy(u.contract.postconditions),
                    "resource_limits": deepcopy(u.contract.resource_limits),
                    "ports": [
                        {
                            "port_id": port.port_id,
                            "direction": port.direction.value,
                            "kind": port.kind.value,
                            "schema": deepcopy(port.schema),
                            "cardinality": port.cardinality.value,
                            "description": port.description,
                        }
                        for port in u.contract.ports
                    ],
                    "idempotency": {
                        "mode": u.contract.idempotency.mode.value,
                        "scope": u.contract.idempotency.scope.value,
                        "key_field": u.contract.idempotency.key_field,
                        "payload_hash_required": u.contract.idempotency.payload_hash_required,
                    },
                    "side_effects": {
                        "classification": u.contract.side_effects.classification.value,
                        "effect_types": sorted(
                            item.value for item in u.contract.side_effects.effect_types
                        ),
                        "compensation_action": u.contract.side_effects.compensation_action,
                        "minimum_isolation": u.contract.side_effects.minimum_isolation.value,
                    },
                    "placement": {
                        "allowed_regions": sorted(u.contract.placement.allowed_regions),
                        "allowed_devices": sorted(u.contract.placement.allowed_devices),
                        "allowed_runtimes": sorted(u.contract.placement.allowed_runtimes),
                        "required_capabilities": sorted(
                            u.contract.placement.required_capabilities
                        ),
                        "preferred_regions": list(u.contract.placement.preferred_regions),
                        "preferred_devices": list(u.contract.placement.preferred_devices),
                        "requires_local_inputs": u.contract.placement.requires_local_inputs,
                    },
                    "security": {
                        "tenant_id": u.contract.security.tenant_id,
                        "required_permissions": sorted(
                            u.contract.security.required_permissions
                        ),
                        "security_labels": sorted(u.contract.security.security_labels),
                        "output_classification": (
                            u.contract.security.output_classification.value
                        ),
                        "maximum_input_classification": (
                            u.contract.security.maximum_input_classification.value
                        ),
                        "allowed_residencies": sorted(
                            u.contract.security.allowed_residencies
                        ),
                        "trust_zone": u.contract.security.trust_zone,
                        "accepted_trust_zones": sorted(
                            u.contract.security.accepted_trust_zones
                        ),
                        "confidential_compute_required": (
                            u.contract.security.confidential_compute_required
                        ),
                    },
                },
                "mutation_contract": {
                    **asdict(u.mutation_contract),
                    "allowed_mutations": sorted(u.mutation_contract.allowed_mutations),
                },
                "constraints": [asdict(c) for c in u.constraints],
                "metadata": u.metadata,
                "sub_units": [str(s) for s in u.sub_units]
            }

        # Sort edges by source, target, type for determinism
        sorted_edges = sorted(
            graph.edges,
            key=lambda e: (
                e.source.value,
                e.target.value,
                e.edge_type.value,
                e.source_port or "",
                e.target_port or "",
            ),
        )
        for e in sorted_edges:
            data["edges"].append({
                "source": e.source.value,
                "target": e.target.value,
                "edge_type": e.edge_type.value,
                "metadata": e.metadata,
                "source_port": e.source_port,
                "target_port": e.target_port,
            })

        return data

    @staticmethod
    def to_json(graph: StructuralGraph) -> str:
        d = DNWIRSerializer.to_dict(graph)
        return json.dumps(d, sort_keys=True, indent=2)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> StructuralGraph:
        # Version metadata was added after the original freeze. Older vectors
        # without schema headers remain valid inputs for compatibility.
        validate_ir_document(data)
        try:
            return DNWIRSerializer._from_validated_dict(data)
        except DNCValidationError:
            raise
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
            raise DNCValidationError("invalid DNC-IR document semantics") from error

    @staticmethod
    def _from_validated_dict(data: Dict[str, Any]) -> StructuralGraph:
        g_id = GraphID(data["graph_id"])
        v_data = data.get("version", {})
        version = GraphVersion(
            major=v_data.get("major", 1),
            minor=v_data.get("minor", 0),
            patch=v_data.get("patch", 0),
            sequence=v_data.get("sequence", 0)
        )
        
        graph = StructuralGraph(graph_id=g_id, version=version, metadata=data.get("metadata", {}))

        for uid, u_data in data.get("units", {}).items():
            u = ComputationalUnit(
                unit_id=UnitID(u_data["unit_id"]),
                name=u_data["name"],
                structure=StructureDimension(u_data["structure"]),
                visibility=VisibilityDimension(u_data["visibility"]),
                lifecycle=LifecycleDimension(u_data["lifecycle"]),
                sub_units=[UnitID(s) for s in u_data.get("sub_units", [])],
                metadata=u_data.get("metadata", {})
            )
            c_data = dict(u_data.get("contract", {}))
            port_data = c_data.pop("ports", [])
            idempotency_data = c_data.pop("idempotency", {})
            side_effect_data = c_data.pop("side_effects", {})
            placement_data = c_data.pop("placement", {})
            security_data = c_data.pop("security", {})
            u.contract = UnitContract(
                **c_data,
                ports=[
                    PortContract(
                        port_id=port["port_id"],
                        direction=PortDirection(port["direction"]),
                        kind=PortKind(port["kind"]),
                        schema=port.get("schema", {}),
                        cardinality=PortCardinality(
                            port.get("cardinality", PortCardinality.EXACTLY_ONE.value)
                        ),
                        description=port.get("description", ""),
                    )
                    for port in port_data
                ],
                idempotency=IdempotencyContract(
                    mode=IdempotencyMode(
                        idempotency_data.get("mode", IdempotencyMode.NONE.value)
                    ),
                    scope=IdempotencyScope(
                        idempotency_data.get("scope", IdempotencyScope.TASK.value)
                    ),
                    key_field=idempotency_data.get("key_field"),
                    payload_hash_required=idempotency_data.get(
                        "payload_hash_required", True
                    ),
                ),
                side_effects=SideEffectContract(
                    classification=SideEffectClass(
                        side_effect_data.get(
                            "classification", SideEffectClass.NONE.value
                        )
                    ),
                    effect_types=frozenset(
                        EffectType(value)
                        for value in side_effect_data.get("effect_types", [])
                    ),
                    compensation_action=side_effect_data.get("compensation_action"),
                    minimum_isolation=IsolationGrade(
                        side_effect_data.get(
                            "minimum_isolation", IsolationGrade.I0_NONE.value
                        )
                    ),
                ),
                placement=PlacementContract(
                    allowed_regions=frozenset(placement_data.get("allowed_regions", [])),
                    allowed_devices=frozenset(placement_data.get("allowed_devices", [])),
                    allowed_runtimes=frozenset(placement_data.get("allowed_runtimes", [])),
                    required_capabilities=frozenset(
                        placement_data.get("required_capabilities", [])
                    ),
                    preferred_regions=tuple(placement_data.get("preferred_regions", [])),
                    preferred_devices=tuple(placement_data.get("preferred_devices", [])),
                    requires_local_inputs=placement_data.get("requires_local_inputs", False),
                ),
                security=SecurityContract(
                    tenant_id=security_data.get("tenant_id"),
                    required_permissions=frozenset(
                        security_data.get("required_permissions", [])
                    ),
                    security_labels=frozenset(security_data.get("security_labels", [])),
                    output_classification=DataClassification(
                        security_data.get(
                            "output_classification", DataClassification.INTERNAL.value
                        )
                    ),
                    maximum_input_classification=DataClassification(
                        security_data.get(
                            "maximum_input_classification",
                            DataClassification.RESTRICTED.value,
                        )
                    ),
                    allowed_residencies=frozenset(
                        security_data.get("allowed_residencies", [])
                    ),
                    trust_zone=security_data.get("trust_zone", ""),
                    accepted_trust_zones=frozenset(
                        security_data.get("accepted_trust_zones", [])
                    ),
                    confidential_compute_required=security_data.get(
                        "confidential_compute_required", False
                    ),
                ),
            )
            
            mc_data = u_data.get("mutation_contract", {})
            u.mutation_contract = MutationContract(
                allowed_mutations=set(mc_data.get("allowed_mutations", [])),
                max_children=mc_data.get("max_children", 100),
                is_immutable=mc_data.get("is_immutable", False)
            )

            for const_data in u_data.get("constraints", []):
                u.constraints.append(Constraint(
                    constraint_id=const_data["constraint_id"],
                    tier=EnforcementTier(const_data["tier"]),
                    expression=const_data["expression"],
                    description=const_data["description"]
                ))
            graph.add_unit(u)

        for e_data in data.get("edges", []):
            edge = Edge(
                source=UnitID(e_data["source"]),
                target=UnitID(e_data["target"]),
                edge_type=EdgeType(e_data["edge_type"]),
                metadata=e_data.get("metadata", {}),
                source_port=e_data.get("source_port"),
                target_port=e_data.get("target_port"),
            )
            graph.add_edge(edge)

        return graph

    @staticmethod
    def from_json(json_str: str) -> StructuralGraph:
        try:
            d = json.loads(json_str)
        except (TypeError, json.JSONDecodeError) as error:
            raise DNCValidationError("DNC-IR payload MUST be valid JSON") from error
        return DNWIRSerializer.from_dict(d)
