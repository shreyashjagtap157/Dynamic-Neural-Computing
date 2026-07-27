"""Working memory W(t): ModuleInstanceID → Buffer.

Per state-management.md DEF-2: immutable once written, no mutation in place.
"""

from collections.abc import ItemsView
from typing import Dict, Iterator, Optional

from dnc.runtime.types import (
    Buffer,
    ModuleInstanceID,
    UNBOUND,
    PENDING,
)


class WorkingMemory:
    """Maps module instance IDs to their input-output buffers.

    Per DEF-2: W(t) is a total function. Each entry is immutable once written.
    Updates create new entries via setitem, never mutating in place.
    """

    def __init__(self) -> None:
        self._entries: Dict[ModuleInstanceID, Buffer] = {}

    def __getitem__(self, instance_id: ModuleInstanceID) -> Buffer:
        if instance_id not in self._entries:
            raise KeyError(f"ModuleInstanceID {instance_id} not in working memory")
        return self._entries[instance_id]

    def __setitem__(self, instance_id: ModuleInstanceID, buffer: Buffer) -> None:
        new_entries = dict(self._entries)
        new_entries[instance_id] = buffer
        self._entries = new_entries

    def __contains__(self, instance_id: ModuleInstanceID) -> bool:
        return instance_id in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[ModuleInstanceID]:
        return iter(self._entries)

    def items(self) -> ItemsView[ModuleInstanceID, Buffer]:
        """Return the conventional key/value view for this mapping."""
        return self._entries.items()

    def get(self, instance_id: ModuleInstanceID) -> Optional[Buffer]:
        return self._entries.get(instance_id)

    def register(self, instance_id: ModuleInstanceID) -> None:
        """Register a new module instance with UNBOUND output."""
        if instance_id in self._entries:
            raise ValueError(
                f"ModuleInstanceID {instance_id} already registered in working memory"
            )
        new_entries = dict(self._entries)
        new_entries[instance_id] = Buffer.unbound_input()
        self._entries = new_entries

    def is_bound(self, instance_id: ModuleInstanceID) -> bool:
        """True if the module has received input."""
        buf = self._entries.get(instance_id)
        if buf is None:
            return False
        return not isinstance(buf.input, UNBOUND)

    def is_complete(self, instance_id: ModuleInstanceID) -> bool:
        """True if the module has produced output (not UNBOUND and not PENDING).

        Source modules legitimately have no bound input, so completion is an
        output-state property rather than an input-state property.
        """
        buf = self._entries.get(instance_id)
        if buf is None:
            return False
        return (
            not isinstance(buf.output, UNBOUND)
            and not isinstance(buf.output, PENDING)
        )

    def get_output(self, instance_id: ModuleInstanceID) -> object:
        """Return the output value, or raise if not complete."""
        buf = self[instance_id]
        if isinstance(buf.output, UNBOUND):
            raise ValueError(
                f"ModuleInstanceID {instance_id} output is UNBOUND"
            )
        if isinstance(buf.output, PENDING):
            raise ValueError(
                f"ModuleInstanceID {instance_id} output is PENDING"
            )
        return buf.output

    def copy(self) -> "WorkingMemory":
        """Create a deep copy of working memory."""
        wm = WorkingMemory()
        wm._entries = dict(self._entries)
        return wm


class HistoryLog:
    """Append-only record H(t) of state mutations since last checkpoint.

    Per state-management.md DEF-6: H_i = (index, timestamp, mutation_type,
    target_module, before_value, after_value, trigger_provenance_ref).
    Append-only per INV-STATE-10.
    """

    def __init__(self) -> None:
        self._entries: list = []
        self._index_counter = 0

    def append(
        self,
        mutation_type: str,
        target_module: ModuleInstanceID,
        before_value: object,
        after_value: object,
        trigger_provenance_ref: Optional[str] = None,
    ) -> int:
        """Append a history log entry. Returns the assigned index."""
        entry = ImmutableHistoryEntry({
            "index": self._index_counter,
            "timestamp": 0.0,  # Set by clock in runtime
            "mutation_type": mutation_type,
            "target_module": target_module,
            "before_value": before_value,
            "after_value": after_value,
            "trigger_provenance_ref": trigger_provenance_ref,
        })
        self._entries.append(entry)
        idx = self._index_counter
        self._index_counter += 1
        return idx

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int):
        return self._entries[index]

    def __iter__(self) -> Iterator[dict]:
        return iter(self._entries)

    def truncate(self) -> None:
        """Clear the history log. Called after a checkpoint is taken per INV-STATE-11."""
        self._entries = []
        self._index_counter = 0

    def copy(self) -> "HistoryLog":
        hl = HistoryLog()
        hl._entries = list(self._entries)
        hl._index_counter = self._index_counter
        return hl


class ImmutableHistoryEntry(dict):
    """Dictionary-compatible, immutable history record."""

    def _immutable(self, *args: object, **kwargs: object) -> None:
        raise TypeError("history entries are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
