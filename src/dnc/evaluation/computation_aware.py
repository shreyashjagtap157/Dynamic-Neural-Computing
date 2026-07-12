"""Computation-Aware Evaluation: measuring intelligence of computation allocation.

Per evaluation-framework.md: Computation-Aware Evaluation measures not just what answer
was produced, but what execution path, resources, adaptations, and recovery behaviors
produced it. This is the core research contribution of DNC.

The framework defines four metric levels:
- Level 0 (Infrastructure): latency, tokens, memory, cost
- Level 1 (Execution): graph depth, width, parallelism, replans, rollbacks
- Level 2 (Adaptivity): DCI, CCG, Budget Elasticity, Graph Entropy, Planning Stability
- Level 3 (Outcome): accuracy, verifier score, human preference

Per evaluation-framework.md Section 2.B: Level 2 metrics MUST NOT be computed from
Level 3 metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import math


@dataclass(frozen=True)
class Level0Metrics:
    """Per evaluation-framework.md Section 2.C: Level 0 Infrastructure metrics."""

    total_latency_ms: float
    total_tokens: int
    peak_memory_bytes: int
    estimated_cost_usd: float


@dataclass(frozen=True)
class Level1Metrics:
    """Per evaluation-framework.md Section 2.C: Level 1 Execution metrics."""

    graph_depth: int
    graph_width: int
    avg_parallelism: float
    replan_count: int
    rollback_count: int
    total_steps: int


@dataclass(frozen=True)
class Level2Metrics:
    """Per evaluation-framework.md Section 2.C: Level 2 Adaptivity metrics (research contribution).

    These metrics measure how intelligently computation was allocated, not whether
    the answer is correct (that's Level 3).
    """

    dynamic_compute_index: float
    counterfactual_compute_gain: float
    budget_elasticity: float
    graph_entropy: float
    planning_stability: float
    tool_diversity: float

    @property
    def dci(self) -> float:
        return self.dynamic_compute_index

    @property
    def ccg(self) -> float:
        return self.counterfactual_compute_gain


@dataclass(frozen=True)
class Level3Metrics:
    """Per evaluation-framework.md Section 2.C: Level 3 Outcome metrics."""

    accuracy: Optional[float] = None
    verifier_score: Optional[float] = None
    human_preference: Optional[float] = None
    benchmark_score: Optional[float] = None


@dataclass
class ComputationReport:
    """Full computation-aware evaluation report."""

    level0: Level0Metrics
    level1: Level1Metrics
    level2: Level2Metrics
    level3: Optional[Level3Metrics] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level0": {
                "total_latency_ms": self.level0.total_latency_ms,
                "total_tokens": self.level0.total_tokens,
                "peak_memory_bytes": self.level0.peak_memory_bytes,
                "estimated_cost_usd": self.level0.estimated_cost_usd,
            },
            "level1": {
                "graph_depth": self.level1.graph_depth,
                "graph_width": self.level1.graph_width,
                "avg_parallelism": self.level1.avg_parallelism,
                "replan_count": self.level1.replan_count,
                "rollback_count": self.level1.rollback_count,
                "total_steps": self.level1.total_steps,
            },
            "level2": {
                "dynamic_compute_index": self.level2.dynamic_compute_index,
                "counterfactual_compute_gain": self.level2.counterfactual_compute_gain,
                "budget_elasticity": self.level2.budget_elasticity,
                "graph_entropy": self.level2.graph_entropy,
                "planning_stability": self.level2.planning_stability,
                "tool_diversity": self.level2.tool_diversity,
            },
            "recommendations": self.recommendations,
        }


class ComputationMonitor:
    """Computes computation-aware evaluation metrics from ExecutionTrace data.

    Per evaluation-framework.md Section 2.A: The computation monitor takes an execution
    trace and produces metrics at all four levels. Level 2 (Adaptivity) is the novel
    research contribution.
    """

    def evaluate(self, trace: Any, baseline: Optional[ComputationReport] = None) -> ComputationReport:
        """Compute all four levels of metrics from an ExecutionTrace.

        Args:
            trace: ExecutionTrace (per execution-trace-format.md)
            baseline: Optional baseline ComputationReport for DCI normalization

        Returns:
            ComputationReport with Level 0-3 metrics
        """
        level0 = self._compute_level0(trace)
        level1 = self._compute_level1(trace)
        level2 = self._compute_level2(trace, baseline)
        level3 = self._compute_level3(trace)

        recommendations = self._generate_recommendations(level0, level1, level2, level3)

        return ComputationReport(
            level0=level0,
            level1=level1,
            level2=level2,
            level3=level3,
            recommendations=recommendations,
        )

    def _compute_level0(self, trace: Any) -> Level0Metrics:
        """Compute Level 0 Infrastructure metrics."""
        total_latency = 0.0
        total_tokens = 0
        peak_memory = 0
        total_cost = 0.0

        for record in trace.execution_record:
            for invocation in record.module_invocations:
                total_latency += invocation.latency_ms
                if invocation.tokens_used is not None:
                    total_tokens += invocation.tokens_used
                if getattr(invocation, 'cost_usd', None) is not None:
                    total_cost += invocation.cost_usd

            if record.resource_usage is not None:
                mem = getattr(record.resource_usage, 'memory_bytes', 0) or 0
                if mem > peak_memory:
                    peak_memory = mem

        return Level0Metrics(
            total_latency_ms=total_latency,
            total_tokens=total_tokens,
            peak_memory_bytes=peak_memory,
            estimated_cost_usd=total_cost,
        )

    def _compute_level1(self, trace: Any) -> Level1Metrics:
        """Compute Level 1 Execution metrics."""
        replan_count = 0
        rollback_count = 0

        for record in trace.execution_record:
            d = record.decision.decision
            if d == "REPLAN":
                replan_count += 1
            elif d == "ROLLBACK":
                rollback_count += 1

        total_steps = len(trace.execution_record)
        graph_depth = self._estimate_graph_depth(trace)
        graph_width = self._estimate_graph_width(trace)
        avg_parallelism = self._estimate_avg_parallelism(trace)

        return Level1Metrics(
            graph_depth=graph_depth,
            graph_width=graph_width,
            avg_parallelism=avg_parallelism,
            replan_count=replan_count,
            rollback_count=rollback_count,
            total_steps=total_steps,
        )

    def _compute_level2(
        self,
        trace: Any,
        baseline: Optional[ComputationReport] = None,
    ) -> Level2Metrics:
        """Compute Level 2 Adaptivity metrics (per evaluation-framework.md Section 3)."""
        dci = self._compute_dci(trace, baseline)
        ccg = self._compute_ccg(trace)
        budget_elasticity = self._compute_budget_elasticity(trace)
        graph_entropy = self._compute_graph_entropy(trace)
        planning_stability = self._compute_planning_stability(trace)
        tool_diversity = self._compute_tool_diversity(trace)

        return Level2Metrics(
            dynamic_compute_index=dci,
            counterfactual_compute_gain=ccg,
            budget_elasticity=budget_elasticity,
            graph_entropy=graph_entropy,
            planning_stability=planning_stability,
            tool_diversity=tool_diversity,
        )

    def _compute_level3(self, trace: Any) -> Optional[Level3Metrics]:
        """Compute Level 3 Outcome metrics (if available in trace)."""
        return None

    def _compute_dci(
        self,
        trace: Any,
        baseline: Optional[ComputationReport] = None,
    ) -> float:
        """Per evaluation-framework.md MET-DCI-1: Dynamic Compute Index.

        DCI = (OutputQuality / ComputeBudgetSpent) / (BaselineQuality / BaselineBudget)

        Since we don't have OutputQuality (Level 3) here, we compute a proxy using
        task completion rate derived from termination_reason.
        """
        total_budget = trace.resource_budget
        if total_budget <= 0:
            return 0.0

        termination = trace.termination_reason
        task_completion_rate = 1.0 if termination and termination.name in (
            "ALL_MODULES_COMPLETE", "TERMINATE_DECISION"
        ) else 0.5

        compute_efficiency = task_completion_rate / total_budget

        if baseline is not None:
            baseline_budget = baseline.level0.estimated_cost_usd or 1.0
            baseline_quality = 1.0
            baseline_efficiency = baseline_quality / baseline_budget
            if baseline_efficiency > 0:
                return compute_efficiency / baseline_efficiency

        baseline_efficiency = 1.0 / 100.0
        return compute_efficiency / baseline_efficiency if baseline_efficiency > 0 else 0.0

    def _compute_ccg(self, trace: Any) -> float:
        """Per evaluation-framework.md MET-CCG-1: Counterfactual Compute Gain.

        CCG = Score(selected_graph) - Score(simplest_alternative)
        We estimate CCG from replan count and module complexity.
        """
        replans = sum(
            1 for r in trace.execution_record if r.decision.decision == "REPLAN"
        )
        module_count = sum(
            len(r.module_invocations) for r in trace.execution_record
        )

        if module_count == 0:
            return 0.0

        avg_modules_per_step = module_count / max(len(trace.execution_record), 1)
        ccg_estimate = (replans * 0.1) - (max(0, avg_modules_per_step - 1.5) * 0.05)
        return max(0.0, ccg_estimate)

    def _compute_budget_elasticity(self, trace: Any) -> float:
        """Per evaluation-framework.md MET-BE-1: Budget Elasticity.

        Budget elasticity measures how much output quality changes with budget.
        We estimate this from the ratio of used budget to initial budget.
        """
        initial = trace.resource_budget
        if initial <= 0:
            return 0.0

        total_spent = 0.0
        for r in trace.execution_record:
            if r.resource_usage is not None:
                br = getattr(r.resource_usage, "budget_remaining", None)
                if br is not None:
                    total_spent += br

        if total_spent <= 0:
            total_spent = initial * 0.5

        utilization = min(1.0, total_spent / initial)
        return utilization

    def _compute_graph_entropy(self, trace: Any) -> float:
        """Per evaluation-framework.md MET-GE-1: Graph Entropy.

        Graph entropy measures the diversity of execution paths.
        We measure this as the entropy of module type distribution.
        """
        module_types: Dict[str, int] = {}
        total = 0

        for record in trace.execution_record:
            for inv in record.module_invocations:
                mtype = getattr(inv, "module_type", "unknown")
                module_types[mtype] = module_types.get(mtype, 0) + 1
                total += 1

        if total == 0:
            return 0.0

        entropy = 0.0
        for count in module_types.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(module_types)) if module_types else 1.0
        if max_entropy == 0:
            return 0.0

        return entropy / max_entropy

    def _compute_planning_stability(self, trace: Any) -> float:
        """Per evaluation-framework.md MET-PS-1: Planning Stability.

        Planning stability measures consistency of graph synthesis.
        High stability = similar graphs across steps (good for convergence).
        Low stability = wildly varying graphs (may indicate instability).
        """
        replan_count = sum(
            1 for r in trace.execution_record if r.decision.decision == "REPLAN"
        )
        total_steps = len(trace.execution_record)

        if total_steps <= 1:
            return 1.0

        stability = 1.0 - (replan_count / total_steps)
        return max(0.0, min(1.0, stability))

    def _compute_tool_diversity(self, trace: Any) -> float:
        """Per evaluation-framework.md MET-TD-1: Tool Diversity.

        Tool diversity measures the distribution of module types used.
        Perfect diversity = equal distribution across all module types.
        """
        module_types: Set[str] = set()
        total = 0

        for record in trace.execution_record:
            for inv in record.module_invocations:
                mtype = getattr(inv, "module_type", "unknown")
                module_types.add(mtype)
                total += 1

        if total == 0 or len(module_types) == 0:
            return 0.0

        type_counts: Dict[str, int] = {}
        for record in trace.execution_record:
            for inv in record.module_invocations:
                mtype = getattr(inv, "module_type", "unknown")
                type_counts[mtype] = type_counts.get(mtype, 0) + 1

        counts = list(type_counts.values())
        n = len(counts)
        if n == 1:
            return 0.0

        ideal_count = sum(counts) / n
        variance = sum((c - ideal_count) ** 2 for c in counts) / n
        max_variance = (sum(counts) ** 2 - sum(c ** 2 for c in counts)) / (n * n)

        if max_variance == 0:
            return 0.0

        diversity = 1.0 - (variance / max_variance)
        return max(0.0, min(1.0, diversity))

    def _estimate_graph_depth(self, trace: Any) -> int:
        steps = len(trace.execution_record)
        return min(steps, 10)

    def _estimate_graph_width(self, trace: Any) -> int:
        max_width = 0
        for record in trace.execution_record:
            width = len(record.module_invocations)
            if width > max_width:
                max_width = width
        return max(1, max_width)

    def _estimate_avg_parallelism(self, trace: Any) -> float:
        if not trace.execution_record:
            return 0.0
        total = sum(len(r.module_invocations) for r in trace.execution_record)
        return total / len(trace.execution_record)

    def _generate_recommendations(
        self,
        level0: Level0Metrics,
        level1: Level1Metrics,
        level2: Level2Metrics,
        level3: Optional[Level3Metrics],
    ) -> List[str]:
        """Generate actionable recommendations based on computed metrics."""
        recs = []

        if level2.dci < 0.8:
            recs.append("DCI < 0.8: Compute budget underutilized — consider reducing budget or increasing task complexity")
        if level2.ccg < 0.05:
            recs.append("CCG < 0.05: Counterfactual compute gain low — graph complexity may not justify overhead")
        if level1.replan_count > level1.total_steps * 0.3:
            recs.append(f"High replan rate ({level1.replan_count}/{level1.total_steps}): Consider improving graph stability")
        if level2.graph_entropy < 0.3:
            recs.append("Low graph entropy: Execution paths lack diversity — may indicate over-specialization")
        if level2.planning_stability < 0.5:
            recs.append("Low planning stability: Graph synthesis varies significantly across steps")

        if not recs:
            recs.append("All computation-aware metrics within acceptable ranges")

        return recs