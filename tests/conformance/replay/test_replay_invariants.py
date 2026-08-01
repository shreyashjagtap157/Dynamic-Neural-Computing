"""Executable evidence for INV-REP-1 through INV-REP-5."""

from dataclasses import replace

import pytest

from dnc.execution.execution_provider import (
    CostEstimate,
    ExecutionCapability,
    ExecutionProvider,
    ProviderMetadata,
)
from dnc.execution.execution_trace import DecisionRecord
from dnc.execution.replay_engine import ReplayConfig, ReplayEngine
from dnc.execution.snapshot import ReproducibilityGrade
from dnc.runtime.runtime import ProviderMode, Runtime
from dnc.runtime.types import ModuleContract, ModuleTypeID


class FailingProvider(ExecutionProvider):
    def __init__(self):
        self.calls = 0

    @property
    def provider_id(self):
        return "must-not-call"

    @property
    def provider_version(self):
        return "1"

    @property
    def provider_metadata(self):
        return ProviderMetadata("must-not-call", "1", frozenset({ExecutionCapability.CAP_EXECUTION}))

    def supports(self, capability):
        return True

    def execute(self, capability, input, config=None):
        self.calls += 1
        raise AssertionError("replay made a fresh provider call")

    def estimate_cost(self, capability, input):
        return CostEstimate(capability)

    def get_capabilities(self):
        return {ExecutionCapability.CAP_EXECUTION}


def _runtime() -> tuple[Runtime, object]:
    runtime = Runtime()
    runtime.register_module(
        ModuleContract(module_type_id=ModuleTypeID("Source", "v1"), output_signature=object)
    )
    state = runtime.initiate("replay", seed=23)
    runtime.set_dispatch_fn(lambda mid: {"recorded": mid.type_id})
    return runtime, state


def _trace():
    runtime, state = _runtime()
    runtime.step(state)
    runtime.step(state)
    return runtime.execution_trace


def test_inv_rep_1_replays_every_step_in_order() -> None:
    """INV-REP-1: ReplayEngine replays every trace step in order."""
    trace = _trace()
    runtime, state = _runtime()
    result = ReplayEngine().replay(trace, runtime, state)
    assert result.replayed_steps == len(trace.execution_record)
    assert [item.step_index for item in result.step_results] == [0, 1]
    assert result.verified_reexecution
    assert result.reproducibility_grade is ReproducibilityGrade.R3_RECORDED_EXTERNALS


def test_inv_rep_2_uses_recorded_responses_not_fresh_provider_calls() -> None:
    """INV-REP-2: recorded provider results suppress fresh provider calls."""
    trace = _trace()
    runtime, state = _runtime()
    provider = FailingProvider()
    runtime.register_provider(provider)
    runtime.set_provider_mode(ProviderMode.PROD)
    node = runtime._current_graph.get_vertices()[0]
    runtime.set_node_capabilities({node: ExecutionCapability.CAP_EXECUTION})
    result = ReplayEngine().replay(trace, runtime, state)
    assert result.is_identical
    assert provider.calls == 0


def test_inv_rep_3_critical_divergence_marks_replay_non_identical() -> None:
    """INV-REP-3: any critical decision divergence makes replay non-identical."""
    trace = _trace()
    first = trace.execution_record[0]
    object.__setattr__(
        first,
        "decision",
        replace(first.decision, decision="ROLLBACK"),
    )
    runtime, state = _runtime()
    result = ReplayEngine().replay(trace, runtime, state)
    assert not result.is_identical
    assert result.deviations


def test_inv_rep_4_verifier_halts_on_first_critical_divergence() -> None:
    """INV-REP-4: verification halts at the first critical divergence."""
    trace = _trace()
    first = trace.execution_record[0]
    object.__setattr__(
        first,
        "decision",
        DecisionRecord("REPLAN", "test", "1"),
    )
    runtime, state = _runtime()
    result = ReplayEngine().replay(trace, runtime, state)
    assert result.replayed_steps == 1
    assert len(result.deviations) == 1


def test_inv_rep_5_deterministic_trace_contains_seed_inputs_time_and_responses() -> None:
    """INV-REP-5: deterministic replay evidence includes seed, inputs, time, responses."""
    trace = _trace()
    assert trace.random_seed == 23
    assert all(record.observation.timestamp for record in trace.execution_record)
    invocations = [
        invocation
        for record in trace.execution_record
        for invocation in record.module_invocations
    ]
    assert invocations and all("recorded_output" in item.metadata for item in invocations)
    runtime, state = _runtime()
    assert ReplayEngine().replay(trace, runtime, state).is_identical


def test_trace_inspection_cannot_satisfy_deterministic_core_grade() -> None:
    trace = _trace()
    with pytest.raises(ValueError, match="below required"):
        ReplayEngine().replay(
            trace,
            config=ReplayConfig(
                required_grade=ReproducibilityGrade.R2_DETERMINISTIC_CORE
            ),
        )
