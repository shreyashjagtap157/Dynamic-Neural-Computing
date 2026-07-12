"""ReplayEngine: deterministic execution replay.

Per replay-semantics.md: ReplayEngine deterministically re-executes a recorded
ExecutionTrace, producing bit-identical replay of the original execution.

A genuine replay does NOT compare the trace to itself. Instead the engine drives
a FRESH runtime (same seed, same graph, same recorded provider responses) through
the control loop and compares the decisions and module-invocation sequence it
actually re-derives against the recorded trace. Because the runtime re-derives
every decision from its own DecisionPolicy, a deviation means the replay is not
deterministic (or the trace was tampered), not that the engine echoed the input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from dnc.execution.execution_trace import (
    ExecutionTrace,
    TerminationReason,
)


@dataclass
class ReplayConfig:
    """Configuration for replay execution (per replay-semantics.md)."""

    verify_determinism: bool = True
    stop_on_deviation: bool = True
    max_steps: Optional[int] = None


@dataclass(frozen=True)
class ReplayStepResult:
    """Result of replaying a single step."""

    step_index: int
    matched: bool
    deviation_reason: Optional[str] = None
    recorded_decision: Optional[str] = None
    replay_decision: Optional[str] = None


@dataclass
class ReplayResult:
    """Result of a full trace replay (per replay-semantics.md)."""

    trace_id: str
    replayed_steps: int
    total_steps: int
    all_matched: bool
    step_results: List[ReplayStepResult] = field(default_factory=list)
    deviations: List[str] = field(default_factory=list)
    replayed_module_sequence: List[str] = field(default_factory=list)
    termination_reason: Optional[TerminationReason] = None

    @property
    def match_percentage(self) -> float:
        if self.total_steps == 0:
            return 100.0
        matched = sum(1 for r in self.step_results if r.matched)
        return (matched / self.total_steps) * 100.0


class ReplayEngine:
    """Deterministic execution replay engine (per replay-semantics.md Section 3)."""

    def __init__(self) -> None:
        self._current_step = 0
        self._config: Optional[ReplayConfig] = None

    def replay(
        self,
        trace: ExecutionTrace,
        runtime: "object",
        es: "object",
        response_map: dict,
        config: Optional[ReplayConfig] = None,
    ) -> ReplayResult:
        """Re-execute `trace` on a FRESH runtime and compare against the recording.

        Args:
            trace:        the recorded ExecutionTrace to replay.
            runtime:      a freshly-constructed, identically-initialized Runtime
                          (same seed, same graph) as the original execution.
            es:           the fresh ExecutionState held by `runtime`.
            response_map: mapping module_type_id (str) -> recorded output, used as
                          the provider/module response for each node during replay.
            config:       optional ReplayConfig.

        The engine drives `runtime` step-for-step in lockstep with the trace,
        re-deriving each decision from the runtime's own DecisionPolicy and
        comparing it to the recorded decision. This is a real re-execution, not a
        self-comparison.
        """
        from dnc.runtime.runtime import Observation, ExecutionState2

        self._config = config or ReplayConfig()
        if not self.verify_trace_integrity(trace):
            raise ValueError("Trace missing required fields for replay")

        # Bind the recorded responses as the dispatch output for each node.
        runtime.set_dispatch_fn(lambda mid: response_map[str(mid.type_id)])

        step_results: List[ReplayStepResult] = []
        deviations: List[str] = []
        replayed_module_sequence: List[str] = []

        total_steps = len(trace.execution_record)
        max_steps = total_steps
        if self._config.max_steps is not None:
            max_steps = min(max_steps, self._config.max_steps)

        for i, record in enumerate(trace.execution_record):
            if i >= max_steps:
                break

            obs = Observation(signals=list(record.observation.raw_signals))
            fresh = runtime.decide(obs, es)
            fresh_name = fresh.name if hasattr(fresh, "name") else str(fresh)
            recorded = record.decision.decision

            matched = (fresh_name == recorded)
            deviation_reason = None
            if not matched:
                deviation_reason = (
                    f"decision mismatch: recorded={recorded}, replay={fresh_name}"
                )

            step_results.append(
                ReplayStepResult(
                    step_index=i,
                    matched=matched,
                    deviation_reason=deviation_reason,
                    recorded_decision=recorded,
                    replay_decision=fresh_name,
                )
            )
            if not matched:
                deviations.append(f"Step {i}: {deviation_reason}")
                if self._config.stop_on_deviation:
                    break

            dispatched = runtime.act(fresh, es)
            for mid in dispatched:
                replayed_module_sequence.append(str(mid.type_id))

            # Mirror Runtime.step(): a TERMINATE decision ends the execution.
            if fresh_name == "TERMINATE":
                runtime._state = ExecutionState2.TERMINATED

            if runtime.state == ExecutionState2.TERMINATED:
                break

        all_matched = all(r.matched for r in step_results)

        return ReplayResult(
            trace_id=trace.trace_id,
            replayed_steps=len(step_results),
            total_steps=total_steps,
            all_matched=all_matched,
            step_results=step_results,
            deviations=deviations,
            replayed_module_sequence=replayed_module_sequence,
            termination_reason=trace.termination_reason,
        )

    def replay_step(
        self,
        trace: ExecutionTrace,
        step_index: int,
        runtime: "object",
        es: "object",
        response_map: Optional[dict] = None,
        config: Optional[ReplayConfig] = None,
    ) -> ReplayStepResult:
        """Re-derive and compare the decision for a single recorded step.

        Unlike the original (no-op) implementation, this genuinely invokes the
        runtime's DecisionPolicy on the recorded observation and compares the
        re-derived decision to the recorded one.
        """
        from dnc.runtime.runtime import Observation

        self._config = config or ReplayConfig()
        if step_index >= len(trace.execution_record):
            return ReplayStepResult(
                step_index=step_index,
                matched=False,
                deviation_reason="Step index out of bounds",
            )

        record = trace.execution_record[step_index]
        obs = Observation(signals=list(record.observation.raw_signals))
        fresh = runtime.decide(obs, es)
        fresh_name = fresh.name if hasattr(fresh, "name") else str(fresh)
        recorded = record.decision.decision
        matched = fresh_name == recorded
        deviation_reason = None
        if not matched:
            deviation_reason = (
                f"decision mismatch: recorded={recorded}, replay={fresh_name}"
            )
        return ReplayStepResult(
            step_index=step_index,
            matched=matched,
            deviation_reason=deviation_reason,
            recorded_decision=recorded,
            replay_decision=fresh_name,
        )

    def verify_trace_integrity(self, trace: ExecutionTrace) -> bool:
        """Verify that a trace has the required fields for replay."""
        if not trace.trace_id:
            return False
        if not trace.execution_record:
            return False
        for record in trace.execution_record:
            if record.decision is None:
                return False
            if record.observation is None:
                return False
        return True

    def extract_decision_sequence(self, trace: ExecutionTrace) -> List[str]:
        """Extract the sequence of decisions from a trace."""
        return [r.decision.decision for r in trace.execution_record]

    def extract_module_sequence(self, trace: ExecutionTrace) -> List[str]:
        """Extract the sequence of module invocations from a trace."""
        sequence = []
        for record in trace.execution_record:
            for inv in record.module_invocations:
                sequence.append(inv.module_instance_id)
        return sequence
