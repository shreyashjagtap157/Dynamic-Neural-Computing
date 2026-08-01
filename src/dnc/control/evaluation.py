"""Quality-cost-risk evaluation for semantic controller policies."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class ControllerTrial:
    task_id: str
    policy: str
    correct: bool
    authorized: bool
    traced: bool
    cost: float
    risk: float


@dataclass(frozen=True)
class ControllerEvaluation:
    count: int
    accuracy: float
    authorization_rate: float
    trace_rate: float
    average_cost: float
    average_risk: float


def evaluate_controller_trials(trials: tuple[ControllerTrial, ...]) -> ControllerEvaluation:
    if not trials:
        raise ValueError("controller evaluation requires trials")
    return ControllerEvaluation(
        len(trials),
        mean(trial.correct for trial in trials),
        mean(trial.authorized for trial in trials),
        mean(trial.traced for trial in trials),
        mean(trial.cost for trial in trials),
        mean(trial.risk for trial in trials),
    )


def compare_controller(
    controller: tuple[ControllerTrial, ...], baseline: tuple[ControllerTrial, ...]
) -> dict[str, float | bool]:
    controller_ids = {trial.task_id for trial in controller}
    baseline_ids = {trial.task_id for trial in baseline}
    if len(controller_ids) != len(controller) or len(baseline_ids) != len(baseline):
        raise ValueError("controller comparison task IDs MUST be unique")
    if controller_ids != baseline_ids:
        raise ValueError("controller comparison requires paired tasks")
    selected, reference = evaluate_controller_trials(controller), evaluate_controller_trials(baseline)
    return {
        "quality_delta": selected.accuracy - reference.accuracy,
        "cost_delta": selected.average_cost - reference.average_cost,
        "risk_delta": selected.average_risk - reference.average_risk,
        "authorization_complete": selected.authorization_rate == 1.0,
        "trace_complete": selected.trace_rate == 1.0,
        "pareto_improved": (
            selected.accuracy >= reference.accuracy
            and selected.average_cost <= reference.average_cost
            and selected.average_risk <= reference.average_risk
            and (
                selected.accuracy > reference.accuracy
                or selected.average_cost < reference.average_cost
                or selected.average_risk < reference.average_risk
            )
        ),
    }
