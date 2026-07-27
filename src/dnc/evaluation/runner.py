"""
Phase 13 Benchmark Infrastructure & Runner (Phase 13D & 13C)
Orchestrates experiment executions across systems and workloads with deterministic seeds.
"""

import random
import time
from typing import List, Dict, Any, Type
from dnc.evaluation.contracts import BenchmarkSystem, ExperimentResult
from dnc.evaluation.baselines.static_dag import StaticDAGSystem
from dnc.evaluation.baselines.replanner import ReplannerSystem
from dnc.evaluation.baselines.agentic_loop import AgenticLoopSystem
from dnc.evaluation.baselines.dnc_variants import DNCVariantSystem
from dnc.evaluation.workloads.taxonomy import WorkloadTaxonomy


class BenchmarkRunner:
    """Orchestrates benchmark runs across workloads, baselines, and DNC variants."""

    def __init__(self, repetitions: int = 3):
        self.repetitions = repetitions
        self.registered_systems: Dict[str, Type[BenchmarkSystem]] = {
            "StaticDAG": StaticDAGSystem,
            "Replanner": ReplannerSystem,
            "AgenticLoop": AgenticLoopSystem,
            "DNC_Full": lambda: DNCVariantSystem("DNC_Full", enable_learning=True, enable_mutation=True, enable_provenance=True),
            "DNC_L": lambda: DNCVariantSystem("DNC_L", enable_learning=False, enable_mutation=True, enable_provenance=True),
            "DNC_M": lambda: DNCVariantSystem("DNC_M", enable_learning=True, enable_mutation=False, enable_provenance=True),
            "DNC_P": lambda: DNCVariantSystem("DNC_P", enable_learning=True, enable_mutation=True, enable_provenance=False),
        }

    def run_workload_experiment(
        self,
        system_key: str,
        workload_id: str,
        base_seed: int = 42
    ) -> List[ExperimentResult]:
        """Run repetitions of an experiment for a given system and workload taxonomy definition."""
        workload_def = WorkloadTaxonomy.get_workload(workload_id)
        results: List[ExperimentResult] = []

        system_factory = self.registered_systems.get(system_key)
        if not system_factory:
            raise KeyError(f"System '{system_key}' not registered in BenchmarkRunner.")

        for rep in range(self.repetitions):
            seed = base_seed + rep
            random.seed(seed)

            # Generate workload task inputs deterministically from seed
            task_inputs = workload_def.task_generator(seed)

            # Instantiate system
            system = system_factory() if callable(system_factory) and not isinstance(system_factory, type) else system_factory()
            system.initialize(workload_id=workload_id, seed=seed, config={})

            # Execute workload task sequence
            for task_input in task_inputs:
                system.execute(task_input)

            result = system.get_result()
            # Apply ground truth evaluation
            result.task_quality = workload_def.ground_truth_evaluator(task_inputs, result, seed)
            results.append(result)
            system.shutdown()

        return results
