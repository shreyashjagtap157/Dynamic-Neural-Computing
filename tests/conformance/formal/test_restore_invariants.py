"""Executable evidence for INV-FM-1 and INV-FM-2."""

import pickle

from dnc.runtime.runtime import Runtime
from dnc.runtime.types import Buffer, ModuleContract, ModuleTypeID
from dnc.state.checkpoint import Checkpoint


def _checkpointed():
    runtime = Runtime()
    runtime.register_module(
        ModuleContract(module_type_id=ModuleTypeID("Source", "v1"), output_signature=object)
    )
    state = runtime.initiate("restore")
    node = runtime._current_graph.get_vertices()[0]
    state.W[node] = Buffer.completed(None, 7)
    checkpoint = Checkpoint.take(state.step_index, state.execution_id, state.to_dict(), "restore")
    checkpoint.validate()
    state.C.add(checkpoint)
    return runtime, state, checkpoint


def test_inv_fm_1_restore_does_not_modify_checkpoint() -> None:
    """INV-FM-1: restore copies state without modifying the checkpoint."""
    runtime, state, checkpoint = _checkpointed()
    before = pickle.dumps(checkpoint)
    runtime._rollback_to_checkpoint(state)
    assert pickle.dumps(checkpoint) == before


def test_inv_fm_2_restore_continues_step_index_linearly() -> None:
    """INV-FM-2: restore sets checkpoint step and subsequent advance is linear."""
    runtime, state, checkpoint = _checkpointed()
    state.advance_step()
    state.advance_step()
    runtime._rollback_to_checkpoint(state)
    assert state.step_index == checkpoint.step_index
    assert state.advance_step() == checkpoint.step_index + 1
