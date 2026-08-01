"""Capability-card factories for legacy execution providers."""

from __future__ import annotations

import hashlib
import json

from dnc.capabilities.contracts import CapabilityCard, CapabilityFeature, HealthStatus
from dnc.cognition.contracts import CognitiveActionType, RiskClass
from dnc.execution.execution_provider import ExecutionCapability, ExecutionProvider


def provider_capability_card(
    provider: ExecutionProvider,
    *,
    model_id: str | None = None,
    locality: str = "remote",
    competence: float = 0.5,
) -> CapabilityCard:
    metadata = provider.provider_metadata
    model = model_id or str(metadata.custom.get("default_model", "unspecified"))
    features = {CapabilityFeature.USAGE, CapabilityFeature.CANCELLATION}
    if metadata.supports_streaming:
        features.add(CapabilityFeature.STREAMING)
    if metadata.supports_function_calling:
        features.update({CapabilityFeature.TOOL_CALLING, CapabilityFeature.STRUCTURED_OUTPUT})
    if locality == "local":
        features.add(CapabilityFeature.LOCAL)
    actions = frozenset(
        action for capability, action in _CAPABILITY_ACTIONS.items()
        if capability in provider.get_capabilities()
    )
    fingerprint_data = {
        "provider_id": provider.provider_id,
        "provider_version": provider.provider_version,
        "model": model,
        "capabilities": sorted(item.name for item in provider.get_capabilities()),
        "features": sorted(item.value for item in features),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CapabilityCard(
        capability_id=f"provider.{provider.provider_id}",
        name=f"{metadata.provider_name} / {model}",
        provider_id=provider.provider_id,
        provider_version=provider.provider_version,
        model_id=model,
        supported_actions=actions,
        risk_limit=RiskClass.HIGH,
        features=frozenset(features),
        locality=locality,
        competence=competence,
        max_tokens=metadata.context_window,
        max_parallelism=metadata.max_concurrent_requests,
        health=HealthStatus.HEALTHY,
        fingerprint=fingerprint,
        metadata={
            "rate_limit_rpm": metadata.rate_limit_rpm,
            "streaming_mode": "buffered" if metadata.supports_streaming else "unsupported",
        },
    )


_CAPABILITY_ACTIONS = {
    ExecutionCapability.CAP_REASONING: CognitiveActionType.REASON,
    ExecutionCapability.CAP_RETRIEVAL: CognitiveActionType.RETRIEVE,
    ExecutionCapability.CAP_PLANNING: CognitiveActionType.RESTRUCTURE,
    ExecutionCapability.CAP_VERIFICATION: CognitiveActionType.VERIFY,
    ExecutionCapability.CAP_SIMULATION: CognitiveActionType.OBSERVE_OR_TEST,
    ExecutionCapability.CAP_EXECUTION: CognitiveActionType.OBSERVE_OR_TEST,
}
