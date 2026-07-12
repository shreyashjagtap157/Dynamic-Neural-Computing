"""Evaluation suite: metric framework, evaluation protocol, and regression detection.

Per evaluation-suite.md DEF-EVAL-1 through DEF-EVAL-12, INV-EVAL-1 through INV-EVAL-15.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto


class MetricClass(Enum):
    CLASS_1_FUNCTIONAL = auto()
    CLASS_2_ADAPTABILITY = auto()
    CLASS_3_EFFICIENCY = auto()
    CLASS_4_LEARNING = auto()


class ResultClassification(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    TIE = "TIE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class MetricResult:
    metric_name: str
    metric_class: MetricClass
    dnc_value: float
    baseline_value: float
    p_value: float
    effect_size: float
    classification: ResultClassification


@dataclass
class EvaluationScenario:
    scenario_id: str
    task_class: str
    task_description: str
    input_distribution: str
    expected_output_spec: str
    baseline_implementations: List[str]
    success_criteria: str


@dataclass
class EvaluationRun:
    run_id: str
    scenario_id: str
    runtime_under_test: str
    baseline_ids: List[str]
    metric_results: List[MetricResult]
    timestamp: float
    statistical_analysis: Dict[str, Any]


class EvaluationStage(Enum):
    SMOKE = "SMOKE"
    INTEGRATION = "INTEGRATION"
    FULL = "FULL"
    ASYNC = "ASYNC"


@dataclass
class StagedEvaluationResult:
    stage: EvaluationStage
    trial_count: int
    metric_results: List[MetricResult]
    statistical_analysis: Dict[str, Any]
    pass_fail: bool
    blocking_decision: str
    next_stage_recommendation: Optional[EvaluationStage]


class EvaluationSuite:
    """Per evaluation-suite.md: metric framework and evaluation protocol.

    MIN_TRIAL_COUNT = 30 per INV-EVAL-2.
    Holm-Bonferroni correction per INV-EVAL-10.
    Staged evaluation per DEF-EVAL-9.
    """

    MIN_TRIAL_COUNT: int = 30
    DEGRADATION_TOLERANCE: float = 0.05
    NOVEL_TASK_SUCCESS_RATE: float = 0.60
    DRIFT_BOUND: float = 0.1

    def __init__(self) -> None:
        self._scenarios: Dict[str, EvaluationScenario] = {}
        self._history: List[EvaluationRun] = []

    def register_scenario(self, scenario: EvaluationScenario) -> None:
        self._scenarios[scenario.scenario_id] = scenario

    def compute_statistics(
        self,
        values: List[float],
        baseline_values: List[float],
    ) -> Tuple[float, float, float, float]:
        """Compute mean, std, p_value (Welch's t-test), and Cohen's d."""
        n = len(values)
        if n == 0:
            return 0.0, 0.0, 1.0, 0.0

        mean_val = sum(values) / n
        mean_base = sum(baseline_values) / len(baseline_values) if baseline_values else 0.0

        var_val = sum((v - mean_val) ** 2 for v in values) / max(n - 1, 1)
        std_val = math.sqrt(var_val)
        n_base = len(baseline_values)
        var_base = sum((v - mean_base) ** 2 for v in baseline_values) / max(n_base - 1, 1)
        std_base = math.sqrt(var_base)

        pooled_n = n + n_base
        if pooled_n > 0 and std_val + std_base > 0:
            cohens_d = (mean_val - mean_base) / ((std_val + std_base) / 2)
        else:
            cohens_d = 0.0

        t_stat = 0.0
        p_value = 1.0
        if std_val > 0 and std_base > 0 and n > 1 and n_base > 1:
            se = math.sqrt((std_val ** 2 / n) + (std_base ** 2 / n_base))
            if se > 0:
                t_stat = (mean_val - mean_base) / se
                p_value = self._approximate_p(t_stat, n + n_base - 2)

        return mean_val, std_val, p_value, cohens_d

    def _approximate_p(self, t_stat: float, df: int) -> float:
        """Approximate p-value from t-statistic. Two-tailed test."""
        x = abs(t_stat)
        if x <= 0:
            return 1.0
        if df <= 0:
            df = max(1, int(2 * x))
        z = x / math.sqrt(1 + x ** 2 / df)
        p = math.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
        p = min(p * (1 + z ** 2 / df), 1.0)
        return max(0.0, min(1.0, 2 * p))

    def classify_result(self, p_value: float, effect_size: float) -> ResultClassification:
        """Per DEF-EVAL-4: WIN/LOSS/TIE based on statistical significance and effect size."""
        if p_value >= 0.05:
            return ResultClassification.TIE
        if effect_size > 0:
            return ResultClassification.WIN
        return ResultClassification.LOSS

    def holm_bonferroni(
        self,
        metric_results: List[MetricResult],
        alpha: float = 0.05,
    ) -> List[MetricResult]:
        """Per INV-EVAL-10: Holm-Bonferroni correction for multiple comparisons.
        Applied per metric class, not globally.
        """
        by_class: Dict[MetricClass, List[MetricResult]] = {}
        for mr in metric_results:
            if mr.metric_class not in by_class:
                by_class[mr.metric_class] = []
            by_class[mr.metric_class].append(mr)

        corrected = []
        for mclass, results in by_class.items():
            sorted_results = sorted(results, key=lambda r: r.p_value)
            k = len(sorted_results)
            for i, mr in enumerate(sorted_results):
                adjusted_p = min(mr.p_value * (k - i), 1.0)
                new_classification = self.classify_result(adjusted_p, mr.effect_size)
                new_mr = MetricResult(
                    metric_name=mr.metric_name,
                    metric_class=mr.metric_class,
                    dnc_value=mr.dnc_value,
                    baseline_value=mr.baseline_value,
                    p_value=adjusted_p,
                    effect_size=mr.effect_size,
                    classification=new_classification,
                )
                corrected.append(new_mr)

        return corrected

    def detect_regression(
        self,
        current: EvaluationRun,
        prior_results: Dict[str, Dict[str, ResultClassification]],
    ) -> List[Tuple[str, str, str]]:
        """Per DEF-EVAL-7: detect regressions (WIN/TIE → LOSS)."""
        regressions = []
        for mr in current.metric_results:
            scenario = current.scenario_id
            metric = mr.metric_name
            prior_class = prior_results.get(scenario, {}).get(metric, ResultClassification.TIE)

            if prior_class in (ResultClassification.WIN, ResultClassification.TIE) and \
               mr.classification == ResultClassification.LOSS:
                regressions.append((scenario, metric, prior_class.value))

        return regressions

    def stage_for_update(self, update_type: str) -> EvaluationStage:
        """Per DEF-EVAL-10: select verification stage based on update type."""
        stage_map = {
            "rollback": EvaluationStage.SMOKE,
            "parameter_tweak": EvaluationStage.SMOKE,
            "cost_estimate_change": EvaluationStage.SMOKE,
            "security_patch": EvaluationStage.SMOKE,
            "module_parameter_change": EvaluationStage.INTEGRATION,
            "graph_template_change": EvaluationStage.INTEGRATION,
            "new_module_type": EvaluationStage.FULL,
            "new_planner_algorithm": EvaluationStage.FULL,
            "new_module_added": EvaluationStage.FULL,
        }
        return stage_map.get(update_type, EvaluationStage.INTEGRATION)

    def degradation_within_tolerance(
        self,
        baseline_values: Dict[str, float],
        updated_values: Dict[str, float],
    ) -> bool:
        """Per INV-EVAL-4: check all metrics within DEGRADATION_TOLERANCE."""
        for metric, baseline in baseline_values.items():
            updated = updated_values.get(metric, baseline)
            if baseline == 0:
                if updated != 0:
                    return False
                continue
            ratio = abs(updated - baseline) / abs(baseline)
            if ratio > self.DEGRADATION_TOLERANCE:
                return False
        return True


@dataclass
class NovelTaskBenchmark:
    scenario_id: str
    task_description: str
    input_distribution: str
    expected_output_spec: str
    success_criteria: str
    baseline_implementations: List[str]


def get_canonical_novel_benchmarks() -> List[NovelTaskBenchmark]:
    """Per DEF-EVAL-8: the 10 canonical novel task benchmarks."""
    return [
        NovelTaskBenchmark(
            scenario_id="NOVEL-1",
            task_description="Unseen data type composition",
            input_distribution="Random combination of CIFAR-10 images and Wikipedia text",
            expected_output_spec="Fused embedding vectors normalized to [0,1]",
            success_criteria="DNC ≥ 70% accuracy vs baseline ≤ 55%",
            baseline_implementations=["StaticEmbedding", "FixedFusionPipeline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-2",
            task_description="Out-of-distribution constraint satisfaction",
            input_distribution="Randomly generated CSP instances with 10-50 variables",
            expected_output_spec="Valid assignment or proof of no assignment",
            success_criteria="DNC solves ≥ 80% of instances within 100ms",
            baseline_implementations=["FixedCSPBaseline", "HeuristicSearch"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-3",
            task_description="Cross-domain transfer reasoning",
            input_distribution="Logical analogy tasks with novel rule combinations",
            expected_output_spec="Correct answer choice from 8 options",
            success_criteria="DNC achieves ≥ 65% accuracy vs baseline ≤ 45%",
            baseline_implementations=["FixedReasoner", "Rule-basedBaseline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-4",
            task_description="Resource-constrained multi-objective optimization",
            input_distribution="Sequential multi-objective problems with hidden secondary objective",
            expected_output_spec="Pareto-optimal solution set",
            success_criteria="DNC within 10% of offline optimal vs baseline 40% gap",
            baseline_implementations=["StaticOptimizer", "FixedWeightBaseline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-5",
            task_description="Unseen failure recovery with partial KB",
            input_distribution="Synthetic problems with 20 unseen failure modes",
            expected_output_spec="Task completion despite failure",
            success_criteria="DNC ≥ 75% task completion vs baseline ≤ 30%",
            baseline_implementations=["FailoverBaseline", "NoReplanBaseline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-6",
            task_description="Novel modality fusion",
            input_distribution="Synthetic audio-depth pairs with novel pairings",
            expected_output_spec="Scene segmentation labels with ≥ 0.7 IoU",
            success_criteria="DNC achieves ≥ 0.72 IoU vs best baseline ≤ 0.61",
            baseline_implementations=["AudioOnly", "DepthOnly", "FixedFusion"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-7",
            task_description="Time-varying goal adaptation",
            input_distribution="Grid navigation with goal teleported at step 2",
            expected_output_spec="Path to final goal position",
            success_criteria="DNC total path ≤ 1.3x optimal vs baseline ≥ 2x",
            baseline_implementations=["StaticPlanner", "RestartPlanner"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-8",
            task_description="Adaptive query decomposition",
            input_distribution="Multi-hop reasoning queries with novel bridge types",
            expected_output_spec="Correct answer with supporting evidence",
            success_criteria="DNC achieves ≥ 68% accuracy vs baseline ≤ 52%",
            baseline_implementations=["FixedPipeline", "RetrievalBaseline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-9",
            task_description="Continual tool use with novel API",
            input_distribution="Tasks requiring a simulated web API with novel response schema",
            expected_output_spec="Correct task completion using the novel tool",
            success_criteria="DNC achieves ≥ 60% task completion vs baseline ≤ 25%",
            baseline_implementations=["NoToolBaseline", "FixedToolBaseline"],
        ),
        NovelTaskBenchmark(
            scenario_id="NOVEL-10",
            task_description="Conflicting constraint resolution",
            input_distribution="CSP with induced conflicts not in training",
            expected_output_spec="Conflict detection + optimal relaxation",
            success_criteria="DNC detects conflict in ≤ 3 steps within 10% of optimal",
            baseline_implementations=["RelaxBaseline", "ExactBaseline"],
        ),
    ]