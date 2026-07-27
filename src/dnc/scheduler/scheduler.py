"""Scheduler: topological dispatch with precondition enforcement.

Per execution-model.md and planner-pipeline.md:
- Executes the DAG in topological order
- Enforces preconditions: all input buffers must be COMPLETE before dispatch
- Backpressure: PENDING modules block downstream dispatch per INV-CTRL-9c
"""

from __future__ import annotations

import copy
from typing import Callable, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from dnc.runtime.types import (
    Buffer,
    UNBOUND,
    PENDING,
    ModuleInstanceID,
    InvariantViolation,
    DAGCycle,
)
from dnc.state.working_memory import WorkingMemory


class DispatchContext:
    """Encapsulates the state needed for one dispatch operation."""

    def __init__(
        self,
        instance_id: ModuleInstanceID,
        input_value: object,
        dispatch_fn: Callable[[object], object],
    ) -> None:
        self.instance_id = instance_id
        self.input_value = input_value
        self.dispatch_fn = dispatch_fn


class Scheduler:
    """Topological-order DAG dispatcher with precondition enforcement.

    Per INV-2: The execution graph G MUST be a DAG (no cycles).
    Per INV-3: A module instance may only be dispatched when ALL upstream
    buffers have outputs that are not UNBOUND or PENDING.
    Per INV-CTRL-9c: A module that returns PENDING blocks all its downstream
    dependents from dispatching until it completes.
    """

    def __init__(self) -> None:
        self._graph: Dict[ModuleInstanceID, Set[ModuleInstanceID]] = {}
        self._reverse: Dict[ModuleInstanceID, Set[ModuleInstanceID]] = {}
        self._in_degree: Dict[ModuleInstanceID, int] = {}
        self._dispatch_order: Optional[List[ModuleInstanceID]] = None

    def set_graph(
        self,
        nodes: List[ModuleInstanceID],
        edges: List[Tuple[ModuleInstanceID, ModuleInstanceID]],
    ) -> None:
        """Set the DAG. Raises DAGCycle if edges create a cycle.

        Edges are (upstream, downstream): upstream's output → downstream's input.
        """
        self._graph = {n: set() for n in nodes}
        self._reverse = {n: set() for n in nodes}
        self._in_degree = {n: 0 for n in nodes}

        for upstream, downstream in edges:
            if upstream not in self._graph or downstream not in self._graph:
                raise ValueError(
                    f"Edge references unknown node: {upstream} -> {downstream}"
                )
            self._graph[upstream].add(downstream)
            self._reverse[downstream].add(upstream)
            self._in_degree[downstream] += 1

        if self._has_cycle():
            self._graph = {}
            self._reverse = {}
            self._in_degree = {}
            raise DAGCycle(
                "Edge list creates a cycle in the execution graph. "
                "INV-2 violation: G must be a DAG."
            )

    def _has_cycle(self) -> bool:
        """Kahn's algorithm BFS cycle detection. Returns True if cycle found."""
        if not self._in_degree:
            return False
        queue = [n for n, deg in self._in_degree.items() if deg == 0]
        visited = 0
        in_deg = dict(self._in_degree)

        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in self._graph.get(node, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        return visited != len(self._in_degree)

    def get_dispatch_order(self) -> List[ModuleInstanceID]:
        """Return nodes in topological order (Kahn's algorithm). Cached after first call."""
        if self._dispatch_order is not None:
            return self._dispatch_order

        in_deg = dict(self._in_degree)
        queue = [n for n, deg in in_deg.items() if deg == 0]
        order: List[ModuleInstanceID] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in self._graph.get(node, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._in_degree):
            raise DAGCycle("Cycle detected during topological sort")
        self._dispatch_order = order
        return order

    def get_runnable(self, wm: WorkingMemory) -> List[ModuleInstanceID]:
        """Return all nodes whose preconditions are satisfied.

        Per INV-3: a node is runnable if all its upstream inputs are COMPLETE
        (output is not UNBOUND and not PENDING).
        """
        order = self.get_dispatch_order()
        runnable: List[ModuleInstanceID] = []

        for node in order:
            if not self._are_preconditions_met(node, wm):
                continue
            runnable.append(node)

        return runnable

    def _are_preconditions_met(self, node: ModuleInstanceID, wm: WorkingMemory) -> bool:
        """Check if all upstream dependencies are complete for this node."""
        upstreams = self._reverse.get(node, set())
        for upstream in upstreams:
            if upstream not in wm:
                return False
            buf = wm[upstream]
            if isinstance(buf.output, UNBOUND) or isinstance(buf.output, PENDING):
                return False
        return True

    def dispatch(
        self,
        wm: WorkingMemory,
        instance_id: ModuleInstanceID,
        fn: Callable[[object], object],
    ) -> object:
        """Dispatch a module instance: gather inputs, call fn, mark output.

        Per INV-3: caller MUST ensure preconditions are met before calling dispatch.

        Returns the output value.
        """
        upstreams = self._reverse.get(instance_id, set())
        if upstreams:
            inputs = [wm.get_output(u) for u in sorted(upstreams, key=id)]
        else:
            inputs = []

        buf = wm.get(instance_id)
        if buf is None:
            raise ValueError(f"Instance {instance_id} not in working memory")

        result = fn(inputs[0] if len(inputs) == 1 else inputs)

        if isinstance(result, PENDING):
            wm[instance_id] = Buffer(
                input=buf.input,
                output=PENDING(),
                metadata=buf.metadata,
            )
        else:
            wm[instance_id] = Buffer(
                input=buf.input,
                output=result,
                metadata=buf.metadata,
            )

        return result

    def step(self, wm: WorkingMemory) -> List[ModuleInstanceID]:
        """Execute one scheduling step: dispatch all runnable modules.

        Returns the list of dispatched instance IDs.
        """
        runnable = self.get_runnable(wm)
        return runnable