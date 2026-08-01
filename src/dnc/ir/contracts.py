"""Typed port contracts for the Generic DNC-IR graph boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PortDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class PortKind(str, Enum):
    DATA = "DATA"
    CONTROL = "CONTROL"
    STATE = "STATE"
    RESOURCE = "RESOURCE"


class PortCardinality(str, Enum):
    EXACTLY_ONE = "EXACTLY_ONE"
    ZERO_OR_ONE = "ZERO_OR_ONE"
    ONE_OR_MORE = "ONE_OR_MORE"
    ZERO_OR_MORE = "ZERO_OR_MORE"

    @property
    def minimum(self) -> int:
        return 1 if self in {self.EXACTLY_ONE, self.ONE_OR_MORE} else 0

    @property
    def maximum(self) -> int | None:
        return 1 if self in {self.EXACTLY_ONE, self.ZERO_OR_ONE} else None


@dataclass(frozen=True)
class PortContract:
    port_id: str
    direction: PortDirection
    kind: PortKind
    schema: dict[str, Any] = field(default_factory=dict)
    cardinality: PortCardinality = PortCardinality.EXACTLY_ONE
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.direction, PortDirection):
            raise TypeError("port direction MUST be a PortDirection")
        if not isinstance(self.kind, PortKind):
            raise TypeError("port kind MUST be a PortKind")
        if not isinstance(self.cardinality, PortCardinality):
            raise TypeError("port cardinality MUST be a PortCardinality")
        if not isinstance(self.schema, dict):
            raise TypeError("port schema MUST be an object")
        if not isinstance(self.port_id, str) or not self.port_id or self.port_id.strip() != self.port_id:
            raise ValueError("port_id MUST be non-empty and whitespace-normalized")
        if not isinstance(self.description, str):
            raise TypeError("port description MUST be a string")
        if self.kind is not PortKind.CONTROL and not self.schema:
            raise ValueError(f"{self.kind.value} ports MUST declare a non-empty schema")
