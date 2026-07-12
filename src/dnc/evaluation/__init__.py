"""DNC Evaluation package: Computation-Aware Evaluation.

Per evaluation-framework.md: The evaluation package provides computation-aware
evaluation metrics that measure how intelligently computation was allocated,
not just whether the answer is correct.
"""

from __future__ import annotations

from dnc.evaluation.computation_aware import (
    ComputationMonitor,
    ComputationReport,
    Level0Metrics,
    Level1Metrics,
    Level2Metrics,
    Level3Metrics,
)

__all__ = [
    "ComputationMonitor",
    "ComputationReport",
    "Level0Metrics",
    "Level1Metrics",
    "Level2Metrics",
    "Level3Metrics",
]