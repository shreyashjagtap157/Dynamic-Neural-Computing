"""
Phase 13 Benchmark Contracts (Phase 13B & 13D)
Defines uniform experiment interfaces, experiment results, and system adapter contracts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class ExperimentResult:
    """Canonical result record for every benchmark run across all baselines and DNC systems."""
    experiment_id: str
    workload_id: str
    system_id: str
    seed: int
    success: bool
    task_quality: float
    latency_ms: float
    total_cost: float
    resource_usage: float
    execution_steps: int
    adaptation_events: int
    structural_mutations: int
    recovery_events: int
    provenance_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkSystem(ABC):
    """Uniform abstract interface that all baselines and DNC systems must satisfy."""

    @abstractmethod
    def initialize(self, workload_id: str, seed: int, config: Dict[str, Any]) -> None:
        """Initialize the system with workload parameters and deterministic seed."""
        pass

    @abstractmethod
    def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task instance and return intermediate/final output."""
        pass

    @abstractmethod
    def observe(self) -> Dict[str, Any]:
        """Observe current system internal state, graph metrics, or memory."""
        pass

    @abstractmethod
    def get_result(self) -> ExperimentResult:
        """Extract canonical ExperimentResult summary."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up system resources."""
        pass
