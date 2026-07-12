"""Execution state ES(t) per state-management.md DEF-1 and formal-model.md DEF-FM-2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import uuid

from dnc.runtime.types import (
    StateComponentViolation,
    UNBOUND,
    PENDING,
)
from dnc.state.working_memory import WorkingMemory, HistoryLog
from dnc.state.checkpoint import CheckpointRecord


@dataclass
class ExecutionState:
    """ES(t) = (W(t), M(t), C(t), H(t), R(t)) — the complete runtime state at step index t.

    Per state-management.md DEF-1:
    - W(t): working memory (module instance → Buffer)
    - M(t): module registry snapshot
    - C(t): checkpoint record
    - H(t): history log
    - R(t): RNG state (deterministic, from execution header Random Seed)

    Per formal-model.md DEF-FM-2, the execution record ε contains:
    - ExecutionID, H_exec, ES, G, step_index, state, provenance_log, R

    All components MUST be non-null per DEF-1. Any null component is a
    State-Component Violation and MUST halt execution.
    """

    _step_index: int = 0
    _execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _rng_state: int = field(default=0)

    def __post_init__(self) -> None:
        self._validate_components()

    def _validate_components(self) -> None:
        """Verify all required fields are non-null. Raises StateComponentViolation if any is None."""
        required = [self.W, self.M, self.C, self.H]
        names = ["W", "M", "C", "H"]
        for i, (component, name) in enumerate(zip(required, names)):
            if component is None:
                raise StateComponentViolation(
                    f"Execution state component {name}[{i}] is None at step {self._step_index}. "
                    f"Execution MUST halt per state-management.md DEF-1."
                )

    W: Optional[WorkingMemory] = field(default_factory=WorkingMemory)
    M: Optional[Dict[str, Any]] = field(default_factory=dict)  # module registry snapshot
    C: Optional[CheckpointRecord] = field(default_factory=CheckpointRecord)
    H: Optional[HistoryLog] = field(default_factory=HistoryLog)
    G: Optional[Any] = field(default=None)  # Execution graph G = (V, E, w)

    @property
    def step_index(self) -> int:
        return self._step_index

    def advance_step(self) -> int:
        """Increment step_index and return the new value. Per formal-model.md AX-2."""
        self._step_index += 1
        return self._step_index

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def pending_count(self) -> int:
        """Number of registered module instances whose output is not yet bound.

        Drives natural control-loop termination: when pending_count reaches 0
        every node in the execution graph has produced an output, so the
        DecisionPolicy may TERMINATE. Per ACD-001 this makes the runtime own
        execution instead of infinitely re-dispatching.
        """
        if self.W is None:
            return 0
        return sum(
            1
            for _mid, buf in self.W.items()
            if isinstance(buf.output, (UNBOUND, PENDING))
        )

    @property
    def R(self) -> int:
        """RNG state. Deterministic per formal-model.md DEF-FM-2."""
        return self._rng_state

    def advance_rng(self, n: int = 1) -> int:
        """Advance RNG state by n steps. Returns the new state."""
        self._rng_state += n
        return self._rng_state

    def initialize_from_seed(self, seed: int) -> None:
        """Initialize RNG from execution header's Random Seed per PR-10."""
        self._rng_state = seed

    def get_rng_int(self, bound: int) -> int:
        """Return a deterministic random integer in [0, bound)."""
        return (self._rng_state * 1103515245 + 12345) % (2**31) % bound

    def set_execution_id(self, exec_id: str) -> None:
        self._execution_id = exec_id

    def to_dict(self) -> dict:
        """Serialize ES(t) for checkpointing per DEF-FM-11."""
        return {
            "W": self.W,
            "M": self.M,
            "C": self.C,
            "H": self.H,
            "step_index": self._step_index,
            "execution_id": self._execution_id,
            "rng_state": self._rng_state,
            "G": self.G,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionState":
        """Deserialize ES(t) from a checkpoint snapshot.

        Per ACD-002 (INV-RP-2): the restored state MUST be a deep-isolated copy.
        The original ES(t) and the restored ES'(t) must NOT share mutable
        working-memory / checkpoint / history objects, otherwise a checkpoint
        would alias live state and rollback could corrupt its own snapshot.
        """
        es = cls()
        wm_src = data.get("W")
        es.W = wm_src.copy() if wm_src is not None else WorkingMemory()
        es.M = dict(data.get("M")) if data.get("M") else {}
        cr_src = data.get("C")
        es.C = CheckpointRecord()
        if cr_src is not None:
            es.C._checkpoints = list(cr_src._checkpoints)
        hl_src = data.get("H")
        es.H = hl_src.copy() if hl_src is not None else HistoryLog()
        es._step_index = data.get("step_index", 0)
        es._execution_id = data.get("execution_id", str(uuid.uuid4()))
        es._rng_state = data.get("rng_state", 0)
        es.G = data.get("G")
        es._validate_components()
        return es

    def copy(self) -> "ExecutionState":
        """Create a deep copy of ES(t) for checkpoint restoration."""
        es = ExecutionState()
        es.W = self.W.copy() if self.W else WorkingMemory()
        es.M = dict(self.M) if self.M else {}
        es.C = CheckpointRecord()
        if self.C:
            es.C._checkpoints = list(self.C._checkpoints)
        es.H = self.H.copy() if self.H else HistoryLog()
        es._step_index = self._step_index
        es._execution_id = self._execution_id
        es._rng_state = self._rng_state
        es.G = self.G
        return es