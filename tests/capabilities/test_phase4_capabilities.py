import time
import os
from dataclasses import replace

import pytest

from dnc.capabilities import (
    CapabilityBroker,
    CapabilityCard,
    CapabilityFeature,
    CapabilityLifecycle,
    CapabilityRegistry,
    CapabilityRequirement,
    CircuitBreaker,
    DeterministicCapability,
    HealthStatus,
    HumanCapability,
    ProviderAdapter,
    ProviderRequest,
    RateLimiter,
    deterministic_card,
    human_card,
    optional_backend_card,
    provider_capability_card,
    pytorch_capability_card,
)
from dnc.cognition import (
    CalibrationProfile,
    CalibrationRegistry,
    CognitiveActionType,
    CognitiveState,
    GoalInvariant,
    PolicyContext,
    RiskClass,
    TaskSpec,
)
from dnc.execution.execution_provider import (
    CostEstimate,
    ExecutionCapability,
    ExecutionProvider,
    ProviderMetadata,
    ProviderResult,
    ReferenceExecutionProvider,
)
from dnc.execution.snapshot import CancellationToken
from dnc.system import DNCSystem


def _card(**changes: object) -> CapabilityCard:
    card = CapabilityCard(
        capability_id="provider.test.model-v1",
        name="Test model",
        provider_id="test",
        provider_version="1",
        model_id="model-v1",
        supported_actions=frozenset({CognitiveActionType.REASON}),
        risk_limit=RiskClass.HIGH,
        features=frozenset(
            {
                CapabilityFeature.STREAMING,
                CapabilityFeature.STRUCTURED_OUTPUT,
                CapabilityFeature.TOOL_CALLING,
                CapabilityFeature.CANCELLATION,
                CapabilityFeature.USAGE,
            }
        ),
        permissions=frozenset({"model:invoke"}),
        calibration_domains=frozenset({"general"}),
        competence=0.8,
        cost_per_call=0.01,
        latency_ms=10,
        max_tokens=4096,
        health=HealthStatus.HEALTHY,
        fingerprint="fingerprint-v1",
    )
    return replace(card, **changes)


def test_registry_lifecycle_health_expiry_and_kill_switch() -> None:
    registry = CapabilityRegistry()
    registry.register(_card())
    assert len(registry.available()) == 1

    registry.disable("provider.test.model-v1")
    assert not registry.available()
    registry.enable("provider.test.model-v1")
    registry.set_health("provider.test.model-v1", HealthStatus.UNHEALTHY)
    assert not registry.available()
    registry.set_health("provider.test.model-v1", HealthStatus.HEALTHY)
    registry.set_lifecycle("provider.test.model-v1", CapabilityLifecycle.SUSPENDED)
    assert not registry.available()

    registry.register(_card(expires_at_ns=time.time_ns() - 1))
    assert not registry.available()


def test_system_snapshot_restores_phase3_and_phase4_state_as_one_boundary() -> None:
    registry = CapabilityRegistry()
    registry.register(_card())
    state = CognitiveState(
        task=TaskSpec(
            task_id="integrated-task",
            tenant_id="tenant-a",
            actor_id="actor-a",
            session_id="session-a",
            description="Verify integrated restoration",
            goal=GoalInvariant(objective="Verify integrated restoration"),
            policy=PolicyContext(risk_class=RiskClass.HIGH),
        )
    )
    system = DNCSystem(
        execution_id="phase1-4-integration",
        cognitive_state=state,
        capability_registry=registry,
    )
    snapshot = system.capture_execution_snapshot("integrated-snapshot")

    system.update_cognitive_state(state.with_materialized_view("empty-view", ()))
    registry.disable("provider.test.model-v1")
    registry.register(_card(name="Changed model", fingerprint="fingerprint-v2"))
    system.restore_execution_snapshot(snapshot)

    assert system.cognitive_state is not None
    assert system.cognitive_state.canonical_hash() == state.canonical_hash()
    assert system.capability_registry.get("provider.test.model-v1") == _card()
    assert not system.capability_registry.is_disabled("provider.test.model-v1")
    selection = system.select_capability(
        CapabilityRequirement(CognitiveActionType.REASON, RiskClass.HIGH),
        now_ns=0,
    )
    assert selection.satisfied
    assert selection.selected == _card()


def test_broker_matches_all_requirements_and_records_rejections() -> None:
    registry = CapabilityRegistry()
    registry.register(_card())
    registry.register(
        _card(
            capability_id="provider.weak.model",
            competence=0.2,
            permissions=frozenset(),
            features=frozenset(),
        )
    )
    requirement = CapabilityRequirement(
        action_type=CognitiveActionType.REASON,
        risk_class=RiskClass.HIGH,
        required_features=frozenset({CapabilityFeature.STRUCTURED_OUTPUT}),
        required_permissions=frozenset({"model:invoke"}),
        domain="general",
        minimum_competence=0.7,
        maximum_cost=0.02,
        maximum_latency_ms=20,
        token_budget=2048,
    )

    selection = CapabilityBroker(registry).match(requirement)

    assert selection.satisfied
    assert selection.selected.capability_id == "provider.test.model-v1"
    rejected = {item.capability_id: item.reason_codes for item in selection.rejections}
    assert "FEATURES_MISSING" in rejected["provider.weak.model"]
    assert "PERMISSIONS_MISSING" in rejected["provider.weak.model"]
    assert "COMPETENCE_LOW" in rejected["provider.weak.model"]


class RecordedProvider(ExecutionProvider):
    def __init__(self, results: list[ProviderResult]) -> None:
        self.results = results
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return "test"

    @property
    def provider_version(self) -> str:
        return "1"

    @property
    def provider_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            "test", "1", frozenset({ExecutionCapability.CAP_REASONING}),
            supports_streaming=True, supports_function_calling=True,
        )

    def supports(self, capability: ExecutionCapability) -> bool:
        return capability is ExecutionCapability.CAP_REASONING

    def execute(self, capability, input, config=None) -> ProviderResult:
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return result

    def estimate_cost(self, capability, input) -> CostEstimate:
        return CostEstimate(capability)

    def get_capabilities(self) -> set[ExecutionCapability]:
        return {ExecutionCapability.CAP_REASONING}


def _result(*, output=None, error=None) -> ProviderResult:
    return ProviderResult(
        ExecutionCapability.CAP_REASONING, output, "test", 1.0,
        tokens_used=7, error=error,
    )


def test_adapter_retries_accounts_usage_and_validates_structured_output() -> None:
    provider = RecordedProvider([_result(error="temporary"), _result(output={"answer": 42})])
    adapter = ProviderAdapter(provider, _card())
    request = ProviderRequest(
        "request-1", CognitiveActionType.REASON, "question", max_retries=1,
        response_schema={"type": "object", "required": ["answer"]},
    )

    response = adapter.execute(request)

    assert response.success
    assert response.attempts == 2
    assert response.usage.input_tokens > 0
    assert response.usage.input_tokens + response.usage.output_tokens == 7
    assert provider.calls == 2


def test_adapter_explicitly_rejects_unsupported_features_and_bad_output() -> None:
    provider = RecordedProvider([_result(output="not-json")])
    unsupported = ProviderAdapter(provider, _card(features=frozenset()))
    response = unsupported.execute(
        ProviderRequest("r1", CognitiveActionType.REASON, "x", stream=True)
    )
    assert response.error_code == "UNSUPPORTED_FEATURE"
    assert provider.calls == 0

    invalid = ProviderAdapter(provider, _card()).execute(
        ProviderRequest(
            "r2", CognitiveActionType.REASON, "x",
            response_schema={"type": "object", "required": ["answer"]},
        )
    )
    assert invalid.error_code == "INVALID_STRUCTURED_OUTPUT"


def test_stream_cancellation_is_terminal_and_does_not_emit_output() -> None:
    provider = RecordedProvider([_result(output="must-not-appear")])
    token = CancellationToken(cancelled=True, reason="user stop")
    events = tuple(
        ProviderAdapter(provider, _card()).stream(
            ProviderRequest("stream-1", CognitiveActionType.REASON, "x", stream=True),
            cancellation=token,
        )
    )

    assert [event.kind for event in events] == ["start", "cancelled"]
    assert events[-1].terminal
    assert provider.calls == 0


def test_cancellation_during_provider_call_discards_completed_output() -> None:
    token = CancellationToken()

    class CancellingProvider(RecordedProvider):
        def execute(self, capability, input, config=None) -> ProviderResult:
            token.cancel("cancelled during provider call")
            return _result(output="must-not-be-promoted")

    response = ProviderAdapter(CancellingProvider([_result(output="unused")]), _card()).execute(
        ProviderRequest("cancel-mid-call", CognitiveActionType.REASON, "x"),
        cancellation=token,
    )

    assert not response.success
    assert response.error_code == "CANCELLED"
    assert response.output is None


def test_rate_limit_timeout_and_circuit_breaker_fail_explicitly() -> None:
    provider = RecordedProvider([_result(error="down")])
    adapter = ProviderAdapter(
        provider,
        _card(),
        breaker=CircuitBreaker(failure_threshold=1),
        rate_limiter=RateLimiter(1),
    )
    request = ProviderRequest("r", CognitiveActionType.REASON, "x")
    assert adapter.execute(request).error_code == "PROVIDER_ERROR"
    assert adapter.execute(request).error_code == "CIRCUIT_OPEN"

    limited = ProviderAdapter(
        RecordedProvider([_result(output="ok")]), _card(), rate_limiter=RateLimiter(1)
    )
    assert limited.execute(request).success
    assert limited.execute(replace(request, request_id="r2")).error_code == "RATE_LIMITED"


def test_timeout_bounds_adapter_wall_time() -> None:
    class SlowProvider(RecordedProvider):
        def execute(self, capability, input, config=None) -> ProviderResult:
            time.sleep(0.1)
            return _result(output="late")

    adapter = ProviderAdapter(SlowProvider([_result(output="unused")]), _card())
    started = time.monotonic()
    response = adapter.execute(
        ProviderRequest("timeout", CognitiveActionType.REASON, "x", timeout_ms=5)
    )
    elapsed_ms = (time.monotonic() - started) * 1000

    assert response.error_code == "TIMEOUT"
    assert elapsed_ms < 50


def test_usage_attributes_input_and_output_tokens() -> None:
    response = ProviderAdapter(RecordedProvider([_result(output="answer")]), _card()).execute(
        ProviderRequest("usage", CognitiveActionType.REASON, "a sufficiently long input prompt")
    )

    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens >= 0


def test_deterministic_and_human_capabilities_enforce_contracts() -> None:
    deterministic = DeterministicCapability(
        deterministic_card("verify.json", CognitiveActionType.VERIFY),
        lambda value: {"valid": isinstance(value, dict)},
    )
    assert deterministic.execute(
        ProviderRequest("verify", CognitiveActionType.VERIFY, {"x": 1})
    ).output == {"valid": True}

    human = HumanCapability(
        human_card(), lambda request: {"approved": True}, "owner", frozenset({"deploy"})
    )
    denied = human.execute(
        ProviderRequest(
            "approval", CognitiveActionType.ESCALATE, "deploy?",
            metadata={"required_authority": ["finance"]},
        )
    )
    assert denied.error_code == "AUTHORITY_DENIED"

    unavailable = HumanCapability(
        human_card(),
        lambda request: (_ for _ in ()).throw(RuntimeError("operator unavailable")),
        "owner",
        frozenset(),
    ).execute(ProviderRequest("human-down", CognitiveActionType.ASK, "question"))
    assert unavailable.error_code == "HUMAN_UNAVAILABLE"


def test_provider_cards_optional_backends_and_system_integration() -> None:
    provider = ReferenceExecutionProvider(capabilities={ExecutionCapability.CAP_REASONING})
    card = provider_capability_card(provider, locality="local")
    registry = CapabilityRegistry()
    registry.register(card)

    assert CapabilityFeature.LOCAL in card.features
    assert pytorch_capability_card().provider_version
    assert optional_backend_card("definitely_missing_dnc_package", backend="onnx").metadata[
        "prototype_only"
    ]
    assert DNCSystem(capability_registry=registry).capability_registry is registry


def test_model_change_invalidates_matching_calibration() -> None:
    calibrations = CalibrationRegistry()
    profile = CalibrationProfile(
        "profile", "general", "1",
        {risk: 0.1 for risk in RiskClass},
        capability_fingerprint="fingerprint-v1",
    )
    calibrations.register(profile)
    registry = CapabilityRegistry()
    registry.add_change_listener(calibrations.handle_model_change)
    registry.register(_card())
    registry.register(_card(fingerprint="fingerprint-v2", model_id="model-v2"))

    assert calibrations.get("profile") is None
    assert calibrations.invalidation_reason("profile") == "provider/model fingerprint changed"


def test_provider_card_model_change_uses_stable_identity_and_invalidates_calibration() -> None:
    first_provider = ReferenceExecutionProvider(provider_id="stable-provider", provider_version="1")
    second_provider = ReferenceExecutionProvider(provider_id="stable-provider", provider_version="2")
    first = provider_capability_card(first_provider, model_id="model-a")
    second = provider_capability_card(second_provider, model_id="model-b")
    calibrations = CalibrationRegistry()
    calibrations.register(
        CalibrationProfile(
            "factory-profile", "general", "1", {risk: 0.1 for risk in RiskClass},
            capability_fingerprint=first.fingerprint,
        )
    )
    registry = CapabilityRegistry()
    registry.add_change_listener(calibrations.handle_model_change)

    registry.register(first)
    registry.register(second)

    assert first.capability_id == second.capability_id
    assert calibrations.get("factory-profile") is None


@pytest.mark.live_provider
def test_live_provider_qualification_is_opt_in() -> None:
    if os.environ.get("DNC_LIVE_PROVIDER_QUALIFICATION") != "1":
        pytest.skip("set DNC_LIVE_PROVIDER_QUALIFICATION=1 to enable")
    backend = os.environ.get("DNC_LIVE_PROVIDER", "ollama")
    if backend == "ollama":
        from dnc.providers.ollama import OllamaConfig, OllamaProvider

        base_url = os.environ.get("DNC_LIVE_PROVIDER_URL", "http://localhost:11434")
        discovery = OllamaProvider(OllamaConfig(base_url=base_url))
        models = discovery.list_models()
        if not models:
            pytest.fail("live Ollama qualification requested but no models are available")
        model = os.environ.get("DNC_LIVE_MODEL") or models[0].get("name") or models[0].get("model")
        if not model:
            pytest.fail("live Ollama model discovery returned no usable model identity")
        provider = OllamaProvider(OllamaConfig(base_url=base_url, default_model=model))
    elif backend == "vllm":
        from dnc.providers.vllm import vLLMConfig, vLLMProvider

        provider = vLLMProvider(
            vLLMConfig(base_url=os.environ.get("DNC_LIVE_PROVIDER_URL", "http://localhost:8000"))
        )
        if not provider.is_available():
            pytest.fail("live vLLM qualification requested but the service is unavailable")
    elif backend == "openai":
        from dnc.providers.openai import OpenAIConfig, OpenAIProvider

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            pytest.fail("live OpenAI qualification requested without OPENAI_API_KEY")
        provider = OpenAIProvider(
            OpenAIConfig(
                api_key=api_key,
                base_url=os.environ.get("DNC_LIVE_PROVIDER_URL", "https://api.openai.com/v1"),
                default_model=os.environ.get("DNC_LIVE_MODEL", "gpt-4o"),
            )
        )
    else:
        pytest.fail(f"unsupported live qualification provider: {backend}")

    result = provider.execute(ExecutionCapability.CAP_REASONING, "Reply with OK")
    assert result.is_success
    assert not (isinstance(result.output, dict) and result.output.get("_mock"))
