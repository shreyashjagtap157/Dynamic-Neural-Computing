"""Phase 5B (Reference Runtime) exit criteria tests.

Per mvp-roadmap.md Section 7.B: Phase 5B Reference Runtime components:
- DecisionPolicy interface + RulePolicy reference implementation
- ExecutionProvider interface + ReferenceExecutionProvider
- ExecutionTrace schema and structured logging
- ReplayEngine for deterministic replay
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict

sys.path.insert(0, "src")

from dnc.execution.decision_policy import (
    Decision,
    DecisionMetadata,
    DecisionPolicy,
    RulePolicy,
)
from dnc.execution.execution_provider import (
    ExecutionCapability,
    ExecutionProvider,
    ProviderMetadata,
    ProviderResult,
    CostEstimate,
    ReferenceExecutionProvider,
)
from dnc.execution.execution_trace import (
    CausalEvent,
    DecisionRecord,
    ExecutionRecord,
    ExecutionTrace,
    ModuleInvocationRecord,
    ObservationRecord,
    ResourceUsageRecord,
    TerminationReason,
    TraceHeader,
)
from dnc.execution.replay_engine import (
    ReplayConfig,
    ReplayEngine,
    ReplayResult,
    ReplayStepResult,
)
from dnc.state.execution_state import ExecutionState


def test_ec1_decision_policy_interface():
    """EC-1: DecisionPolicy interface has version, policy_type, decide, can_replan, get_decision_metadata."""
    policy = RulePolicy()

    assert hasattr(policy, "version")
    assert hasattr(policy, "policy_type")
    assert hasattr(policy, "decide")
    assert hasattr(policy, "can_replan")
    assert hasattr(policy, "get_decision_metadata")
    assert policy.version == "1.0.0"
    assert policy.policy_type == "rule"
    print("PASS: ec1_decision_policy_interface")


def test_ec2_rule_policy_continues_by_default():
    """EC-2: RulePolicy returns CONTINUE when no special conditions apply."""
    policy = RulePolicy()
    es = ExecutionState()
    obs = {}

    decision = policy.decide(obs, es)
    assert decision == Decision.CONTINUE, f"Expected CONTINUE, got {decision}"
    print("PASS: ec2_rule_policy_continues_by_default")


def test_ec3_rule_policy_replans_on_failure_signal():
    """EC-3: RulePolicy returns REPLAN when failure_detected signal is True (if can_replan)."""
    policy = RulePolicy(replan_coolout_steps=0)
    es = ExecutionState()
    obs = {"failure_detected": True}

    decision = policy.decide(obs, es)
    assert decision == Decision.REPLAN, f"Expected REPLAN, got {decision}"
    print("PASS: ec3_rule_policy_replans_on_failure_signal")


def test_ec4_rule_policy_can_replan_blocks_during_critical_section():
    """EC-4: RulePolicy.can_replan() returns False during critical section."""
    policy = RulePolicy()
    policy.set_critical_section(True)
    assert not policy.can_replan(), "can_replan should return False during critical section"
    policy.set_critical_section(False)
    assert policy.can_replan(), "can_replan should return True when not in critical section"
    print("PASS: ec4_rule_policy_can_replan_blocks_during_critical_section")


def test_ec5_rule_policy_metadata_has_reasoning():
    """EC-5: RulePolicy.get_decision_metadata() returns metadata with reasoning."""
    policy = RulePolicy()
    es = ExecutionState()
    obs = {}

    policy.decide(obs, es)
    meta = policy.get_decision_metadata()

    assert isinstance(meta, DecisionMetadata)
    assert meta.decision == Decision.CONTINUE
    assert meta.reasoning is not None
    assert meta.policy_version == "1.0.0"
    assert meta.latency_ms >= 0
    print("PASS: ec5_rule_policy_metadata_has_reasoning")


def test_ec6_execution_provider_interface():
    """EC-6: ExecutionProvider interface has provider_id, provider_version, supports, execute."""
    provider = ReferenceExecutionProvider()

    assert hasattr(provider, "provider_id")
    assert hasattr(provider, "provider_version")
    assert hasattr(provider, "supports")
    assert hasattr(provider, "execute")
    assert hasattr(provider, "estimate_cost")
    assert hasattr(provider, "get_capabilities")
    print("PASS: ec6_execution_provider_interface")


def test_ec7_reference_provider_supports_reasoning():
    """EC-7: ReferenceExecutionProvider supports CAP_REASONING by default."""
    provider = ReferenceExecutionProvider()
    assert provider.supports(ExecutionCapability.CAP_REASONING)
    assert ExecutionCapability.CAP_REASONING in provider.get_capabilities()
    print("PASS: ec7_reference_provider_supports_reasoning")


def test_ec8_reference_provider_execute_returns_provider_result():
    """EC-8: ReferenceExecutionProvider.execute() returns a ProviderResult."""
    provider = ReferenceExecutionProvider()
    result = provider.execute(ExecutionCapability.CAP_REASONING, "test input")

    assert isinstance(result, ProviderResult)
    assert result.is_success
    assert result.provider_id == "reference"
    assert result.output is not None
    assert result.latency_ms >= 0
    print("PASS: ec8_reference_provider_execute_returns_provider_result")


def test_ec9_execution_provider_unsupported_capability_returns_error():
    """EC-9: ExecutionProvider.execute() returns error for unsupported capability."""
    provider = ReferenceExecutionProvider(
        capabilities={ExecutionCapability.CAP_EMBEDDING}
    )
    result = provider.execute(ExecutionCapability.CAP_REASONING, "test input")

    assert not result.is_success
    assert result.error is not None
    assert "not supported" in result.error
    print("PASS: ec9_execution_provider_unsupported_capability_returns_error")


def test_ec10_execution_provider_estimate_cost():
    """EC-10: ExecutionProvider.estimate_cost() returns a CostEstimate."""
    provider = ReferenceExecutionProvider()
    estimate = provider.estimate_cost(ExecutionCapability.CAP_REASONING, "test input")

    assert isinstance(estimate, CostEstimate)
    assert estimate.capability == ExecutionCapability.CAP_REASONING
    print("PASS: ec10_execution_provider_estimate_cost")


def test_ec11_execution_trace_initialization():
    """EC-11: ExecutionTrace initializes with required header fields."""
    trace = ExecutionTrace(
        execution_id="exec_001",
        runtime_version="0.1.0",
        planner_version="0.1.0",
        resource_budget=100.0,
        random_seed=42,
    )

    assert trace.trace_id != ""
    assert trace.execution_id == "exec_001"
    assert trace.specification_version == "Architecture v1.0"
    assert trace.runtime_version == "0.1.0"
    assert trace.architecture_version == "v1.0"
    assert trace.timestamp_start != ""
    assert trace.timestamp_end is None
    print("PASS: ec11_execution_trace_initialization")


def test_ec12_execution_trace_add_record():
    """EC-12: ExecutionTrace.add_execution_record() appends a record."""
    trace = ExecutionTrace(execution_id="exec_001")

    obs_record = ObservationRecord(raw_signals={}, signal_types=["signal_1"])
    dec_record = DecisionRecord(
        decision="CONTINUE",
        policy_type="rule",
        policy_version="1.0.0",
    )
    exec_record = ExecutionRecord(
        step_index=0,
        loop_iteration=1,
        observation=obs_record,
        decision=dec_record,
    )

    trace.add_execution_record(exec_record)
    assert len(trace.execution_record) == 1
    assert trace.execution_record[0].step_index == 0
    print("PASS: ec12_execution_trace_add_record")


def test_ec13_execution_trace_finalize():
    """EC-13: ExecutionTrace.finalize() sets timestamp_end and termination_reason."""
    trace = ExecutionTrace(execution_id="exec_001")
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE, final_outcome={"result": "ok"})

    assert trace.timestamp_end is not None
    assert trace.termination_reason == TerminationReason.ALL_MODULES_COMPLETE
    assert trace.final_outcome == {"result": "ok"}
    assert trace.is_complete
    print("PASS: ec13_execution_trace_finalize")


def test_ec14_execution_trace_serialization():
    """EC-14: ExecutionTrace.to_dict() produces a serializable dictionary."""
    trace = ExecutionTrace(execution_id="exec_001", resource_budget=100.0)
    obs_record = ObservationRecord(raw_signals={"key": "value"})
    dec_record = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
    exec_record = ExecutionRecord(
        step_index=0, loop_iteration=1, observation=obs_record, decision=dec_record
    )
    trace.add_execution_record(exec_record)
    trace.finalize(TerminationReason.TERMINATE_DECISION)

    d = trace.to_dict()
    assert isinstance(d, dict)
    assert d["trace_id"] == trace.trace_id
    assert d["termination_reason"] == "TERMINATE_DECISION"
    assert len(d["execution_record"]) == 1
    print("PASS: ec14_execution_trace_serialization")


def test_ec15_module_invocation_record():
    """EC-15: ModuleInvocationRecord captures invocation details."""
    record = ModuleInvocationRecord(
        module_instance_id="mod_001",
        module_type="SourceModule",
        capability="CAP_REASONING",
        input_size_bytes=100,
        output_size_bytes=200,
        provider_id="reference",
        provider_version="1.0.0",
        latency_ms=50.0,
        tokens_used=150,
    )

    assert record.module_instance_id == "mod_001"
    assert record.provider_id == "reference"
    assert record.latency_ms == 50.0
    assert record.tokens_used == 150
    print("PASS: ec15_module_invocation_record")


def test_ec16_replay_engine_replay_full_trace():
    """EC-16: ReplayEngine.replay() returns a ReplayResult."""
    trace = ExecutionTrace(execution_id="exec_001")
    for i in range(3):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
        trace.add_execution_record(
            ExecutionRecord(step_index=i, loop_iteration=i + 1, observation=obs, decision=dec)
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    engine = ReplayEngine()
    result = engine.replay(trace)

    assert isinstance(result, ReplayResult)
    assert result.trace_id == trace.trace_id
    assert result.replayed_steps == 3
    assert result.all_matched
    print("PASS: ec16_replay_engine_replay_full_trace")


def test_ec17_replay_engine_detects_decision_mismatch():
    """EC-17: ReplayEngine detects when recorded and replay decisions don't match."""
    trace = ExecutionTrace(execution_id="exec_001")
    obs = ObservationRecord(raw_signals={})
    dec = DecisionRecord(decision="REPLAN", policy_type="rule", policy_version="1.0.0")
    trace.add_execution_record(
        ExecutionRecord(step_index=0, loop_iteration=1, observation=obs, decision=dec)
    )
    trace.finalize(TerminationReason.TERMINATE_DECISION)

    engine = ReplayEngine()
    result = engine.replay(trace)

    step_result = result.step_results[0]
    assert step_result.matched, "Recorded REPLAN should match REPLAN replay"
    print("PASS: ec17_replay_engine_detects_decision_mismatch")


def test_ec18_replay_engine_replay_step():
    """EC-18: ReplayEngine.replay_step() returns a ReplayStepResult for a single step."""
    trace = ExecutionTrace(execution_id="exec_001")
    obs = ObservationRecord(raw_signals={})
    dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
    trace.add_execution_record(
        ExecutionRecord(step_index=0, loop_iteration=1, observation=obs, decision=dec)
    )

    engine = ReplayEngine()
    step_result = engine.replay_step(trace, 0)

    assert isinstance(step_result, ReplayStepResult)
    assert step_result.step_index == 0
    assert step_result.matched
    print("PASS: ec18_replay_engine_replay_step")


def test_ec19_replay_engine_verify_trace_integrity():
    """EC-19: ReplayEngine.verify_trace_integrity() returns True for valid traces."""
    trace = ExecutionTrace(execution_id="exec_001")
    obs = ObservationRecord(raw_signals={})
    dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
    trace.add_execution_record(
        ExecutionRecord(step_index=0, loop_iteration=1, observation=obs, decision=dec)
    )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    engine = ReplayEngine()
    assert engine.verify_trace_integrity(trace)
    print("PASS: ec19_replay_engine_verify_trace_integrity")


def test_ec20_replay_result_match_percentage():
    """EC-20: ReplayResult.match_percentage correctly reports match ratio."""
    trace = ExecutionTrace(execution_id="exec_001")
    for i in range(4):
        obs = ObservationRecord(raw_signals={})
        dec = DecisionRecord(decision="CONTINUE", policy_type="rule", policy_version="1.0.0")
        trace.add_execution_record(
            ExecutionRecord(step_index=i, loop_iteration=i + 1, observation=obs, decision=dec)
        )
    trace.finalize(TerminationReason.ALL_MODULES_COMPLETE)

    engine = ReplayEngine()
    result = engine.replay(trace)

    assert result.match_percentage == 100.0
    print("PASS: ec20_replay_result_match_percentage")


if __name__ == "__main__":
    tests = [
        test_ec1_decision_policy_interface,
        test_ec2_rule_policy_continues_by_default,
        test_ec3_rule_policy_replans_on_failure_signal,
        test_ec4_rule_policy_can_replan_blocks_during_critical_section,
        test_ec5_rule_policy_metadata_has_reasoning,
        test_ec6_execution_provider_interface,
        test_ec7_reference_provider_supports_reasoning,
        test_ec8_reference_provider_execute_returns_provider_result,
        test_ec9_execution_provider_unsupported_capability_returns_error,
        test_ec10_execution_provider_estimate_cost,
        test_ec11_execution_trace_initialization,
        test_ec12_execution_trace_add_record,
        test_ec13_execution_trace_finalize,
        test_ec14_execution_trace_serialization,
        test_ec15_module_invocation_record,
        test_ec16_replay_engine_replay_full_trace,
        test_ec17_replay_engine_detects_decision_mismatch,
        test_ec18_replay_engine_replay_step,
        test_ec19_replay_engine_verify_trace_integrity,
        test_ec20_replay_result_match_percentage,
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

    print(f"\n{passed}/20 Phase 5B tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/20 Phase 5B tests failed")
        exit(1)
    else:
        print("PASS: All Phase 5B tests passed")
        exit(0)