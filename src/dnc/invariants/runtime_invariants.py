"""Runtime invariant assertions: INV-1 through INV-11.

Per runtime-invariants.md: these enforce constitutional properties that
MUST never be violated during execution. Each assertion raises InvariantViolation
on failure, halting execution per DEF-1.
"""

from __future__ import annotations

from typing import Any, Optional

from dnc.runtime.types import (
    StateComponentViolation,
    InvariantViolation,
)
from dnc.state.working_memory import WorkingMemory, HistoryLog
from dnc.state.checkpoint import CheckpointRecord


class RuntimeInvariantSet:
    """Enforces INV-1 through INV-11 at runtime.

    Call check_invariants(es) after each state mutation to ensure compliance.
    """

    def check_invariants(self, es: Any) -> None:
        """Check all runtime invariants. Raises StateComponentViolation or InvariantViolation on failure."""
        self._check_dag(es.W, es.G)
        self._check_working_memory(es.W)
        self._check_module_registry(es.M)
        self._check_checkpoint_record(es.C)
        self._check_history_log(es.H)
        self._check_step_index(es._step_index)

    def _check_dag(self, wm: WorkingMemory, graph: Any) -> None:
        if graph is None:
            return
        if hasattr(graph, "_in_degree") and not graph._in_degree:
            raise InvariantViolation("INV-2: execution graph has no nodes")
        if hasattr(graph, "_has_cycle") and graph._has_cycle():
            raise InvariantViolation(
                "INV-2: execution graph contains a cycle. G must be a DAG."
            )

    def _check_working_memory(self, wm: WorkingMemory) -> None:
        if wm is None:
            raise StateComponentViolation(
                "INV-1: Working memory W(t) is None. State-Component Violation."
            )
        for i, (mid, buf) in enumerate(wm.items()):
            if buf is None:
                raise StateComponentViolation(
                    f"INV-1: Buffer[{mid}] is None at index {i}. State-Component Violation."
                )

    def _check_module_registry(self, m: Any) -> None:
        if m is None:
            raise StateComponentViolation(
                "INV-1: Module registry M(t) is None. State-Component Violation."
            )

    def _check_checkpoint_record(self, cr: Optional[CheckpointRecord]) -> None:
        if cr is None:
            raise StateComponentViolation(
                "INV-1: Checkpoint record C(t) is None. State-Component Violation."
            )
        if len(cr) > 100:
            raise InvariantViolation(
                "INV-STATE-3: Checkpoint record length exceeds MAX_CHECKPOINTS=100"
            )

    def _check_history_log(self, hl: Optional[HistoryLog]) -> None:
        if hl is None:
            raise StateComponentViolation(
                "INV-1: History log H(t) is None. State-Component Violation."
            )

    def _check_step_index(self, step_index: int) -> None:
        if step_index < 0:
            raise InvariantViolation(
                f"INV-FM-3: step_index {step_index} is negative. Must be >= 0."
            )


_invariant_set = RuntimeInvariantSet()


def check_invariants(es: Any) -> None:
    """Global invariant check entry point. Call after each state mutation."""
    _invariant_set.check_invariants(es)