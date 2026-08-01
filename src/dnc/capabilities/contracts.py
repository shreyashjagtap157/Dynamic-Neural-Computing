"""Provider-neutral capability contracts for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dnc.cognition.contracts import CognitiveActionType, RiskClass


class CapabilityLifecycle(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class HealthStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class CapabilityFeature(str, Enum):
    STREAMING = "STREAMING"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    TOOL_CALLING = "TOOL_CALLING"
    CANCELLATION = "CANCELLATION"
    USAGE = "USAGE"
    DETERMINISTIC = "DETERMINISTIC"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    LOCAL = "LOCAL"


@dataclass(frozen=True)
class CapabilityCard:
    capability_id: str
    name: str
    provider_id: str
    provider_version: str
    model_id: str
    supported_actions: frozenset[CognitiveActionType]
    risk_limit: RiskClass
    features: frozenset[CapabilityFeature] = frozenset()
    permissions: frozenset[str] = frozenset()
    calibration_domains: frozenset[str] = frozenset()
    locality: str = "remote"
    competence: float = 0.0
    cost_per_call: float = 0.0
    latency_ms: int = 0
    max_tokens: int | None = None
    max_parallelism: int = 1
    lifecycle: CapabilityLifecycle = CapabilityLifecycle.ACTIVE
    health: HealthStatus = HealthStatus.UNKNOWN
    expires_at_ns: int | None = None
    fingerprint: str = ""
    failure_modes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("capability_id", "name", "provider_id", "provider_version", "model_id"):
            if not getattr(self, name):
                raise ValueError(f"{name} MUST be non-empty")
        if not self.supported_actions:
            raise ValueError("supported_actions MUST be non-empty")
        if not 0.0 <= self.competence <= 1.0:
            raise ValueError("competence MUST be between 0 and 1")
        if self.cost_per_call < 0 or self.latency_ms < 0:
            raise ValueError("cost and latency MUST be non-negative")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens MUST be positive")
        if self.max_parallelism <= 0:
            raise ValueError("max_parallelism MUST be positive")

    def is_expired(self, now_ns: int) -> bool:
        return self.expires_at_ns is not None and now_ns >= self.expires_at_ns


@dataclass(frozen=True)
class CapabilityRequirement:
    action_type: CognitiveActionType
    risk_class: RiskClass
    required_features: frozenset[CapabilityFeature] = frozenset()
    required_permissions: frozenset[str] = frozenset()
    locality: str | None = None
    domain: str | None = None
    minimum_competence: float = 0.0
    maximum_cost: float | None = None
    maximum_latency_ms: int | None = None
    token_budget: int | None = None


@dataclass(frozen=True)
class CapabilityRejection:
    capability_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CapabilitySelection:
    selected: CapabilityCard | None
    requirement: CapabilityRequirement
    satisfied: bool
    reason: str
    candidates: tuple[str, ...] = ()
    rejections: tuple[CapabilityRejection, ...] = ()


@dataclass(frozen=True)
class ProviderRequest:
    request_id: str
    action_type: CognitiveActionType
    input: Any
    model: str | None = None
    stream: bool = False
    response_schema: dict[str, Any] | None = None
    tools: tuple[dict[str, Any], ...] = ()
    timeout_ms: int | None = None
    max_retries: int = 0
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id MUST be non-empty")
        if self.timeout_ms is not None and self.timeout_ms < 0:
            raise ValueError("timeout_ms MUST be non-negative")
        if self.max_retries < 0:
            raise ValueError("max_retries MUST be non-negative")


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


@dataclass(frozen=True)
class ProviderResponse:
    request_id: str
    provider_id: str
    model_id: str
    output: Any
    success: bool
    complete: bool = True
    usage: Usage = field(default_factory=Usage)
    error_code: str | None = None
    error: str | None = None
    attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamEvent:
    request_id: str
    sequence: int
    kind: str
    data: Any = None
    terminal: bool = False


@dataclass(frozen=True)
class ModelChangeEvent:
    capability_id: str
    previous_fingerprint: str
    current_fingerprint: str
