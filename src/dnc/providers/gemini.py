"""Google Gemini execution provider for DNC.

Per Phase 5E (mvp-roadmap.md): Gemini integration for broad compatibility.
GeminiProvider implements the ExecutionProvider interface for the Google AI Gemini API.
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
class GeminiConfig:
    """Configuration for Gemini provider."""

    api_key: str = ""
    base_url: str = "https://generativelanguage.googleapis.com"
    timeout_seconds: float = 60.0
    max_retries: int = 3
    default_model: str = "gemini-2.0-flash"


class GeminiProvider(ExecutionProvider):
    """ExecutionProvider implementation for Google Gemini API.

    Supports CAP_REASONING (via /v1beta/models/{model}:generateContent).
    Gemini's long context window and multimodal capabilities are well-suited
    for complex DNC execution graphs.
    """

    DEFAULT_CAPABILITIES: FrozenSet[ExecutionCapability] = frozenset({
        ExecutionCapability.CAP_REASONING,
    })

    def __init__(
        self,
        config: Optional[GeminiConfig] = None,
        provider_id: str = "gemini",
        provider_version: str = "1.0.0",
    ) -> None:
        import os

        self._config = config or GeminiConfig()
        if not self._config.api_key:
            self._config = GeminiConfig(api_key=os.environ.get("GOOGLE_API_KEY", ""))
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
            provider_name="gemini",
            provider_version=self._provider_version,
            supported_capabilities=self.DEFAULT_CAPABILITIES,
            max_concurrent_requests=10,
            supports_streaming=True,
            supports_function_calling=True,
            context_window=1_000_000,
            rate_limit_rpm=60,
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
                error=f"Capability {capability.name} not supported by GeminiProvider",
            )

        cfg = config or {}
        model = cfg.get("model", self._config.default_model)

        try:
            output = self._execute_generate_content(input, model, cfg)
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

    def _execute_generate_content(
        self,
        input: Any,
        model: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        import urllib.request
        import json

        contents = self._build_contents(input)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {},
        }
        if "temperature" in config:
            payload["generationConfig"]["temperature"] = config["temperature"]
        if "max_tokens" in config:
            payload["generationConfig"]["maxOutputTokens"] = config["max_tokens"]
        if "top_p" in config:
            payload["generationConfig"]["topP"] = config["top_p"]

        url = (
            f"{self._config.base_url}/v1beta/models/{model}:generateContent"
            f"?key={self._config.api_key}"
        )
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    content = "".join(p.get("text", "") for p in parts)

            return {
                "content": content,
                "model": model,
                "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
            }

    def _build_contents(self, input: Any) -> list:
        if isinstance(input, list):
            return [{"role": p.get("role", "user"), "parts": [{"text": p.get("content", "")}]}
                    for p in input]
        elif isinstance(input, dict):
            return [{"role": input.get("role", "user"), "parts": [{"text": input.get("content", "")}]}]
        else:
            return [{"role": "user", "parts": [{"text": str(input)}]}]

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
        model = self._config.default_model
        price_per_mtok = 0.1 if "gemini-2.0" in model else 0.5
        cost = (tokens / 1_000_000) * price_per_mtok
        return CostEstimate(
            capability=capability,
            estimated_tokens=tokens,
            estimated_latency_ms=500.0,
            estimated_cost_usd=cost,
            confidence=0.95,
        )