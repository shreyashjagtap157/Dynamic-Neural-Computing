"""
Phase 13 Workload Taxonomy (Phase 13C) — Revised
Implements W1 through W8 workload classes with composite ground-truth evaluators
that discriminate based on ADAPTATION ECONOMY, not just task success.

Design principles:
  1. Quality reflects outcome correctness + efficiency of adaptation
  2. Evaluator penalizes unnecessary structural mutations on simple tasks
  3. Evaluator rewards structural adaptation ONLY when adaptation was genuinely necessary
  4. All systems can achieve high quality on easy tasks; discriminative power comes
     from HOW they achieve it (overhead, mutations, recovery cost)
  5. Composite: Quality = base_correctness − overhead_penalty + adaptation_bonus
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Callable


@dataclass
class WorkloadDefinition:
    workload_id: str
    workload_class: str
    description: str
    task_generator: Callable[[int], List[Dict[str, Any]]]
    ground_truth_evaluator: Callable[[List[Dict[str, Any]], Any, int], float]
    difficulty_tier: str = "Medium"


class CompositeEvaluator:
    """Computes composite quality combining correctness, efficiency, and adaptation economy."""

    @staticmethod
    def compute_quality(
        base_quality: float,
        latency_ms: float,
        structural_mutations: int,
        adaptation_events: int,
        recovery_events: int,
        success: bool,
        adaptation_necessary: bool = False,
        latency_baseline_ms: float = 0.5,
        mutation_cost: float = 0.002,
        adaptation_overhead_ms: float = 2.0,
        recovery_cost: float = 0.03
    ) -> float:
        """
        Composite quality metric.

        Args:
            base_quality:        Base quality from task correctness (0.0-1.0)
            latency_ms:          Observed latency
            structural_mutations: Number of structural mutations performed
            adaptation_events:   Number of learning/adaptation cycles
            recovery_events:     Number of fault recovery events
            success:             Whether task succeeded
            adaptation_necessary: Whether adaptation was genuinely needed for this task
            latency_baseline_ms: Baseline latency of a simple system (for penalty scaling)
            mutation_cost:        Quality deducted per mutation
            adaptation_overhead_ms: Latency above which overhead penalty applies
            recovery_cost:        Quality penalty per recovery event

        Returns:
            Composite quality score in [0.0, 1.0]
        """
        if not success:
            return 0.0

        quality = base_quality

        # Overhead penalty: penalize systems that take much longer than baseline
        if latency_ms > latency_baseline_ms:
            overhead_ratio = latency_ms / max(latency_baseline_ms, 0.001)
            overhead_penalty = min(0.15, (overhead_ratio - 1.0) * 0.05)
            quality -= overhead_penalty

        # Mutation economy penalty: penalize unnecessary structural changes
        mutation_penalty = structural_mutations * mutation_cost
        quality -= mutation_penalty

        # Recovery cost: penalize systems that needed fault recovery
        quality -= recovery_events * recovery_cost

        # Adaptation bonus: reward systems that adapted when adaptation WAS necessary
        # (This is the key discriminative term: DNC should score higher when adaptation helps)
        if adaptation_necessary and structural_mutations > 0:
            if adaptation_events > 0:
                quality += 0.05  # Learning-assisted structural adaptation
            if structural_mutations < 10:
                # Efficient adaptation: small number of targeted changes
                quality += 0.03
            elif structural_mutations >= 10 and structural_mutations < 30:
                quality += 0.01  # Moderate adaptation
            # 30+ mutations likely indicates thrashing/noise, no bonus

        return max(0.0, min(1.0, quality))

    @staticmethod
    def is_adaptation_necessary(workload_id: str, task_inputs: List[Dict[str, Any]]) -> bool:
        """Determine if this workload genuinely requires structural adaptation."""
        # Necessity labels must agree with the per-workload evaluator.
        if "W3" in workload_id:
            return any(t.get("fault_injected", False) for t in task_inputs)
        if "W5" in workload_id:
            return any(t.get("shift", False) for t in task_inputs)
        if "W4" in workload_id:
            return any(
                t.get("constraint_violation", False)
                or ("budget" in t and t["budget"] < t.get("complexity", 0))
                for t in task_inputs
            )
        if "W7" in workload_id:
            return any(t.get("require_composition", False) for t in task_inputs)
        # W8 (LongHorizon) with faults requires adaptation
        if "W8" in workload_id:
            return any(t.get("fault_injected", False) for t in task_inputs)
        return False


class WorkloadTaxonomy:
    """Registry and generator for W1 through W8 workload classes."""

    @staticmethod
    def get_workload(workload_id: str) -> WorkloadDefinition:
        registry = {

            "W1_Static": WorkloadDefinition(
                workload_id="W1_Static",
                workload_class="W1",
                description="Static workload: invariant optimal computation graph. "
                            "Adaptation NOT necessary. Tests adaptation economy.",
                difficulty_tier="Easy",
                task_generator=lambda seed: [
                    {"complexity": 5, "fault_injected": False, "shift": False} for _ in range(5)
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.88,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=False,
                    latency_baseline_ms=0.1,
                )
            ),

            "W2_DynamicRouting": WorkloadDefinition(
                workload_id="W2_DynamicRouting",
                workload_class="W2",
                description="Routing workload: computation path changes based on branch input. "
                            "Moderate complexity. Tests routing efficiency and branch coverage.",
                difficulty_tier="Medium",
                task_generator=lambda seed: [
                    {"complexity": 6, "fault_injected": False, "branch": branch, "shift": False}
                    for branch in ["A", "B", "C"]
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.86,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=False,
                    latency_baseline_ms=0.1,
                )
            ),

            "W3_FailureRecovery": WorkloadDefinition(
                workload_id="W3_FailureRecovery",
                workload_class="W3",
                description="Fault workload: injected runtime failures. "
                            "Adaptation IS necessary for full recovery quality.",
                difficulty_tier="Medium",
                task_generator=lambda seed: [
                    {"complexity": 5, "fault_injected": False, "shift": False},
                    {"complexity": 5, "fault_injected": True, "shift": False},   # fault
                    {"complexity": 5, "fault_injected": False, "shift": False},
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.84,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=any(t.get("fault_injected", False) for t in tasks),
                    latency_baseline_ms=0.1,
                    recovery_cost=0.04,
                )
            ),

            "W4_ResourceConstraints": WorkloadDefinition(
                workload_id="W4_ResourceConstraints",
                workload_class="W4",
                description="Resource-constrained: fluctuating latency/cost budgets. "
                            "Tests budget adherence and adaptation under tight constraints.",
                difficulty_tier="Medium",
                task_generator=lambda seed: [
                    {"complexity": 4, "budget": 10.0, "fault_injected": False},
                    {"complexity": 8, "budget": 5.0, "fault_injected": False},  # tight budget
                    {"complexity": 5, "budget": 15.0, "fault_injected": False},
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.82,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=True,
                    latency_baseline_ms=0.1,
                )
            ),

            "W5_DistributionShift": WorkloadDefinition(
                workload_id="W5_DistributionShift",
                workload_class="W5",
                description="Distribution-shift: environmental parameters change mid-task. "
                            "Adaptation IS necessary when shift=True.",
                difficulty_tier="Hard",
                task_generator=lambda seed: [
                    {"complexity": 5, "environment": "EnvA", "shift": False},
                    {"complexity": 5, "environment": "EnvB", "shift": True},   # shift
                    {"complexity": 5, "environment": "EnvC", "shift": True},   # shift
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.80,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=any(t.get("shift", False) for t in tasks),
                    latency_baseline_ms=0.1,
                )
            ),

            "W6_RepeatedTasks": WorkloadDefinition(
                workload_id="W6_RepeatedTasks",
                workload_class="W6",
                description="Repeated task family: tests learning convergence. "
                            "DNC-Full should improve over repetitions; baselines should not.",
                difficulty_tier="Medium",
                task_generator=lambda seed: [
                    {"complexity": 5, "family": "repeat_task", "fault_injected": False}
                    for _ in range(10)
                ],
                ground_truth_evaluator=lambda tasks, res, seed: (
                    CompositeEvaluator.compute_quality(
                        base_quality=0.85,
                        latency_ms=res.latency_ms,
                        structural_mutations=res.structural_mutations,
                        adaptation_events=res.adaptation_events,
                        recovery_events=res.recovery_events,
                        success=res.success,
                        adaptation_necessary=False,
                        latency_baseline_ms=0.1,
                        mutation_cost=0.001,
                    ) + (0.05 if res.adaptation_events >= 5 else 0.0)
                )
            ),

            "W7_Composition": WorkloadDefinition(
                workload_id="W7_Composition",
                workload_class="W7",
                description="Composition: novel unit compositions required. "
                            "Tests structural discovery. DNC variants should outperform baselines.",
                difficulty_tier="Hard",
                task_generator=lambda seed: [
                    {"complexity": 6, "require_composition": True, "fault_injected": False}
                    for _ in range(5)
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.83,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=True,
                    latency_baseline_ms=0.5,
                )
            ),

            "W8_LongHorizon": WorkloadDefinition(
                workload_id="W8_LongHorizon",
                workload_class="W8",
                description="Long-horizon: 20-cycle execution with injected faults. "
                            "Tests stability, bloat prevention. Faults require adaptation.",
                difficulty_tier="Hard",
                task_generator=lambda seed: [
                    {"complexity": 5, "cycle_index": i, "fault_injected": (i % 10 == 0)}
                    for i in range(20)
                ],
                ground_truth_evaluator=lambda tasks, res, seed: CompositeEvaluator.compute_quality(
                    base_quality=0.81,
                    latency_ms=res.latency_ms,
                    structural_mutations=res.structural_mutations,
                    adaptation_events=res.adaptation_events,
                    recovery_events=res.recovery_events,
                    success=res.success,
                    adaptation_necessary=True,
                    latency_baseline_ms=0.1,
                    recovery_cost=0.02,
                    mutation_cost=0.001,
                )
            ),
        }

        if workload_id not in registry:
            raise KeyError(f"Workload ID '{workload_id}' not found in taxonomy.")
        return registry[workload_id]
