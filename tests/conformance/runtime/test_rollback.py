"""Conformance tests for the ROLLBACK decision path (state-management.md 3.C).

Per state-management.md Section 3.C (Rollback Path): when DecisionPolicy returns
ROLLBACK, the runtime restores ES(t) from the most recent valid checkpoint. The
restored state must be deep-isolated (ACD-002) and the ROLLBACK decision must be
wired end-to-end (it previously raised AttributeError). These tests close ACD-003.
"""

import sys

sys.path.insert(0, "src")

from dnc.runtime.types import (
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
    Buffer,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import Checkpoint, CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.planner.pipeline import ExecutionGraph, VertexAssignment
from dnc.runtime.runtime import Runtime, Decision, ExecutionState2


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
    es.W[mids["SRC"]] = Buffer.completed(None, 1)

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


class TestRollbackDecision:
    """ROLLBACK restores ES(t) from the latest checkpoint (ACD-003)."""

    def test_rollback_restores_from_checkpoint(self):
        """act(ROLLBACK) restores live state to the latest checkpoint snapshot."""
        runtime, es, mids = _build_linear_runtime()

        # Take a checkpoint with a known SRC output.
        es.W[mids["SRC"]] = Buffer.completed(None, 111)
        ck = Checkpoint.take(es.step_index, es.execution_id, es.copy().to_dict(), "CK_RB")
        ck.validate()
        es.C.add(ck)

        # Mutate the live state after checkpointing.
        es.W[mids["SRC"]] = Buffer.completed(None, 999)
        es.W[mids["TR"]] = Buffer.completed(None, 555)

        # Trigger rollback via the control-loop decision.
        runtime.act(Decision.ROLLBACK, es)

        assert es.W[mids["SRC"]].output == 111, (
            f"ROLLBACK did not restore SRC output: {es.W[mids['SRC']].output}"
        )
        assert es.W[mids["TR"]].output is None or isinstance(
            es.W[mids["TR"]].output, (object,)
        ), "ROLLBACK should revert TR to pre-checkpoint state"
        # TR was unbound at checkpoint time -> after rollback it is unbound.
        from dnc.runtime.types import UNBOUND, PENDING

        assert isinstance(es.W[mids["TR"]].output, (UNBOUND, PENDING)), (
            "TR must be reverted to its unbound checkpoint state"
        )
        print("PASS: test_rollback_restores_from_checkpoint")

    def test_rollback_is_deep_isolated(self):
        """The restored ES(t) does not alias the checkpoint snapshot (INV-STATE-4)."""
        runtime, es, mids = _build_linear_runtime()

        es.W[mids["SRC"]] = Buffer.completed(None, 7)
        ck = Checkpoint.take(es.step_index, es.execution_id, es.copy().to_dict(), "CK_ISO")
        ck.validate()
        es.C.add(ck)

        # Mutate live state, then rollback.
        es.W[mids["SRC"]] = Buffer.completed(None, 13)
        runtime.act(Decision.ROLLBACK, es)

        # Mutating live state after rollback must not change the stored snapshot.
        es.W[mids["SRC"]] = Buffer.completed(None, 42)
        assert ck.es_snapshot["W"][mids["SRC"]].output == 7, (
            "Live mutation after rollback leaked into checkpoint (aliasing)"
        )
        print("PASS: test_rollback_is_deep_isolated")

    def test_rollback_without_checkpoint_is_safe(self):
        """ROLLBACK with no checkpoint is a no-op, not a crash (C3 fix)."""
        runtime, es, mids = _build_linear_runtime()
        # Must not raise (previously raised AttributeError: _rollback_to_checkpoint).
        runtime.act(Decision.ROLLBACK, es)
        assert es.C.latest() is None
        print("PASS: test_rollback_without_checkpoint_is_safe")


if __name__ == "__main__":
    import traceback

    g = TestRollbackDecision()
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
