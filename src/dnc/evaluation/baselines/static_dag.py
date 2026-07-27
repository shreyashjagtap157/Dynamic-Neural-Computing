"""
Baseline A: Static DAG (Fixed Workflow)
Implements BenchmarkSystem for a static, non-adaptive execution graph.
"""

import time
from typing import Dict, Any, Optional
from dnc.evaluation.contracts import BenchmarkSystem, ExperimentResult


class StaticDAGSystem(BenchmarkSystem):
    """Static DAG baseline executing a fixed execution path without runtime adaptation."""

    def __init__(self, system_id: str = "Baseline_StaticDAG"):
        self.system_id = system_id
        self.workload_id = ""
        self.seed = 0
        self.config = {}
        self.start_time = 0.0
        self.end_time = 0.0
        self.steps_executed = 0
        self.success = False
        self.quality = 0.0
        self.cost = 0.0

    def initialize(self, workload_id: str, seed: int, config: Dict[str, Any]) -> None:
        self.workload_id = workload_id
        self.seed = seed
        self.config = config
        self.start_time = time.time()
        self.steps_executed = 0
        self.success = False
        self.quality = 0.0
        self.cost = config.get("base_cost", 1.0)

    def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        # Simulate fixed static DAG execution
        steps = task_input.get("complexity", 5)
        self.steps_executed += steps
        
        # Static systems fail if injected faults exceed static error tolerance
        fault_injected = task_input.get("fault_injected", False)
        if fault_injected and not self.config.get("static_fault_tolerance", False):
            self.success = False
            self.quality = 0.0
        else:
            self.success = True
            self.quality = 0.85  # Fixed static quality ceiling

        elapsed = (time.time() - start) * 1000.0
        self.end_time = time.time()
        return {"output": "static_result", "latency_ms": elapsed, "success": self.success}

    def observe(self) -> Dict[str, Any]:
        return {"units": 5, "edges": 4, "mutations": 0, "adaptation_active": False}

    def get_result(self) -> ExperimentResult:
        latency = (self.end_time - self.start_time) * 1000.0 if self.end_time > 0 else 0.0
        return ExperimentResult(
            experiment_id=f"exp_{self.workload_id}_{self.seed}",
            workload_id=self.workload_id,
            system_id=self.system_id,
            seed=self.seed,
            success=self.success,
            task_quality=self.quality,
            latency_ms=latency,
            total_cost=self.cost,
            resource_usage=float(self.steps_executed),
            execution_steps=self.steps_executed,
            adaptation_events=0,
            structural_mutations=0,
            recovery_events=0,
            provenance_reference=None
        )

    def shutdown(self) -> None:
        pass
