"""Deterministic, human, and optional-backend capability implementations."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import platform
from dataclasses import dataclass
from typing import Any, Callable

from dnc.capabilities.contracts import (
    CapabilityCard,
    CapabilityFeature,
    HealthStatus,
    ProviderRequest,
    ProviderResponse,
)
from dnc.cognition.contracts import CognitiveActionType, RiskClass


@dataclass
class DeterministicCapability:
    card: CapabilityCard
    operation: Callable[[Any], Any]

    def execute(self, request: ProviderRequest, **_: Any) -> ProviderResponse:
        if request.action_type not in self.card.supported_actions:
            return ProviderResponse(
                request.request_id, self.card.provider_id, self.card.model_id, None, False,
                error_code="UNSUPPORTED_ACTION", error="action unsupported",
            )
        try:
            output = self.operation(request.input)
        except Exception as exc:
            return ProviderResponse(
                request.request_id, self.card.provider_id, self.card.model_id, None, False,
                error_code="EXECUTION_ERROR", error=str(exc),
            )
        return ProviderResponse(
            request.request_id, self.card.provider_id, self.card.model_id, output, True
        )


@dataclass
class HumanCapability:
    card: CapabilityCard
    handler: Callable[[ProviderRequest], Any]
    role: str
    authority_scope: frozenset[str]

    def execute(self, request: ProviderRequest, **_: Any) -> ProviderResponse:
        if request.action_type not in {CognitiveActionType.ASK, CognitiveActionType.ESCALATE}:
            return ProviderResponse(
                request.request_id, self.card.provider_id, self.card.model_id, None, False,
                error_code="UNSUPPORTED_ACTION", error="human capability only clarifies or approves",
            )
        required = frozenset(request.metadata.get("required_authority", ()))
        if not required.issubset(self.authority_scope):
            return ProviderResponse(
                request.request_id, self.card.provider_id, self.card.model_id, None, False,
                error_code="AUTHORITY_DENIED", error="human authority scope is insufficient",
            )
        try:
            output = self.handler(request)
        except Exception as exc:
            return ProviderResponse(
                request.request_id, self.card.provider_id, self.card.model_id, None, False,
                error_code="HUMAN_UNAVAILABLE", error=str(exc), metadata={"role": self.role},
            )
        return ProviderResponse(
            request.request_id, self.card.provider_id, self.card.model_id,
            output, True, metadata={"role": self.role},
        )


def deterministic_card(
    capability_id: str,
    action: CognitiveActionType,
    *,
    name: str = "Deterministic capability",
) -> CapabilityCard:
    return CapabilityCard(
        capability_id=capability_id,
        name=name,
        provider_id="dnc.reference",
        provider_version="1",
        model_id="deterministic-v1",
        supported_actions=frozenset({action}),
        risk_limit=RiskClass.CRITICAL,
        features=frozenset({CapabilityFeature.DETERMINISTIC, CapabilityFeature.LOCAL}),
        locality="local",
        competence=1.0,
        health=HealthStatus.HEALTHY,
        fingerprint=_fingerprint({"id": capability_id, "action": action.value, "version": 1}),
    )


def human_card(capability_id: str = "human.approval") -> CapabilityCard:
    return CapabilityCard(
        capability_id=capability_id,
        name="Human clarification and approval",
        provider_id="human",
        provider_version="1",
        model_id="human-authority",
        supported_actions=frozenset({CognitiveActionType.ASK, CognitiveActionType.ESCALATE}),
        risk_limit=RiskClass.CRITICAL,
        features=frozenset({CapabilityFeature.HUMAN_APPROVAL}),
        competence=1.0,
        health=HealthStatus.HEALTHY,
        fingerprint=_fingerprint({"id": capability_id, "version": 1}),
    )


def pytorch_capability_card() -> CapabilityCard:
    available = importlib.util.find_spec("torch") is not None
    version = importlib.metadata.version("torch") if available else "unavailable"
    details = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": version,
    }
    return CapabilityCard(
        capability_id="backend.pytorch",
        name="PyTorch backend",
        provider_id="pytorch",
        provider_version=version,
        model_id="local-module",
        supported_actions=frozenset({CognitiveActionType.OBSERVE_OR_TEST}),
        risk_limit=RiskClass.HIGH,
        features=frozenset({CapabilityFeature.LOCAL}),
        locality="local",
        competence=0.8 if available else 0.0,
        health=HealthStatus.HEALTHY if available else HealthStatus.UNHEALTHY,
        fingerprint=_fingerprint(details),
        metadata=details,
    )


def optional_backend_card(package: str, *, backend: str) -> CapabilityCard:
    available = importlib.util.find_spec(package) is not None
    version = importlib.metadata.version(package) if available else "unavailable"
    return CapabilityCard(
        capability_id=f"backend.{backend}",
        name=f"{backend.upper()} prototype backend",
        provider_id=backend,
        provider_version=version,
        model_id="prototype",
        supported_actions=frozenset({CognitiveActionType.OBSERVE_OR_TEST}),
        risk_limit=RiskClass.LOW,
        features=frozenset({CapabilityFeature.LOCAL}),
        locality="separate-environment",
        competence=0.1 if available else 0.0,
        health=HealthStatus.DEGRADED if available else HealthStatus.UNHEALTHY,
        fingerprint=_fingerprint({"backend": backend, "version": version}),
        metadata={"prototype_only": True, "package": package},
    )


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
