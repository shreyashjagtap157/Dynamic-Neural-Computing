"""DNC Execution layer: DecisionPolicy, ExecutionProvider, ExecutionTrace, ReplayEngine.

Per architecture.md: The execution layer encompasses the control loop, the scheduler's
binding to execution providers, and the structured trace/audit log. This layer is where
LLM providers (Ollama, vLLM, OpenAI, Anthropic) are integrated into DNC.
"""

from __future__ import annotations

from dnc.execution.decision_policy import (
    Decision,
    DecisionMetadata,
    DecisionPolicy,
    RulePolicy,
)
from dnc.execution.execution_provider import (
    ExecutionCapability,
    ExecutionProvider,
    ProviderMetadata,
    ProviderResult,
    CostEstimate,
    ReferenceExecutionProvider,
)
from dnc.execution.execution_trace import (
    CausalEvent,
    DecisionRecord,
    ExecutionRecord,
    ExecutionTrace,
    ModuleInvocationRecord,
    ObservationRecord,
    ResourceUsageRecord,
    TerminationReason,
    TraceHeader,
)
from dnc.execution.replay_engine import (
    ReplayConfig,
    ReplayEngine,
    ReplayResult,
    ReplayStepResult,
)

__all__ = [
    # Decision Policy
    "Decision",
    "DecisionMetadata",
    "DecisionPolicy",
    "RulePolicy",
    # Execution Provider
    "ExecutionCapability",
    "ExecutionProvider",
    "ProviderMetadata",
    "ProviderResult",
    "CostEstimate",
    "ReferenceExecutionProvider",
    # Execution Trace
    "CausalEvent",
    "DecisionRecord",
    "ExecutionRecord",
    "ExecutionTrace",
    "ModuleInvocationRecord",
    "ObservationRecord",
    "ResourceUsageRecord",
    "TerminationReason",
    "TraceHeader",
    # Replay
    "ReplayConfig",
    "ReplayEngine",
    "ReplayResult",
    "ReplayStepResult",
]