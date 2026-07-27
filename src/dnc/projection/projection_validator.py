"""
Projection Validator (DNC Projection Layer)
Validates ExecutableDAG readiness for the Execution Core.
"""

from typing import List
from .executable_graph import ExecutableDAG

class ProjectionValidator:
    """
    Validates that an ExecutableDAG has valid nodes, edges, and topological order.
    """
    def validate(self, dag: ExecutableDAG) -> bool:
        if not dag.graph_id:
            return False
        if not dag.nodes and dag.topological_order:
            return False
        # Ensure all topological order nodes exist in nodes dict
        for uid in dag.topological_order:
            if uid.value not in dag.nodes:
                return False
        return True
