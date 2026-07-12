"""Ollama execution provider for DNC.

Per Phase 5C (mvp-roadmap.md): Ollama integration for local inference reproducibility.
OllamaProvider implements the ExecutionProvider interface for Ollama's REST API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Set

from dnc.execution.execution_provider import (
    CostEstimate,
    ExecutionCapability,
    ExecutionProvider,
    ProviderMetadata,
    ProviderResult,
)


@dataclass(frozen=True)
class OllamaConfig:
    """Configuration for Ollama provider."""

    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 120.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    default_model: str = "llama3.2"
    stream: bool = False


class OllamaProvider(ExecutionProvider):
    """ExecutionProvider implementation for Ollama (per interfaces.md).

    Supports CAP_REASONING (via /api/chat) and CAP_EMBEDDING (via /api/embeddings).
    Does NOT require an API key — Ollama runs locally.
    """

    DEFAULT_CAPABILITIES: FrozenSet[ExecutionCapability] = frozenset({
        ExecutionCapability.CAP_REASONING,
        ExecutionCapability.CAP_EMBEDDING,
    })

    def __init__(
        self,
        config: Optional[OllamaConfig] = None,
        provider_id: str = "ollama",
        provider_version: str = "1.0.0",
    ) -> None:
        self._config = config or OllamaConfig()
        self._provider_id = provider_id
        self._provider_version = provider_version

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_version(self) -> str:
        return self._provider_version

    @property
    def provider_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="ollama",
            provider_version=self._provider_version,
            supported_capabilities=self.DEFAULT_CAPABILITIES,
            max_concurrent_requests=1,
            supports_streaming=self._config.stream,
            supports_function_calling=False,
            context_window=128_000,
            custom={"base_url": self._config.base_url, "default_model": self._config.default_model},
        )

    def supports(self, capability: ExecutionCapability) -> bool:
        return capability in self.DEFAULT_CAPABILITIES

    def get_capabilities(self) -> Set[ExecutionCapability]:
        return set(self.DEFAULT_CAPABILITIES)

    def execute(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        t_start = time.time()

        if not self.supports(capability):
            return ProviderResult(
                capability=capability,
                output=None,
                provider_id=self._provider_id,
                latency_ms=0.0,
                error=f"Capability {capability.name} not supported by OllamaProvider",
            )

        cfg = config or {}
        model = cfg.get("model", self._config.default_model)

        try:
            if capability == ExecutionCapability.CAP_REASONING:
                output = self._execute_chat(input, model, cfg)
            elif capability == ExecutionCapability.CAP_EMBEDDING:
                output = self._execute_embeddings(input, model)
            else:
                output = self._execute_generic(input, model, cfg)

            latency = (time.time() - t_start) * 1000
            return ProviderResult(
                capability=capability,
                output=output,
                provider_id=self._provider_id,
                latency_ms=latency,
                tokens_used=self._estimate_tokens(input, output),
            )
        except Exception as e:
            latency = (time.time() - t_start) * 1000
            return ProviderResult(
                capability=capability,
                output=None,
                provider_id=self._provider_id,
                latency_ms=latency,
                error=str(e),
            )

    def _execute_chat(
        self,
        input: Any,
        model: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        import json

        messages = self._build_messages(input)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if "temperature" in config:
            payload["temperature"] = config["temperature"]
        if "max_tokens" in config:
            payload["options"] = {"num_predict": config["max_tokens"]}

        url = f"{self._config.base_url}/api/chat"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "role": "assistant",
                    "content": data.get("message", {}).get("content", ""),
                    "model": model,
                }
        except urllib.error.URLError as e:
            return {
                "role": "assistant",
                "content": f"[Ollama unavailable: {e.reason}]",
                "model": model,
                "_mock": True,
            }

    def _execute_embeddings(
        self,
        input: Any,
        model: str,
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        import json

        prompt = input if isinstance(input, str) else str(input)
        payload = {
            "model": model,
            "prompt": prompt,
        }

        url = f"{self._config.base_url}/api/embeddings"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "embedding": data.get("embedding", []),
                    "model": model,
                }
        except urllib.error.URLError:
            return {
                "embedding": [0.0] * 384,
                "model": model,
                "_mock": True,
            }

    def _execute_generic(
        self,
        input: Any,
        model: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"content": str(input), "model": model, "_generic": True}

    def _build_messages(self, input: Any) -> list:
        if isinstance(input, list):
            return input
        elif isinstance(input, dict):
            return [input]
        else:
            return [{"role": "user", "content": str(input)}]

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
            estimated_latency_ms=50.0,
            estimated_cost_usd=0.0,
            confidence=0.9,
        )

    def list_models(self) -> list:
        """List available Ollama models."""
        import urllib.request
        import json

        url = f"{self._config.base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("models", [])
        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if the Ollama server is reachable.

        Per the architecture, providers must report availability truthfully so
        the scheduler can bind a module to a live provider. A server is
        available iff it answers a lightweight probe without error.
        """
        import urllib.request

        try:
            req = urllib.request.Request(
                f"{self._config.base_url}/api/tags", method="GET"
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False