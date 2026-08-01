"""Matched-quality adaptive-depth benchmark and tail-risk evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NeuralBenchmark:
    adaptive_accuracy: float
    full_depth_accuracy: float
    calibration_error: float
    average_compute_fraction: float
    p95_compute_fraction: float
    latency_fraction: float
    memory_fraction: float
    energy_fraction_estimate: float
    shifted_error: float
    worst_group_error: float

    def passes(
        self,
        *,
        quality_tolerance: float,
        maximum_shifted_error: float,
        maximum_worst_group_error: float,
    ) -> bool:
        return (
            self.adaptive_accuracy >= self.full_depth_accuracy - quality_tolerance
            and self.average_compute_fraction < 1
            and self.calibration_error <= quality_tolerance
            and self.shifted_error <= maximum_shifted_error
            and self.worst_group_error <= maximum_worst_group_error
        )


def benchmark_compute_fractions(fractions: tuple[float, ...]) -> tuple[float, float]:
    if not fractions or any(not 0 < value <= 1 for value in fractions):
        raise ValueError("compute fractions MUST be non-empty and in (0, 1]")
    ordered = sorted(fractions)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered))))
    return sum(ordered) / len(ordered), ordered[p95_index]
