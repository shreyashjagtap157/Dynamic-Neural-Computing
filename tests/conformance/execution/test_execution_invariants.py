"""Executable evidence for INV-EXEC-1 through INV-EXEC-7."""

import pickle

from dnc.execution.decision_policy import RulePolicy
from dnc.runtime.runtime import Decision, Runtime
from dnc.runtime.types import Buffer, ModuleContract, ModuleTypeID
from dnc.state.checkpoint import Checkpoint


def _runtime() -> tuple[Runtime, object]:
    runtime = Runtime(decision_policy=RulePolicy())
    runtime.register_module(
        ModuleContract(module_type_id=ModuleTypeID("Source", "v1"), output_signature=object)
    )
    state = runtime.initiate("conformance")
    runtime.set_dispatch_fn(lambda mid: {"module": mid.type_id})
    return runtime, state


def test_inv_exec_1_control_loop_order() -> None:
    """INV-EXEC-1: each step executes Observe → Decide → Act → Assess."""
    runtime, state = _runtime()
    calls: list[str] = []
    for name in ("observe", "decide", "act", "assess"):
        original = getattr(runtime, name)

        def wrapper(*args, _name=name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        setattr(runtime, name, wrapper)
    runtime.step(state)
    assert calls == ["observe", "decide", "act", "assess"]


def test_inv_exec_2_policy_invoked_each_decide_phase() -> None:
    """INV-EXEC-2: DecisionPolicy executes once for every Decide phase."""
    runtime, state = _runtime()
    count = 0
    original = runtime.decision_policy.decide

    def decide(*args, **kwargs):
        nonlocal count
        count += 1
        return original(*args, **kwargs)

    runtime.decision_policy.decide = decide
    runtime.step(state)
    runtime.step(state)
    assert count == 2


def test_inv_exec_3_planner_only_runs_for_replan() -> None:
    """INV-EXEC-3: Act invokes Planner only for a REPLAN decision."""
    runtime, state = _runtime()
    calls = 0
    original = runtime._planner.plan

    def plan(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    runtime._planner.plan = plan
    runtime.act(Decision.CONTINUE, state)
    assert calls == 0
    runtime.act(Decision.REPLAN, state)
    assert calls == 1


def test_inv_exec_4_scheduler_requires_complete_upstream() -> None:
    """INV-EXEC-4: downstream dispatch requires every upstream output COMPLETE."""
    runtime, state = _runtime()
    node = runtime._current_graph.get_vertices()[0]
    state.W[node] = Buffer.unbound_input()
    assert state.G.get_runnable(state.W) == [node]
    state.W[node] = Buffer.completed(None, 1)
    assert state.G.get_runnable(state.W) == []


def test_inv_exec_5_trace_records_iteration_dispatch_and_mutation() -> None:
    """INV-EXEC-5: trace records each loop, decision, dispatch, and state mutation."""
    runtime, state = _runtime()
    runtime.step(state)
    trace = runtime.execution_trace
    assert trace is not None and len(trace.execution_record) == 1
    record = trace.execution_record[0]
    assert record.decision.decision == "CONTINUE"
    assert len(record.module_invocations) == 1
    assert [item.mutation_type for item in record.state_mutations] == ["OUTPUT_BOUND"]


def test_inv_exec_6_checkpoint_precedes_replan() -> None:
    """INV-EXEC-6: every REPLAN action takes a checkpoint first."""
    runtime, state = _runtime()
    assert len(state.C) == 0
    runtime.act(Decision.REPLAN, state)
    assert len(state.C) == 1
    assert state.C.latest().provenance_ref == "PRE_REPLAN"


def test_inv_exec_7_rollback_restores_exact_checkpoint_state() -> None:
    """INV-EXEC-7: rollback restores the selected checkpoint exactly."""
    runtime, state = _runtime()
    node = runtime._current_graph.get_vertices()[0]
    state.W[node] = Buffer.completed(None, {"value": 7})
    checkpoint = Checkpoint.take(state.step_index, state.execution_id, state.to_dict(), "before")
    checkpoint.validate()
    state.C.add(checkpoint)
    expected = pickle.dumps(checkpoint.es_snapshot)
    state.W[node] = Buffer.completed(None, {"value": 99})
    runtime.act(Decision.ROLLBACK, state)
    assert pickle.dumps(state.to_dict()) == expected
