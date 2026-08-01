"""Capability-protocol evidence for neural exit decisions."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.neural.adaptive import AdaptiveDepthResult


@dataclass(frozen=True)
class NeuralExitEvidence:
    capability_id: str
    model_fingerprint: str
    task_id: str
    exit_layer: int
    layers_executed: int
    full_depth: int
    calibrated: bool
    reason_codes: tuple[str, ...]


def issue_exit_evidence(
    result: AdaptiveDepthResult,
    *,
    capability_id: str,
    model_fingerprint: str,
    task_id: str,
) -> NeuralExitEvidence:
    if not all((capability_id, model_fingerprint, task_id)):
        raise ValueError("neural exit evidence identity MUST be complete")
    return NeuralExitEvidence(
        capability_id, model_fingerprint, task_id, result.exit_layer,
        result.layers_executed, result.full_depth, result.calibrated, result.reason_codes,
    )
