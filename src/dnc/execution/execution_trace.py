"""ExecutionTrace: structured log format for computation-aware evaluation.

Per execution-trace-format.md: ExecutionTrace records the complete computational
history of a DNC execution. The trace is the primary artifact for evaluation
and learned policy training.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import uuid


class TerminationReason(Enum):
    """Per execution-trace-format.md Section 2.F: reasons for execution termination."""

    ALL_MODULES_COMPLETE = auto()
    TERMINATE_DECISION = auto()
    RESOURCE_EXHAUSTED = auto()
    UNRECOVERABLE_FAILURE = auto()
    EXTERNAL_SIGNAL = auto()
    INCOMPLETE = auto()


@dataclass(frozen=True)
class TraceHeader:
    """Per execution-trace-format.md Section 2.A: trace header fields."""

    trace_id: str
    execution_id: str
    specification_version: str = "Architecture v1.0"
    runtime_version: str = "0.1.0"
    planner_version: str = "0.1.0"
    registry_version: str = "0.1.0"
    architecture_version: str = "v1.0"
    timestamp_start: str = ""
    timestamp_end: Optional[str] = None
    resource_budget: float = 0.0
    random_seed: int = 42
    latency_config: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ObservationRecord:
    """Per execution-trace-format.md Section 2.B: what was observed at a step."""

    raw_signals: Any
    signal_types: List[str] = field(default_factory=list)
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionRecord:
    """Per execution-trace-format.md Section 2.C: what decision was made."""

    decision: str
    policy_type: str
    policy_version: str
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    alternative_considered: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass(frozen=True)
class ModuleInvocationRecord:
    """Per execution-trace-format.md Section 2.D: a single module invocation."""

    module_instance_id: str
    module_type: str
    capability: str
    input_size_bytes: int
    output_size_bytes: int
    provider_id: str
    provider_version: str
    latency_ms: float
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResourceUsageRecord:
    """Per execution-trace-format.md Section 2.E: resource consumption at a step."""

    step_index: int
    budget_remaining: float
    cpu_time_ms: float
    memory_bytes: int
    network_calls: int = 0


@dataclass(frozen=True)
class ExecutionRecord:
    """Per execution-trace-format.md: a single record within the execution trace."""

    step_index: int
    loop_iteration: int
    observation: ObservationRecord
    decision: DecisionRecord
    module_invocations: List[ModuleInvocationRecord] = field(default_factory=list)
    resource_usage: Optional[ResourceUsageRecord] = None
    timestamp: str = ""


@dataclass(frozen=True)
class CausalEvent:
    """Per execution-trace-format.md Section 2.G: causal connection between events."""

    cause_step: int
    effect_step: int
    causal_type: str
    description: str


class ExecutionTrace:
    """Complete record of a single DNC execution (per execution-trace-format.md)."""

    def __init__(
        self,
        execution_id: str,
        specification_version: str = "Architecture v1.0",
        runtime_version: str = "0.1.0",
        planner_version: str = "0.1.0",
        registry_version: str = "0.1.0",
        resource_budget: float = 100.0,
        random_seed: int = 42,
        latency_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.trace_id = str(uuid.uuid4())
        self.execution_id = execution_id
        self.specification_version = specification_version
        self.runtime_version = runtime_version
        self.planner_version = planner_version
        self.registry_version = registry_version
        self.architecture_version = "v1.0"
        self.timestamp_start = datetime.now(timezone.utc).isoformat()
        self.timestamp_end: Optional[str] = None
        self.resource_budget = resource_budget
        self.random_seed = random_seed
        self.latency_config = latency_config or {}
        self.execution_record: List[ExecutionRecord] = []
        self.causal_chain: List[CausalEvent] = []
        self.provenance_hash_chain: List[str] = []
        self.termination_reason: Optional[TerminationReason] = None
        self.final_outcome: Optional[Any] = None

    def add_execution_record(self, record: ExecutionRecord) -> None:
        self.execution_record.append(record)

    def add_causal_event(self, event: CausalEvent) -> None:
        self.causal_chain.append(event)

    def append_provenance_hash(self, content_hash: str) -> None:
        self.provenance_hash_chain.append(content_hash)

    def finalize(
        self,
        termination_reason: TerminationReason,
        final_outcome: Optional[Any] = None,
    ) -> None:
        self.timestamp_end = datetime.now(timezone.utc).isoformat()
        self.termination_reason = termination_reason
        self.final_outcome = final_outcome

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the trace to a dictionary for JSON serialization."""
        return {
            "trace_id": self.trace_id,
            "execution_id": self.execution_id,
            "specification_version": self.specification_version,
            "runtime_version": self.runtime_version,
            "planner_version": self.planner_version,
            "registry_version": self.registry_version,
            "architecture_version": self.architecture_version,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "resource_budget": self.resource_budget,
            "random_seed": self.random_seed,
            "latency_config": self.latency_config,
            "execution_record": [
                {
                    "step_index": r.step_index,
                    "loop_iteration": r.loop_iteration,
                    "observation": {
                        "raw_signals": r.observation.raw_signals,
                        "signal_types": r.observation.signal_types,
                        "timestamp": r.observation.timestamp,
                    },
                    "decision": {
                        "decision": r.decision.decision,
                        "policy_type": r.decision.policy_type,
                        "policy_version": r.decision.policy_version,
                        "reasoning": r.decision.reasoning,
                    },
                    "module_invocations": [
                        {
                            "module_instance_id": m.module_instance_id,
                            "module_type": m.module_type,
                            "latency_ms": m.latency_ms,
                        }
                        for m in r.module_invocations
                    ],
                }
                for r in self.execution_record
            ],
            "termination_reason": (
                self.termination_reason.name if self.termination_reason else None
            ),
            "final_outcome": self.final_outcome,
        }

    @property
    def is_complete(self) -> bool:
        return self.timestamp_end is not None and self.termination_reason is not None