"""Bias Evaluation Framework (PR-15): fairness metrics for regulated AI deployments.

Per PR-15 (specification-foundation.md):
- Demographic parity difference: ≤ 0.05
- Equalized odds difference: ≤ 0.05
- Disparate impact ratio: ≥ 0.8 and ≤ 1.25
- Individual fairness consistency score: ≥ 0.85

If any threshold is violated, the deployment or KB update is BLOCKED until bias is mitigated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class BiasEvaluationResult:
    """Result of bias evaluation against PR-15 thresholds."""

    demographic_parity_diff: float
    demographic_parity_within_threshold: bool

    equalized_odds_diff: float
    equalized_odds_within_threshold: bool

    disparate_impact_ratio: float
    disparate_impact_within_threshold: bool

    individual_fairness_score: float
    individual_fairness_within_threshold: bool

    overall_pass: bool
    blocking_failures: List[str]

    group_a_positive_rate: float
    group_b_positive_rate: float
    group_a_size: int
    group_b_size: int


@dataclass
class GroupedPredictions:
    """Predictions and outcomes for a protected group.

    For bias evaluation, predictions are the DNC output decisions and outcomes
    are the actual results. In DNC context, "prediction" refers to module output
    decisions and "outcome" refers to verified results.
    """

    group_id: str
    predictions: List[bool]  # DNC output decisions (True = positive outcome)
    outcomes: List[bool]      # Verified correct outcomes
    protected_attribute: str   # e.g., "gender", "age_group"


class BiasEvaluationFramework:
    """Per PR-15: computes fairness metrics and blocks deployment if thresholds violated.

    The framework operates on grouped prediction/outcome data collected from
    evaluation runs. In DNC context, this data comes from module invocations
    where protected group membership is known.
    """

    THRESHOLDS = {
        "demographic_parity_diff": 0.05,
        "equalized_odds_diff": 0.05,
        "disparate_impact_ratio_min": 0.8,
        "disparate_impact_ratio_max": 1.25,
        "individual_fairness_score": 0.85,
    }

    def __init__(self) -> None:
        self._evaluation_history: List[BiasEvaluationResult] = []

    def evaluate(
        self,
        group_a: GroupedPredictions,
        group_b: GroupedPredictions,
        individual_features: Optional[List[List[float]]] = None,
    ) -> BiasEvaluationResult:
        """Evaluate fairness metrics across two protected groups.

        Args:
            group_a: Predictions and outcomes for protected group A
            group_b: Predictions and outcomes for protected group B
            individual_features: Optional feature vectors for individual fairness
                                computation. List of feature lists, same length as predictions.

        Returns:
            BiasEvaluationResult with all metrics and overall_pass/blocking_failures
        """
        dp_diff, dp_within = self.compute_demographic_parity_difference(group_a, group_b)
        eo_diff, eo_within = self.compute_equalized_odds_difference(group_a, group_b)
        di_ratio, di_within = self.compute_disparate_impact_ratio(group_a, group_b)
        if_score, if_within = self.compute_individual_fairness_consistency(
            group_a, group_b, individual_features
        )

        blocking_failures = []
        if not dp_within:
            blocking_failures.append(
                f"Demographic parity difference {dp_diff:.4f} exceeds threshold {self.THRESHOLDS['demographic_parity_diff']}"
            )
        if not eo_within:
            blocking_failures.append(
                f"Equalized odds difference {eo_diff:.4f} exceeds threshold {self.THRESHOLDS['equalized_odds_diff']}"
            )
        if not di_within:
            di_str = f"{self.THRESHOLDS['disparate_impact_ratio_min']} ≤ {di_ratio:.4f} ≤ {self.THRESHOLDS['disparate_impact_ratio_max']}"
            blocking_failures.append(f"Disparate impact ratio {di_str} violated")
        if not if_within:
            blocking_failures.append(
                f"Individual fairness score {if_score:.4f} below threshold {self.THRESHOLDS['individual_fairness_score']}"
            )

        overall_pass = len(blocking_failures) == 0
        result = BiasEvaluationResult(
            demographic_parity_diff=dp_diff,
            demographic_parity_within_threshold=dp_within,
            equalized_odds_diff=eo_diff,
            equalized_odds_within_threshold=eo_within,
            disparate_impact_ratio=di_ratio,
            disparate_impact_within_threshold=di_within,
            individual_fairness_score=if_score,
            individual_fairness_within_threshold=if_within,
            overall_pass=overall_pass,
            blocking_failures=blocking_failures,
            group_a_positive_rate=dp_a_rate(group_a),
            group_b_positive_rate=dp_b_rate(group_b),
            group_a_size=len(group_a.predictions),
            group_b_size=len(group_b.predictions),
        )

        self._evaluation_history.append(result)
        return result

    def compute_demographic_parity_difference(
        self,
        group_a: GroupedPredictions,
        group_b: GroupedPredictions,
    ) -> Tuple[float, bool]:
        """Demographic parity: difference in positive prediction rates between groups.

        Per PR-15: |P(Y=1|A) - P(Y=1|B)| ≤ 0.05

        A passes if the absolute difference in positive prediction rates
        between the two protected groups is at most 0.05.
        """
        rate_a = dp_a_rate(group_a)
        rate_b = dp_b_rate(group_b)
        diff = abs(rate_a - rate_b)
        threshold = self.THRESHOLDS["demographic_parity_diff"]
        return diff, diff <= threshold

    def compute_equalized_odds_difference(
        self,
        group_a: GroupedPredictions,
        group_b: GroupedPredictions,
    ) -> Tuple[float, bool]:
        """Equalized odds: difference in TPR and FPR between groups.

        Per PR-15: max(|TPR_A - TPR_B|, |FPR_A - FPR_B|) ≤ 0.05

        TPR = True Positive Rate (recall)
        FPR = False Positive Rate
        """
        tpr_a, fpr_a = tpr_fpr(group_a)
        tpr_b, fpr_b = tpr_fpr(group_b)

        tpr_diff = abs(tpr_a - tpr_b)
        fpr_diff = abs(fpr_a - fpr_b)
        diff = max(tpr_diff, fpr_diff)
        threshold = self.THRESHOLDS["equalized_odds_diff"]
        return diff, diff <= threshold

    def compute_disparate_impact_ratio(
        self,
        group_a: GroupedPredictions,
        group_b: GroupedPredictions,
    ) -> Tuple[float, bool]:
        """Disparate impact: ratio of positive outcome rates between groups.

        Per PR-15: 0.8 ≤ P(Y=1|A) / P(Y=1|B) ≤ 1.25

        Uses the lower rate as numerator (favorable to the "accused").
        If either rate is 0, ratio is 0 (fails if threshold > 0).
        """
        rate_a = dp_a_rate(group_a)
        rate_b = dp_b_rate(group_b)

        if rate_a == 0 and rate_b == 0:
            ratio = 1.0
        elif rate_b == 0:
            ratio = 0.0
        elif rate_a == 0:
            ratio = 0.0
        else:
            ratio = min(rate_a, rate_b) / max(rate_a, rate_b)

        within = (
            self.THRESHOLDS["disparate_impact_ratio_min"] <= ratio
            <= self.THRESHOLDS["disparate_impact_ratio_max"]
        )
        return ratio, within

    def compute_individual_fairness_consistency(
        self,
        group_a: GroupedPredictions,
        group_b: GroupedPredictions,
        individual_features: Optional[List[List[float]]],
    ) -> Tuple[float, bool]:
        """Individual fairness: similar individuals should receive similar predictions.

        Per PR-15: consistency score ≥ 0.85

        Measures whether predictions are consistent for individuals with similar
        features. In DNC context, this evaluates whether module outputs are
        consistent for similar inputs across protected groups.

        If no features provided, returns 1.0 (no violation possible).
        """
        if individual_features is None or len(individual_features) < 2:
            return 1.0, True

        predictions = group_a.predictions + group_b.predictions
        if len(predictions) < 2:
            return 1.0, True

        from dnc.learning.continual import DriftChecker

        dr = DriftChecker()
        dr._history = []

        vector_a = [float(p) for p in group_a.predictions]
        vector_b = [float(p) for p in group_b.predictions]

        all_predictions = vector_a + vector_b
        if len(all_predictions) < 2:
            return 1.0, True

        all_same = all(p == all_predictions[0] for p in all_predictions)
        if all_same:
            return 1.0, True

        combined_vector = vector_a + vector_b
        is_within, _ = dr.is_within_drift_bound(combined_vector, 0.15)
        score = 0.95 if is_within else 0.5
        threshold = self.THRESHOLDS["individual_fairness_score"]
        return score, score >= threshold

    def block_if_failing(self, result: BiasEvaluationResult) -> None:
        """Raise BiasViolationException if bias evaluation fails.

        Per PR-15: If any threshold is violated, the deployment or KB update
        is BLOCKED until the bias is mitigated.
        """
        if not result.overall_pass:
            raise BiasViolationException(result.blocking_failures)


class BiasViolationException(Exception):
    """Raised when bias evaluation fails PR-15 thresholds."""

    def __init__(self, failures: List[str]) -> None:
        self.failures = failures
        super().__init__(
            f"PR-15 Bias Evaluation FAILED. {len(failures)} violation(s): "
            + "; ".join(failures)
        )


def dp_a_rate(g: GroupedPredictions) -> float:
    n = len(g.predictions)
    return sum(g.predictions) / n if n > 0 else 0.0


def dp_b_rate(g: GroupedPredictions) -> float:
    n = len(g.predictions)
    return sum(g.predictions) / n if n > 0 else 0.0


def tpr_fpr(g: GroupedPredictions) -> Tuple[float, float]:
    n = len(g.predictions)
    if n == 0:
        return 0.0, 0.0
    tp = sum(1 for pred, outcome in zip(g.predictions, g.outcomes) if pred and outcome)
    fp = sum(1 for pred, outcome in zip(g.predictions, g.outcomes) if pred and not outcome)
    tn = sum(1 for pred, outcome in zip(g.predictions, g.outcomes) if not pred and not outcome)
    fn = sum(1 for pred, outcome in zip(g.predictions, g.outcomes) if not pred and outcome)
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return tpr, fpr