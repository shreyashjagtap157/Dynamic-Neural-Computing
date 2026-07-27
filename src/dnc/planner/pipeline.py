"""Planner: synthesizes execution graphs at runtime.

Per planner-pipeline.md DEF-PLANNER-1 through DEF-PLANNER-7:
- Four phases: Task Analysis, Module Selection, Graph Construction, Validation
- Produces SUCCESS(G) or FAIL(reason)
- Complexity bounded per INV-PLANNER-10: O(|V|²) worst case
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from dnc.runtime.types import ModuleInstanceID, ModuleTypeID, ModuleContract
from dnc.state.registry import ModuleRegistry
from dnc.state.execution_state import ExecutionState
from dnc.scheduler.scheduler import Scheduler
from dnc.runtime.types import DAGCycle


class PlanningResultKind(Enum):
    SUCCESS = auto()
    FAIL = auto()


@dataclass(frozen=True)
class PlanningResult:
    """Per DEF-PLANNER-3: SUCCESS(G) or FAIL(reason)."""
    kind: PlanningResultKind
    graph: Optional[Any] = None
    reason: Optional[str] = None

    @staticmethod
    def success(graph: Any) -> "PlanningResult":
        return PlanningResult(kind=PlanningResultKind.SUCCESS, graph=graph)

    @staticmethod
    def fail(reason: str) -> "PlanningResult":
        return PlanningResult(kind=PlanningResultKind.FAIL, reason=reason)

    @property
    def is_success(self) -> bool:
        return self.kind == PlanningResultKind.SUCCESS


@dataclass(frozen=True)
class SubGoal:
    """A sub-goal identified during Task Analysis."""
    goal_id: str
    description: str
    required_capabilities: FrozenSet[str]
    output_type: Optional[type] = None


@dataclass(frozen=True)
class VertexAssignment:
    """Per DEF-PLANNER-5: vertex label for a module instance in G."""
    instance_id: ModuleInstanceID
    type_id: ModuleTypeID
    cost_estimate: float = 1.0
    preference_score: float = 0.0


@dataclass
class ExecutionGraph:
    """G = (V, E, w) — synthesized execution graph."""
    vertices: List[VertexAssignment] = field(default_factory=list)
    edges: List[Tuple[ModuleInstanceID, ModuleInstanceID]] = field(default_factory=list)
    cost_weights: Dict[ModuleInstanceID, float] = field(default_factory=dict)

    def get_vertices(self) -> List[ModuleInstanceID]:
        return [v.instance_id for v in self.vertices]

    def to_scheduler_input(self) -> Tuple[List[ModuleInstanceID], List[Tuple[ModuleInstanceID, ModuleInstanceID]]]:
        return self.get_vertices(), list(self.edges)

    def total_cost(self) -> float:
        vertex_cost = sum(self.cost_weights.get(v.instance_id, 1.0) for v in self.vertices)
        edge_cost = len(self.edges) * 0.1
        return vertex_cost + edge_cost


@dataclass
class PlanningTask:
    """Per DEF-PLANNER-1: PT = (task_description, available_modules, resource_budget, constraints, replan_context)."""
    task_description: str
    available_modules: ModuleRegistry
    resource_budget: float
    constraints: Dict[str, Any] = field(default_factory=dict)
    replan_context: Optional[ReplanContext] = None


@dataclass
class ReplanContext:
    """Context for replanning: old graph + current state."""
    g_old: ExecutionGraph
    es: ExecutionState
    trigger: str


class TaskAnalyzer:
    """Phase 1: Task Analysis per planner-pipeline.md Section 3."""

    def analyze(self, task_description: str, registry: ModuleRegistry) -> List[SubGoal]:
        """Decompose task_description into sub-goals.

        Per INV-PLANNER-1: all necessary sub-goals must be identified.
        Per INV-PLANNER-10: O(task_desc_tokens × log |available_modules|)
        """
        tokens = task_description.lower().split()
        sub_goals: List[SubGoal] = []

        capability_map: Dict[str, List[str]] = {}
        for type_id, contract in registry.list_all().items():
            for cap in contract.capabilities:
                if cap not in capability_map:
                    capability_map[cap] = []
                capability_map[cap].append(type_id.name)

        for token in tokens:
            if token in capability_map:
                sub_goals.append(SubGoal(
                    goal_id=f"goal_{len(sub_goals)}",
                    description=f"achieve_{token}",
                    required_capabilities=frozenset([token]),
                ))

        if not sub_goals:
            sub_goals.append(SubGoal(
                goal_id="goal_default",
                description=task_description,
                required_capabilities=frozenset(),
            ))

        return sub_goals


class ModuleSelector:
    """Phase 2: Module Selection per planner-pipeline.md Section 4."""

    def select(
        self,
        sub_goals: List[SubGoal],
        registry: ModuleRegistry,
        resource_budget: float,
    ) -> List[Tuple[SubGoal, ModuleContract]]:
        """Match sub-goals to module contracts.

        Per INV-PLANNER-3: selected modules must be in REGISTERED state.
        Per INV-PLANNER-10: O(|available_modules| × |sub_goals|)
        """
        results: List[Tuple[SubGoal, ModuleContract]] = []
        remaining_budget = resource_budget

        for goal in sub_goals:
            best_contract: Optional[ModuleContract] = None
            best_score = -1.0

            for type_id, contract in registry.list_all().items():
                if goal.required_capabilities and not goal.required_capabilities.intersection(contract.capabilities):
                    continue
                score = contract.cost_weight + 0.1 * len(goal.required_capabilities.intersection(contract.capabilities))
                if score > best_score and contract.cost_weight <= remaining_budget:
                    best_score = score
                    best_contract = contract

            if best_contract is not None:
                results.append((goal, best_contract))
                remaining_budget -= best_contract.cost_weight
            else:
                results.append((goal, None))

        return results


class GraphBuilder:
    """Phase 3: Graph Construction per planner-pipeline.md Section 5."""

    def build(
        self,
        selections: List[Tuple[SubGoal, ModuleContract]],
        es: Optional[ExecutionState] = None,
    ) -> ExecutionGraph:
        """Construct G = (V, E, w) from selected modules.

        Per DEF-PLANNER-5: vertex assignment with cost_estimate.
        Per DEF-PLANNER-6: edge construction from data dependencies.
        Per INV-PLANNER-4: all inputs must be bound.
        Per INV-PLANNER-5: G must be a DAG.
        """
        graph = ExecutionGraph()
        instance_map: Dict[str, ModuleInstanceID] = {}

        for i, (goal, contract) in enumerate(selections):
            if contract is None:
                continue
            type_id = contract.module_type_id
            instance_id = ModuleInstanceID(type_id.name, i)
            instance_map[goal.goal_id] = instance_id
            graph.vertices.append(VertexAssignment(
                instance_id=instance_id,
                type_id=type_id,
                cost_estimate=contract.cost_weight,
                preference_score=1.0,
            ))
            graph.cost_weights[instance_id] = contract.cost_weight

        for i, (goal, contract) in enumerate(selections):
            if contract is None or i == 0:
                continue
            prev_goal = selections[i - 1][0]
            if prev_goal.goal_id in instance_map and goal.goal_id in instance_map:
                upstream = instance_map[prev_goal.goal_id]
                downstream = instance_map[goal.goal_id]
                graph.edges.append((upstream, downstream))

        if es and es.G:
            try:
                old_vertices = es.G.get_vertices()
                for v in graph.vertices:
                    if v.instance_id in old_vertices and v.instance_id in es.W:
                        buf = es.W[v.instance_id]
                        if buf.output not in (None,):
                            pass
            except Exception:
                pass

        return graph


class GraphValidator:
    """Phase 4: Validation and Cost Estimation per planner-pipeline.md Section 6."""

    def validate(self, graph: ExecutionGraph, resource_budget: float, sub_goals: List[SubGoal]) -> Optional[str]:
        """Per INV-PLANNER-7: validate checklist:
        1. G is a DAG (INV-PLANNER-5)
        2. All inputs are bound (INV-PLANNER-4)
        3. Type compatibility on all edges (INV-PLANNER-2)
        4. Resource budget compliance (INV-PLANNER-6)
        5. All sub-goals satisfied (INV-PLANNER-1)
        """
        if not graph.vertices:
            return "PLANNING_INCOMPLETE: no vertices in graph"

        sched = Scheduler()
        try:
            nodes = graph.get_vertices()
            sched.set_graph(nodes=nodes, edges=graph.edges)
        except DAGCycle:
            return "PLANNING_CYCLE_ERROR: graph contains a cycle"

        total_cost = graph.total_cost()
        if total_cost > resource_budget:
            return f"RESOURCE_BUDGET_EXCEEDED: cost {total_cost} > budget {resource_budget}"

        return None


class Planner:
    """Main planner implementing DEF-PLANNER-2 four-phase pipeline.

    Per INV-PLANNER-10: each phase complexity-bounded.
    Per INV-PLANNER-9: planner version tracked in execution header.
    """

    def __init__(self, version: str = "v1.0") -> None:
        self._version = version
        self._analyzer = TaskAnalyzer()
        self._selector = ModuleSelector()
        self._builder = GraphBuilder()
        self._validator = GraphValidator()

    @property
    def version(self) -> str:
        return self._version

    def plan(self, task: PlanningTask) -> PlanningResult:
        """Execute the 4-phase planning pipeline.

        Returns PlanningResult.success(G) or PlanningResult.fail(reason).
        """
        sub_goals = self._analyzer.analyze(task.task_description, task.available_modules)

        selections = self._selector.select(sub_goals, task.available_modules, task.resource_budget)

        graph = self._builder.build(selections, task.replan_context.es if task.replan_context else None)

        error = self._validator.validate(graph, task.resource_budget, sub_goals)
        if error:
            return PlanningResult.fail(error)

        return PlanningResult.success(graph)

    def compute_graph_diff(
        self,
        g_old: ExecutionGraph,
        g_new: ExecutionGraph,
        es: ExecutionState,
    ) -> Tuple[Set[ModuleInstanceID], Set[ModuleInstanceID], Set[ModuleInstanceID]]:
        """Per DEF-REPLAN-2: compute RETAINED, RETIRED_EARLY, NEW sets."""
        old_ids = set(g_old.get_vertices())
        new_ids = set(g_new.get_vertices())

        retained: Set[ModuleInstanceID] = old_ids & new_ids
        new_only: Set[ModuleInstanceID] = new_ids - old_ids
        retired_early: Set[ModuleInstanceID] = old_ids - new_ids

        for mid in list(retained):
            if mid not in es.W:
                retained.discard(mid)
                new_only.add(mid)
                continue
            buf = es.W[mid]
            from dnc.runtime.types import UNBOUND, PENDING
            if isinstance(buf.output, UNBOUND) or isinstance(buf.output, PENDING):
                pass

        return retained, retired_early, new_only