# Execution Trace Format

## Metadata

| Field | Value |
|---|---|
| Document | execution-trace-format.md |
| Title | Execution Trace Format |
| Document ID | SPEC-TRC |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | What does an execution trace record, and in what format? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md, interfaces.md |
| Defines | ExecutionTrace schema, field classifications, serialization format |
| Referenced by | evaluation-framework.md, replay-semantics.md |

---

## Section 1 — Overview

### 1.A Purpose

An **ExecutionTrace** is a complete, exportable record of a single execution's computational history. The trace is the primary artifact for computation-aware evaluation and learned policy training.

The trace records not just input-output pairs, but the entire computational path: the decisions made, the graphs synthesized, the modules invoked, the resources consumed, the failures encountered, and the recoveries performed.

### 1.B Design Principles

The trace format follows three principles:

**Completeness:** The trace must contain enough information to reconstruct the full execution state at any point, enabling deterministic replay.

**Exportability:** The trace schema is DNC-native but serializable to standard formats (JSON, Protocol Buffers) for interoperability. The schema is the source of truth; serialization is a derived concern.

**Evolability:** The schema supports optional fields that may be added in future versions without breaking backward compatibility with existing traces.

---

## Section 2 — Trace Schema

### 2.A Top-Level Structure

```python
@dataclass(frozen=True)
class ExecutionTrace:
    """Complete record of a single execution."""

    # Header (all REQUIRED)
    trace_id: str                        # Unique trace identifier (UUID)
    execution_id: str                    # DNC execution identifier
    specification_version: str           # e.g., "Architecture v1.0"
    runtime_version: str                # Version of the DNC runtime
    planner_version: str                 # Version of the planner
    registry_version: str                # Version of the module registry
    architecture_version: str            # Always "v1.0" for Architecture v1.0
    timestamp_start: str                 # ISO 8601 UTC timestamp
    timestamp_end: Optional[str]         # ISO 8601 UTC timestamp (None if incomplete)

    # Configuration (all REQUIRED)
    resource_budget: float               # Initial resource budget
    latency_config: LatencyConfig        # Control loop latency budgets
    random_seed: int                     # RNG seed for deterministic replay

    # Execution record (REQUIRED — at least one entry)
    execution_record: List[ExecutionRecord]

    # Provenance (all OPTIONAL)
    causal_chain: List[CausalEvent]       # Causal connections between events
    provenance_hash_chain: List[str]     # Hash chain per INV-PROV-4

    # Termination (REQUIRED)
    termination_reason: TerminationReason
    final_outcome: Optional[Any]         # Final output, if available


@dataclass(frozen=True)
class ExecutionRecord:
    """A single record within the execution trace."""

    # Identity (all REQUIRED)
    step_index: int                       # Control loop step index
    loop_iteration: int                  # Control loop iteration number

    # Observation (all REQUIRED)
    observation: ObservationRecord        # What was observed at this step

    # Decision (all REQUIRED)
    decision: DecisionRecord             # What decision was made

    # Action (all REQUIRED)
    action: ActionRecord                  # What action was taken

    # Assessment (all REQUIRED)
    assessment: AssessmentRecord          # What outcome was assessed

    # Execution graph state (all REQUIRED at first record; OPTIONAL thereafter)
    execution_graph: Optional[ExecutionGraphRecord]  # None means unchanged

    # Module invocations (all REQUIRED)
    module_invocations: List[ModuleInvocationRecord]

    # State mutations (all REQUIRED)
    state_mutations: List[StateMutationRecord]

    # Resource consumption (all REQUIRED)
    resource_snapshot: ResourceSnapshot


@dataclass(frozen=True)
class ObservationRecord:
    """Record of the Observe phase."""

    timestamp: str                       # ISO 8601 UTC
    signals: List[SignalRecord]           # All signals received
    latency_ms: float                    # Observe phase latency


@dataclass(frozen=True)
class SignalRecord:
    """A single signal received during Observe."""

    signal_type: str                      # e.g., "user_input", "module_complete", "budget_warning"
    signal_value: Any                     # Signal payload
    source: str                           # Source of the signal
    timestamp: str                         # ISO 8601 UTC


@dataclass(frozen=True)
class DecisionRecord:
    """Record of the Decide phase."""

    timestamp: str                        # ISO 8601 UTC
    decision: str                          # CONTINUE / REPLAN / PAUSE / TERMINATE / ROLLBACK
    reasoning: Optional[str]               # Rationale for the decision (for LLM policies)
    latency_ms: float                     # Decide phase latency
    policy_version: str                   # Version of the DecisionPolicy used


@dataclass(frozen=True)
class ActionRecord:
    """Record of the Act phase."""

    timestamp: str                        # ISO 8601 UTC
    dispatched_module_ids: List[str]     # Modules dispatched in this action
    replan_trigger: Optional[str]         # If REPLAN: the trigger (RESOURCE_EXHAUSTION, etc.)
    latency_ms: float                    # Act phase latency


@dataclass(frozen=True)
class AssessmentRecord:
    """Record of the Assess phase."""

    timestamp: str                        # ISO 8601 UTC
    outcome: str                          # OUTCOME_MET / OUTCOME_DEGRADED / OUTCOME_FAILED
    metrics_summary: Dict[str, float]      # Key metrics at this step
    latency_ms: float                    # Assess phase latency


@dataclass(frozen=True)
class ExecutionGraphRecord:
    """Record of the execution graph state."""

    graph_id: str                          # Unique graph identifier
    planner_version: str                 # Planner that produced this graph
    vertices: List[VertexRecord]          # All nodes in the graph
    edges: List[EdgeRecord]               # All edges in the graph
    cost_weights: Dict[str, float]        # Cost per node


@dataclass(frozen=True)
class VertexRecord:
    """A single node in the execution graph."""

    instance_id: str                       # ModuleInstanceID
    type_id: str                          # ModuleTypeID
    capability: str                       # ExecutionCapability (CAP-*)
    cost_estimate: float                  # Estimated cost
    bound_provider: Optional[str]          # Provider ID if bound at graph construction


@dataclass(frozen=True)
class EdgeRecord:
    """A single edge in the execution graph."""

    upstream: str                          # Source ModuleInstanceID
    downstream: str                       # Target ModuleInstanceID
    edge_type: str                        # DATA_DEPENDENCY / CONTROL_DEPENDENCY


@dataclass(frozen=True)
class ModuleInvocationRecord:
    """Record of a single module invocation."""

    instance_id: str                       # ModuleInstanceID
    invocation_id: str                    # Unique invocation identifier
    capability: str                       # ExecutionCapability invoked
    provider_id: Optional[str]            # ExecutionProvider ID
    provider_type: Optional[str]          # Provider type (openai, anthropic, etc.)
    input: Any                            # Input to the module
    output: Any                           # Output from the module
    latency_ms: float                     # Wall-clock execution time
    token_usage: Optional[TokenUsage]     # Token consumption (if applicable)
    cost_usd: float                       # Cost in USD
    status: str                           # SUCCESS / FAILURE / PARTIAL_FAILURE
    error: Optional[str]                  # Error message if failed
    timestamp_start: str                  # ISO 8601 UTC
    timestamp_end: Optional[str]          # ISO 8601 UTC (None if incomplete)


@dataclass(frozen=True)
class StateMutationRecord:
    """Record of a state mutation in working memory or history log."""

    mutation_type: str                     # BUFFER_UPDATE / CHECKPOINT_CREATE / ROLLBACK / ARCHIVE
    target_instance_id: Optional[str]     # ModuleInstanceID if applicable
    before: Any                          # State before mutation
    after: Any                           # State after mutation
    trigger: str                          # What triggered the mutation
    provenance_ref: Optional[str]         # Provenance chain reference
    step_index: int                       # Step index at mutation


@dataclass(frozen=True)
class ResourceSnapshot:
    """Record of resource consumption at a given step."""

    budget_remaining: float                # Remaining resource budget
    tokens_spent: int                     # Total tokens spent
    cost_spent_usd: float                 # Total cost in USD
    memory_mb: float                      # Estimated memory usage
    compute_ms: float                     # Total compute time
    graph_depth: int                     # Current graph depth
    graph_width: int                     # Current graph width (max parallelism)
    active_nodes: int                     # Currently executing nodes


@dataclass(frozen=True)
class CausalEvent:
    """A single event in the causal chain."""

    event_id: str                          # Unique event identifier
    event_type: str                       # Event type (observation, decision, action, etc.)
    causal_refs: List[str]                # IDs of events this event depends on
    payload: Dict[str, Any]               # Event payload
    provenance_ref: str                   # Hash chain reference


@dataclass(frozen=True)
class LatencyConfig:
    """Control loop latency configuration."""

    observe_budget_ms: float
    decide_budget_ms: float
    act_budget_ms: float
    control_loop_budget_ms: float
    control_loop_grace_ms: float
    decision_latency_budget_ms: float
    max_replans_per_execution: int


@dataclass(frozen=True)
class TokenUsage:
    """Token consumption record."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: Optional[int] = None
    total_tokens: int = 0


@dataclass(frozen=True)
class TerminationReason:
    """Reason for execution termination."""

    reason: str                            # COMPLETED / TERMINATE / FAILED / ROLLED_BACK / BUDGET_EXHAUSTED
    details: Optional[str]                 # Additional details
```

### 2.B Field Classification

All fields are classified as:

| Class | Description | Required |
|---|---|---|
| **REQUIRED** | Must be present in every conformant trace | Always |
| **CONDITIONAL** | Required under specific conditions | Per specification |
| **OPTIONAL** | May be present without affecting conformance | Never required |
| **EXTENDED** | Added via extension mechanism | Only if used |

### 2.C Schema Evolution

The trace schema supports evolution via the following rules:

- New OPTIONAL fields may be added without breaking backward compatibility
- New CONDITIONAL fields may be added with a default value
- Existing fields may NOT be removed or renamed
- Field types may NOT be changed
- New REQUIRED fields are added only in major version increments

---

## Section 3 — Serialization

### 3.A JSON Serialization

The default serialization format is JSON. All timestamps use ISO 8601 UTC format. Numeric values use JSON numbers. Null values represent missing optional data.

### 3.B Protocol Buffers

A Protocol Buffer schema (trace.proto) MAY be defined as a binary serialization format. The Protocol Buffer schema is derived from the canonical JSON schema and MUST be kept in sync.

### 3.C Exportability

The trace format is designed to be trivially exportable to external systems:

```python
trace.to_dict()    # → Python dict (native)
trace.to_json()    # → JSON string
trace.to_proto()   # → Protocol Buffer (if proto schema defined)
```

---

## Section 4 — Conformance Clause

An implementation conforms to this specification if:

- Every ExecutionTrace contains all REQUIRED fields
- CONDITIONAL fields are present when the specified condition holds
- All timestamps are valid ISO 8601 UTC strings
- The trace is serializable to JSON via the defined schema
- The schema evolution rules in Section 2.C are observed

A trace that fails conformance is non-conformant and MUST NOT be used as a reference trace for evaluation or replay.

Extensions are permitted only for OPTIONAL fields using the EXT-* namespace.

---

## Section 5 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| TRC-AMEND-001 | execution-trace-format.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of ExecutionTrace schema, field classifications, serialization rules. | No |