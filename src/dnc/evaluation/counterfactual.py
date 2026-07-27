"""Counterfactual value contracts for adaptation-economy experiments.

The estimator consumes only information available before a structural decision.
Realized values are measured separately by paired executions with mutation enabled
and disabled from equivalent initial conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CounterfactualFeatures:
    """Decision-time features shared by candidate and no-op estimates."""

    workload_id: str
    task_count: int
    mean_complexity: float
    fault_rate: float
    shift_rate: float
    constraint_rate: float
    composition_rate: float
    current_unit_count: int
    expected_mutation_cost: float


@dataclass(frozen=True)
class CounterfactualPrediction:
    """Predicted quality of preserving and mutating the current structure."""

    v_no_op: float
    v_mutation: float

    @property
    def delta_v(self) -> float:
        return self.v_mutation - self.v_no_op


class CounterfactualValueEstimator(Protocol):
    """Estimator boundary; learned estimators can replace the reference model."""

    @property
    def estimator_id(self) -> str: ...

    def predict(self, features: CounterfactualFeatures) -> CounterfactualPrediction: ...


class EvidenceValueEstimator:
    """Transparent pre-decision baseline derived from observable necessity evidence.

    This is intentionally a baseline rather than a claim of a calibrated learned
    model. Unlike the former campaign constants, each estimate varies with the
    actual workload observations and anticipated structural cost.
    """

    estimator_id = "evidence-value-v1"

    def predict(self, features: CounterfactualFeatures) -> CounterfactualPrediction:
        complexity_pressure = max(0.0, (features.mean_complexity - 5.0) / 10.0)
        capacity_pressure = max(
            0.0,
            (features.mean_complexity - (5.0 * features.current_unit_count)) / 10.0,
        )
        evidence = min(
            1.0,
            0.35 * features.fault_rate
            + 0.35 * features.shift_rate
            + 0.20 * features.constraint_rate
            + 0.30 * features.composition_rate
            + 0.10 * complexity_pressure
            + 0.15 * capacity_pressure,
        )
        base = max(0.0, min(1.0, 0.86 - 0.10 * evidence))
        mutation_gain = 0.24 * evidence
        mutation_cost = min(0.25, max(0.0, features.expected_mutation_cost))
        return CounterfactualPrediction(
            v_no_op=base,
            v_mutation=max(0.0, min(1.0, base + mutation_gain - mutation_cost)),
        )


def features_from_tasks(
    workload_id: str,
    tasks: list[dict[str, object]],
    *,
    current_unit_count: int = 0,
    expected_mutation_cost: float = 0.02,
) -> CounterfactualFeatures:
    """Build reproducible decision-time features from generated task observations."""

    count = max(1, len(tasks))
    return CounterfactualFeatures(
        workload_id=workload_id,
        task_count=len(tasks),
        mean_complexity=sum(float(task.get("complexity", 0.0)) for task in tasks) / count,
        fault_rate=sum(bool(task.get("fault_injected", False)) for task in tasks) / count,
        shift_rate=sum(bool(task.get("shift", False)) for task in tasks) / count,
        constraint_rate=sum(
            bool(task.get("constraint_violation", False))
            or ("budget" in task and float(task["budget"]) < float(task.get("complexity", 0.0)))
            for task in tasks
        )
        / count,
        composition_rate=sum(bool(task.get("require_composition", False)) for task in tasks)
        / count,
        current_unit_count=current_unit_count,
        expected_mutation_cost=expected_mutation_cost,
    )
