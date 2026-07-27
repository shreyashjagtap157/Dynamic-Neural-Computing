"""Conformance tests for ACD-001 (INV-CTRL-11: Loop Termination Conditions).

Per architecture.md Section 5 (Conformance Clause) and control-loop.md
INV-CTRL-11, the control loop MUST transition to the TERMINATED state when
DecisionPolicy returns TERMINATE, and it MUST NOT terminate for any other
reason. The runtime owns execution: it dispatches runnable nodes, never
re-executes a node whose output is already bound, and terminates exactly when
every registered module instance has produced an output (pending_count == 0).

These tests close ACD-001.
"""

import sys

sys.path.insert(0, "src")

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
    UNBOUND,
    PENDING,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import ExecutionGraph, VertexAssignment
from dnc.runtime.runtime import Runtime, Decision, ExecutionState2


def _build_linear_runtime() -> tuple[Runtime, ExecutionState, dict]:
    """Build a linear SRC -> TR -> SINK graph and a fresh RUNNING runtime."""
    registry = ModuleRegistry()
    for name in ["SRC", "TR", "SINK"]:
        registry.register(
            ModuleContract(
                module_type_id=ModuleTypeID(name, "h_" + name),
                output_signature=object,
                capabilities=frozenset([name.lower()]),
            )
        )

    runtime = Runtime(config=None, initial_budget=100.0)
    runtime._registry = registry

    es = ExecutionState()
    es.W = WorkingMemory()
    es.M = registry.snapshot()
    es.C = CheckpointRecord()
    es.initialize_from_seed(0)

    mids = {n: ModuleInstanceID(n, 0) for n in ["SRC", "TR", "SINK"]}
    for m in mids.values():
        es.W.register(m)

    graph = ExecutionGraph()
    graph.vertices = [
        VertexAssignment(
            instance_id=mids[n],
            type_id=ModuleTypeID(n, "h_" + n),
            cost_estimate=1.0,
            preference_score=1.0,
        )
        for n in ["SRC", "TR", "SINK"]
    ]
    graph.edges = [
        (mids["SRC"], mids["TR"]),
        (mids["TR"], mids["SINK"]),
    ]
    graph.cost_weights = {m: 1.0 for m in mids.values()}

    sched = Scheduler()
    sched.set_graph(graph.get_vertices(), graph.edges)
    es.G = sched
    runtime._current_graph = graph
    runtime._state = ExecutionState2.RUNNING
    return runtime, es, mids


def _dispatch_with_counts(es: ExecutionState, mids: dict, counts: dict):
    """Return a dispatch fn that tracks per-node invocation counts."""

    def _dispatch(mid: ModuleInstanceID):
        counts[mid] = counts.get(mid, 0) + 1
        name = mid.type_id
        if name == "SRC":
            return [1.0, 2.0]
        if name == "TR":
            upstream = mids["SRC"]
            val = es.W[upstream].output
            return val[0] * 2 + val[1] * 2
        if name == "SINK":
            upstream = mids["TR"]
            return es.W[upstream].output
        raise ValueError(f"unknown node {name}")

    return _dispatch


class TestControlLoopTermination:
    """ACD-001 / INV-CTRL-11: the control loop terminates correctly."""

    def test_loop_reaches_terminate_and_terminated_state(self):
        """The loop must reach TERMINATE and the runtime must enter TERMINATED."""
        runtime, es, mids = _build_linear_runtime()
        counts: dict = {}
        runtime.set_dispatch_fn(_dispatch_with_counts(es, mids, counts))

        reached_terminate = False
        for _ in range(50):
            runtime.step(es)
            if runtime.state == ExecutionState2.TERMINATED:
                reached_terminate = True
                break

        assert reached_terminate, "Control loop must terminate (state -> TERMINATED)"
        # Final node output must be fully computed (no UNBOUND/PENDING left).
        for mid in mids.values():
            buf = es.W[mid]
            assert not isinstance(buf.output, (UNBOUND, PENDING)), (
                f"Node {mid.type_id} still unbound after termination"
            )
        print("PASS: test_loop_reaches_terminate_and_terminated_state")

    def test_no_module_is_reexecuted(self):
        """ACD-001 completion guard: each module is dispatched exactly once."""
        runtime, es, mids = _build_linear_runtime()
        counts: dict = {}
        runtime.set_dispatch_fn(_dispatch_with_counts(es, mids, counts))

        for _ in range(50):
            runtime.step(es)
            if runtime.state == ExecutionState2.TERMINATED:
                break

        # Three nodes -> exactly three dispatches, one per node.
        assert sum(counts.values()) == len(mids), (
            f"Total dispatches {sum(counts.values())} != {len(mids)} nodes"
        )
        for mid in mids.values():
            assert counts.get(mid, 0) == 1, (
                f"Node {mid.type_id} dispatched {counts.get(mid,0)} times; "
                "expected exactly 1 (no re-execution)"
            )
        print("PASS: test_no_module_is_reexecuted")

    def test_termination_is_not_infinite_loop(self):
        """The loop must terminate within a bounded number of iterations."""
        runtime, es, mids = _build_linear_runtime()
        counts: dict = {}
        runtime.set_dispatch_fn(_dispatch_with_counts(es, mids, counts))

        steps = 0
        max_steps = 50
        for _ in range(max_steps):
            runtime.step(es)
            steps += 1
            if runtime.state == ExecutionState2.TERMINATED:
                break

        # Pending work is 3 nodes; a correct loop finishes in |V| + slack steps.
        assert runtime.state == ExecutionState2.TERMINATED, (
            "Loop did not terminate within bound (possible infinite re-dispatch)"
        )
        assert steps <= len(mids) + 5, (
            f"Termination took {steps} steps; expected <= {len(mids) + 5}"
        )
        print("PASS: test_termination_is_not_infinite_loop")


if __name__ == "__main__":
    import traceback

    # Wire up the global es_ref used by the dispatch closure per test instance.
    g = TestControlLoopTermination()
    results = []
    for name in sorted(dir(g)):
        if name.startswith("test_"):
            # re-bind es_ref by running setup inside the test via_monkeypatch
            try:
                # each test builds its own es; capture it through dispatch closure
                getattr(g, name)()
                results.append(f"PASS: {name}")
            except Exception as e:  # noqa: BLE001
                results.append(f"FAIL: {name} -- {e}")
                traceback.print_exc()
    for r in results:
        print(r)
    passed = sum(1 for r in results if r.startswith("PASS"))
    print(f"{passed}/{len(results)} conformance tests passed")
