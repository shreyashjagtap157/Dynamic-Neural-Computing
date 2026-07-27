"""DNC Runtime: main entry point wiring planner, scheduler, state, and control loop.

Per control-loop.md DEF-CTRL-1: ControlLoop(t) = Observe(t) → Decide(t) → Act(t) → Assess(t) → ControlLoop(t+1)
Per replanning-protocol.md: replan triggers, graph diff, state migration, rollback
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
from dnc.state.working_memory import HistoryLog
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
from dnc.execution.execution_provider import ExecutionCapability, ExecutionProvider
from dnc.execution.decision_policy import (
    Decision as PolicyDecision,
    DecisionMetadata,
    DecisionPolicy,
    RulePolicy,
)
from dnc.execution.execution_trace import (
    DecisionRecord,
    ExecutionRecord,
    ExecutionTrace,
    ModuleInvocationRecord,
    ObservationRecord,
    ResourceUsageRecord,
    StateMutationRecord,
    TerminationReason,
)


class ProviderMode(Enum):
    """Select local development dispatch or capability-based providers."""

    DEV = auto()
    PROD = auto()


class RegressionMonitor:
    """Track evaluation regressions and request rollback at a threshold."""

    def __init__(self, rollback_threshold: int = 1) -> None:
        if rollback_threshold < 1:
            raise ValueError("rollback_threshold must be at least one")
        self._rollback_threshold = rollback_threshold
        self._regression_count = 0

    def check_regressions(self, evaluation_run: Any, es: ExecutionState, prior_results: Dict[str, Any]) -> bool:
        del es  # Reserved for checkpoint-aware rollback integration.
        for result in evaluation_run.trial_results:
            prior = prior_results.get(result.scenario_id, {}).get(result.metric_spec.name)
            classification = getattr(result, "classification", None)
            if classification is not None:
                current = getattr(classification, "name", str(classification))
            else:
                improved = (
                    result.current_mean >= result.baseline_mean
                    if result.metric_spec.higher_is_better
                    else result.current_mean <= result.baseline_mean
                )
                current = "WIN" if improved else "LOSS"
            if prior in {"WIN", "TIE"} and current == "LOSS":
                self._regression_count += 1
        return self.should_rollback()

    def should_rollback(self) -> bool:
        return self._regression_count >= self._rollback_threshold

    def get_regression_count(self) -> int:
        return self._regression_count


class ExecutionState2(Enum):
    """Runtime execution states."""
    INIT = auto()
    RUNNING = auto()
    IDLE = auto()
    TERMINATED = auto()
    FAILED = auto()


class Decision(Enum):
    """Per control-loop.md DEF-CTRL-3: D(i) decision options."""
    CONTINUE = auto()
    REPLAN = auto()
    IDLE = auto()
    PAUSE = auto()
    ROLLBACK = auto()
    TERMINATE = auto()


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


class Runtime:
    """Main DNC runtime: orchestrates planner, scheduler, and control loop.

    Per control-loop.md DEF-CTRL-1:
    ControlLoop(t) ::= Observe(t) → Decide(t) → Act(t) → Assess(t) → ControlLoop(t+1)
    """

    def __init__(
        self,
        config: Optional[LatencyConfig] = None,
        initial_budget: float = 100.0,
        decision_policy: Optional[DecisionPolicy] = None,
        trace_enabled: bool = True,
    ) -> None:
        self._config = config or LatencyConfig()
        self._config.validate()

        self._registry = ModuleRegistry()
        self._planner = Planner()
        self._cost_budget = CostBudget(total_budget=initial_budget)
        self._cost_forecaster = CostForecaster(self._cost_budget)
        self._staged_checkpoint = StagedCheckpointBudget(self._cost_budget)

        self._state = ExecutionState2.INIT
        self._replan_count = 0
        self._critical_section = False
        self._async_pending: Set[ModuleInstanceID] = set()
        self._pending_signals: List[Any] = []
        self._loop_iteration_times: List[float] = []

        self._module_dispatch_fn: Optional[Callable[[ModuleInstanceID], Any]] = None
        self._current_graph: Optional[ExecutionGraph] = None
        self._provider_mode = ProviderMode.DEV
        self._providers: List[ExecutionProvider] = []
        self._node_capabilities: Dict[ModuleInstanceID, ExecutionCapability] = {}
        self._regression_monitor = RegressionMonitor()
        self._decision_policy = decision_policy or RulePolicy(
            max_replans=self._config.MAX_REPLANS_PER_EXECUTION
        )
        self._last_policy_metadata: Optional[DecisionMetadata] = None
        self._trace_enabled = trace_enabled
        self._execution_trace: Optional[ExecutionTrace] = None

    def register_module(self, contract: ModuleContract) -> None:
        self._registry.register(contract)

    def set_dispatch_fn(self, fn: Callable[[ModuleInstanceID], Any]) -> None:
        self._module_dispatch_fn = fn

    def register_provider(self, provider: ExecutionProvider) -> None:
        self._providers.append(provider)

    def set_provider_mode(self, mode: ProviderMode) -> None:
        self._provider_mode = mode

    def set_node_capabilities(self, capabilities: Dict[ModuleInstanceID, ExecutionCapability]) -> None:
        self._node_capabilities = dict(capabilities)

    @property
    def regression_monitor(self) -> RegressionMonitor:
        return self._regression_monitor

    def check_regressions(self, evaluation_run: Any, es: ExecutionState, prior_results: Dict[str, Any]) -> bool:
        return self._regression_monitor.check_regressions(evaluation_run, es, prior_results)

    @property
    def decision_policy(self) -> DecisionPolicy:
        return self._decision_policy

    @property
    def execution_trace(self) -> Optional[ExecutionTrace]:
        return self._execution_trace

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
        es.H = es.H or HistoryLog()
        es._budget_remaining = self._cost_budget.remaining
        self._execution_trace = self._new_trace(es) if self._trace_enabled else None
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
        """
        if self._state != ExecutionState2.RUNNING:
            return Decision.TERMINATE

        if hasattr(self._decision_policy, "set_critical_section"):
            self._decision_policy.set_critical_section(self._critical_section)
        policy_decision = self._decision_policy.decide(
            {"signals": list(obs.signals), "timestamp": obs.timestamp}, es
        )
        self._last_policy_metadata = self._decision_policy.get_decision_metadata()

        if self._cost_forecaster.should_trigger_replan():
            return Decision.REPLAN

        if self._replan_count >= self._config.MAX_REPLANS_PER_EXECUTION:
            return Decision.TERMINATE

        mapped = {
            PolicyDecision.CONTINUE: Decision.CONTINUE,
            PolicyDecision.REPLAN: Decision.REPLAN,
            PolicyDecision.PAUSE: Decision.PAUSE,
            PolicyDecision.TERMINATE: Decision.TERMINATE,
            PolicyDecision.ROLLBACK: Decision.ROLLBACK,
        }[policy_decision]
        if mapped != Decision.CONTINUE:
            return mapped

        if not obs.signals:
            runnable = es.G.get_runnable(es.W) if es.G else []
            if not runnable:
                return Decision.TERMINATE
            return Decision.CONTINUE

        return Decision.CONTINUE

    def act(
        self,
        decision: Decision,
        es: ExecutionState,
    ) -> List[ModuleInstanceID]:
        """Per control-loop.md 2.C: dispatch steps as prescribed by decision."""
        if decision in (Decision.TERMINATE, Decision.IDLE, Decision.PAUSE):
            return []

        if decision == Decision.ROLLBACK:
            self._rollback_to_checkpoint(es)
            return []

        dispatched: List[ModuleInstanceID] = []

        if decision == Decision.REPLAN:
            replanned = self._execute_replan(es)
            return replanned

        if decision == Decision.CONTINUE and es.G:
            sched: Scheduler = es.G
            runnable = sched.get_runnable(es.W)
            for mid in runnable:
                if self._backpressure_active():
                    break
                result: Any
                if self._provider_mode == ProviderMode.PROD:
                    capability = self._node_capabilities.get(mid)
                    provider = next(
                        (p for p in self._providers if capability is not None and p.supports(capability)),
                        None,
                    )
                    if provider is None or capability is None:
                        raise RuntimeError(f"no provider bound for module {mid}")
                    provider_result = provider.execute(capability, str(es.W[mid].input))
                    if not provider_result.is_success:
                        raise RuntimeError(provider_result.error or "provider execution failed")
                    result = provider_result.output
                elif self._module_dispatch_fn:
                    result = self._module_dispatch_fn(mid)
                else:
                    continue
                es.W[mid] = Buffer.completed(es.W[mid].input, result)
                check_invariants(es)
                dispatched.append(mid)
                es.advance_step()

        return dispatched

    def _rollback_to_checkpoint(self, es: ExecutionState) -> bool:
        """Restore the latest valid checkpoint into the live state in place."""
        checkpoint = es.C.latest() if es.C is not None else None
        if checkpoint is None:
            return False
        restored = ExecutionState.from_dict(checkpoint.es_snapshot)
        es.W = restored.W
        es.M = restored.M
        es.C = restored.C
        es.H = restored.H
        es.G = restored.G
        es._step_index = restored._step_index
        es._execution_id = restored._execution_id
        es._rng_state = restored._rng_state
        es._budget_remaining = restored._budget_remaining
        return True

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

        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "PRE_REPLAN")
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

        step_before = es.step_index
        obs = self.observe()
        decision = self.decide(obs, es)
        dispatched = self.act(decision, es)
        assessment = self.assess(dispatched, es)

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
        elif decision == Decision.PAUSE:
            self._state = ExecutionState2.IDLE

        if self._trace_enabled:
            self._record_trace_iteration(
                es=es,
                observation=obs,
                decision=decision,
                dispatched=dispatched,
                assessment=assessment,
                step_before=step_before,
                elapsed_ms=iter_time,
            )

        return es

    def resume(self) -> None:
        """Resume an execution paused by its DecisionPolicy."""
        if self._state == ExecutionState2.IDLE:
            self._state = ExecutionState2.RUNNING

    def _new_trace(self, es: ExecutionState) -> ExecutionTrace:
        return ExecutionTrace(
            execution_id=es.execution_id,
            resource_budget=self._cost_budget.total_budget,
            random_seed=es.R,
            latency_config=asdict(self._config),
        )

    def _record_trace_iteration(
        self,
        *,
        es: ExecutionState,
        observation: Observation,
        decision: Decision,
        dispatched: List[ModuleInstanceID],
        assessment: AssessmentKind,
        step_before: int,
        elapsed_ms: float,
    ) -> None:
        if self._execution_trace is None:
            self._execution_trace = self._new_trace(es)
        metadata = self._last_policy_metadata
        invocations: List[ModuleInvocationRecord] = []
        mutations: List[StateMutationRecord] = []
        for mid in dispatched:
            buffer = es.W[mid]
            invocations.append(
                ModuleInvocationRecord(
                    module_instance_id=str(mid.uuid),
                    module_type=mid.type_id,
                    capability=self._node_capabilities.get(mid, ExecutionCapability.CAP_EXECUTION).name,
                    input_size_bytes=len(repr(buffer.input).encode()),
                    output_size_bytes=len(repr(buffer.output).encode()),
                    provider_id=("provider" if self._provider_mode == ProviderMode.PROD else "local"),
                    provider_version="1",
                    latency_ms=0.0,
                    metadata={"recorded_output": buffer.output},
                )
            )
            mutations.append(
                StateMutationRecord(
                    mutation_type="OUTPUT_BOUND",
                    target=str(mid.uuid),
                    step_before=step_before,
                    step_after=es.step_index,
                    metadata={"module_type": mid.type_id},
                )
            )
        self._execution_trace.add_execution_record(
            ExecutionRecord(
                step_index=step_before,
                loop_iteration=len(self._execution_trace.execution_record),
                observation=ObservationRecord(
                    raw_signals=list(observation.signals),
                    timestamp=str(observation.timestamp),
                ),
                decision=DecisionRecord(
                    decision=decision.name,
                    policy_type=self._decision_policy.policy_type,
                    policy_version=self._decision_policy.version,
                    reasoning=metadata.reasoning if metadata else None,
                    confidence=metadata.confidence if metadata else None,
                    alternative_considered=(
                        [item.name for item in metadata.alternative_considered]
                        if metadata else []
                    ),
                    latency_ms=metadata.latency_ms if metadata else 0.0,
                ),
                module_invocations=invocations,
                state_mutations=mutations,
                resource_usage=ResourceUsageRecord(
                    step_index=es.step_index,
                    budget_remaining=self._cost_budget.remaining,
                    cpu_time_ms=elapsed_ms,
                    memory_bytes=0,
                    network_calls=sum(1 for item in invocations if item.provider_id == "provider"),
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        if decision == Decision.TERMINATE and not self._execution_trace.is_complete:
            self._execution_trace.finalize(TerminationReason.TERMINATE_DECISION)

    @property
    def replan_count(self) -> int:
        return self._replan_count

    @property
    def state(self) -> ExecutionState2:
        return self._state

    @property
    def config(self) -> LatencyConfig:
        return self._config


class DNCRuntime(Runtime):
    """Compatibility entry point for the frozen v1 runtime API."""

    def __init__(self, registry: Optional[ModuleRegistry] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if registry is not None:
            self._registry = registry
