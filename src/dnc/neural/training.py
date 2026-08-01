"""Adaptive-depth training objective and checkpoint lineage contracts."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.cognition.canonical import canonical_hash


@dataclass(frozen=True)
class AdaptiveLoss:
    total: float
    exit_loss: float
    teacher_loss: float
    compute_regularization: float


def adaptive_training_loss(
    exit_losses: tuple[float, ...],
    teacher_losses: tuple[float, ...],
    exit_depth_fractions: tuple[float, ...],
    *,
    teacher_weight: float,
    compute_weight: float,
) -> AdaptiveLoss:
    if not exit_losses or len(exit_losses) != len(teacher_losses) or len(exit_losses) != len(exit_depth_fractions):
        raise ValueError("training loss inputs MUST be aligned and non-empty")
    if any(value < 0 for value in (*exit_losses, *teacher_losses, *exit_depth_fractions)):
        raise ValueError("training losses and compute fractions MUST be non-negative")
    exit_loss = sum(exit_losses) / len(exit_losses)
    teacher_loss = sum(teacher_losses) / len(teacher_losses)
    compute = sum(exit_depth_fractions) / len(exit_depth_fractions)
    return AdaptiveLoss(
        exit_loss + teacher_weight * teacher_loss + compute_weight * compute,
        exit_loss, teacher_loss, compute,
    )


@dataclass(frozen=True)
class NeuralCheckpoint:
    checkpoint_id: str
    model_family: str
    dataset_hash: str
    seed: int
    parameters_hash: str
    optimizer_hash: str
    step: int
    fingerprint: str = ""

    def __post_init__(self) -> None:
        expected = canonical_hash(
            {
                "checkpoint_id": self.checkpoint_id,
                "model_family": self.model_family,
                "dataset_hash": self.dataset_hash,
                "seed": self.seed,
                "parameters_hash": self.parameters_hash,
                "optimizer_hash": self.optimizer_hash,
                "step": self.step,
            }, namespace="dnc.neural.checkpoint.v1"
        )
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("neural checkpoint fingerprint mismatch")
        object.__setattr__(self, "fingerprint", expected)
