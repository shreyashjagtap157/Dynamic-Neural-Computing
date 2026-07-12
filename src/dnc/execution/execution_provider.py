"""ExecutionProvider: abstraction for LLM and computational backends.

Per interfaces.md: ExecutionProvider is the interface to external computational
resources. Providers are swappable — OpenAI, Anthropic, Ollama, vLLM, or any
conformant implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, Optional, Set


class ExecutionCapability(Enum):
    """Per interfaces.md Section 2.B: capability registry for execution providers."""

    CAP_REASONING = auto()
    CAP_RETRIEVAL = auto()
    CAP_PLANNING = auto()
    CAP_VERIFICATION = auto()
    CAP_SIMULATION = auto()
    CAP_OPTIMIZATION = auto()
    CAP_EXECUTION = auto()
    CAP_EMBEDDING = auto()
    CAP_TRANSCRIPTION = auto()
    CAP_TRANSLATION = auto()


@dataclass(frozen=True)
class ProviderMetadata:
    """Per interfaces.md: metadata describing provider capabilities and limits."""

    provider_name: str
    provider_version: str
    supported_capabilities: FrozenSet[ExecutionCapability]
    max_concurrent_requests: int = 1
    rate_limit_rpm: Optional[int] = None
    supports_streaming: bool = False
    supports_function_calling: bool = False
    context_window: Optional[int] = None
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CostEstimate:
    """Per interfaces.md: estimated cost of executing a capability."""

    capability: ExecutionCapability
    estimated_tokens: Optional[int] = None
    estimated_latency_ms: float = 0.0
    estimated_cost_usd: Optional[float] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ProviderResult:
    """Result of executing a capability through an ExecutionProvider."""

    capability: ExecutionCapability
    output: Any
    provider_id: str
    latency_ms: float
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.error is None


class ExecutionProvider(ABC):
    """Abstract execution provider interface (per interfaces.md Section 3.A)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider instance."""

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Version string of the provider implementation."""

    @property
    @abstractmethod
    def provider_metadata(self) -> ProviderMetadata:
        """Metadata describing provider capabilities and limits."""

    @abstractmethod
    def supports(self, capability: ExecutionCapability) -> bool:
        """Return True if this provider implements the given capability."""

    @abstractmethod
    def execute(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        """Execute the given capability with the provided input."""

    @abstractmethod
    def estimate_cost(
        self,
        capability: ExecutionCapability,
        input: Any,
    ) -> CostEstimate:
        """Estimate the cost (tokens, time, money) of executing the given input."""

    @abstractmethod
    def get_capabilities(self) -> Set[ExecutionCapability]:
        """Return the set of all capabilities this provider supports."""


class ReferenceExecutionProvider(ExecutionProvider):
    """Reference implementation of ExecutionProvider.

    A minimal conformant provider that implements all capabilities in-memory.
    Used for testing and as a base for other implementations.
    """

    def __init__(
        self,
        provider_id: str = "reference",
        provider_version: str = "1.0.0",
        capabilities: Optional[Set[ExecutionCapability]] = None,
    ) -> None:
        self._provider_id = provider_id
        self._provider_version = provider_version
        self._capabilities = capabilities or {ExecutionCapability.CAP_REASONING}

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_version(self) -> str:
        return self._provider_version

    @property
    def provider_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self._provider_id,
            provider_version=self._provider_version,
            supported_capabilities=frozenset(self._capabilities),
            max_concurrent_requests=1,
        )

    def supports(self, capability: ExecutionCapability) -> bool:
        return capability in self._capabilities

    def execute(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        import time
        t_start = time.time()

        if not self.supports(capability):
            return ProviderResult(
                capability=capability,
                output=None,
                provider_id=self._provider_id,
                latency_ms=0.0,
                error=f"Capability {capability.name} not supported",
            )

        output = self._execute_reference(capability, input, config)
        latency = (time.time() - t_start) * 1000

        return ProviderResult(
            capability=capability,
            output=output,
            provider_id=self._provider_id,
            latency_ms=latency,
            tokens_used=self._estimate_tokens(input, output),
        )

    def _execute_reference(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: Optional[Dict[str, Any]],
    ) -> Any:
        if isinstance(input, str):
            return f"[Reference:{capability.name}] {input}"
        return {"reference_output": True, "capability": capability.name, "input": input}

    def _estimate_tokens(self, input: Any, output: Any) -> int:
        input_str = str(input)
        output_str = str(output)
        return len(input_str) // 4 + len(output_str) // 4

    def estimate_cost(
        self,
        capability: ExecutionCapability,
        input: Any,
    ) -> CostEstimate:
        tokens = self._estimate_tokens(input, "")
        return CostEstimate(
            capability=capability,
            estimated_tokens=tokens,
            estimated_latency_ms=10.0,
            estimated_cost_usd=None,
            confidence=1.0,
        )

    def get_capabilities(self) -> Set[ExecutionCapability]:
        return set(self._capabilities)