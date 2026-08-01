"""vLLM execution provider for DNC.

Per Phase 5C (mvp-roadmap.md): vLLM integration for local inference reproducibility.
vLLMProvider implements the ExecutionProvider interface for vLLM's OpenAI-compatible API.
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
class vLLMConfig:
    """Configuration for vLLM provider."""

    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 120.0
    max_retries: int = 3
    default_model: str = "meta-llama/Llama-3.2-3B-Instruct"
    api_key: Optional[str] = None


class vLLMProvider(ExecutionProvider):
    """ExecutionProvider implementation for vLLM (per interfaces.md).

    vLLM provides an OpenAI-compatible API. Supports CAP_REASONING (via /v1/chat/completions)
    and CAP_EMBEDDING (via /v1/embeddings).
    """

    DEFAULT_CAPABILITIES: FrozenSet[ExecutionCapability] = frozenset({
        ExecutionCapability.CAP_REASONING,
        ExecutionCapability.CAP_EMBEDDING,
    })

    def __init__(
        self,
        config: Optional[vLLMConfig] = None,
        provider_id: str = "vllm",
        provider_version: str = "1.0.0",
    ) -> None:
        self._config = config or vLLMConfig()
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
            provider_name="vllm",
            provider_version=self._provider_version,
            supported_capabilities=self.DEFAULT_CAPABILITIES,
            max_concurrent_requests=4,
            supports_streaming=True,
            supports_function_calling=True,
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
                error=f"Capability {capability.name} not supported by vLLMProvider",
            )

        cfg = config or {}
        model = cfg.get("model", self._config.default_model)

        try:
            if capability == ExecutionCapability.CAP_REASONING:
                output = self._execute_chat_completions(input, model, cfg)
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

    def _execute_chat_completions(
        self,
        input: Any,
        model: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        import json

        messages = self._build_messages(input)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if "temperature" in config:
            payload["temperature"] = config["temperature"]
        if "max_tokens" in config:
            payload["max_tokens"] = config["max_tokens"]
        if "top_p" in config:
            payload["top_p"] = config["top_p"]
        if "guided_decoding" in config:
            payload["guided_decoding"] = config["guided_decoding"]
        if "response_format" in config:
            payload["response_format"] = config["response_format"]
        if "tools" in config:
            payload["tools"] = config["tools"]
        if "tool_choice" in config:
            payload["tool_choice"] = config["tool_choice"]

        url = f"{self._config.base_url}/v1/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key or 'dummy'}",
        }
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return {
                        "content": choices[0].get("message", {}).get("content", ""),
                        "model": data.get("model", model),
                        "usage": data.get("usage", {}),
                    }
                return {"content": "", "model": model}
        except urllib.error.URLError as e:
            return {
                "content": f"[vLLM unavailable: {e.reason}]",
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

        texts = [input] if isinstance(input, str) else (input if isinstance(input, list) else [str(input)])
        payload = {"model": model, "input": texts}

        url = f"{self._config.base_url}/v1/embeddings"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key or 'dummy'}",
        }
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = data.get("data", [])
                if embeddings:
                    return {
                        "embedding": embeddings[0].get("embedding", []),
                        "model": model,
                    }
                return {"embedding": [], "model": model}
        except urllib.error.URLError:
            return {"embedding": [0.0] * 768, "model": model, "_mock": True}

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
            estimated_latency_ms=30.0,
            estimated_cost_usd=0.0,
            confidence=0.9,
        )

    def is_available(self) -> bool:
        """Check if vLLM server is reachable via health endpoint."""
        import urllib.request
        import json

        url = f"{self._config.base_url}/v1/models"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return len(data.get("data", [])) > 0
        except Exception:
            return False
