"""
Structural Graph to Executable DAG Projector (DNC Projection Layer)
Implements deterministic lowering of a valid DNC-IR Structural Graph into an Executable DAG.
"""

from typing import Tuple, List, Dict
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.contracts import ExecutionContext
from dnc.ir.validator import DNCIRValidator
from .executable_graph import ExecutableDAG, ExecutableNode, ExecutableEdge

class StructuralProjector:
    """
    Deterministically projects a validated Structural Graph into an Executable DAG.
    Enforces the invariant: Structural Graph remains unchanged.
    """
    def __init__(self, validator: DNCIRValidator = None):
        self.validator = validator or DNCIRValidator()

    def project(
        self,
        graph: StructuralGraph,
        context: ExecutionContext | None = None,
    ) -> Tuple[ExecutableDAG, List[str]]:
        # 1. Validate structural graph prior to projection
        val_res = self.validator.validate_graph(graph)
        if not val_res.is_valid:
            raise ValueError(f"Cannot project invalid Structural Graph: {val_res.errors}")
        requires_context = any(
            unit.contract.requires_execution_context() for unit in graph.units.values()
        )
        if requires_context and context is None:
            raise ValueError("Cannot project governed graph without an ExecutionContext")
        if context is not None:
            context_result = self.validator.validate_execution_context(graph, context)
            if not context_result.is_valid:
                raise ValueError(
                    f"ExecutionContext does not satisfy Structural Graph: {context_result.errors}"
                )

        warnings: List[str] = []

        # 2. Build adjacency for topological sorting (DATA, CONTROL, DEPENDENCY edges)
        adj: Dict[str, List[str]] = {uid: [] for uid in graph.units}
        in_degree: Dict[str, int] = {uid: 0 for uid in graph.units}

        for e in graph.edges:
            if e.edge_type in (EdgeType.DATA, EdgeType.CONTROL, EdgeType.DEPENDENCY):
                src = e.source.value
                tgt = e.target.value
                if src in adj and tgt in in_degree:
                    adj[src].append(tgt)
                    in_degree[tgt] += 1

        # 3. Kahn's algorithm for topological sorting / cycle detection
        queue = [uid for uid, deg in in_degree.items() if deg == 0]
        # Sort queue for determinism
        queue.sort()
        
        topo_order = []
        while queue:
            u = queue.pop(0)
            topo_order.append(graph.units[u].unit_id)
            for v in sorted(adj.get(u, [])):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(topo_order) != len(graph.units):
            warnings.append("Structural graph contains cycles in execution edges; topological sort linearized via fallback order.")
            # Fallback: include remaining units deterministically
            remaining = sorted([uid for uid in graph.units if graph.units[uid].unit_id not in topo_order])
            for r in remaining:
                topo_order.append(graph.units[r].unit_id)

        # 4. Construct ExecutableDAG
        exec_dag = ExecutableDAG(
            graph_id=graph.graph_id,
            source_version=graph.version,
            topological_order=topo_order,
            metadata=dict(graph.metadata)
        )

        for uid, unit in sorted(graph.units.items()):
            exec_dag.nodes[uid] = ExecutableNode(
                unit_id=unit.unit_id,
                name=unit.name,
                metadata=dict(unit.metadata),
                idempotency=unit.contract.idempotency,
                side_effects=unit.contract.side_effects,
                placement=unit.contract.placement,
                security=unit.contract.security,
            )

        sorted_edges = sorted(graph.edges, key=lambda e: (e.source.value, e.target.value, e.edge_type.value))
        for e in sorted_edges:
            exec_dag.edges.append(ExecutableEdge(
                source=e.source,
                target=e.target,
                edge_type=e.edge_type.value,
                metadata=dict(e.metadata),
                source_port=e.source_port,
                target_port=e.target_port,
            ))

        return exec_dag, warnings
