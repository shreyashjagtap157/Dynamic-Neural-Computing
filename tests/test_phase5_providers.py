"""Phase 5C/5D/5E (Providers + Computation-Aware Evaluation) tests.

Tests for:
- Phase 5C: OllamaProvider, vLLMProvider (local inference)
- Phase 5D: ComputationMonitor and efficiency metrics
- Phase 5E: OpenAIProvider, AnthropicProvider, GeminiProvider (cloud)
"""

from __future__ import annotations

import sys
import math

sys.path.insert(0, "src")

from dnc.execution.execution_provider import (
    ExecutionCapability,
    ExecutionProvider,
    ProviderResult,
)
from dnc.providers.ollama import OllamaConfig, OllamaProvider
from dnc.providers.vllm import vLLMConfig, vLLMProvider
from dnc.providers.openai import OpenAIConfig, OpenAIProvider
from dnc.providers.anthropic import AnthropicConfig, AnthropicProvider
from dnc.providers.gemini import GeminiConfig, GeminiProvider
from dnc.evaluation.computation_aware import (
    ComputationMonitor,
    ComputationReport,
    Level0Metrics,
    Level1Metrics,
    Level2Metrics,
    Level3Metrics,
)
from dnc.execution.execution_trace import (
    ExecutionTrace,
    ExecutionRecord,
    ObservationRecord,
    DecisionRecord,
    ModuleInvocationRecord,
    TerminationReason,
)


def test_ec1_ollama_provider_supports_reasoning_and_embedding():
    """EC-1: OllamaProvider supports CAP_REASONING and CAP_EMBEDDING."""
    provider = OllamaProvider()
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert provider.supports(ExecutionCapability.CAP_EMBEDDING)
    assert not provider.supports(ExecutionCapability.CAP_PLANNING)
    print("PASS: ec1_ollama_provider_supports_reasoning_and_embedding")


def test_ec2_ollama_provider_execute_returns_provider_result():
    """EC-2: OllamaProvider.execute() returns a ProviderResult."""
    config = OllamaConfig(base_url="http://localhost:11434", default_model="llama3.2")
    provider = OllamaProvider(config=config)
    result = provider.execute(ExecutionCapability.CAP_REASONING, "test prompt")

    assert isinstance(result, ProviderResult)
    assert result.provider_id == "ollama"
    assert result.capability == ExecutionCapability.CAP_REASONING
    assert result.is_success
    assert result.output is not None
    print("PASS: ec2_ollama_provider_execute_returns_provider_result")


def test_ec3_ollama_provider_metadata():
    """EC-3: OllamaProvider.provider_metadata contains required fields."""
    provider = OllamaProvider()
    meta = provider.provider_metadata

    assert meta.provider_name == "ollama"
    assert meta.provider_version == "1.0.0"
    assert ExecutionCapability.CAP_REASONING in meta.supported_capabilities
    assert ExecutionCapability.CAP_EMBEDDING in meta.supported_capabilities
    print("PASS: ec3_ollama_provider_metadata")


def test_ec4_vllm_provider_supports_reasoning_and_embedding():
    """EC-4: vLLMProvider supports CAP_REASONING and CAP_EMBEDDING."""
    provider = vLLMProvider()
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert provider.supports(ExecutionCapability.CAP_EMBEDDING)
    print("PASS: ec4_vllm_provider_supports_reasoning_and_embedding")


def test_ec5_vllm_provider_execute_returns_provider_result():
    """EC-5: vLLMProvider.execute() returns a ProviderResult."""
    config = vLLMConfig(base_url="http://localhost:8000", default_model="meta-llama/Llama-3.2-3B-Instruct")
    provider = vLLMProvider(config=config)
    result = provider.execute(ExecutionCapability.CAP_REASONING, "test prompt")

    assert isinstance(result, ProviderResult)
    assert result.provider_id == "vllm"
    assert result.is_success
    print("PASS: ec5_vllm_provider_execute_returns_provider_result")


def test_ec6_openai_provider_supports_reasoning_and_embedding():
    """EC-6: OpenAIProvider supports CAP_REASONING and CAP_EMBEDDING."""
    config = OpenAIConfig(api_key="test-key", default_model="gpt-4o")
    provider = OpenAIProvider(config=config)
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert provider.supports(ExecutionCapability.CAP_EMBEDDING)
    assert provider.provider_id == "openai"
    print("PASS: ec6_openai_provider_supports_reasoning_and_embedding")


def test_ec7_openai_provider_estimate_cost():
    """EC-7: OpenAIProvider.estimate_cost() returns a CostEstimate."""
    from dnc.execution.execution_provider import CostEstimate
    config = OpenAIConfig(api_key="test-key", default_model="gpt-4o")
    provider = OpenAIProvider(config=config)
    estimate = provider.estimate_cost(ExecutionCapability.CAP_REASONING, "test input")

    assert isinstance(estimate, CostEstimate)
    assert estimate.capability == ExecutionCapability.CAP_REASONING
    assert estimate.estimated_cost_usd is not None
    assert estimate.estimated_cost_usd >= 0
    print("PASS: ec7_openai_provider_estimate_cost")


def test_ec8_anthropic_provider_supports_reasoning():
    """EC-8: AnthropicProvider supports CAP_REASONING."""
    config = AnthropicConfig(api_key="test-key")
    provider = AnthropicProvider(config=config)
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert not provider.supports(ExecutionCapability.CAP_EMBEDDING)
    print("PASS: ec8_anthropic_provider_supports_reasoning")


def test_ec9_gemini_provider_supports_reasoning():
    """EC-9: GeminiProvider supports CAP_REASONING."""
    config = GeminiConfig(api_key="test-key")
    provider = GeminiProvider(config=config)
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert not provider.supports(ExecutionCapability.CAP_EMBEDDING)
    print("PASS: ec9_gemini_provider_supports_reasoning")


def test_ec10_computation_monitor_level0_metrics():
    """EC-10: ComputationMonitor computes Level 0 (Infrastructure) metrics."""
    trace = ExecutionTrace(execution_id="exec_test")
    for i in range(3):
        obs = ObservationRecord(raw_signals={}, signal_types=["test"])
        dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
        inv = ModuleInvocationRecord(
            module_instance_id=f"mod_{i}",
            module_type="ReasoningModule",
            capability="CAP_REASONING",
            input_size_bytes=100,
            output_size_bytes=200,
            provider_id="ollama",
            provider_version="1.0.0",
            latency_ms=50.0,
            tokens_used=150,
        )
        trace.add_execution_record(
            ExecutionRecord(
                step_index=i,
                loop_iteration=i + 1,
                observation=obs,
                decision=dec,
                module_invocations=[inv],
            )
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)

    assert isinstance(report.level0, Level0Metrics)
    assert report.level0.total_latency_ms > 0
    assert report.level0.total_tokens > 0
    print("PASS: ec10_computation_monitor_level0_metrics")


def test_ec11_computation_monitor_level1_metrics():
    """EC-11: ComputationMonitor computes Level 1 (Execution) metrics."""
    trace = ExecutionTrace(execution_id="exec_test")
    for i in range(5):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(
            decision="REPLAN" if i == 2 else "CONTINUE",
            policy_type="rule",
            policy_version="1.0.0",
        )
        inv = ModuleInvocationRecord(
            module_instance_id=f"mod_{i}",
            module_type="ReasoningModule",
            capability="CAP_REASONING",
            input_size_bytes=50,
            output_size_bytes=100,
            provider_id="ollama",
            provider_version="1.0.0",
            latency_ms=30.0,
        )
        trace.add_execution_record(
            ExecutionRecord(
                step_index=i,
                loop_iteration=i + 1,
                observation=obs,
                decision=dec,
                module_invocations=[inv] if i < 3 else [],
            )
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)

    assert isinstance(report.level1, Level1Metrics)
    assert report.level1.replan_count == 1
    assert report.level1.total_steps == 5
    print("PASS: ec11_computation_monitor_level1_metrics")


def test_ec12_computation_monitor_level2_metrics():
    """EC-12: ComputationMonitor computes Level 2 (Adaptivity) metrics."""
    trace = ExecutionTrace(execution_id="exec_test")
    for i in range(4):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(
            decision="CONTINUE",
            policy_type="rule",
            policy_version="1.0.0",
        )
        inv = ModuleInvocationRecord(
            module_instance_id=f"mod_{i}",
            module_type="ReasoningModule",
            capability="CAP_REASONING",
            input_size_bytes=50,
            output_size_bytes=100,
            provider_id="ollama",
            provider_version="1.0.0",
            latency_ms=30.0,
            tokens_used=100,
        )
        trace.add_execution_record(
            ExecutionRecord(
                step_index=i,
                loop_iteration=i + 1,
                observation=obs,
                decision=dec,
                module_invocations=[inv],
            )
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)

    assert isinstance(report.level2, Level2Metrics)
    assert 0.0 <= report.level2.dynamic_compute_index <= 10.0
    assert 0.0 <= report.level2.graph_entropy <= 1.0
    assert 0.0 <= report.level2.planning_stability <= 1.0
    print("PASS: ec12_computation_monitor_level2_metrics")


def test_ec13_computation_monitor_tool_diversity():
    """EC-13: ComputationMonitor correctly computes tool diversity."""
    trace = ExecutionTrace(execution_id="exec_test")
    module_types = ["ReasoningModule", "RetrievalModule", "VerificationModule", "ReasoningModule"]

    for i, mtype in enumerate(module_types):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
        inv = ModuleInvocationRecord(
            module_instance_id=f"mod_{i}",
            module_type=mtype,
            capability="CAP_REASONING",
            input_size_bytes=50,
            output_size_bytes=100,
            provider_id="ollama",
            provider_version="1.0.0",
            latency_ms=30.0,
        )
        trace.add_execution_record(
            ExecutionRecord(
                step_index=i,
                loop_iteration=i + 1,
                observation=obs,
                decision=dec,
                module_invocations=[inv],
            )
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)

    assert isinstance(report.level2, Level2Metrics)
    assert 0.0 <= report.level2.tool_diversity <= 1.0
    print("PASS: ec13_computation_monitor_tool_diversity")


def test_ec14_computation_monitor_recommendations():
    """EC-14: ComputationMonitor generates actionable recommendations."""
    trace = ExecutionTrace(execution_id="exec_test")
    for i in range(3):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
        inv = ModuleInvocationRecord(
            module_instance_id=f"mod_{i}",
            module_type="ReasoningModule",
            capability="CAP_REASONING",
            input_size_bytes=50,
            output_size_bytes=100,
            provider_id="ollama",
            provider_version="1.0.0",
            latency_ms=30.0,
        )
        trace.add_execution_record(
            ExecutionRecord(
                step_index=i,
                loop_iteration=i + 1,
                observation=obs,
                decision=dec,
                module_invocations=[inv],
            )
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)

    assert len(report.recommendations) > 0
    assert isinstance(report.recommendations, list)
    print("PASS: ec14_computation_monitor_recommendations")


def test_ec15_computation_report_to_dict():
    """EC-15: ComputationReport.to_dict() produces serializable output."""
    trace = ExecutionTrace(execution_id="exec_test")
    obs = ObservationRecord(raw_signals={})
    dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
    inv = ModuleInvocationRecord(
        module_instance_id="mod_0",
        module_type="ReasoningModule",
        capability="CAP_REASONING",
        input_size_bytes=50,
        output_size_bytes=100,
        provider_id="ollama",
        provider_version="1.0.0",
        latency_ms=30.0,
        tokens_used=100,
    )
    trace.add_execution_record(
        ExecutionRecord(
            step_index=0,
            loop_iteration=1,
            observation=obs,
            decision=dec,
            module_invocations=[inv],
        )
    )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    monitor = ComputationMonitor()
    report = monitor.evaluate(trace)
    d = report.to_dict()

    assert isinstance(d, dict)
    assert "level0" in d
    assert "level1" in d
    assert "level2" in d
    assert "recommendations" in d
    print("PASS: ec15_computation_report_to_dict")


def test_ec16_all_providers_implement_execution_provider_interface():
    """EC-16: All providers implement ExecutionProvider interface."""
    providers = [
        OllamaProvider(),
        vLLMProvider(),
        OpenAIProvider(config=OpenAIConfig(api_key="test")),
        AnthropicProvider(config=AnthropicConfig(api_key="test")),
        GeminiProvider(config=GeminiConfig(api_key="test")),
    ]

    for p in providers:
        assert isinstance(p, ExecutionProvider)
        assert hasattr(p, "provider_id")
        assert hasattr(p, "provider_version")
        assert hasattr(p, "provider_metadata")
        assert hasattr(p, "supports")
        assert hasattr(p, "execute")
        assert hasattr(p, "estimate_cost")
        assert hasattr(p, "get_capabilities")
    print("PASS: ec16_all_providers_implement_execution_provider_interface")


def test_ec17_all_providers_have_unique_ids():
    """EC-17: Each provider has a unique provider_id."""
    providers = [
        OllamaProvider(),
        vLLMProvider(),
        OpenAIProvider(config=OpenAIConfig(api_key="test")),
        AnthropicProvider(config=AnthropicConfig(api_key="test")),
        GeminiProvider(config=GeminiConfig(api_key="test")),
    ]

    ids = [p.provider_id for p in providers]
    assert len(ids) == len(set(ids)), f"Duplicate provider IDs: {ids}"
    print("PASS: ec17_all_providers_have_unique_ids")


if __name__ == "__main__":
    tests = [
        test_ec1_ollama_provider_supports_reasoning_and_embedding,
        test_ec2_ollama_provider_execute_returns_provider_result,
        test_ec3_ollama_provider_metadata,
        test_ec4_vllm_provider_supports_reasoning_and_embedding,
        test_ec5_vllm_provider_execute_returns_provider_result,
        test_ec6_openai_provider_supports_reasoning_and_embedding,
        test_ec7_openai_provider_estimate_cost,
        test_ec8_anthropic_provider_supports_reasoning,
        test_ec9_gemini_provider_supports_reasoning,
        test_ec10_computation_monitor_level0_metrics,
        test_ec11_computation_monitor_level1_metrics,
        test_ec12_computation_monitor_level2_metrics,
        test_ec13_computation_monitor_tool_diversity,
        test_ec14_computation_monitor_recommendations,
        test_ec15_computation_report_to_dict,
        test_ec16_all_providers_implement_execution_provider_interface,
        test_ec17_all_providers_have_unique_ids,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/17 Phase 5C/5D/5E tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/17 Phase 5C/5D/5E tests failed")
        exit(1)
    else:
        print("PASS: All Phase 5C/5D/5E tests passed")
        exit(0)