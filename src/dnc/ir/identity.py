"""
DNC-IR Identity Semantics (SPEC-IR Section 6)
Implements stable, immutable, mutation-tracked identifiers across DNC v2.x.
"""

from dataclasses import dataclass, field
import uuid
from typing import Set

@dataclass(frozen=True)
class UnitID:
    value: str = field(default_factory=lambda: f"unit_{uuid.uuid4().hex[:12]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class InstanceID:
    value: str = field(default_factory=lambda: f"inst_{uuid.uuid4().hex[:12]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class GraphID:
    value: str = field(default_factory=lambda: f"graph_{uuid.uuid4().hex[:12]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class GraphVersion:
    major: int = 1
    minor: int = 0
    patch: int = 0
    sequence: int = 0

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}-{self.sequence}"

    def next_sequence(self) -> 'GraphVersion':
        return GraphVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            sequence=self.sequence + 1
        )

@dataclass(frozen=True)
class MutationID:
    value: str = field(default_factory=lambda: f"mut_{uuid.uuid4().hex[:12]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class TransactionID:
    value: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:12]}")
    
    def __str__(self) -> str:
        return self.value

class IdentityRegistry:
    """
    Enforces DNC-IR identity permanence: retired UnitIDs are never reused.
    """
    def __init__(self):
        self._active_units: Set[str] = set()
        self._retired_units: Set[str] = set()

    def register_unit(self, unit_id: UnitID) -> None:
        uid = unit_id.value
        if uid in self._retired_units:
            raise ValueError(f"Identity Violation: Retired UnitID {uid} cannot be reused.")
        if uid in self._active_units:
            raise ValueError(f"Identity Violation: UnitID {uid} is already active.")
        self._active_units.add(uid)

    def retire_unit(self, unit_id: UnitID) -> None:
        uid = unit_id.value
        if uid in self._active_units:
            self._active_units.remove(uid)
            self._retired_units.add(uid)

    def is_active(self, unit_id: UnitID) -> bool:
        return unit_id.value in self._active_units

    def is_retired(self, unit_id: UnitID) -> bool:
        return unit_id.value in self._retired_units
