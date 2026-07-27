"""Anthropic execution provider for DNC.

Per Phase 5E (mvp-roadmap.md): Anthropic integration for broad compatibility.
AnthropicProvider implements the ExecutionProvider interface for the Anthropic Messages API.
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
class AnthropicConfig:
    """Configuration for Anthropic provider."""

    api_key: str = ""
    base_url: str = "https://api.anthropic.com"
    timeout_seconds: float = 60.0
    max_retries: int = 3
    default_model: str = "claude-sonnet-4-20250514"


class AnthropicProvider(ExecutionProvider):
    """ExecutionProvider implementation for Anthropic Messages API.

    Supports CAP_REASONING (via /v1/messages). Anthropic's models excel at
    extended thinking and tool use.
    """

    DEFAULT_CAPABILITIES: FrozenSet[ExecutionCapability] = frozenset({
        ExecutionCapability.CAP_REASONING,
    })

    def __init__(
        self,
        config: Optional[AnthropicConfig] = None,
        provider_id: str = "anthropic",
        provider_version: str = "1.0.0",
    ) -> None:
        import os

        self._config = config or AnthropicConfig()
        if not self._config.api_key:
            self._config = AnthropicConfig(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
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
            provider_name="anthropic",
            provider_version=self._provider_version,
            supported_capabilities=self.DEFAULT_CAPABILITIES,
            max_concurrent_requests=5,
            supports_streaming=True,
            supports_function_calling=True,
            context_window=200_000,
            rate_limit_rpm=50,
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
                error=f"Capability {capability.name} not supported by AnthropicProvider",
            )

        cfg = config or {}
        model = cfg.get("model", self._config.default_model)

        try:
            if capability == ExecutionCapability.CAP_REASONING:
                output = self._execute_messages(input, model, cfg)
            else:
                output = {"content": str(input), "model": model}

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

    def _execute_messages(
        self,
        input: Any,
        model: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        import urllib.request
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
        if config.get("thinking"):
            payload["thinking"] = config["thinking"]

        url = f"{self._config.base_url}/v1/messages"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._config.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "content": data.get("content", [{}])[0].get("text", ""),
                "model": model,
                "usage": {
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                "stop_reason": data.get("stop_reason"),
            }

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
        model = self._config.default_model
        price_per_mtok = 3.0 if "claude-opus" in model else 1.5 if "claude-sonnet" in model else 0.8
        cost = (tokens / 1_000_000) * price_per_mtok
        return CostEstimate(
            capability=capability,
            estimated_tokens=tokens,
            estimated_latency_ms=1000.0,
            estimated_cost_usd=cost,
            confidence=0.95,
        )