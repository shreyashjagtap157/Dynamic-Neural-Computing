"""Typed port contracts for the Generic DNC-IR graph boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.kernel.contracts import EffectType, IsolationGrade, SideEffectClass


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


class IdempotencyMode(str, Enum):
    NONE = "NONE"
    IDEMPOTENT = "IDEMPOTENT"
    KEY_REQUIRED = "KEY_REQUIRED"
    AT_MOST_ONCE = "AT_MOST_ONCE"


class IdempotencyScope(str, Enum):
    REQUEST = "REQUEST"
    TASK = "TASK"
    TENANT = "TENANT"


@dataclass(frozen=True)
class IdempotencyContract:
    mode: IdempotencyMode = IdempotencyMode.NONE
    scope: IdempotencyScope = IdempotencyScope.TASK
    key_field: str | None = None
    payload_hash_required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.mode, IdempotencyMode):
            raise TypeError("idempotency mode MUST be IdempotencyMode")
        if not isinstance(self.scope, IdempotencyScope):
            raise TypeError("idempotency scope MUST be IdempotencyScope")
        if self.mode is IdempotencyMode.KEY_REQUIRED and not self.key_field:
            raise ValueError("KEY_REQUIRED idempotency MUST declare key_field")
        if self.mode is IdempotencyMode.NONE and self.key_field is not None:
            raise ValueError("NONE idempotency cannot declare key_field")
        if self.key_field is not None and (
            not isinstance(self.key_field, str) or not self.key_field.strip()
        ):
            raise ValueError("idempotency key_field MUST be non-empty when provided")
        if not isinstance(self.payload_hash_required, bool):
            raise TypeError("payload_hash_required MUST be boolean")


@dataclass(frozen=True)
class SideEffectContract:
    classification: SideEffectClass = SideEffectClass.NONE
    effect_types: frozenset[EffectType] = frozenset()
    compensation_action: str | None = None
    minimum_isolation: IsolationGrade = IsolationGrade.I0_NONE

    def __post_init__(self) -> None:
        if not isinstance(self.classification, SideEffectClass):
            raise TypeError("side-effect classification MUST be SideEffectClass")
        if not all(isinstance(item, EffectType) for item in self.effect_types):
            raise TypeError("effect_types MUST contain EffectType values")
        if not isinstance(self.minimum_isolation, IsolationGrade):
            raise TypeError("minimum_isolation MUST be IsolationGrade")
        if self.compensation_action is not None and (
            not isinstance(self.compensation_action, str)
            or not self.compensation_action.strip()
        ):
            raise ValueError("compensation_action MUST be non-empty when provided")
        if self.classification is SideEffectClass.NONE:
            if self.effect_types or self.compensation_action:
                raise ValueError("effect-free units cannot declare effects or compensation")
            if self.minimum_isolation is not IsolationGrade.I0_NONE:
                raise ValueError("effect-free units MUST use I0_NONE effect isolation")
            return
        if not self.effect_types:
            raise ValueError("effectful units MUST declare effect_types")
        if self.minimum_isolation.rank < IsolationGrade.I2_PROCESS_LOCAL.rank:
            raise ValueError("effectful units require at least process-local isolation")
        if self.classification in {
            SideEffectClass.REVERSIBLE,
            SideEffectClass.COMPENSATABLE,
        } and not self.compensation_action:
            raise ValueError("reversible or compensatable effects MUST declare compensation_action")
        if self.classification is SideEffectClass.IRREVERSIBLE:
            if self.compensation_action:
                raise ValueError("irreversible effects cannot declare compensation_action")
            if self.minimum_isolation.rank < IsolationGrade.I3_RECORDED_EXTERNALS.rank:
                raise ValueError("irreversible effects require recorded-external isolation")


@dataclass(frozen=True)
class PlacementContract:
    allowed_regions: frozenset[str] = frozenset()
    allowed_devices: frozenset[str] = frozenset()
    allowed_runtimes: frozenset[str] = frozenset()
    required_capabilities: frozenset[str] = frozenset()
    preferred_regions: tuple[str, ...] = ()
    preferred_devices: tuple[str, ...] = ()
    requires_local_inputs: bool = False

    def __post_init__(self) -> None:
        for name in (
            "allowed_regions",
            "allowed_devices",
            "allowed_runtimes",
            "required_capabilities",
        ):
            values = getattr(self, name)
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{name} MUST contain non-empty strings")
        for name in ("preferred_regions", "preferred_devices"):
            if any(
                not isinstance(value, str) or not value.strip()
                for value in getattr(self, name)
            ):
                raise ValueError(f"{name} MUST contain non-empty strings")
        if self.allowed_regions and not set(self.preferred_regions) <= self.allowed_regions:
            raise ValueError("preferred_regions MUST be allowed")
        if self.allowed_devices and not set(self.preferred_devices) <= self.allowed_devices:
            raise ValueError("preferred_devices MUST be allowed")
        if len(self.preferred_regions) != len(set(self.preferred_regions)):
            raise ValueError("preferred_regions MUST be unique")
        if len(self.preferred_devices) != len(set(self.preferred_devices)):
            raise ValueError("preferred_devices MUST be unique")
        if not isinstance(self.requires_local_inputs, bool):
            raise TypeError("requires_local_inputs MUST be boolean")


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"

    @property
    def rank(self) -> int:
        return list(type(self)).index(self)


@dataclass(frozen=True)
class SecurityContract:
    tenant_id: str | None = None
    required_permissions: frozenset[str] = frozenset()
    security_labels: frozenset[str] = frozenset()
    output_classification: DataClassification = DataClassification.INTERNAL
    maximum_input_classification: DataClassification = DataClassification.RESTRICTED
    allowed_residencies: frozenset[str] = frozenset()
    trust_zone: str = ""
    accepted_trust_zones: frozenset[str] = frozenset()
    confidential_compute_required: bool = False

    def __post_init__(self) -> None:
        if self.tenant_id is not None and (
            not isinstance(self.tenant_id, str) or not self.tenant_id.strip()
        ):
            raise ValueError("security tenant_id MUST be non-empty when provided")
        if not isinstance(self.output_classification, DataClassification):
            raise TypeError("output_classification MUST be DataClassification")
        if not isinstance(self.maximum_input_classification, DataClassification):
            raise TypeError("maximum_input_classification MUST be DataClassification")
        for name in (
            "required_permissions",
            "security_labels",
            "allowed_residencies",
            "accepted_trust_zones",
        ):
            if any(not isinstance(value, str) or not value.strip() for value in getattr(self, name)):
                raise ValueError(f"{name} MUST contain non-empty strings")
        if not isinstance(self.trust_zone, str):
            raise TypeError("trust_zone MUST be a string")
        if not isinstance(self.confidential_compute_required, bool):
            raise TypeError("confidential_compute_required MUST be boolean")


@dataclass(frozen=True)
class ExecutionContext:
    tenant_id: str
    permissions: frozenset[str]
    isolation_grade: IsolationGrade
    region: str = ""
    device: str = ""
    runtime: str = ""
    capabilities: frozenset[str] = frozenset()
    trust_zone: str = ""
    confidential_compute: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id:
            raise ValueError("execution tenant_id MUST be non-empty")
        if not isinstance(self.isolation_grade, IsolationGrade):
            raise TypeError("execution isolation_grade MUST be IsolationGrade")
        for name in ("permissions", "capabilities"):
            if any(not isinstance(value, str) or not value.strip() for value in getattr(self, name)):
                raise ValueError(f"execution {name} MUST contain non-empty strings")
        for name in ("region", "device", "runtime", "trust_zone"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"execution {name} MUST be a string")
        if not isinstance(self.confidential_compute, bool):
            raise TypeError("execution confidential_compute MUST be boolean")
