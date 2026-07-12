"""Cost semantics: resource accounting, budget enforcement, and forecast.

Per cost-semantics.md and INV-COST-1 through INV-COST-8:
- Tracks resource consumption per step and per module type
- Enforces budget limits with staged checkpoint protocol (INV-COST-8)
- Forecasts resource exhaustion and triggers replanning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from dnc.runtime.types import ModuleInstanceID


@dataclass
class CostBudget:
    """Per-module and per-execution cost budgets.

    Per cost-semantics.md: cost accounting tracks resource consumption
    at step granularity.
    """
    total_budget: float = 100.0
    consumed: float = 0.0
    per_module_budgets: Dict[ModuleInstanceID, float] = field(default_factory=dict)

    @property
    def remaining(self) -> float:
        return self.total_budget - self.consumed

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

    def charge(self, module_id: ModuleInstanceID, cost: float) -> bool:
        """Charge a cost to the budget. Returns True if within budget."""
        self.consumed += cost
        if module_id not in self.per_module_budgets:
            self.per_module_budgets[module_id] = cost
        else:
            self.per_module_budgets[module_id] += cost
        return not self.is_exhausted

    def forecast_exhaustion(self, avg_step_cost: float) -> Optional[float]:
        """Return estimated step count until budget exhaustion, or None if unlimited."""
        if avg_step_cost <= 0:
            return None
        return self.remaining / avg_step_cost


class CostForecaster:
    """Per INV-COST-6: forecasts resource exhaustion and triggers replan."""

    def __init__(self, budget: CostBudget) -> None:
        self._budget = budget
        self._step_costs: list = []
        self._replan_threshold: float = 0.2

    def record_step(self, cost: float) -> None:
        """Record the cost of a step for forecasting."""
        self._step_costs.append(cost)
        if len(self._step_costs) > 100:
            self._step_costs.pop(0)

    def avg_step_cost(self) -> float:
        if not self._step_costs:
            return 0.0
        return sum(self._step_costs) / len(self._step_costs)

    def should_trigger_replan(self) -> bool:
        """Per INV-REPLAN-4: forecast triggers replan when exhaustion is imminent."""
        avg = self.avg_step_cost()
        if avg <= 0:
            return False
        steps_remaining = self._budget.forecast_exhaustion(avg)
        if steps_remaining is None:
            return False
        if steps_remaining < self._replan_threshold * self._budget.total_budget:
            return True
        return False

    def set_replan_threshold(self, fraction: float) -> None:
        """Set the fraction of budget remaining that triggers replan warning."""
        self._replan_threshold = fraction


class StagedCheckpointBudget:
    """Per INV-COST-8: staged checkpoint protocol.

    Budget consumption is staged: checkpoints are taken at cost milestones
    to ensure state is preserved before resource exhaustion.
    """

    def __init__(self, budget: CostBudget) -> None:
        self._budget = budget
        self._stages = [0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
        self._triggered_stages: set = set()

    def check_stage(self) -> Optional[float]:
        """Return the current budget fraction consumed. None if no new stage reached."""
        fraction = self._budget.consumed / self._budget.total_budget if self._budget.total_budget > 0 else 0.0
        for stage in self._stages:
            if fraction >= stage and stage not in self._triggered_stages:
                self._triggered_stages.add(stage)
                return stage
        return None

    def reset(self) -> None:
        """Reset stage tracking. Called after replan."""
        self._triggered_stages = set()