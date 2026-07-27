"""Conformance tests for deterministic replay (replay-semantics.md).

These tests verify that ReplayEngine performs a GENUINE re-execution: it drives a
fresh runtime through the control loop and re-derives each decision from the
runtime's own DecisionPolicy, comparing the re-derived decisions to the recorded
trace. A tampered trace is detected as a deviation (the engine does not merely
echo its own input).
"""

import sys

sys.path.insert(0, "src")

from dnc.runtime.types import (
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import ExecutionGraph, VertexAssignment
from dnc.runtime.runtime import Runtime, Decision, ExecutionState2
from dnc.execution.replay_engine import ReplayEngine, ReplayConfig
from dnc.execution.execution_trace import (
    ExecutionTrace,
    ExecutionRecord,
    ObservationRecord,
    DecisionRecord,
    ModuleInvocationRecord,
    TerminationReason,
)


def _build_linear_runtime() -> tuple:
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


def _run_and_record(runtime, es) -> tuple:
    """Run the control loop, recording (decision, dispatched, signals) per step."""
    steps = []
    response_map = {}
    for idx in range(50):
        obs = runtime.observe()
        d = runtime.decide(obs, es)
        dispatched = runtime.act(d, es)
        steps.append(
            {
                "idx": idx,
                "signals": list(obs.signals),
                "decision": d.name,
                "dispatched": [str(m.type_id) for m in dispatched],
            }
        )
        if d == Decision.TERMINATE or runtime.state == ExecutionState2.TERMINATED:
            break
    for name, mid in runtime._current_graph.vertices and {}:  # no-op guard
        pass
    # Capture final outputs for every node as recorded provider responses.
    mids = {str(v.instance_id.type_id): v.instance_id for v in runtime._current_graph.vertices}
    for name, mid in mids.items():
        response_map[name] = es.W[mid].output
    return steps, response_map


def _build_trace(steps, execution_id) -> ExecutionTrace:
    trace = ExecutionTrace(execution_id=execution_id, random_seed=0)
    for s in steps:
        rec = ExecutionRecord(
            step_index=s["idx"],
            loop_iteration=s["idx"],
            observation=ObservationRecord(raw_signals=s["signals"]),
            decision=DecisionRecord(
                decision=s["decision"],
                policy_type="RulePolicy",
                policy_version="1.0.0",
            ),
            module_invocations=[
                ModuleInvocationRecord(
                    module_instance_id=m,
                    module_type=m,
                    capability="",
                    input_size_bytes=0,
                    output_size_bytes=0,
                    provider_id="mock",
                    provider_version="1.0.0",
                    latency_ms=0.0,
                )
                for m in s["dispatched"]
            ],
        )
        trace.add_execution_record(rec)
    trace.finalize(TerminationReason.TERMINATE_DECISION)
    return trace


class TestDeterministicReplay:
    """ReplayEngine must re-execute, not self-compare (C1)."""

    def test_replay_reproduces_recorded_decisions(self):
        """A genuine replay of an unmodified trace matches on every step."""
        runtime, es, mids = _build_linear_runtime()
        steps, response_map = _run_and_record(runtime, es)
        trace = _build_trace(steps, es.execution_id)

        engine = ReplayEngine()
        fresh_runtime, fresh_es, _ = _build_linear_runtime()
        result = engine.replay(trace, fresh_runtime, fresh_es, response_map)

        assert result.all_matched, f"Replay deviated: {result.deviations}"
        assert result.replayed_steps == len(steps)
        assert fresh_runtime.state == ExecutionState2.TERMINATED
        print("PASS: test_replay_reproduces_recorded_decisions")

    def test_replay_detects_tampered_trace(self):
        """A tampered decision in the trace is flagged as a deviation."""
        runtime, es, mids = _build_linear_runtime()
        steps, response_map = _run_and_record(runtime, es)
        trace = _build_trace(steps, es.execution_id)

        # Tamper: flip a middle step's recorded decision to REPLAN.
        tampered = trace.execution_record[0]
        object.__setattr__(
            tampered,
            "decision",
            DecisionRecord(
                decision="REPLAN",
                policy_type="RulePolicy",
                policy_version="1.0.0",
            ),
        )

        engine = ReplayEngine()
        fresh_runtime, fresh_es, _ = _build_linear_runtime()
        result = engine.replay(trace, fresh_runtime, fresh_es, response_map)

        assert not result.all_matched, "Tampered trace must NOT replay cleanly"
        assert result.deviations, "A deviation must be recorded"
        assert "REPLAN" in result.deviations[0]
        print("PASS: test_replay_detects_tampered_trace")


if __name__ == "__main__":
    import traceback

    g = TestDeterministicReplay()
    results = []
    for name in sorted(dir(g)):
        if name.startswith("test_"):
            try:
                getattr(g, name)()
                results.append(f"PASS: {name}")
            except Exception as e:  # noqa: BLE001
                results.append(f"FAIL: {name} -- {e}")
                traceback.print_exc()
    for r in results:
        print(r)
    passed = sum(1 for r in results if r.startswith("PASS"))
    print(f"{passed}/{len(results)} conformance tests passed")
