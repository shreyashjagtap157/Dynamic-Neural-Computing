"""Core data types for the DNC runtime."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional


class ModuleInstanceID:
    """Unique identifier for a module instance within an execution.

    Per state-management.md: each registered module instance has exactly one
    ModuleInstanceID, and no two instances share the same ID within an execution.
    """

    def __init__(self, type_id: str, instance_counter: Optional[int] = None) -> None:
        self._type_id = type_id
        self._instance_uuid = uuid.uuid4()

    @property
    def type_id(self) -> str:
        return self._type_id

    @property
    def uuid(self) -> uuid.UUID:
        return self._instance_uuid

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleInstanceID):
            return NotImplemented
        return (
            self._type_id == other._type_id
            and self._instance_uuid == other._instance_uuid
        )

    def __hash__(self) -> int:
        return hash((self._type_id, self._instance_uuid))

    def __repr__(self) -> str:
        return f"ModuleInstanceID({self._type_id}, {str(self._instance_uuid)[:8]})"


class ModuleTypeID:
    """Stable identifier for a type of module in the registry.

    Per INV-4 (Single-Ownership of Module Semantics): each ModuleTypeID maps
    to exactly one document in the registry.
    """

    def __init__(self, name: str, contract_hash: str) -> None:
        self._name = name
        self._contract_hash = contract_hash

    @property
    def name(self) -> str:
        return self._name

    @property
    def contract_hash(self) -> str:
        return self._contract_hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleTypeID):
            return NotImplemented
        return (
            self._name == other._name
            and self._contract_hash == other._contract_hash
        )

    def __hash__(self) -> int:
        return hash((self._name, self._contract_hash))

    def __repr__(self) -> str:
        return f"ModuleTypeID({self._name}, hash={self._contract_hash[:8]})"


class UNBOUND:
    """Marker for a module instance with no input yet received.

    Per state-management.md DEF-2: an UNBOUND output cannot be dispatched.
    This is implemented as a singleton instance.
    """

    _instance: Optional["UNBOUND"] = None

    def __new__(cls) -> "UNBOUND":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNBOUND"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UNBOUND)

    def __hash__(self) -> int:
        return hash("UNBOUND")


class PENDING:
    """Marker for a module instance that has received input but not yet produced output.

    Per state-management.md DEF-2: PENDING is set when a module has been
    dispatched but has not yet completed.
    """

    _instance: Optional["PENDING"] = None

    def __new__(cls) -> "PENDING":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "PENDING"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PENDING)

    def __hash__(self) -> int:
        return hash("PENDING")


Value = Any
Metadata = Dict[str, Any]


@dataclass(frozen=True)
class Buffer:
    """Working memory buffer for a module instance.

    Per state-management.md DEF-2: Buffer = (input, output, metadata).
    All fields are immutable once written.
    """

    input: Value
    output: Value
    metadata: Metadata

    @staticmethod
    def unbound_input() -> "Buffer":
        """Create a buffer with UNBOUND output (no input yet)."""
        return Buffer(input=UNBOUND(), output=UNBOUND(), metadata={})

    @staticmethod
    def with_input(input_value: Value) -> "Buffer":
        """Create a buffer with bound input but UNBOUND output."""
        return Buffer(input=input_value, output=UNBOUND(), metadata={})

    @staticmethod
    def completed(input_value: Value, output_value: Value, metadata: Optional[Metadata] = None) -> "Buffer":
        """Create a complete buffer with both input and output bound."""
        return Buffer(
            input=input_value,
            output=output_value,
            metadata=metadata if metadata is not None else {},
        )


@dataclass(frozen=True)
class ModuleContract:
    """Declared interface of a module.

    Per module-lifecycle.md: contract consists of input signature,
    output signature, capability annotations, cost parameters,
    and confidence thresholds.
    """

    module_type_id: ModuleTypeID
    output_signature: type = field()
    input_signature: Dict[str, type] = field(default_factory=dict)
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    cost_weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.module_type_id, ModuleTypeID):
            raise TypeError(
                f"module_type_id MUST be ModuleTypeID, got {type(self.module_type_id)}"
            )


class StateComponentViolation(Exception):
    """Raised when any component of ES(t) is null.

    Per state-management.md DEF-1: Any component found null at runtime is a
    State-Component Violation and MUST halt execution.
    """


class InvalidCheckpoint(Exception):
    """Raised when a checkpoint fails validity check per DEF-FM-11."""


class InvariantViolation(Exception):
    """Raised when a runtime invariant (INV-1 to INV-11) is violated."""


class HandoffFailure(Exception):
    """Raised when a state handoff fails per INV-STATE-6 atomicity requirement."""


class ModuleNotFound(Exception):
    """Raised when a module instance ID is not registered."""


class DAGCycle(Exception):
    """Raised when the execution graph contains a cycle (INV-2)."""