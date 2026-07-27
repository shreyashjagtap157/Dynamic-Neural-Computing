"""
DNC Mutation Engine (Mutation Semantics & Transaction Semantics)
Applies authorized structural operations to StructuralGraphs and records inverse compensation.
"""

from typing import Tuple, List, Optional
from dnc.ir.graph import StructuralGraph, Edge, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.unit import ComputationalUnit
from dnc.ir.identity import UnitID, IdentityRegistry
from .undo import UndoLog, InverseOperation

class MutationEngine:
    """
    Applies authorized structural mutations to a StructuralGraph, updating graph version
    and populating undo logs for rollback compensation.
    """
    def __init__(self, identity_registry: Optional[IdentityRegistry] = None):
        self.identity_registry = identity_registry

    def apply_operation(self, graph: StructuralGraph, operation: IROperation) -> Tuple[bool, List[str], UndoLog]:
        undo_log = UndoLog()
        warnings: List[str] = []

        if not operation.validate():
            return False, ["Operation parameters invalid."], undo_log

        try:
            if operation.op_type == OperationType.ADD_UNIT:
                unit: ComputationalUnit = operation.parameters["unit"]
                retired = set(graph.metadata.get("retired_unit_ids", []))
                if unit.unit_id.value in retired:
                    raise ValueError(
                        f"Identity Violation: Retired UnitID {unit.unit_id} cannot be reused."
                    )
                graph.add_unit(unit)
                # Inverse of ADD_UNIT is REMOVE_UNIT
                undo_log.push(InverseOperation("REMOVE_UNIT", {"unit_id": unit.unit_id}))

            elif operation.op_type == OperationType.REMOVE_UNIT:
                unit_id: UnitID = operation.parameters["unit_id"]
                uid_str = unit_id.value
                if uid_str not in graph.units:
                    return False, [f"Unit {unit_id} not found for removal."], undo_log
                removed_unit = graph.units[uid_str]
                # Capture incident edges for inverse restoration
                incident_edges = [e for e in graph.edges if e.source.value == uid_str or e.target.value == uid_str]
                graph.remove_unit(unit_id)
                retired = set(graph.metadata.get("retired_unit_ids", []))
                retired.add(unit_id.value)
                graph.metadata["retired_unit_ids"] = sorted(retired)
                # Inverse of REMOVE_UNIT is ADD_UNIT + restoring edges
                undo_log.push(InverseOperation("RESTORE_UNIT", {"unit": removed_unit, "edges": incident_edges}))

            elif operation.op_type == OperationType.CONNECT_UNITS:
                source: UnitID = operation.parameters["source"]
                target: UnitID = operation.parameters["target"]
                edge_type: EdgeType = operation.parameters["edge_type"]
                metadata = operation.parameters.get("metadata", {})
                
                edge = Edge(source=source, target=target, edge_type=edge_type, metadata=metadata)
                graph.add_edge(edge)
                # Inverse of CONNECT_UNITS is DISCONNECT_UNITS
                undo_log.push(InverseOperation("DISCONNECT_UNITS", {"source": source, "target": target, "edge_type": edge_type}))

            elif operation.op_type == OperationType.DISCONNECT_UNITS:
                source: UnitID = operation.parameters["source"]
                target: UnitID = operation.parameters["target"]
                edge_type: Optional[EdgeType] = operation.parameters.get("edge_type", None)
                
                # Find matching edges to remove
                removed_edges = []
                new_edges = []
                for e in graph.edges:
                    match = (e.source.value == source.value and e.target.value == target.value)
                    if edge_type:
                        match = match and (e.edge_type == edge_type)
                    if match:
                        removed_edges.append(e)
                    else:
                        new_edges.append(e)
                graph.edges = new_edges
                # Inverse is reconnecting removed edges
                undo_log.push(InverseOperation("RESTORE_EDGES", {"edges": removed_edges}))

            elif operation.op_type == OperationType.REWIRE_EDGE:
                old_source: UnitID = operation.parameters["old_source"]
                old_target: UnitID = operation.parameters["old_target"]
                new_source: UnitID = operation.parameters["new_source"]
                new_target: UnitID = operation.parameters["new_target"]
                
                # Find and update edge
                found = False
                for e in graph.edges:
                    if e.source.value == old_source.value and e.target.value == old_target.value:
                        e.source = new_source
                        e.target = new_target
                        found = True
                        break
                if not found:
                    return False, ["Edge to rewire not found."], undo_log
                # Inverse is rewiring back
                undo_log.push(InverseOperation("REWIRE_EDGE", {"old_source": new_source, "old_target": new_target, "new_source": old_source, "new_target": old_target}))

            else:
                return False, [f"Unsupported operation type {operation.op_type}"], undo_log

            # Increment graph version sequence on success
            graph.version = graph.version.next_sequence()
            return True, warnings, undo_log

        except Exception as e:
            return False, [str(e)], undo_log

    def rollback(self, graph: StructuralGraph, undo_log: UndoLog) -> None:
        """
        Rolls back applied mutations using the recorded undo log in reverse order.
        """
        inverses = undo_log.pop_all()
        for inv in inverses:
            if inv.op_name == "REMOVE_UNIT":
                graph.remove_unit(inv.parameters["unit_id"])
            elif inv.op_name == "RESTORE_UNIT":
                unit: ComputationalUnit = inv.parameters["unit"]
                graph.add_unit(unit)
                for e in inv.parameters.get("edges", []):
                    graph.add_edge(e)
            elif inv.op_name == "DISCONNECT_UNITS":
                graph.remove_edge(inv.parameters["source"], inv.parameters["target"], inv.parameters.get("edge_type"))
            elif inv.op_name == "RESTORE_EDGES":
                for e in inv.parameters.get("edges", []):
                    graph.add_edge(e)
            elif inv.op_name == "REWIRE_EDGE":
                old_s = inv.parameters["old_source"]
                old_t = inv.parameters["old_target"]
                new_s = inv.parameters["new_source"]
                new_t = inv.parameters["new_target"]
                for e in graph.edges:
                    if e.source.value == old_s.value and e.target.value == old_t.value:
                        e.source = new_s
                        e.target = new_t
                        break
        # Decrement version sequence or mark rollback in metadata
        graph.version = graph.version.next_sequence()
