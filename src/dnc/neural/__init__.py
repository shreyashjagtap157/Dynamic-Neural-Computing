"""Tensor-native contracts and backend interfaces."""

from dnc.neural.backend import NeuralBackend, NeuralBackendRegistry
from dnc.neural.adaptive import (
    AdaptiveDepthModel, AdaptiveDepthResult, ExitCalibration, ExitObservation,
    NeuralExperimentDesign,
)
from dnc.neural.capability import NeuralExitEvidence, issue_exit_evidence
from dnc.neural.contracts import (
    CachePolicy,
    CompilationPolicy,
    GradientPolicy,
    NeuralExecutionRequest,
    NeuralExecutionResult,
    NeuralUnitContract,
    ParameterSpec,
    QuantizationPolicy,
    TensorSpec,
)
from dnc.neural.evaluation import NeuralBenchmark, benchmark_compute_fractions
from dnc.neural.training import AdaptiveLoss, NeuralCheckpoint, adaptive_training_loss

__all__ = [
    "CachePolicy",
    "AdaptiveDepthModel",
    "AdaptiveDepthResult",
    "AdaptiveLoss",
    "CompilationPolicy",
    "GradientPolicy",
    "ExitCalibration",
    "ExitObservation",
    "NeuralBackend",
    "NeuralBackendRegistry",
    "NeuralExecutionRequest",
    "NeuralExecutionResult",
    "NeuralBenchmark",
    "NeuralCheckpoint",
    "NeuralExitEvidence",
    "NeuralExperimentDesign",
    "NeuralUnitContract",
    "ParameterSpec",
    "QuantizationPolicy",
    "TensorSpec",
    "adaptive_training_loss",
    "benchmark_compute_fractions",
    "issue_exit_evidence",
]
