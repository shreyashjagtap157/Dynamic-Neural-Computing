"""Provider-neutral adapters and resilience controls."""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol

from dnc.capabilities.contracts import (
    CapabilityCard,
    CapabilityFeature,
    ProviderRequest,
    ProviderResponse,
    StreamEvent,
    Usage,
)
from dnc.cognition.contracts import CognitiveActionType
from dnc.execution.execution_provider import ExecutionCapability, ExecutionProvider
from dnc.execution.snapshot import CancellationToken


class NeutralAdapter(Protocol):
    @property
    def card(self) -> CapabilityCard: ...

    def execute(
        self, request: ProviderRequest, *, cancellation: CancellationToken | None = None
    ) -> ProviderResponse: ...

    def stream(
        self, request: ProviderRequest, *, cancellation: CancellationToken | None = None
    ) -> Iterator[StreamEvent]: ...


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout_ms: int = 30_000
    consecutive_failures: int = 0
    opened_at_ns: int | None = None

    def allow(self, now_ns: int | None = None) -> bool:
        current = time.monotonic_ns() if now_ns is None else now_ns
        if self.opened_at_ns is None:
            return True
        if current - self.opened_at_ns >= self.recovery_timeout_ms * 1_000_000:
            self.consecutive_failures = 0
            self.opened_at_ns = None
            return True
        return False

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.opened_at_ns = None

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at_ns = time.monotonic_ns()


@dataclass
class RateLimiter:
    requests_per_minute: int
    _window_started_ns: int = field(default_factory=time.monotonic_ns)
    _requests: int = 0

    def acquire(self, now_ns: int | None = None) -> bool:
        if self.requests_per_minute <= 0:
            return False
        current = time.monotonic_ns() if now_ns is None else now_ns
        if current - self._window_started_ns >= 60_000_000_000:
            self._window_started_ns = current
            self._requests = 0
        if self._requests >= self.requests_per_minute:
            return False
        self._requests += 1
        return True


@dataclass
class ProviderAdapter:
    provider: ExecutionProvider
    card: CapabilityCard
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    rate_limiter: RateLimiter | None = None

    def execute(
        self,
        request: ProviderRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> ProviderResponse:
        feature_error = self._feature_error(request)
        if feature_error:
            return self._error(request, "UNSUPPORTED_FEATURE", feature_error, attempts=0)
        if cancellation is not None and cancellation.is_cancelled():
            return self._error(request, "CANCELLED", cancellation.reason or "cancelled", attempts=0)
        if not self.breaker.allow():
            return self._error(request, "CIRCUIT_OPEN", "provider circuit is open", attempts=0)
        if self.rate_limiter is not None and not self.rate_limiter.acquire():
            return self._error(request, "RATE_LIMITED", "adapter rate limit exceeded", attempts=0)

        capability = _execution_capability(request.action_type)
        if capability is None or not self.provider.supports(capability):
            return self._error(request, "UNSUPPORTED_ACTION", "provider does not support action", attempts=0)
        config = dict(request.metadata)
        if request.model:
            config["model"] = request.model
        if request.response_schema is not None:
            config["response_format"] = request.response_schema
        if request.tools:
            config["tools"] = list(request.tools)

        attempts = 0
        last_error = "provider execution failed"
        while attempts <= request.max_retries:
            attempts += 1
            if cancellation is not None and cancellation.is_cancelled():
                return self._error(request, "CANCELLED", cancellation.reason or "cancelled", attempts)
            try:
                result, timed_out = self._execute_with_timeout(
                    capability, request.input, config, request.timeout_ms
                )
            except Exception as exc:
                last_error = str(exc)
                self.breaker.record_failure()
                continue
            if timed_out:
                last_error = "provider deadline exceeded"
                self.breaker.record_failure()
                break
            assert result is not None
            if cancellation is not None and cancellation.is_cancelled():
                return self._error(
                    request, "CANCELLED", cancellation.reason or "cancelled", attempts
                )
            if result.is_success:
                schema_error = _validate_structured_output(result.output, request.response_schema)
                if schema_error:
                    self.breaker.record_failure()
                    return self._error(request, "INVALID_STRUCTURED_OUTPUT", schema_error, attempts)
                self.breaker.record_success()
                return ProviderResponse(
                    request_id=request.request_id,
                    provider_id=self.card.provider_id,
                    model_id=request.model or self.card.model_id,
                    output=result.output,
                    success=True,
                    usage=_usage(request.input, result.output, result.tokens_used, result.cost_usd),
                    attempts=attempts,
                    metadata={**result.metadata, "latency_ms": result.latency_ms},
                )
            last_error = result.error or last_error
            self.breaker.record_failure()
        return self._error(
            request,
            "TIMEOUT" if "deadline" in last_error else "PROVIDER_ERROR",
            last_error,
            attempts,
        )

    def _execute_with_timeout(
        self,
        capability: ExecutionCapability,
        input_value: Any,
        config: dict[str, Any],
        timeout_ms: int | None,
    ) -> tuple[Any | None, bool]:
        if timeout_ms is None:
            return self.provider.execute(capability, input_value, config), False
        results: queue.Queue[Any] = queue.Queue(maxsize=1)

        def invoke() -> None:
            try:
                results.put(self.provider.execute(capability, input_value, config))
            except BaseException as exc:
                results.put(exc)

        worker = threading.Thread(target=invoke, daemon=True, name="dnc-provider-call")
        worker.start()
        try:
            result = results.get(timeout=timeout_ms / 1000)
        except queue.Empty:
            return None, True
        if isinstance(result, BaseException):
            raise result
        return result, False

    def stream(
        self,
        request: ProviderRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> Iterator[StreamEvent]:
        if CapabilityFeature.STREAMING not in self.card.features:
            yield StreamEvent(request.request_id, 0, "error", "streaming unsupported", True)
            return
        yield StreamEvent(request.request_id, 0, "start")
        response = self.execute(request, cancellation=cancellation)
        if not response.success:
            yield StreamEvent(
                request.request_id, 1, "cancelled" if response.error_code == "CANCELLED" else "error",
                {"code": response.error_code, "message": response.error}, True,
            )
            return
        yield StreamEvent(request.request_id, 1, "delta", response.output)
        yield StreamEvent(request.request_id, 2, "complete", response.usage, True)

    def _feature_error(self, request: ProviderRequest) -> str | None:
        requirements = []
        if request.stream:
            requirements.append((CapabilityFeature.STREAMING, "streaming"))
        if request.response_schema is not None:
            requirements.append((CapabilityFeature.STRUCTURED_OUTPUT, "structured output"))
        if request.tools:
            requirements.append((CapabilityFeature.TOOL_CALLING, "tool calling"))
        for feature, label in requirements:
            if feature not in self.card.features:
                return f"{label} is unsupported by {self.card.capability_id}"
        return None

    def _error(
        self, request: ProviderRequest, code: str, message: str, attempts: int
    ) -> ProviderResponse:
        return ProviderResponse(
            request.request_id, self.card.provider_id, request.model or self.card.model_id,
            None, False, error_code=code, error=message, attempts=attempts,
        )


class OpenAIAdapter(ProviderAdapter):
    def __init__(self, card: CapabilityCard, config: Any = None) -> None:
        from dnc.providers.openai import OpenAIProvider

        super().__init__(OpenAIProvider(config=config), card)


class OllamaAdapter(ProviderAdapter):
    def __init__(self, card: CapabilityCard, config: Any = None) -> None:
        from dnc.providers.ollama import OllamaProvider

        super().__init__(OllamaProvider(config=config), card)


class VLLMAdapter(ProviderAdapter):
    def __init__(self, card: CapabilityCard, config: Any = None) -> None:
        from dnc.providers.vllm import vLLMProvider

        super().__init__(vLLMProvider(config=config), card)


def _execution_capability(action: CognitiveActionType) -> ExecutionCapability | None:
    return {
        CognitiveActionType.REASON: ExecutionCapability.CAP_REASONING,
        CognitiveActionType.CONTINUE: ExecutionCapability.CAP_REASONING,
        CognitiveActionType.BRANCH: ExecutionCapability.CAP_REASONING,
        CognitiveActionType.RETRIEVE: ExecutionCapability.CAP_RETRIEVAL,
        CognitiveActionType.VERIFY: ExecutionCapability.CAP_VERIFICATION,
        CognitiveActionType.OBSERVE_OR_TEST: ExecutionCapability.CAP_SIMULATION,
        CognitiveActionType.REPAIR: ExecutionCapability.CAP_REASONING,
        CognitiveActionType.RESTRUCTURE: ExecutionCapability.CAP_PLANNING,
    }.get(action)


def _validate_structured_output(output: Any, schema: dict[str, Any] | None) -> str | None:
    if schema is None:
        return None
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return "output is not valid JSON"
    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(output, dict):
        return "output is not an object"
    if expected_type == "array" and not isinstance(output, list):
        return "output is not an array"
    if isinstance(output, dict):
        missing = set(schema.get("required", ())) - set(output)
        if missing:
            return f"required fields are missing: {sorted(missing)}"
    return None


def _usage(input_value: Any, output: Any, total_tokens: int | None, cost: float | None) -> Usage:
    input_tokens = max(1, len(str(input_value)) // 4) if input_value is not None else 0
    if total_tokens is None:
        output_tokens = max(1, len(str(output)) // 4) if output is not None else 0
    else:
        output_tokens = max(0, total_tokens - input_tokens)
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)
