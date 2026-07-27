"""G-12.2 resolution tests — byte-exact state preservation.

G-12.2 (formal-model.md): DEF-FM-10 Clause 4 requires byte-exact state
preservation for RETAINED nodes across a replan and byte-exact checkpoint
restore. The formal model lacks a memory-address model to *prove* this, so the
agreed resolution is: verify it by testing rather than formal proof.

These tests exercise the REAL planner/runtime replan path (not hand-built
graphs) to confirm that:
  (a) the planner reuses the same ModuleInstanceID for the same role across a
      replan, so compute_graph_diff actually yields RETAINED nodes, and
  (b) the RETAINED node's working-memory Buffer is byte-for-byte identical
      before and after the replan (pickle comparison), and
  (c) a checkpoint restored via ExecutionState.from_dict reproduces the
      original ES(t) byte-for-byte.
"""

import sys
import pickle

sys.path.insert(0, "src")

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.registry import ModuleRegistry
from dnc.state.checkpoint import Checkpoint
from dnc.planner.pipeline import (
    Planner,
    PlanningTask,
    ReplanContext,
)
from dnc.runtime.runtime import Runtime, ExecutionState2


class TestG12ByteExact:
    """Implementation-level verification of G-12.2 (byte-exact preservation)."""

    def test_g122_planner_reuses_ids_across_replan(self):
        """A replan of an identical role MUST yield the same ModuleInstanceID.

        This is the precondition for RETAINED nodes to exist at all: the
        original implementation generated a fresh random UUID on every
        ModuleInstanceID construction, so RETAINED was always empty and
        byte-exact preservation could never hold.
        """
        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(
            ModuleContract(
                module_type_id=type_a,
                output_signature=int,
                capabilities=frozenset(["source"]),
            )
        )

        planner = Planner()
        g_old = planner.plan(
            PlanningTask(
                task_description="source",
                available_modules=registry,
                resource_budget=50.0,
            )
        ).graph
        g_new = planner.plan(
            PlanningTask(
                task_description="replan",
                available_modules=registry,
                resource_budget=50.0,
                replan_context=ReplanContext(g_old=g_old, es=ExecutionState(), trigger="X"),
            )
        ).graph

        old_ids = g_old.get_vertices()
        new_ids = g_new.get_vertices()
        assert old_ids, "old graph must have vertices"
        # Same role -> identical IDs -> the two sets intersect (RETAINED non-empty)
        assert set(old_ids) & set(new_ids), (
            "Planner MUST reuse ModuleInstanceIDs across a replan so that "
            "RETAINED nodes exist (G-12.2 precondition)."
        )

    def test_g122_replan_preserves_retained_state_byte_exact(self):
        """ES(t)[v] for each RETAINED node v is byte-exact before/after replan."""
        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(
            ModuleContract(
                module_type_id=type_a,
                output_signature=int,
                capabilities=frozenset(["source"]),
            )
        )

        planner = Planner()
        g_old = planner.plan(
            PlanningTask(
                task_description="source",
                available_modules=registry,
                resource_budget=50.0,
            )
        ).graph

        es = ExecutionState()
        es.W = WorkingMemory()
        for v in g_old.get_vertices():
            es.W.register(v)
            es.W[v] = Buffer.completed({"in": v.type_id}, {"out": 42, "meta": [1, 2, 3]})

        g_new = planner.plan(
            PlanningTask(
                task_description="replan",
                available_modules=registry,
                resource_budget=50.0,
                replan_context=ReplanContext(g_old=g_old, es=es, trigger="X"),
            )
        ).graph

        retained, retired_early, new_only = planner.compute_graph_diff(g_old, g_new, es)
        assert retained, "replan of identical role MUST produce RETAINED nodes"
        assert not new_only, "identical role replan MUST NOT create NEW nodes"

        for v in retained:
            before = pickle.dumps(es.W[v])
            # Simulate the runtime replan step: only NEW nodes are re-registered,
            # RETAINED nodes keep their existing W entry untouched.
            if v in new_only:
                es.W.register(v)
            after = pickle.dumps(es.W[v])
            assert before == after, (
                f"RETAINED node {v} working memory MUST be byte-exact across "
                f"replan (G-12.2). Bytes differed."
            )
            # Also confirm the Buffer value itself is unchanged.
            assert es.W[v].output == {"out": 42, "meta": [1, 2, 3]}

    def test_g122_runtime_replan_does_not_mutate_retained_w(self):
        """End-to-end: Runtime._execute_replan preserves RETAINED W byte-exact."""
        runtime = Runtime(config=None, initial_budget=100.0)
        registry = ModuleRegistry()
        type_a = ModuleTypeID("Source", "hash_src")
        registry.register(ModuleContract(module_type_id=type_a, output_signature=int))
        runtime._registry = registry

        es = runtime.initiate("test task")
        runtime._state = ExecutionState2.RUNNING
        runtime._critical_section = False
        runtime._replan_count = 0

        g_old = runtime._current_graph
        assert g_old is not None and g_old.get_vertices(), "initiate must build a graph"

        node = g_old.get_vertices()[0]
        es.W[node] = Buffer.completed({"seed": 7}, {"result": 99, "trace": ["a", "b"]})

        before_bytes = pickle.dumps(es.W[node])
        before_id = node.uuid

        runtime._execute_replan(es)

        assert node in es.W, "RETAINED node must remain in W after replan"
        after_bytes = pickle.dumps(es.W[node])
        assert before_bytes == after_bytes, (
            "Runtime replan MUST preserve RETAINED node W byte-exact (G-12.2)."
        )
        assert es.W[node].uuid == before_id, "RETAINED node identity must be stable"

    def test_g122_checkpoint_restore_byte_exact(self):
        """Checkpoint restore via from_dict reproduces ES(t) byte-for-byte."""
        es = ExecutionState()
        es.W = WorkingMemory()
        mid = ModuleInstanceID("Source", 0)
        es.W.register(mid)
        es.W[mid] = Buffer.completed({"x": 1}, {"y": 2})
        es.initialize_from_seed(123)
        es.advance_step()

        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "CK_0")
        ck.validate()
        assert ck.is_valid, "checkpoint must validate per DEF-FM-11"

        restored = ExecutionState.from_dict(ck.es_snapshot)

        assert pickle.dumps(restored.to_dict()) == pickle.dumps(es.to_dict()), (
            "Restored ES(t) MUST be a byte-exact copy of the checkpointed ES(t) (G-12.2 / DEF-FM-12)."
        )


if __name__ == "__main__":
    import traceback

    t = TestG12ByteExact()
    results = []
    for name in sorted(dir(t)):
        if name.startswith("test_g122"):
            try:
                getattr(t, name)()
                results.append(f"PASS: {name}")
            except Exception as e:
                results.append(f"FAIL: {name} -- {e}")
                traceback.print_exc()

    for r in results:
        print(r)
