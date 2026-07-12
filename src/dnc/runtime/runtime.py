"""DNC Runtime: main entry point wiring planner, scheduler, state, and control loop.

Per control-loop.md DEF-CTRL-1: ControlLoop(t) = Observe(t) → Decide(t) → Act(t) → Assess(t) → ControlLoop(t+1)
Per replanning-protocol.md: replan triggers, graph diff, state migration, rollback
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleContract,
    UNBOUND,
    PENDING,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import Checkpoint, CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import (
    Planner,
    PlanningTask,
    ExecutionGraph,
    ReplanContext,
)
from dnc.cost.semantics import CostBudget, CostForecaster, StagedCheckpointBudget
from dnc.invariants.runtime_invariants import check_invariants


def _is_output_bound(buf: object) -> bool:
    """True if a module's output has already been produced (not UNBOUND/PENDING)."""
    if buf is None:
        return False
    return not isinstance(getattr(buf, "output", None), (UNBOUND, PENDING))


class ExecutionState2(Enum):
    """Runtime execution states (per control-loop.md)."""
    INIT = auto()
    RUNNING = auto()
    IDLE = auto()
    TERMINATED = auto()
    FAILED = auto()


class Decision(Enum):
    """Per control-loop.md DEF-CTRL-3: D(i) decision options.

    NOTE: This enum is Runtime-internal. The execution layer's DecisionPolicy
    returns dnc.execution.decision_policy.Decision. Conversion happens in
    Runtime.decide().
    """
    CONTINUE = auto()
    REPLAN = auto()
    ROLLBACK = auto()
    TERMINATE = auto()

    @staticmethod
    def from_execution_policy(ep_decision: "Decision") -> "Decision":
        """Convert execution-layer Decision to Runtime Decision.

        The execution-layer Decision has PAUSE; Runtime Decision maps this to CONTINUE.
        All other values (CONTINUE, REPLAN, ROLLBACK, TERMINATE) are identical.
        """
        from dnc.execution.decision_policy import Decision as EPDecision
        if ep_decision == EPDecision.PAUSE:
            return Decision.CONTINUE
        return Decision(ep_decision.value)


class AssessmentKind(Enum):
    """Per control-loop.md INV-CTRL-8: assessment classification."""
    OUTCOME_MET = auto()
    OUTCOME_DEGRADED = auto()
    OUTCOME_FAILED = auto()


@dataclass
class Observation:
    """Per control-loop.md DEF-CTRL-2: signals received since last iteration."""
    signals: List[Any] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class LatencyConfig:
    """Per control-loop.md DEF-CTRL-8: latency budget configuration."""
    OBSERVE_BUDGET_MS: float = 5.0
    DECIDE_BUDGET_MS: float = 10.0
    ACT_BUDGET_MS: float = 1000.0
    CONTROL_LOOP_BUDGET_MS: float = 50.0
    CONTROL_LOOP_GRACE_MS: float = 10.0
    DECISION_LATENCY_BUDGET_MS: float = 100.0
    MAX_REPLANS_PER_EXECUTION: int = 3
    MAX_ASYNC_PENDING: int = 50
    ASYNC_COMPLETION_TIMEOUT_MS: float = 500.0

    def validate(self) -> None:
        """Per INV-CTRL-13: validate configuration constraints."""
        assert self.OBSERVE_BUDGET_MS > 0
        assert self.DECIDE_BUDGET_MS > 0
        assert self.ACT_BUDGET_MS > self.OBSERVE_BUDGET_MS + self.DECIDE_BUDGET_MS
        assert self.CONTROL_LOOP_BUDGET_MS >= self.OBSERVE_BUDGET_MS + self.DECIDE_BUDGET_MS
        assert self.CONTROL_LOOP_GRACE_MS >= 0
        assert self.DECISION_LATENCY_BUDGET_MS >= self.OBSERVE_BUDGET_MS + self.DECIDE_BUDGET_MS
        assert 1 <= self.MAX_REPLANS_PER_EXECUTION <= 10


class RegressionMonitor:
    """Monitors evaluation results for Class 1 regressions and triggers automated rollback.

    Per Phase 4 (mvp-roadmap.md Section 6.F.3): Automated rollback triggers within 5 minutes
    of Class 1 regression in canary deployment. A Class 1 regression occurs when a metric
    that was WIN or TIE in prior evaluation becomes LOSS in current evaluation.

    Integration: RegressionMonitor is polled by the Runtime's control loop after each
    evaluation result is available. If rollback_count >= rollback_threshold, the Runtime
    triggers ROLLBACK via the DecisionPolicy.
    """

    def __init__(
        self,
        rollback_threshold: int = 1,
    ) -> None:
        self._rollback_threshold = rollback_threshold
        self._regression_count = 0
        self._last_regression_step = -1

    def check_regressions(
        self,
        evaluation_result: Optional[Any],
        es: ExecutionState,
        prior_results: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> bool:
        """Check evaluation result for Class 1 regressions.

        Args:
            evaluation_result: The current EvaluationRun or None
            es: Current execution state (used for step tracking)
            prior_results: Dict[scenario_id][metric_name] → prior classification

        Returns:
            True if automated rollback should be triggered
        """
        from dnc.observability.evaluation import EvaluationRun, EvaluationSuite

        if evaluation_result is None or prior_results is None:
            self._regression_count = 0
            return False

        if not isinstance(evaluation_result, EvaluationRun):
            return False

        suite = EvaluationSuite()
        regressions = suite.detect_regression(evaluation_result, prior_results)

        if not regressions:
            self._regression_count = 0
            return False

        current_step = es.step_index
        if current_step > self._last_regression_step:
            self._regression_count += len(regressions)
            self._last_regression_step = current_step

        return self._regression_count >= self._rollback_threshold

    def should_rollback(self) -> bool:
        """Return True if regression count has reached the rollback threshold."""
        return self._regression_count >= self._rollback_threshold

    def get_regression_count(self) -> int:
        return self._regression_count

    def reset(self) -> None:
        self._regression_count = 0
        self._last_regression_step = -1


class Runtime:
    """Main DNC runtime: orchestrates planner, scheduler, and control loop.

    Per control-loop.md DEF-CTRL-1:
    ControlLoop(t) ::= Observe(t) → Decide(t) → Act(t) → Assess(t) → ControlLoop(t+1)
    """

    def __init__(
        self,
        config: Optional[LatencyConfig] = None,
        initial_budget: float = 100.0,
    ) -> None:
        self._config = config or LatencyConfig()
        self._config.validate()

        self._registry = ModuleRegistry()
        self._planner = Planner()
        self._cost_budget = CostBudget(total_budget=initial_budget)
        self._cost_forecaster = CostForecaster(self._cost_budget)
        self._staged_checkpoint = StagedCheckpointBudget(self._cost_budget)
        self._regression_monitor = RegressionMonitor()
        from dnc.execution.decision_policy import RulePolicy
        self._rule_policy = RulePolicy(
            max_replans=config.MAX_REPLANS_PER_EXECUTION if config else 3,
        )

        self._state = ExecutionState2.INIT
        self._replan_count = 0
        self._critical_section = False
        self._async_pending: Set[ModuleInstanceID] = set()
        self._pending_signals: List[Any] = []
        self._loop_iteration_times: List[float] = []

        self._module_dispatch_fn: Optional[Callable[[ModuleInstanceID], Any]] = None
        self._current_graph: Optional[ExecutionGraph] = None

    def register_module(self, contract: ModuleContract) -> None:
        self._registry.register(contract)

    def set_dispatch_fn(self, fn: Callable[[ModuleInstanceID], Any]) -> None:
        self._module_dispatch_fn = fn

    def initiate(
        self,
        task_description: str,
        seed: int = 0,
    ) -> ExecutionState:
        """Initiate execution: create ES(0) and run initial planning."""
        es = ExecutionState()
        es.initialize_from_seed(seed)
        es.W = WorkingMemory()
        es.M = self._registry.snapshot()
        es.C = CheckpointRecord()
        es.H = es.H or WorkingMemory()._entries.__class__()
        self._state = ExecutionState2.RUNNING

        task = PlanningTask(
            task_description=task_description,
            available_modules=self._registry,
            resource_budget=self._cost_budget.remaining,
        )
        result = self._planner.plan(task)

        if not result.is_success:
            self._state = ExecutionState2.FAILED
            return es

        self._current_graph = result.graph
        nodes, edges = result.graph.to_scheduler_input()
        sched = Scheduler()
        sched.set_graph(nodes=nodes, edges=edges)
        es.G = sched

        for node in nodes:
            es.W.register(node)

        check_invariants(es)
        return es

    def observe(self) -> Observation:
        """Per control-loop.md 2.A: collect signals from observation window."""
        return Observation(signals=list(self._pending_signals))

    def decide(
        self,
        obs: Observation,
        es: ExecutionState,
    ) -> Decision:
        """Per control-loop.md 2.B: produce decision D(i) from observation.

        Per INV-CTRL-4: defaults to CONTINUE if DECIDE_BUDGET exceeded.
        Per INV-REPLAN-8: REPLAN forbidden during critical section.

        Delegates to RulePolicy per Phase 5 architecture. Cost forecaster
        and replan count are handled by RulePolicy internally.

        ACD-001: the runtime propagates live execution-control state onto ES(t)
        (pending_count, budget_remaining) so the DecisionPolicy's rules
        (terminate when complete, replan when exhausted) are actually
        evaluated instead of inert.
        """
        if self._state != ExecutionState2.RUNNING:
            return Decision.TERMINATE

        es.budget_remaining = self._cost_budget.remaining

        self._rule_policy.set_observation(obs)
        self._rule_policy.set_execution_state(es)
        if self._critical_section:
            self._rule_policy.set_critical_section(True)

        ep_decision = self._rule_policy.decide(obs, es)
        return Decision.from_execution_policy(ep_decision)

    def act(
        self,
        decision: Decision,
        es: ExecutionState,
    ) -> List[ModuleInstanceID]:
        """Per control-loop.md 2.C: dispatch steps as prescribed by decision."""
        if decision == Decision.TERMINATE:
            return []

        dispatched: List[ModuleInstanceID] = []

        if decision == Decision.REPLAN:
            replanned = self._execute_replan(es)
            return replanned

        if decision == Decision.ROLLBACK:
            self._rollback_to_checkpoint(es)
            return []

        if decision == Decision.CONTINUE and es.G:
            sched: Scheduler = es.G
            runnable = sched.get_runnable(es.W)
            # ACD-001 completion guard: get_runnable reports nodes whose
            # UPSTREAM preconditions are met (per INV-3); it intentionally
            # still lists already-completed nodes. The runtime must not
            # re-dispatch a node whose output is already bound, otherwise the
            # control loop would re-execute finished work forever.
            to_dispatch = [
                mid for mid in runnable if not _is_output_bound(es.W[mid])
            ]
            for mid in to_dispatch:
                if self._backpressure_active():
                    break
                if self._module_dispatch_fn:
                    result = self._module_dispatch_fn(mid)
                    es.W[mid] = Buffer.completed(es.W[mid].input, result)
                    check_invariants(es)
                    dispatched.append(mid)
                    es.advance_step()

        return dispatched

    def assess(
        self,
        dispatched: List[ModuleInstanceID],
        es: ExecutionState,
    ) -> AssessmentKind:
        """Per control-loop.md 2.D: evaluate whether actions produced intended outcomes.

        Per INV-CTRL-7: Assess phase always runs.
        Per INV-CTRL-8: classifies as OUTCOME_MET/DEGRADED/FAILED.
        """
        if not dispatched:
            return AssessmentKind.OUTCOME_MET

        all_complete = True
        for mid in dispatched:
            if mid not in es.W:
                all_complete = False
                break
            buf = es.W[mid]
            if isinstance(buf.output, UNBOUND) or isinstance(buf.output, PENDING):
                all_complete = False

        if all_complete:
            return AssessmentKind.OUTCOME_MET
        return AssessmentKind.OUTCOME_DEGRADED

    def _execute_replan(self, es: ExecutionState) -> List[ModuleInstanceID]:
        """Execute the replanning protocol per replanning-protocol.md Section 5.1."""
        if self._critical_section:
            return []

        if self._replan_count >= self._config.MAX_REPLANS_PER_EXECUTION:
            return []

        if not es.G:
            return []

        self._replan_count += 1

        ck = Checkpoint.take(es.step_index, es.execution_id, es.copy().to_dict(), "PRE_REPLAN")
        ck.validate()
        es.C.add(ck)

        g_old = self._current_graph

        task = PlanningTask(
            task_description="replan",
            available_modules=self._registry,
            resource_budget=self._cost_budget.remaining,
            replan_context=ReplanContext(g_old=g_old, es=es, trigger="RESOURCE_EXHAUSTION"),
        )
        result = self._planner.plan(task)

        if not result.is_success:
            return []

        g_new = result.graph
        retained, retired_early, new_only = self._planner.compute_graph_diff(g_old, g_new, es)

        new_nodes, new_edges = g_new.to_scheduler_input()
        sched = Scheduler()
        sched.set_graph(nodes=new_nodes, edges=new_edges)
        es.G = sched
        self._current_graph = g_new

        for mid in new_only:
            es.W.register(mid)

        es.advance_step()
        self._staged_checkpoint.reset()

        return list(new_only)

    def _backpressure_active(self) -> bool:
        """Per INV-CTRL-9c: check if ASYNC_PENDING is at MAX_ASYNC_PENDING."""
        return len(self._async_pending) >= self._config.MAX_ASYNC_PENDING

    def step(self, es: ExecutionState) -> ExecutionState:
        """Per DEF-CTRL-1: execute one control loop iteration."""
        t_start = time.time()

        obs = self.observe()
        decision = self.decide(obs, es)
        dispatched = self.act(decision, es)
        self.assess(dispatched, es)

        t_end = time.time()
        iter_time = (t_end - t_start) * 1000
        self._loop_iteration_times.append(iter_time)
        if len(self._loop_iteration_times) > 10:
            self._loop_iteration_times.pop(0)

        avg_iter = sum(self._loop_iteration_times) / len(self._loop_iteration_times)
        if avg_iter > self._config.CONTROL_LOOP_BUDGET_MS + self._config.CONTROL_LOOP_GRACE_MS:
            pass

        if decision == Decision.TERMINATE:
            self._state = ExecutionState2.TERMINATED

        return es

    @property
    def replan_count(self) -> int:
        return self._replan_count

    @property
    def state(self) -> ExecutionState2:
        return self._state

    @property
    def config(self) -> LatencyConfig:
        return self._config

    @property
    def regression_monitor(self) -> RegressionMonitor:
        return self._regression_monitor

    def check_regressions(
        self,
        evaluation_result: Any,
        es: ExecutionState,
        prior_results: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> bool:
        """Per Phase 4: check evaluation result for Class 1 regressions.

        Returns True if automated rollback should be triggered.
        """
        return self._regression_monitor.check_regressions(evaluation_result, es, prior_results)