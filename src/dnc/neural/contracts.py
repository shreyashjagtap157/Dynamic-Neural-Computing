"""Tensor-native contracts for dynamic neural computation backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


Dimension = int | str | None


class GradientPolicy(str, Enum):
    FROZEN = "frozen"
    ENABLED = "enabled"
    ADAPTER_ONLY = "adapter_only"
    EXTERNAL = "external"


class CompilationPolicy(str, Enum):
    EAGER = "eager"
    COMPILE_ONCE = "compile_once"
    CACHE_BY_SIGNATURE = "cache_by_signature"
    BACKEND_MANAGED = "backend_managed"


@dataclass(frozen=True)
class TensorSpec:
    """Portable tensor shape, type, layout, and placement contract."""

    shape: tuple[Dimension, ...]
    dtype: str
    name: str = ""
    layout: str = "contiguous"
    device: str = "any"
    requires_gradient: bool = False

    def validate_shape(self, actual: Sequence[int]) -> bool:
        if len(actual) != len(self.shape):
            return False
        symbols: dict[str, int] = {}
        for expected, observed in zip(self.shape, actual):
            if expected is None:
                continue
            if isinstance(expected, int) and expected != observed:
                return False
            if isinstance(expected, str):
                previous = symbols.setdefault(expected, observed)
                if previous != observed:
                    return False
        return True


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    tensor: TensorSpec
    trainable: bool = True
    sharding: str = "replicated"


@dataclass(frozen=True)
class QuantizationPolicy:
    mode: str = "none"
    bits: int | None = None
    calibration_artifact: str | None = None

    def __post_init__(self) -> None:
        if self.mode == "none" and self.bits is not None:
            raise ValueError("unquantized tensors cannot declare a bit width")
        if self.bits is not None and self.bits not in {2, 3, 4, 8, 16}:
            raise ValueError("unsupported quantization bit width")


@dataclass(frozen=True)
class CachePolicy:
    kind: str = "none"
    scope: str = "request"
    max_bytes: int | None = None
    eviction: str = "lru"


@dataclass(frozen=True)
class NeuralUnitContract:
    """Backend-independent contract for a trainable or inferential neural unit."""

    inputs: Mapping[str, TensorSpec]
    outputs: Mapping[str, TensorSpec]
    parameters: tuple[ParameterSpec, ...] = ()
    state: Mapping[str, TensorSpec] = field(default_factory=dict)
    gradient_policy: GradientPolicy = GradientPolicy.FROZEN
    compilation_policy: CompilationPolicy = CompilationPolicy.EAGER
    precision: str = "backend_default"
    quantization: QuantizationPolicy = field(default_factory=QuantizationPolicy)
    cache: CachePolicy = field(default_factory=CachePolicy)
    supported_backends: frozenset[str] = field(default_factory=frozenset)

    def validate(self) -> None:
        if not self.inputs:
            raise ValueError("a neural unit must declare at least one input")
        if not self.outputs:
            raise ValueError("a neural unit must declare at least one output")
        parameter_names = [item.name for item in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("parameter names must be unique")
        if self.gradient_policy == GradientPolicy.FROZEN and any(
            item.trainable for item in self.parameters
        ):
            raise ValueError("frozen units cannot contain trainable parameters")


@dataclass(frozen=True)
class NeuralExecutionRequest:
    unit_id: str
    inputs: Mapping[str, Any]
    state: Mapping[str, Any] = field(default_factory=dict)
    training: bool = False
    seed: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NeuralExecutionResult:
    outputs: Mapping[str, Any]
    state: Mapping[str, Any] = field(default_factory=dict)
    loss: Any | None = None
    metrics: Mapping[str, float] = field(default_factory=dict)
    backend_id: str = ""
    compiled_signature: str | None = None
