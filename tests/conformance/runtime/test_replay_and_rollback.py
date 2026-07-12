"""Conformance tests for ACD-002 (INV-STATE-4: Checkpoint Immutability).

Per state-management.md INV-STATE-4: "Once taken, a checkpoint record Ck is
immutable. No field of a valid checkpoint MAY be modified after creation." A
checkpoint that aliases live execution state is not a checkpoint -- it is a
named pointer to a mutable buffer. These tests verify:

  1. `ExecutionState.to_dict()` freezes the snapshot at capture time, so a
     later mutation of the LIVE ES(t) does not alter an already-taken
     checkpoint's recorded state (capture-time isolation).
  2. `ExecutionState.from_dict()` deep-isolates the restored ES'(t), so a
     mutation of the RESTORED state does not leak back into the checkpoint or
     the live state (restore-time isolation).
  3. A checkpoint record's stored snapshot fields are never mutated by restore.

These tests close ACD-002.
"""

import sys

sys.path.insert(0, "src")

from dnc.runtime.types import Buffer, ModuleInstanceID
from dnc.state.execution_state import ExecutionState
from dnc.state.working_memory import WorkingMemory
from dnc.state.checkpoint import Checkpoint


def _fresh_es() -> ExecutionState:
    """A minimal ES(t) with one completed node and one unbound node."""
    es = ExecutionState()
    es.W = WorkingMemory()
    es.initialize_from_seed(0)
    a = ModuleInstanceID("A", 0)
    b = ModuleInstanceID("B", 0)
    es.W.register(a)
    es.W.register(b)
    es.W[a] = Buffer.completed(None, 42)
    es.W[b] = Buffer.unbound_input()
    return es


class TestCheckpointImmutability:
    """ACD-002 / INV-STATE-4: a taken checkpoint is immutable."""

    def test_snapshot_immune_to_live_mutation(self):
        """Mutating live ES(t) after capture must not change the checkpoint."""
        es = _fresh_es()
        a = ModuleInstanceID("A", 0)

        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "CK_A")
        ck.validate()

        # Now mutate the LIVE state.
        es.W[a] = Buffer.completed(None, 999)
        es.advance_step()

        # The checkpoint's recorded snapshot must still show the original value.
        snap_a = ck.es_snapshot["W"][a]
        assert snap_a.output == 42, (
            f"Checkpoint silently followed live mutation: {snap_a.output} != 42"
        )
        print("PASS: test_snapshot_immune_to_live_mutation")

    def test_restore_is_deep_isolated_from_checkpoint(self):
        """Mutating the RESTORED state must not alter the checkpoint snapshot."""
        es = _fresh_es()
        a = ModuleInstanceID("A", 0)

        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "CK_B")
        ck.validate()

        restored = ExecutionState.from_dict(ck.es_snapshot)
        # Mutate the restored copy.
        restored.W[a] = Buffer.completed(None, 7)

        assert ck.es_snapshot["W"][a].output == 42, (
            "Restore mutated the checkpoint's stored snapshot (aliasing)"
        )
        # Restored state is independent of live state too.
        es.W[a] = Buffer.completed(None, 13)
        assert restored.W[a].output == 7, "Restored state aliases live state"
        assert ck.es_snapshot["W"][a].output == 42, (
            "Live mutation leaked into checkpoint after restore"
        )
        print("PASS: test_restore_is_deep_isolated_from_checkpoint")

    def test_restore_is_deep_isolated_from_live(self):
        """from_dict restore must not share mutable W/H/C with the live ES(t)."""
        es = _fresh_es()
        a = ModuleInstanceID("A", 0)

        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "CK_C")
        restored = ExecutionState.from_dict(ck.es_snapshot)

        # Mutate live state; restored must be unaffected.
        es.W[a] = Buffer.completed(None, 555)
        es.advance_step()

        assert restored.W[a].output == 42, (
            "Restored ES(t) shares working memory with live ES(t) (aliasing)"
        )
        assert ck.es_snapshot["W"][a].output == 42, (
            "Live mutation leaked into checkpoint snapshot"
        )
        print("PASS: test_restore_is_deep_isolated_from_live")

    def test_checkpoint_record_fields_immutable(self):
        """A valid checkpoint record exposes a frozen snapshot (no back-reference)."""
        es = _fresh_es()
        ck = Checkpoint.take(es.step_index, es.execution_id, es.to_dict(), "CK_D")
        ck.validate()

        # The snapshot must be a distinct object, not the live ES(t) container.
        assert ck.es_snapshot is not es, "Checkpoint snapshot aliases live ES(t)"
        assert ck.es_snapshot["W"] is not es.W, (
            "Checkpoint snapshot W aliases live working memory"
        )
        print("PASS: test_checkpoint_record_fields_immutable")


if __name__ == "__main__":
    import traceback

    g = TestCheckpointImmutability()
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