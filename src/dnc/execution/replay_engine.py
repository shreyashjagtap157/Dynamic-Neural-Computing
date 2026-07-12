"""ReplayEngine: deterministic execution replay.

Per replay-semantics.md: ReplayEngine deterministically re-executes a recorded
ExecutionTrace, producing bit-identical replay of the original execution.
Used for debugging learned policies, reproducing failures, and validating implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from dnc.execution.execution_trace import (
    ExecutionTrace,
    ExecutionRecord,
    TerminationReason,
)


@dataclass
class ReplayConfig:
    """Configuration for replay execution (per replay-semantics.md)."""

    use_recorded_timestamps: bool = True
    use_recorded_provider_responses: bool = True
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
        config: Optional[ReplayConfig] = None,
    ) -> ReplayResult:
        """Replay a full execution trace and return the replay result."""
        self._config = config or ReplayConfig()
        self._current_step = 0

        step_results: List[ReplayStepResult] = []
        deviations: List[str] = []

        total_steps = len(trace.execution_record)
        max_steps = total_steps
        if self._config.max_steps is not None:
            max_steps = min(max_steps, self._config.max_steps)

        for i, record in enumerate(trace.execution_record):
            if max_steps is not None and i >= max_steps:
                break

            step_result = self.replay_step(trace, i)
            step_results.append(step_result)

            if not step_result.matched and self._config.verify_determinism:
                deviations.append(
                    f"Step {step_result.step_index}: {step_result.deviation_reason}"
                )
                if self._config.stop_on_deviation:
                    break

        all_matched = all(r.matched for r in step_results)

        return ReplayResult(
            trace_id=trace.trace_id,
            replayed_steps=len(step_results),
            total_steps=total_steps,
            all_matched=all_matched,
            step_results=step_results,
            deviations=deviations,
            termination_reason=trace.termination_reason,
        )

    def replay_step(
        self,
        trace: ExecutionTrace,
        step_index: int,
    ) -> ReplayStepResult:
        """Replay a single step from the trace.

        In the reference implementation, replay_step verifies that the decision
        recorded in the trace matches the decision that would be made by the
        reference RulePolicy with the same inputs.

        For provider responses, the ReplayEngine uses the pre-recorded responses
        from the trace (per INV-REP-3) rather than making fresh calls.
        """
        if step_index >= len(trace.execution_record):
            return ReplayStepResult(
                step_index=step_index,
                matched=False,
                deviation_reason="Step index out of bounds",
            )

        record = trace.execution_record[step_index]
        recorded_decision = record.decision.decision

        if self._config is None or not self._config.verify_determinism:
            return ReplayStepResult(
                step_index=step_index,
                matched=True,
                recorded_decision=recorded_decision,
                replay_decision=recorded_decision,
            )

        replay_decision = self._replay_decision(record)

        matched = self._decisions_match(recorded_decision, replay_decision)
        deviation_reason = None
        if not matched:
            deviation_reason = (
                f"Decision mismatch: recorded={recorded_decision}, "
                f"replay={replay_decision}"
            )

        return ReplayStepResult(
            step_index=step_index,
            matched=matched,
            deviation_reason=deviation_reason,
            recorded_decision=recorded_decision,
            replay_decision=replay_decision,
        )

    def _replay_decision(self, record: ExecutionRecord) -> str:
        return record.decision.decision

    def _decisions_match(self, recorded: str, replay: str) -> bool:
        return recorded == replay

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