"""OpenAI execution provider for DNC.

Per Phase 5E (mvp-roadmap.md): OpenAI integration for broad compatibility.
OpenAIProvider implements the ExecutionProvider interface for the OpenAI API.
"""

from __future__ import annotations

import time
import urllib.request
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
class OpenAIConfig:
    """Configuration for OpenAI provider."""

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 60.0
    max_retries: int = 3
    default_model: str = "gpt-4o"
    organization: Optional[str] = None


class OpenAIProvider(ExecutionProvider):
    """ExecutionProvider implementation for OpenAI API.

    Supports CAP_REASONING (via /v1/chat/completions) and CAP_EMBEDDING (via /v1/embeddings).
    Requires an API key. Set OPENAI_API_KEY environment variable or pass directly.
    """

    DEFAULT_CAPABILITIES: FrozenSet[ExecutionCapability] = frozenset({
        ExecutionCapability.CAP_REASONING,
        ExecutionCapability.CAP_EMBEDDING,
    })

    def __init__(
        self,
        config: Optional[OpenAIConfig] = None,
        provider_id: str = "openai",
        provider_version: str = "1.0.0",
    ) -> None:
        import os

        self._config = config or OpenAIConfig()
        if not self._config.api_key:
            self._config = OpenAIConfig(api_key=os.environ.get("OPENAI_API_KEY", ""))
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
            provider_name="openai",
            provider_version=self._provider_version,
            supported_capabilities=self.DEFAULT_CAPABILITIES,
            max_concurrent_requests=10,
            supports_streaming=True,
            supports_function_calling=True,
            context_window=128_000,
            rate_limit_rpm=500,
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
                error=f"Capability {capability.name} not supported by OpenAIProvider",
            )

        cfg = config or {}
        model = cfg.get("model", self._config.default_model)

        try:
            if capability == ExecutionCapability.CAP_REASONING:
                output = self._execute_chat(input, model, cfg)
            elif capability == ExecutionCapability.CAP_EMBEDDING:
                output = self._execute_embeddings(input, model)
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
        if "response_format" in config:
            payload["response_format"] = config["response_format"]

        url = f"{self._config.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }
        if self._config.organization:
            headers["OpenAI-Organization"] = self._config.organization

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        self._add_retry_logic(req)

        with self._urlopen_with_retry(req, self._config.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            content = ""
            if choices:
                content = choices[0].get("message", {}).get("content", "")
            return {
                "content": content,
                "model": data.get("model", model),
                "usage": data.get("usage", {}),
            }

    def _execute_embeddings(
        self,
        input: Any,
        model: str,
    ) -> Dict[str, Any]:
        import urllib.request
        import json

        text = input if isinstance(input, str) else str(input)
        payload = {"model": model, "input": text}

        url = f"{self._config.base_url}/embeddings"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with self._urlopen_with_retry(req, self._config.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            embeddings = data.get("data", [])
            if embeddings:
                return {
                    "embedding": embeddings[0].get("embedding", []),
                    "model": model,
                }
            return {"embedding": [], "model": model}

    def _build_messages(self, input: Any) -> list:
        if isinstance(input, list):
            return input
        elif isinstance(input, dict):
            return [input]
        else:
            return [{"role": "user", "content": str(input)}]

    def _add_retry_logic(
        self, req: urllib.request.Request, attempts: Optional[int] = None
    ) -> None:
        """Attach retry metadata to the request.

        The number of attempts is honored by `_urlopen_with_retry`, which
        retries on transient failures (timeouts, connection errors, and 5xx
        responses) with exponential backoff.
        """
        req._retry_attempts = (  # type: ignore[attr-defined]
            attempts if attempts is not None else self._config.max_retries
        )

    def _urlopen_with_retry(
        self, req: urllib.request.Request, timeout: float
    ) -> Any:
        """Open `req` with bounded exponential-backoff retries on transient errors.

        Per the design intent of `_add_retry_logic`: transient failures
        (socket/timeout errors and HTTP 5xx) are retried; permanent failures
        (4xx) are raised immediately.
        """
        import time
        import urllib.error

        attempts = max(1, getattr(req, "_retry_attempts", self._config.max_retries))
        last_err: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as e:
                if e.code >= 500 and attempt < attempts - 1:
                    last_err = e
                    time.sleep(min(2**attempt * 0.1, 1.0))
                    continue
                raise
            except Exception as e:  # transient: timeout / connection reset / etc.
                if attempt < attempts - 1:
                    last_err = e
                    time.sleep(min(2**attempt * 0.1, 1.0))
                    continue
                raise
        if last_err is not None:
            raise last_err
        raise RuntimeError("retry loop completed without a result")

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
        price_per_mtok = 2.5 if "gpt-4" in model else 0.5
        cost = (tokens / 1_000_000) * price_per_mtok
        return CostEstimate(
            capability=capability,
            estimated_tokens=tokens,
            estimated_latency_ms=500.0,
            estimated_cost_usd=cost,
            confidence=0.95,
        )