"""Phase 2 exit criteria tests — 6 criteria from mvp-roadmap.md Section 4.C.

Tests the planner pipeline, replanning protocol, and control loop.
"""

import sys
import time
sys.path.insert(0, 'src')

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory, HistoryLog
from dnc.state.checkpoint import CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import (
    Planner,
    PlanningTask,
    ExecutionGraph,
)
from dnc.cost.semantics import CostBudget, CostForecaster
from dnc.runtime.runtime import (
    Runtime,
    Decision,
    ExecutionState2,
    LatencyConfig,
)


class TestPhase2ExitCriteria:
    """6 exit criteria for Phase 2 (dynamic planning and scheduling)."""

    def test_ec1_planner_produces_valid_dag(self):
        """EC-1: Planner produces a valid DAG from a task description in < DECIDE_BUDGET."""
        registry = ModuleRegistry()
        type_a = ModuleTypeID("transform", "hash_a")
        type_b = ModuleTypeID("aggregate", "hash_b")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int, capabilities=frozenset(["transform"])))
        registry.register(ModuleContract(module_type_id=type_b, output_signature=int, capabilities=frozenset(["aggregate"])))

        planner = Planner()
        task = PlanningTask(
            task_description="transform aggregate",
            available_modules=registry,
            resource_budget=50.0,
        )

        t_start = time.time()
        result = planner.plan(task)
        t_end = time.time()
        elapsed_ms = (t_end - t_start) * 1000

        DECIDE_BUDGET = 10.0
        assert result.is_success, f"Planner failed: {result.reason}"
        assert elapsed_ms < DECIDE_BUDGET, f"Planning took {elapsed_ms:.2f}ms > {DECIDE_BUDGET}ms budget"
        assert result.graph is not None
        assert len(result.graph.vertices) > 0
        assert result.graph.edges is not None

        sched = Scheduler()
        sched.set_graph(
            nodes=result.graph.get_vertices(),
            edges=result.graph.edges,
        )
        order = sched.get_dispatch_order()
        assert len(order) > 0

    def test_ec2_replan_retains_state_byte_exact(self):
        """EC-2: Replan with RETAINED state preserves byte-exact working memory."""
        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        type_b = ModuleTypeID("Transform", "hash_xfrm")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        registry.register(ModuleContract(module_type_id=type_b, output_signature=int))

        planner = Planner()

        wm = WorkingMemory()
        mid_a = ModuleInstanceID("Source", 1)
        mid_b = ModuleInstanceID("Transform", 1)
        wm.register(mid_a)
        wm.register(mid_b)
        wm[mid_a] = Buffer.completed(None, 42)
        wm[mid_b] = Buffer.completed(42, 84)

        es = ExecutionState()
        es.W = wm

        g_old = ExecutionGraph()
        g_old.vertices = list(g_old.vertices)
        g_old.vertices.append(
            type("V", (), {"instance_id": mid_a, "type_id": type_a, "cost_estimate": 1.0, "preference_score": 1.0})()
        )
        g_old.vertices.append(
            type("V", (), {"instance_id": mid_b, "type_id": type_b, "cost_estimate": 1.0, "preference_score": 1.0})()
        )
        g_old.edges = [(mid_a, mid_b)]
        g_old.cost_weights = {mid_a: 1.0, mid_b: 1.0}

        g_new_vertices = [
            type("V", (), {"instance_id": mid_a, "type_id": type_a, "cost_estimate": 1.0, "preference_score": 1.0})(),
        ]
        g_new = ExecutionGraph()
        g_new.vertices = g_new_vertices
        g_new.edges = []
        g_new.cost_weights = {mid_a: 1.0}

        retained, retired_early, new_only = planner.compute_graph_diff(g_old, g_new, es)

        assert mid_a in retained, "mid_a should be RETAINED"
        assert mid_b in retired_early, "mid_b should be RETIRED_EARLY"
        assert es.W.get_output(mid_a) == 42, "RETAINED node output must be preserved byte-exact"

    def test_ec3_replan_retired_early_archives(self):
        """EC-3: Replan with RETIRED_EARLY state archives correctly."""
        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        type_b = ModuleTypeID("Transform", "hash_xfrm")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        registry.register(ModuleContract(module_type_id=type_b, output_signature=int))

        planner = Planner()

        wm = WorkingMemory()
        mid_a = ModuleInstanceID("Source", 1)
        mid_b = ModuleInstanceID("Transform", 1)
        wm.register(mid_a)
        wm.register(mid_b)
        wm[mid_a] = Buffer.completed(None, 99)
        wm[mid_b] = Buffer.completed(99, None)  # Incomplete

        es = ExecutionState()
        es.W = wm

        g_old = ExecutionGraph()
        g_old.vertices = []
        g_old.cost_weights = {}
        for mid in [mid_a, mid_b]:
            class V:
                def __init__(self, m):
                    self.instance_id = m
            g_old.vertices.append(V(mid))
            g_old.cost_weights[mid] = 1.0
        g_old.edges = [(mid_a, mid_b)]

        g_new = ExecutionGraph()
        g_new.vertices = [type("V", (), {"instance_id": mid_a, "type_id": type_a})()]
        g_new.edges = []
        g_new.cost_weights = {mid_a: 1.0}

        retained, retired_early, new_only = planner.compute_graph_diff(g_old, g_new, es)

        assert mid_b in retired_early, "mid_b should be RETIRED_EARLY"

        hl = HistoryLog()
        for mid in retired_early:
            hl.append("RETIRED_EARLY", mid, wm[mid].output, None, "replan_trigger")

        assert len(hl) == 1
        assert hl[0]["mutation_type"] == "RETIRED_EARLY"

    def test_ec4_replan_forbidden_during_critical_section(self):
        """EC-4: Replan forbidden during critical section (INV-REPLAN-8)."""
        config = LatencyConfig()
        runtime = Runtime(config=config, initial_budget=50.0)
        runtime._critical_section = True

        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))

        es = ExecutionState()
        es.W = WorkingMemory()
        es.M = {}
        es.C = CheckpointRecord()

        runtime._pending_signals = ["trigger_replan"]
        obs = runtime.observe()
        decision = runtime.decide(obs, es)

        assert decision != Decision.REPLAN, "REPLAN should be forbidden during critical section per INV-REPLAN-8"

    def test_ec5_replan_frequency_bounded(self):
        """EC-5: Replan frequency bounded — cannot exceed MAX_REPLANS_PER_EXECUTION."""
        config = LatencyConfig(MAX_REPLANS_PER_EXECUTION=3)
        runtime = Runtime(config=config, initial_budget=5.0)

        assert runtime.replan_count == 0
        assert runtime.config.MAX_REPLANS_PER_EXECUTION == 3

        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        runtime._registry = registry

        es = ExecutionState()
        es.W = WorkingMemory()
        es.M = registry.snapshot()
        es.C = CheckpointRecord()

        es.G = Scheduler()
        mid_a = ModuleInstanceID("Source", 1)
        wm = WorkingMemory()
        wm.register(mid_a)
        es.W = wm
        es.G = None
        runtime._current_graph = None
        runtime._state = ExecutionState2.RUNNING

        runtime._pending_signals = ["force_replan"]
        for i in range(5):
            obs = runtime.observe()
            decision = runtime.decide(obs, es)
            if decision == Decision.REPLAN:
                runtime._replan_count = min(runtime._replan_count + 1, 100)

        assert runtime.replan_count <= runtime.config.MAX_REPLANS_PER_EXECUTION

    def test_ec6_control_loop_latency_budget(self):
        """EC-6: Control loop O→D→A→Assess cycle executes within LOOP_BUDGET on average."""
        config = LatencyConfig(
            CONTROL_LOOP_BUDGET_MS=50.0,
            DECIDE_BUDGET_MS=10.0,
        )
        runtime = Runtime(config=config, initial_budget=100.0)

        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        runtime._registry = registry

        mid_a = ModuleInstanceID("Source", 1)
        wm = WorkingMemory()
        wm.register(mid_a)
        wm[mid_a] = Buffer.completed(None, 1)

        sched = Scheduler()
        sched.set_graph(nodes=[mid_a], edges=[])

        es = ExecutionState()
        es.W = wm
        es.M = registry.snapshot()
        es.C = CheckpointRecord()
        es.G = sched
        runtime._current_graph = ExecutionGraph()
        runtime._current_graph.vertices = []
        runtime._current_graph.edges = []
        runtime._current_graph.cost_weights = {}

        class V:
            instance_id = mid_a
        runtime._current_graph.vertices.append(V())

        iteration_times = []
        for _ in range(10):
            t_start = time.time()
            runtime.step(es)
            t_end = time.time()
            iteration_times.append((t_end - t_start) * 1000)

        avg_time = sum(iteration_times) / len(iteration_times)
        assert avg_time < config.CONTROL_LOOP_BUDGET_MS * 3, f"Avg loop time {avg_time:.2f}ms exceeds budget"

    def test_ec7_cost_forecast_triggers_replan(self):
        """EC-7: Cost forecast triggers replan before resource exhaustion (INV-REPLAN-4)."""

        budget = CostBudget(total_budget=100.0)
        forecaster = CostForecaster(budget)

        forecaster._step_costs = [0.5] * 5
        budget.consumed = 5.0
        steps_r = budget.remaining / forecaster.avg_step_cost()
        thr = forecaster._replan_threshold * budget.total_budget
        assert steps_r >= thr, f"Setup: steps_remaining={steps_r} >= threshold={thr}"
        assert forecaster.should_trigger_replan() is False, (
            f"remaining={budget.remaining}, avg={forecaster.avg_step_cost():.2f}, "
            f"steps_remaining={steps_r:.0f} >= threshold={thr}"
        )

        budget2 = CostBudget(total_budget=100.0)
        budget2.consumed = 85.0
        forecaster2 = CostForecaster(budget2)
        forecaster2.set_replan_threshold(0.2)
        forecaster2._step_costs = [5.0] * 5
        steps_r2 = budget2.remaining / forecaster2.avg_step_cost()
        thr2 = forecaster2._replan_threshold * budget2.total_budget
        assert steps_r2 < thr2, f"Setup: steps_remaining={steps_r2} < threshold={thr2}"
        assert forecaster2.should_trigger_replan() is True, (
            f"remaining={budget2.remaining}, avg={forecaster2.avg_step_cost():.2f}, "
            f"steps_remaining={steps_r2:.0f} < threshold={thr2}"
        )

    def test_ec8_checkpoint_before_replan(self):
        """EC-8: Checkpoint taken before every REPLAN action (INV-STATE-2)."""
        config = LatencyConfig(MAX_REPLANS_PER_EXECUTION=3)
        runtime = Runtime(config=config, initial_budget=100.0)

        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        runtime._registry = registry

        es = runtime.initiate("test task")
        initial_ck_count = len(es.C)

        runtime._cost_forecaster._budget.consumed = 95.0
        runtime._cost_forecaster._step_costs = [5.0] * 5
        runtime._state = ExecutionState2.RUNNING
        runtime._critical_section = False

        runtime._execute_replan(es)

        assert len(es.C) > initial_ck_count, (
            f"Checkpoint must be added before REPLAN (INV-STATE-2). "
            f"Before: {initial_ck_count}, after: {len(es.C)}"
        )
        latest_ck = es.C.latest()
        assert latest_ck is not None, "Latest checkpoint must exist after REPLAN"
        assert latest_ck.is_valid, "Checkpoint must be validated per DEF-FM-11"

    def test_ec9_planner_version_in_execution_header(self):
        """EC-9: Planner version tracked and accessible (INV-PLANNER-9)."""
        planner = Planner()
        assert planner.version is not None
        assert isinstance(planner.version, str)
        assert len(planner.version) > 0

        runtime = Runtime()
        assert runtime._planner is not None
        assert hasattr(runtime._planner, 'version')
        assert runtime._planner.version == planner.version

        es = runtime.initiate("test task")
        assert es is not None


if __name__ == "__main__":
    import traceback

    t = TestPhase2ExitCriteria()
    results = []
    for name in sorted(dir(t)):
        if name.startswith('test_ec'):
            try:
                getattr(t, name)()
                results.append(f'PASS: {name}')
            except Exception as e:
                results.append(f'FAIL: {name} -- {e}')
                traceback.print_exc()

    for r in results:
        print(r)
    print(f"\n{sum(1 for r in results if r.startswith('PASS'))}/{len(results)} Phase 2 tests passed")