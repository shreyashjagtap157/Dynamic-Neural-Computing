"""Deterministic shadow outcome, cost, and risk predictors."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.cognition.canonical import canonical_hash
from dnc.policy_learning.contracts import DecisionExample, Prediction


@dataclass
class TabularShadowPredictor:
    _predictions: dict[tuple[str, str], Prediction] = field(default_factory=dict)
    _global: Prediction = Prediction(0.0, 0.0, 1.0)
    training_hash: str = ""

    def fit(self, examples: tuple[DecisionExample, ...]) -> None:
        buckets: dict[tuple[str, str], list[DecisionExample]] = {}
        usable = [item for item in examples if not item.censored and item.corrected_outcome is not None]
        if not usable:
            raise ValueError("predictor requires uncensored outcome data")
        for example in usable:
            buckets.setdefault((example.context_key, example.selected_action_id), []).append(example)

        def aggregate(items: list[DecisionExample]) -> Prediction:
            return Prediction(
                sum(float(item.corrected_outcome) for item in items) / len(items),
                sum(float(item.realized_cost or 0) for item in items) / len(items),
                sum(float(item.constraint_violation) for item in items) / len(items),
            )

        self._predictions = {key: aggregate(items) for key, items in buckets.items()}
        self._global = aggregate(usable)
        self.training_hash = canonical_hash(usable, namespace="dnc.shadow-predictor.v1")

    def predict(self, context_key: str, action_id: str) -> Prediction:
        return self._predictions.get((context_key, action_id), self._global)

    @property
    def model_hash(self) -> str:
        return canonical_hash(
            {"predictions": self._predictions, "global": self._global},
            namespace="dnc.shadow-predictor.model.v1",
        )
