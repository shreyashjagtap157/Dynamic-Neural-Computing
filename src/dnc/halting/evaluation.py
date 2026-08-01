"""Matched-quality evaluation for attempt-level halting policies."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from dnc.assurance.calibration import bootstrap_interval


@dataclass(frozen=True)
class HaltingTrial:
    task_id: str
    policy: str
    correct: bool
    stopped: bool
    critical: bool
    attempts: int
    tokens: int
    cost: float
    latency_ms: int


@dataclass(frozen=True)
class HaltingEvaluation:
    count: int
    accuracy: float
    average_attempts: float
    average_tokens: float
    average_cost: float
    average_latency_ms: float
    critical_false_stop_rate: float
    attempt_savings_interval: tuple[float, float]


def evaluate_trials(trials: tuple[HaltingTrial, ...], *, seed: int = 0) -> HaltingEvaluation:
    if not trials:
        raise ValueError("halting evaluation requires trials")
    critical_stops = [trial for trial in trials if trial.critical and trial.stopped]
    false_stops = [trial for trial in critical_stops if not trial.correct]
    attempts = [trial.attempts for trial in trials]
    return HaltingEvaluation(
        len(trials),
        mean(trial.correct for trial in trials),
        mean(attempts),
        mean(trial.tokens for trial in trials),
        mean(trial.cost for trial in trials),
        mean(trial.latency_ms for trial in trials),
        len(false_stops) / len(critical_stops) if critical_stops else 0.0,
        bootstrap_interval(attempts, samples=500, seed=seed),
    )


def compare_matched_quality(
    adaptive: tuple[HaltingTrial, ...], baseline: tuple[HaltingTrial, ...], *, tolerance: float = 0.0
) -> dict[str, float | bool]:
    adaptive_result, baseline_result = evaluate_trials(adaptive), evaluate_trials(baseline)
    return {
        "quality_matched": adaptive_result.accuracy + tolerance >= baseline_result.accuracy,
        "attempt_reduction": baseline_result.average_attempts - adaptive_result.average_attempts,
        "token_reduction": baseline_result.average_tokens - adaptive_result.average_tokens,
        "latency_reduction_ms": baseline_result.average_latency_ms - adaptive_result.average_latency_ms,
        "critical_false_stop_delta": adaptive_result.critical_false_stop_rate - baseline_result.critical_false_stop_rate,
    }
