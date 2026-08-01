"""
DNC-IR Deterministic Serialization (SPEC-IR Section 14, 15)
Implements canonical JSON / dict export and import for StructuralGraph.
"""

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Any
from dnc.kernel.versioning import schema_header
from dnc.ir.schema import validate_ir_document
from .graph import StructuralGraph, Edge, EdgeType
from .identity import GraphID, GraphVersion, UnitID
from .unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension, UnitContract, MutationContract, Constraint, EnforcementTier
from .contracts import PortCardinality, PortContract, PortDirection, PortKind

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
        sorted_edges = sorted(graph.edges, key=lambda e: (e.source.value, e.target.value, e.edge_type.value))
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
        d = json.loads(json_str)
        return DNWIRSerializer.from_dict(d)
