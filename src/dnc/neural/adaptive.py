"""Model-specific adaptive-depth execution with calibrated full-depth fallback."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable

from dnc.cognition.contracts import RiskClass


@dataclass(frozen=True)
class NeuralExperimentDesign:
    model_family: str
    task_domain: str
    dataset_hash: str
    full_depth: int
    exit_layers: tuple[int, ...]
    seed: int

    def __post_init__(self) -> None:
        if not all((self.model_family, self.task_domain, self.dataset_hash)):
            raise ValueError("neural experiment identity and data lineage MUST be complete")
        if self.full_depth <= 0 or not self.exit_layers:
            raise ValueError("adaptive model MUST declare depth and exits")
        if tuple(sorted(set(self.exit_layers))) != self.exit_layers:
            raise ValueError("exit layers MUST be unique and sorted")
        if self.exit_layers[-1] != self.full_depth or self.exit_layers[0] <= 0:
            raise ValueError("exit layers MUST terminate at full depth")


@dataclass(frozen=True)
class ExitCalibration:
    layer: int
    domain: str
    risk_class: RiskClass
    model_fingerprint: str
    confidence_threshold: float
    maximum_error: float
    observed_error: float
    sample_count: int
    shifted: bool = False

    @property
    def applicable(self) -> bool:
        return (
            self.sample_count >= 20
            and self.observed_error <= self.maximum_error
            and not self.shifted
        )


@dataclass(frozen=True)
class ExitObservation:
    output: Any
    confidence: float
    layer: int

    def __post_init__(self) -> None:
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("neural exit confidence MUST be finite and between zero and one")


@dataclass(frozen=True)
class AdaptiveDepthResult:
    output: Any
    exit_layer: int
    layers_executed: int
    full_depth: int
    used_early_exit: bool
    calibrated: bool
    reason_codes: tuple[str, ...]
    layer_trace: tuple[int, ...]

    @property
    def compute_fraction(self) -> float:
        return self.layers_executed / self.full_depth


Layer = Callable[[Any], Any]
ExitHead = Callable[[Any], tuple[Any, float]]


@dataclass
class AdaptiveDepthModel:
    design: NeuralExperimentDesign
    model_fingerprint: str
    layers: tuple[Layer, ...]
    exit_heads: dict[int, ExitHead]
    calibrations: tuple[ExitCalibration, ...]
    kill_switch: bool = False

    def __post_init__(self) -> None:
        if len(self.layers) != self.design.full_depth:
            raise ValueError("layer count MUST match experiment full depth")
        if set(self.exit_heads) != set(self.design.exit_layers):
            raise ValueError("one exit head is required at every declared exit")

    def execute(
        self,
        value: Any,
        *,
        domain: str,
        risk_class: RiskClass,
        force_full_depth: bool = False,
    ) -> AdaptiveDepthResult:
        hidden = value
        trace: list[int] = []
        fallback_reasons: list[str] = []
        for layer_number, layer in enumerate(self.layers, start=1):
            hidden = layer(hidden)
            trace.append(layer_number)
            if layer_number not in self.exit_heads:
                continue
            output, confidence = self.exit_heads[layer_number](hidden)
            observation = ExitObservation(output, confidence, layer_number)
            is_final = layer_number == self.design.full_depth
            if is_final:
                return AdaptiveDepthResult(
                    observation.output, layer_number, len(trace), self.design.full_depth,
                    False, True, tuple(fallback_reasons or ("FULL_DEPTH",)), tuple(trace),
                )
            calibration = self._calibration(layer_number, domain, risk_class)
            if self.kill_switch or force_full_depth:
                fallback_reasons.append("FULL_DEPTH_KILL_SWITCH" if self.kill_switch else "FULL_DEPTH_FORCED")
            elif calibration is None:
                fallback_reasons.append(f"NO_APPLICABLE_CALIBRATION:{layer_number}")
            elif observation.confidence < calibration.confidence_threshold:
                fallback_reasons.append(f"EXIT_CONFIDENCE_LOW:{layer_number}")
            else:
                return AdaptiveDepthResult(
                    observation.output, layer_number, len(trace), self.design.full_depth,
                    True, True, ("CALIBRATED_EARLY_EXIT",), tuple(trace),
                )
        raise RuntimeError("adaptive model did not reach its mandatory final exit")

    def _calibration(
        self, layer: int, domain: str, risk_class: RiskClass
    ) -> ExitCalibration | None:
        return next(
            (
                item for item in self.calibrations
                if item.layer == layer
                and item.domain == domain
                and item.risk_class is risk_class
                and item.model_fingerprint == self.model_fingerprint
                and item.applicable
            ),
            None,
        )
