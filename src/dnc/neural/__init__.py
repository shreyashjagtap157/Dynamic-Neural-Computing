"""Tensor-native contracts and backend interfaces."""

from dnc.neural.backend import NeuralBackend, NeuralBackendRegistry
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

__all__ = [
    "CachePolicy",
    "CompilationPolicy",
    "GradientPolicy",
    "NeuralBackend",
    "NeuralBackendRegistry",
    "NeuralExecutionRequest",
    "NeuralExecutionResult",
    "NeuralUnitContract",
    "ParameterSpec",
    "QuantizationPolicy",
    "TensorSpec",
]
