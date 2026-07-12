"""Integration tests: full pipeline DAG execution.

Tests a complete Source → Transform → Aggregate → Sink linear pipeline
with checkpoint and rollback capabilities.
"""

import sys
sys.path.insert(0, 'src')

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import Checkpoint, CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.invariants.runtime_invariants import check_invariants
from dnc.modules.standard import SourceModule, TransformModule, AggregateModule, SinkModule


class TestIntegrationLinearPipeline:
    """Integration test: Source → Transform → Aggregate → Sink."""

    def test_full_linear_pipeline(self):
        """Run a complete 4-node linear DAG and verify all outputs."""
        # Create registry entries
        source_type = ModuleTypeID("Source", "src_v1")
        transform_type = ModuleTypeID("Transform", "xfrm_v1")
        aggregate_type = ModuleTypeID("Aggregate", "agg_v1")
        sink_type = ModuleTypeID("Sink", "sink_v1")

        source_contract = ModuleContract(module_type_id=source_type, output_signature=int)
        transform_contract = ModuleContract(module_type_id=transform_type, output_signature=int)
        aggregate_contract = ModuleContract(module_type_id=aggregate_type, output_signature=int)
        sink_contract = ModuleContract(module_type_id=sink_type, output_signature=type(None))

        registry = ModuleRegistry()
        for c in [source_contract, transform_contract, aggregate_contract, sink_contract]:
            registry.register(c)

        # Create instances
        src = ModuleInstanceID("Source", 1)
        xfrm = ModuleInstanceID("Transform", 1)
        agg = ModuleInstanceID("Aggregate", 1)
        sink = ModuleInstanceID("Sink", 1)

        # Create module implementations
        source_mod = SourceModule(source_type, source_contract, output_value=42)
        transform_mod = TransformModule(transform_type, transform_contract, transform_fn=lambda x: x * 2)
        aggregate_mod = AggregateModule(aggregate_type, aggregate_contract, reduce_fn=sum)
        sink_mod = SinkModule(sink_type, sink_contract)

        # Wire into working memory
        wm = WorkingMemory()
        wm.register(src)
        wm.register(xfrm)
        wm.register(agg)
        wm.register(sink)

        # Set up scheduler DAG: src → xfrm → agg → sink
        sched = Scheduler()
        sched.set_graph(
            nodes=[src, xfrm, agg, sink],
            edges=[
                (src, xfrm),
                (xfrm, agg),
                (agg, sink),
            ]
        )

        # Build execution state
        es = ExecutionState()
        es.W = wm
        es.M = registry.snapshot()
        es.G = sched
        es.C = CheckpointRecord()

        check_invariants(es)

        # Take initial checkpoint
        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "INIT")
        ck.validate()
        es.C.add(ck)

        # Dispatch in topological order
        for instance_id in sched.get_dispatch_order():
            if instance_id == src:
                result = source_mod.observe(None)
                wm[instance_id] = Buffer.completed(None, result)
            elif instance_id == xfrm:
                result = transform_mod.observe(wm.get_output(src))
                wm[instance_id] = Buffer.completed(wm.get_output(src), result)
            elif instance_id == agg:
                result = aggregate_mod.observe(wm.get_output(xfrm))
                wm[instance_id] = Buffer.completed(wm.get_output(xfrm), result)
            elif instance_id == sink:
                result = sink_mod.observe(wm.get_output(agg))
                wm[instance_id] = Buffer.completed(wm.get_output(agg), result)

            check_invariants(es)
            es.advance_step()

        # Verify final outputs
        assert wm.get_output(src) == 42
        assert wm.get_output(xfrm) == 84
        assert wm.get_output(agg) == 84
        assert sink_mod._accumulator == 84

        # Take final checkpoint
        ck_final = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "FINAL")
        ck_final.validate()
        es.C.add(ck_final)

        assert len(es.C) == 2
        assert es.step_index == 4

    def test_checkpoint_restore(self):
        """Restore ES(t) from a checkpoint and verify state matches."""
        es = ExecutionState()
        es.advance_step()
        es.advance_step()

        snapshot = es.to_dict()
        ck = Checkpoint.take(es.step_index, es.execution_id, snapshot, "RESTORE_TEST")
        ck.validate()

        cr = CheckpointRecord()
        cr.add(ck)

        restored = ExecutionState.from_dict(ck.es_snapshot)
        assert restored.step_index == es.step_index
        assert restored.execution_id == es.execution_id
        assert restored._rng_state == es._rng_state


class TestSchedulerEdgeCases:
    """Edge cases for the scheduler and dispatch logic."""

    def test_diamond_dag(self):
        """Test a diamond DAG: one source branching to two transforms that merge."""
        src = ModuleInstanceID("Source", 1)
        xfrm1 = ModuleInstanceID("Transform", 1)
        xfrm2 = ModuleInstanceID("Transform", 2)
        sink = ModuleInstanceID("Sink", 1)

        sched = Scheduler()
        sched.set_graph(
            nodes=[src, xfrm1, xfrm2, sink],
            edges=[
                (src, xfrm1),
                (src, xfrm2),
                (xfrm1, sink),
                (xfrm2, sink),
            ]
        )

        order = sched.get_dispatch_order()
        # src must come before both xfrm1 and xfrm2
        # sink must come after both xfrm1 and xfrm2
        assert order.index(src) < order.index(xfrm1)
        assert order.index(src) < order.index(xfrm2)
        assert order.index(xfrm1) < order.index(sink)
        assert order.index(xfrm2) < order.index(sink)

    def test_empty_graph(self):
        """Test scheduler with no nodes (no-op)."""
        sched = Scheduler()
        sched.set_graph(nodes=[], edges=[])
        assert sched.get_dispatch_order() == []

    def test_single_node_graph(self):
        """Test scheduler with a single node."""
        n = ModuleInstanceID("Source", 1)
        sched = Scheduler()
        sched.set_graph(nodes=[n], edges=[])
        assert sched.get_dispatch_order() == [n]

    def test_multi_step_dispatch(self):
        """Test that runnable detection changes as buffers complete."""
        src = ModuleInstanceID("Source", 1)
        xfrm = ModuleInstanceID("Transform", 1)

        sched = Scheduler()
        sched.set_graph(nodes=[src, xfrm], edges=[(src, xfrm)])

        wm = WorkingMemory()
        wm.register(src)
        wm.register(xfrm)

        # Initially only src is runnable (xfrm is blocked by UNBOUND src output)
        runnable1 = sched.get_runnable(wm)
        assert src in runnable1
        assert xfrm not in runnable1

        # After src completes, xfrm becomes runnable
        wm[src] = Buffer.completed(None, 10)
        runnable2 = sched.get_runnable(wm)
        assert src in runnable2
        assert xfrm in runnable2


if __name__ == "__main__":
    import traceback

    test_classes = [TestIntegrationLinearPipeline, TestSchedulerEdgeCases]
    all_passed = 0
    all_failed = 0

    for cls in test_classes:
        t = cls()
        for name in sorted(dir(t)):
            if name.startswith('test_'):
                try:
                    getattr(t, name)()
                    print(f"PASS: {cls.__name__}.{name}")
                    all_passed += 1
                except Exception:
                    print(f"FAIL: {cls.__name__}.{name}")
                    traceback.print_exc()
                    all_failed += 1

    print(f"\n{all_passed}/{all_passed + all_failed} integration tests passed")