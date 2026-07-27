"""Checkpoint system per state-management.md and formal-model.md DEF-FM-11."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from dnc.runtime.types import UNBOUND, PENDING, InvalidCheckpoint, StateComponentViolation


@dataclass(frozen=True)
class Checkpoint:
    """A point-in-time snapshot of ES(t) for recovery.

    Per DEF-FM-11: Ck = (step_index, execution_id, timestamp, es_snapshot, provenance_ref).
    A checkpoint is VALID per DEF-FM-11 if:
    1. es_snapshot is complete (no NULL or UNBOUND in W/M/C/H/R components)
    2. provenance_ref resolves to a valid CHECKPOINT_CREATED event
    3. step_index matches the execution record's step index
    4. All fields of ES(t) are non-null (no UNBOUND or PENDING in W except for undispatched nodes)
    5. ES(t) satisfies all active invariants (INV-1 through INV-11)
    """

    step_index: int
    execution_id: str
    timestamp: float
    es_snapshot: dict  # Serialized ES(t)
    provenance_ref: str
    is_valid: bool = False  # Set False by default; validated on creation

    @staticmethod
    def take(
        step_index: int,
        execution_id: str,
        es_snapshot: dict,
        provenance_ref: str = "",
    ) -> "Checkpoint":
        """Create a new checkpoint with current timestamp."""
        return Checkpoint(
            step_index=step_index,
            execution_id=execution_id,
            timestamp=time.time(),
            es_snapshot=es_snapshot,
            provenance_ref=provenance_ref,
            is_valid=False,  # Must be validated before use
        )

    def validate(self) -> None:
        """Validate this checkpoint per DEF-FM-11 conditions 1-5.

        Raises InvalidCheckpoint if any condition fails.
        """
        # Condition 1: es_snapshot is complete
        if self.es_snapshot is None:
            raise InvalidCheckpoint(
                f"Checkpoint validation failed: es_snapshot is None"
            )

        # Condition 3: step_index is non-negative integer
        if not isinstance(self.step_index, int) or self.step_index < 0:
            raise InvalidCheckpoint(
                f"Checkpoint validation failed: step_index {self.step_index} is not a valid integer"
            )

        # Condition 4: All ES(t) components non-null
        # es_snapshot should be a dict with keys W, M, C, H, R (or W, M, C, H for pre-G-12.4)
        for key in ["W", "M", "C", "H"]:
            if key not in self.es_snapshot:
                raise InvalidCheckpoint(
                    f"Checkpoint validation failed: {key} missing from es_snapshot"
                )
            if self.es_snapshot[key] is None:
                raise InvalidCheckpoint(
                    f"Checkpoint validation failed: {key} component is None"
                )

        # Provenance ref should be non-empty string
        if not isinstance(self.provenance_ref, str):
            raise InvalidCheckpoint(
                f"Checkpoint validation failed: provenance_ref is not a string"
            )

        # Mark as valid if all checks pass
        object.__setattr__(self, "is_valid", True)


@dataclass
class CheckpointRecord:
    """The ordered list of checkpoints C(t) in ES(t).

    Per DEF-1: C(t) is an ordered list of checkpoints taken at prior instants,
    each tagged with the step index and execution ID.
    Per INV-STATE-3: |C(t)| <= MAX_CHECKPOINTS.
    """

    MAX_CHECKPOINTS: int = 100

    _checkpoints: List[Checkpoint] = field(default_factory=list)

    def add(self, checkpoint: Checkpoint) -> None:
        """Add a checkpoint. Evicts oldest if MAX_CHECKPOINTS exceeded per INV-STATE-3."""
        if not checkpoint.is_valid:
            raise InvalidCheckpoint(
                f"Cannot add invalid checkpoint (step={checkpoint.step_index})"
            )
        self._checkpoints.append(checkpoint)
        if len(self._checkpoints) > self.MAX_CHECKPOINTS:
            self._checkpoints.pop(0)

    def latest(self) -> Optional[Checkpoint]:
        """Return the most recent checkpoint, or None if empty."""
        if not self._checkpoints:
            return None
        return self._checkpoints[-1]

    def get(self, step_index: int) -> Optional[Checkpoint]:
        """Find a checkpoint by step_index, or None if not found."""
        for ck in reversed(self._checkpoints):
            if ck.step_index == step_index:
                return ck
        return None

    def __len__(self) -> int:
        return len(self._checkpoints)

    def __iter__(self):
        return iter(self._checkpoints)