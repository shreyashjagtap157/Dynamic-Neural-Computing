"""Phase 1 exit criteria tests — 9 criteria from mvp-roadmap.md Section 3.

These tests verify the core execution engine is correctly implemented before
proceeding to Phase 2 (planning/scheduling).
"""

import sys
sys.path.insert(0, 'src')

from dnc.runtime.types import (
    UNBOUND,
    PENDING,
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
    InvariantViolation,
    StateComponentViolation,
    DAGCycle,
)
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory, HistoryLog
from dnc.state.checkpoint import Checkpoint, CheckpointRecord
from dnc.state.registry import ModuleRegistry
from dnc.scheduler.scheduler import Scheduler
from dnc.invariants.runtime_invariants import check_invariants
from dnc.modules.standard import SourceModule, TransformModule, AggregateModule, SinkModule


class TestPhase1ExitCriteria:
    """9 exit criteria for Phase 1 (core execution engine)."""

    def test_ec1_execution_state_initialization(self):
        """EC-1: ES(t) initializes correctly with all 5 components non-null."""
        es = ExecutionState()
        assert es.W is not None
        assert es.M is not None
        assert es.C is not None
        assert es.H is not None
        assert hasattr(es, "R")
        assert es._step_index == 0

    def test_ec2_working_memory_binding(self):
        """EC-2: WorkingMemory.register() binds new module instance IDs."""
        wm = WorkingMemory()
        mid1 = ModuleInstanceID("Source")
        mid2 = ModuleInstanceID("Transform")

        wm.register(mid1)
        wm.register(mid2)

        assert mid1 in wm
        assert mid2 in wm
        assert isinstance(wm[mid1].input, UNBOUND)
        assert isinstance(wm[mid1].output, UNBOUND)

        wm[mid1] = Buffer.completed("value", "out")
        assert wm[mid1].input == "value"
        assert wm[mid1].output == "out"

    def test_ec3_working_memory_immutability(self):
        """EC-3: WorkingMemory entries are immutable once written (copy-on-write)."""
        wm = WorkingMemory()
        mid = ModuleInstanceID("Source")
        wm.register(mid)

        buf1 = wm[mid]
        wm[mid] = Buffer.completed("x", "y")
        buf2 = wm[mid]

        assert buf1.output == UNBOUND()
        assert buf2.output == "y"

    def test_ec4_module_registry(self):
        """EC-4: ModuleRegistry enforces single-ownership (INV-4)."""
        registry = ModuleRegistry()
        type_id = ModuleTypeID("Source", "abc123")
        contract = ModuleContract(
            module_type_id=type_id,
            output_signature=str,
        )
        registry.register(contract)

        try:
            registry.register(contract)
            assert False, "Expected ValueError for duplicate registration"
        except ValueError as e:
            assert "already registered" in str(e)

    def test_ec5_dag_scheduler(self):
        """EC-5: Scheduler accepts DAG and computes topological order."""
        s = Scheduler()
        n1 = ModuleInstanceID("A")
        n2 = ModuleInstanceID("B")
        n3 = ModuleInstanceID("C")

        s.set_graph(nodes=[n1, n2, n3], edges=[(n1, n2), (n2, n3)])
        order = s.get_dispatch_order()

        assert order.index(n1) < order.index(n2)
        assert order.index(n2) < order.index(n3)

    def test_ec6_dag_rejects_cycle(self):
        """EC-6: Scheduler.set_graph() raises DAGCycle for cycles."""
        s = Scheduler()
        n1 = ModuleInstanceID("X")
        n2 = ModuleInstanceID("Y")
        n3 = ModuleInstanceID("Z")

        try:
            s.set_graph(nodes=[n1, n2, n3], edges=[(n1, n2), (n2, n3), (n3, n1)])
            assert False, "Expected DAGCycle for cycle detection"
        except DAGCycle:
            pass

    def test_ec7_runnable_detection(self):
        """EC-7: Scheduler.get_runnable() correctly identifies dispatchable nodes."""
        s = Scheduler()
        n1 = ModuleInstanceID("A")
        n2 = ModuleInstanceID("B")
        n3 = ModuleInstanceID("C")

        s.set_graph(nodes=[n1, n2, n3], edges=[(n1, n2), (n2, n3)])

        wm = WorkingMemory()
        wm.register(n1)
        wm.register(n2)
        wm.register(n3)

        runnable = s.get_runnable(wm)
        assert n1 in runnable
        assert n2 not in runnable
        assert n3 not in runnable

        wm[n1] = Buffer.completed("a", "out_a")
        runnable = s.get_runnable(wm)
        assert n1 in runnable
        assert n2 in runnable
        assert n3 not in runnable

    def test_ec8_step_index_advance(self):
        """EC-8: ExecutionState.advance_step() correctly increments step index."""
        es = ExecutionState()
        assert es.step_index == 0
        es.advance_step()
        assert es.step_index == 1
        es.advance_step()
        assert es.step_index == 2

    def test_ec9_checkpoint_lifecycle(self):
        """EC-9: Checkpoint.take() creates a valid checkpoint after validation."""
        es = ExecutionState()
        es.advance_step()

        snapshot = es.to_dict()
        ck = Checkpoint.take(
            step_index=es.step_index,
            execution_id=es.execution_id,
            es_snapshot=snapshot,
            provenance_ref="test_provenance",
        )

        assert not ck.is_valid
        ck.validate()
        assert ck.is_valid

        cr = CheckpointRecord()
        cr.add(ck)
        assert len(cr) == 1
        assert cr.latest().step_index == es.step_index


if __name__ == "__main__":
    t = TestPhase1ExitCriteria()
    results = []
    for name in sorted(dir(t)):
        if name.startswith('test_'):
            try:
                getattr(t, name)()
                results.append(f'PASS: {name}')
            except Exception as e:
                results.append(f'FAIL: {name} -- {e}')
    for r in results:
        print(r)
    print(f"\n{sum(1 for r in results if r.startswith('PASS'))}/{len(results)} tests passed")