"""
Executable DAG Representation (DNC Projection Layer)
Defines the execution-oriented projection of a DNC-IR Structural Graph.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from dnc.ir.identity import GraphID, GraphVersion, UnitID

@dataclass
class ExecutableNode:
    unit_id: UnitID
    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutableEdge:
    source: UnitID
    target: UnitID
    edge_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_port: str | None = None
    target_port: str | None = None

@dataclass
class ExecutableDAG:
    graph_id: GraphID
    source_version: GraphVersion
    nodes: Dict[str, ExecutableNode] = field(default_factory=dict)
    edges: List[ExecutableEdge] = field(default_factory=list)
    topological_order: List[UnitID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
