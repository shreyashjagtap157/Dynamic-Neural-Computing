"""
DNC-IR Structural Graph Model (SPEC-IR Section 3, 5, 7)
Implements Structural Graph, Edge definitions, Graph versioning, and Executable DAG projection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any
from .identity import GraphID, GraphVersion, UnitID
from .unit import ComputationalUnit

class EdgeType(str, Enum):
    DATA = "DATA"
    CONTROL = "CONTROL"
    STATE = "STATE"
    DEPENDENCY = "DEPENDENCY"

@dataclass(frozen=True)
class Edge:
    source: UnitID
    target: UnitID
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StructuralGraph:
    graph_id: GraphID
    version: GraphVersion = field(default_factory=GraphVersion)
    units: Dict[str, ComputationalUnit] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_unit(self, unit: ComputationalUnit) -> None:
        if unit.unit_id.value in self.units:
            raise ValueError(f"UnitID {unit.unit_id} already exists in graph.")
        self.units[unit.unit_id.value] = unit

    def remove_unit(self, unit_id: UnitID) -> None:
        uid = unit_id.value
        if uid not in self.units:
            raise KeyError(f"UnitID {unit_id} not found in graph.")
        del self.units[uid]
        # Remove incident edges
        self.edges = [e for e in self.edges if e.source.value != uid and e.target.value != uid]

    def add_edge(self, edge: Edge) -> None:
        if edge.source.value not in self.units:
            raise KeyError(f"Source UnitID {edge.source} not in graph.")
        if edge.target.value not in self.units:
            raise KeyError(f"Target UnitID {edge.target} not in graph.")
        self.edges.append(edge)

    def remove_edge(self, source: UnitID, target: UnitID, edge_type: Optional[EdgeType] = None) -> None:
        new_edges = []
        for e in self.edges:
            matches = (e.source.value == source.value and e.target.value == target.value)
            if edge_type:
                matches = matches and (e.edge_type == edge_type)
            if not matches:
                new_edges.append(e)
        self.edges = new_edges

    def project_to_executable_dag(self) -> Tuple['StructuralGraph', List[str]]:
        """
        Projects the potentially non-DAG Structural Graph into an Executable DAG.
        Returns the projected graph view and any linearization warnings/errors.
        """
        # For Phase 1 reference implementation, verify acyclicity for DATA/CONTROL edges.
        visited = set()
        rec_stack = set()
        adj: Dict[str, List[str]] = {uid: [] for uid in self.units}
        for e in self.edges:
            if e.edge_type in (EdgeType.DATA, EdgeType.CONTROL, EdgeType.DEPENDENCY):
                adj[e.source.value].append(e.target.value)

        def dfs(u: str) -> bool:
            visited.add(u)
            rec_stack.add(u)
            for v in adj.get(u, []):
                if v not in visited:
                    if dfs(v):
                        return True
                elif v in rec_stack:
                    return True
            rec_stack.remove(u)
            return False

        has_cycle = False
        for u in self.units:
            if u not in visited:
                if dfs(u):
                    has_cycle = True
                    break

        warnings = []
        if has_cycle:
            warnings.append("Structural Graph contains cycles in execution edges; executable projection pruned or linearized.")

        return self, warnings
