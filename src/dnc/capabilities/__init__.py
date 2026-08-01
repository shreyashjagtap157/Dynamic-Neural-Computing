"""Phase 4 capability registry, broker, adapters, and built-ins."""

from dnc.capabilities.adapters import (
    CircuitBreaker, NeutralAdapter, OllamaAdapter, OpenAIAdapter, ProviderAdapter, RateLimiter,
    VLLMAdapter,
)
from dnc.capabilities.broker import CapabilityBroker
from dnc.capabilities.builtins import (
    DeterministicCapability, HumanCapability, deterministic_card, human_card,
    optional_backend_card, pytorch_capability_card,
)
from dnc.capabilities.cards import provider_capability_card
from dnc.capabilities.contracts import (
    CapabilityCard, CapabilityFeature, CapabilityLifecycle, CapabilityRejection,
    CapabilityRequirement, CapabilitySelection, HealthStatus, ModelChangeEvent,
    ProviderRequest, ProviderResponse, StreamEvent, Usage,
)
from dnc.capabilities.registry import CapabilityRegistry

__all__ = [
    "CapabilityBroker", "CapabilityCard", "CapabilityFeature", "CapabilityLifecycle",
    "CapabilityRegistry", "CapabilityRejection", "CapabilityRequirement",
    "CapabilitySelection", "CircuitBreaker", "DeterministicCapability", "HealthStatus",
    "HumanCapability", "ModelChangeEvent", "NeutralAdapter", "OllamaAdapter",
    "OpenAIAdapter", "ProviderAdapter", "ProviderRequest", "ProviderResponse", "RateLimiter", "StreamEvent",
    "Usage", "VLLMAdapter", "deterministic_card", "human_card", "optional_backend_card",
    "provider_capability_card", "pytorch_capability_card",
]
