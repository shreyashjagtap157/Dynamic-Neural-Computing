# Replay Semantics

## Metadata

| Field | Value |
|---|---|
| Document | replay-semantics.md |
| Title | Replay Semantics |
| Document ID | SPEC-REPLAY |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | How is execution replayed deterministically? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md, execution-trace-format.md |
| Defines | ReplayEngine, DeterministicReplay, ReplayVerifier, replay requirements |
| Referenced by | conformance-model.md |

---

## Section 1 — Overview

### 1.A Purpose

The **ReplayEngine** is the runtime component that deterministically re-executes a recorded execution trace, producing a bit-identical replay of the original execution. Replay is used for:

- **Debugging learned policies** — replay a trace to understand why a policy made a specific decision
- **Reproducing failures** — replay a failure trace to investigate root cause
- **Verifying behavioral properties** — verify that the runtime satisfies specified invariants by replaying traces
- **Validating implementations** — compare a new implementation's replay against the reference replay

### 1.B Design Principle

Replay is built on the principle that **non-determinism must be captured or controlled**. If a trace contains all inputs, random states, and external signals, the execution is replayable deterministically regardless of the actual determinism of the underlying components.

---

## Section 2 — Replay Requirements

### 2.A Determinism Requirements

For a replay to be deterministic (producing bit-identical results to the original execution), the following conditions MUST be satisfied:

**INV-REP-1:** The random seed and RNG state at execution start MUST be identical in replay and original execution.

**INV-REP-2:** All external inputs (user signals, timing signals, network responses) MUST be identical in replay and original execution. These are recorded in the trace's ObservationRecord.

**INV-REP-3:** All execution provider responses that would differ between runs (LLM outputs with temperature > 0) MUST be pre-recorded in the trace. The ReplayEngine uses the recorded responses, not fresh provider calls.

**INV-REP-4:** Timestamps in replay MUST match the original trace timestamps, or be controlled by the replay configuration. Time-dependent behavior (e.g., deadline checks) MUST use replay timestamps.

### 2.B Provider Response Recording

For LLM providers, replay requires pre-recorded responses because LLM outputs are non-deterministic even with fixed seeds. The ReplayEngine records and replays as follows:

```
Original execution:
    module_instance → LLMProvider.execute(CAP-REASONING, prompt)
                   ← LLMResponse(content="...")   ← fresh LLM call, recorded in trace

Replay execution:
    module_instance → ReplayEngine.replay_step(step)
                   ← cached LLMResponse from trace  ← no fresh LLM call
```

The trace MUST contain the full ProviderResult for every module invocation, including LLM responses.

---

## Section 3 — ReplayEngine Interface

### 3.A Abstract Interface

```python
class ReplayEngine:
    """Deterministic execution replay engine."""

    def replay(
        self,
        trace: ExecutionTrace,
        config: Optional[ReplayConfig] = None,
    ) -> ReplayResult:
        """Replay a full execution trace and return the replay result."""

    def replay_step(
        self,
        trace: ExecutionTrace,
        step_index: int,
    ) -> ReplayStepResult:
        """Replay a single step from the trace."""

    def compare(
        self,
        original: ExecutionTrace,
        replay: ExecutionTrace,
    ) -> ReplayDiff:
        """Compare two traces and produce a diff report."""


@dataclass(frozen=True)
class ReplayConfig:
    """Configuration for replay execution."""

    use_recorded_timestamps: bool = True   # Use original trace timestamps
    use_recorded_provider_responses: bool = True  # Use cached responses
    inject_failures: bool = False          # Inject failures from trace
    max_steps: Optional[int] = None        # Limit replay to N steps
    verbose: bool = False                  # Emit step-by-step logging


@dataclass(frozen=True)
class ReplayResult:
    """Result of a full replay execution."""

    is_identical: bool                     # True if replay matches original exactly
    divergence_step: Optional[int]        # Step index of first divergence (None if identical)
    divergence_reason: Optional[str]       # Reason for divergence
    execution_trace: ExecutionTrace       # The replayed trace
    replay_metadata: ReplayMetadata        # Replay execution metadata


@dataclass(frozen=True)
class ReplayMetadata:
    """Metadata about the replay execution."""

    replay_duration_ms: float             # Wall-clock replay time
    original_duration_ms: float           # Original execution time
    steps_replayed: int                   # Number of steps replayed
    provider_calls_made: int              # Actual provider calls (vs. cached)
    replay_fidelity: str                  # "bit_identical" / "semantic" / "diverged"
```

### 3.B ReplayStepResult

```python
@dataclass(frozen=True)
class ReplayStepResult:
    """Result of replaying a single step."""

    step_index: int
    is_identical: bool                    # True if step matches original
    original_record: ExecutionRecord      # From original trace
    replay_record: ExecutionRecord       # From replay execution
    divergence: Optional[Divergence]     # Details if not identical


@dataclass(frozen=True)
class Divergence:
    """Details of a divergence between original and replay."""

    divergence_type: str                   # DECISION / GRAPH / OUTPUT / TIMING / RESOURCE
    field_path: str                       # Path to diverging field (e.g., "action.dispatched[0]")
    original_value: Any                   # Value in original trace
    replay_value: Any                     # Value in replay
    severity: str                         # CRITICAL / WARNING / INFO
```

### 3.C ReplayDiff

```python
@dataclass(frozen=True)
class ReplayDiff:
    """Comparison result between original and replay traces."""

    is_identical: bool                     # True if all steps are identical
    step_diffs: List[StepDiff]            # Per-step differences
    summary: DiffSummary                  # Summary statistics


@dataclass(frozen=True)
class StepDiff:
    """Difference at a specific step."""

    step_index: int
    differences: List[FieldDiff]          # List of field-level differences


@dataclass(frozen=True)
class FieldDiff:
    """A single field difference."""

    field_path: str                       # e.g., "module_invocations[0].latency_ms"
    original_value: Any
    replay_value: Any
    tolerance: Optional[float]            # Acceptable difference (for floating point)


@dataclass(frozen=True)
class DiffSummary:
    """Summary of a trace comparison."""

    total_steps: int
    identical_steps: int
    diverged_steps: int
    critical_divergences: int
    warning_divergences: int
    info_divergences: int
```

---

## Section 4 — ReplayVerifier

### 4.A Abstract Interface

The **ReplayVerifier** is a component that uses replay to verify behavioral properties of the runtime.

```python
class ReplayVerifier:
    """Verifies runtime behavior through deterministic replay."""

    def verify_invariant(
        self,
        trace: ExecutionTrace,
        invariant: str,
    ) -> VerificationResult:
        """Verify that an invariant is satisfied at every step of the trace."""

    def verify_all_invariants(
        self,
        trace: ExecutionTrace,
    ) -> Dict[str, VerificationResult]:
        """Verify all active invariants against the trace."""

    def verify_plan_stability(
        self,
        traces: List[ExecutionTrace],
    ) -> VerificationResult:
        """Verify that identical inputs produce identical execution graphs."""

    def verify_resource_accounting(
        self,
        trace: ExecutionTrace,
    ) -> VerificationResult:
        """Verify that resource consumption is accurately tracked."""


@dataclass(frozen=True)
class VerificationResult:
    """Result of a verification check."""

    passed: bool                          # True if verification passed
    invariant_id: str                    # Invariant being verified
    step_index: int                       # Step at which verification was performed (None if global)
    details: str                          # Human-readable details
    evidence: List[str]                   # Trace evidence supporting the result
```

### 4.B Verification Protocol

The ReplayVerifier follows this protocol:

```
For each step in trace:
    1. Replay to that step
    2. Check the invariant condition
    3. Record the result
    4. If CRITICAL divergence found, halt verification
```

---

## Section 5 — Replay Semantics Invariants

**INV-REP-1:** The ReplayEngine MUST replay every step of the execution trace in order.

**INV-REP-2:** If `use_recorded_provider_responses = True`, the ReplayEngine MUST use cached ProviderResults from the trace and MUST NOT make fresh provider calls.

**INV-REP-3:** A replay that produces any CRITICAL divergence is marked `is_identical = False` and MUST NOT be used for verification.

**INV-REP-4:** The ReplayVerifier MUST halt on the first CRITICAL divergence when verifying invariants.

**INV-REP-5:** Deterministic replay is achievable only if the trace satisfies INV-REP-1 through INV-REP-4 in `execution-trace-format.md`.

---

## Section 6 — Conformance Clause

An implementation conforms to this specification if:

- The ReplayEngine interface in Section 3 is fully implemented
- Replay produces bit-identical results for traces satisfying the determinism requirements in Section 2
- The ReplayVerifier in Section 4 is implemented and correctly identifies divergences
- INV-REP-1 through INV-REP-5 are enforced

Extensions are permitted only under `conformance-model.md` Section 3.

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| REP-AMEND-001 | replay-semantics.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of ReplayEngine interface, ReplayVerifier, determinism requirements, divergence reporting. | No |