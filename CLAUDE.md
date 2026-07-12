# DNC Specification + Phase 1-7 Implementation

## Project Overview

This is the Dynamic Neural Computation (DNC) specification project — a formal specification for researching and developing dynamic neural computing systems, with a Python implementation of Phase 1 through Phase 7.

**Specification Version**: 0.1.0 (Baseline v1.0)
**Implementation Version**: 0.1.0 (Phase 1–7 complete, 139/139 tests passing)

## Project Status

**Phase 1 COMPLETE** — Core execution engine fully implemented and tested (30/30 tests passing).
**Phase 2 COMPLETE** — Planner pipeline, replanning protocol, control loop, and cost semantics implemented (9/9 tests passing).
**Phase 3 COMPLETE** — Provenance model, failure taxonomy, evaluation suite, and continual learning implemented (12/12 tests passing).
**Phase 4 COMPLETE** — RegressionMonitor (automated rollback), BiasEvaluationFramework (PR-15), and runtime production hardening implemented (10/10 tests passing).
**Phase 5 COMPLETE** — Architecture v1.0 reference runtime with 5 execution providers, computation-aware evaluation, and deterministic replay (37/37 tests passing).
**Phase 7 COMPLETE** — Distributed handoff protocol (at-least-once delivery, idempotent receivers, 2PC coordinator) (22/22 tests passing).

## Suitability for Dynamic Neural Computing Research

**YES** — This project is designed for DNC research. The specification defines:
- Execution graphs (DAGs) of module instances with structural analogy to neural circuits
- Dynamic runtime planning (planner synthesizes graphs at runtime) with O(|V|²) complexity bounds
- Control loop (Observe → Decide → Act → Assess) with two-tier async execution
- State management with checkpoints, state migration, and rollback
- Formal trace semantics for reasoning about execution
- Continual learning with clustering-based bounded drift, invariant preservation, and root-cause KB rollback
- Full provenance tracking and hierarchical failure taxonomy
- Explicit neural computation definition: structural analogy to neural circuits, not neuron-level simulation

## Directory Structure

```
DNC/
├── docs/                       # Project documentation
│   └── registry.md             # Machine-readable specification registry (11 namespaces, 12 amendments)
├── specs/                      # Formal specification documents
│   ├── layer-0-foundation/    # Governance, 16 principles (PR-1 to PR-16)
│   ├── layer-1-terminology/    # Single authoritative vocabulary + neural computation terms
│   ├── layer-2-invariants/     # 11 constitutional runtime invariants
│   ├── layer-3-execution/      # Formal model, execution model, state management, control loop
│   ├── layer-4-mechanisms/      # Planner pipeline, scheduler, module lifecycle, cost semantics
│   ├── layer-5-observability/  # Provenance model, failure taxonomy, evaluation suite
│   ├── layer-6-evolution/       # Continual learning, MVP roadmap (4 phases)
│   └── layer-7-distributed/     # Distributed handoff protocol (stub, not frozen)
├── tools/                       # Utility scripts
│   └── fix_refs.py             # Cross-reference fixer, PR-4 verifier, RFC 2119 linter
└── research/                    # Research artifacts (empty, for future use)
```

## Specification Architecture

The specification is organized into 7+1 layers where each layer may only reference lower layers (DAG structure enforced by PR-4):

- **Layer 0** (Governance): How the specification is written and evolved
- **Layer 1** (Vocabulary): What every term means
- **Layer 2** (Constitution): What properties must never be violated
- **Layer 3** (Semantics): How execution proceeds mathematically
- **Layer 4** (Mechanisms): How components are implemented
- **Layer 5** (Observability): How runtime behavior is measured and tracked
- **Layer 6** (Evolution): How the runtime improves from experience
- **Layer 7** (Distributed): Inter-process and inter-node handoffs (stub — not frozen)

## Key Documents

| Document | Layer | Purpose |
|----------|-------|---------|
| specification-foundation.md | 0 | 16 governance principles (PR-1 to PR-16) |
| core-terminology.md | 1 | All vocabulary + neural computation definitions |
| runtime-invariants.md | 2 | 11 invariants (INV-1 to INV-11) |
| formal-model.md | 3 | Mathematical execution model with trace semantics |
| state-management.md | 3 | ES(t) = (W,M,C,H,R), checkpoints, migration |
| control-loop.md | 3 | O→D→A→Assess, async neural exclusion (INV-CTRL-9b), backpressure (INV-CTRL-9c) |
| planner-pipeline.md | 4 | Runtime graph synthesis with INV-PLANNER-10 complexity bounds |
| cost-semantics.md | 4 | Resource accounting with staged checkpoint protocol (INV-COST-8) |
| continual-learning.md | 6 | Clustering-based bounded drift (DEF-CL-9 distance metric), root-cause rollback (INV-CL-13), rollback circuit-breaker (INV-CL-17) |
| failure-taxonomy.md | 5 | INVALID_OUTPUT, GPU recovery, PARTIAL_FAILURE classes |

## Identifier Namespaces (11 subspaces)

| Namespace | Prefix | Range |
|-----------|--------|-------|
| Principles | PR- | PR-1 to PR-16 |
| Runtime Invariants | INV- | INV-1 to INV-11 |
| State Invariants | INV-STATE- | INV-STATE-1 to INV-STATE-11 |
| Control Loop Invariants | INV-CTRL- | INV-CTRL-1 to INV-CTRL-15 |
| Learning Invariants | INV-CL- | INV-CL-1 to INV-CL-17 |
| Planner Invariants | INV-PLANNER- | INV-PLANNER-1 to INV-PLANNER-10 |
| Cost Invariants | INV-COST- | INV-COST-1 to INV-COST-8 |
| Theorems | THM- | THM-1 to THM-99 |
| Definitions | DEF- | DEF-1 to DEF-99 |
| Axioms | AX- | AX-1 to AX-20 |
| Lemmas | LEM- | LEM-1 to LEM-99 |

## Tools

**fix_refs.py** — Multi-mode tool for DNC spec file management:

```bash
# Fix cross-references after file moves
python tools/fix_refs.py

# Verify PR-4 compliance (all cross-refs point to lower layers)
python tools/fix_refs.py --verify

# Check RFC 2119 keyword discipline across all spec files
python tools/fix_refs.py --rfc2119
```

## Known Formal Gaps (pre-Baseline v1 resolution tracking)

| Gap | Status | Resolution |
|-----|--------|------------|
| G-12.1 ValidCheckpoint invariant-satisfaction | ✅ RESOLVED | Condition 5 added; INV-STATE-2 now references DEF-FM-11 |
| G-12.4 RNG state in ES(t) | ✅ RESOLVED | R(t) added to execution record |
| G-12.1 cross-file DEF-3 vs DEF-FM-11 | ✅ RESOLVED | INV-REPLAN-9 and INV-STATE-2 both reference DEF-FM-11 |
| G-12.3 INV-8 bootstrapping | ✅ RESOLVED | BootstrapVerifier implemented in src/dnc/invariants/verifier.py; check_invariants() verifies all 7 runtime invariants at bootstrap |
| G-12.2 byte-exact memory | ✅ RESOLVED | ModuleInstanceID now deterministic on (type_id, instance_counter), so the planner reuses IDs across replans and RETAINED nodes actually exist; byte-exact preservation verified by tests/test_g12_byte_exact.py (planner ID reuse, RETAINED W byte-equality, checkpoint restore byte-equality) |

## Architecture Conformance Defects (ACD)

Remediation tracking for the exhaustive runtime-vs-Architecture-v1.0 conformance audit
(remediation plan approved with P0A→P0B→Review gate→P1→P2 structure). Each ACD links a
violating INV-* and is closed only when an executable conformance test in `tests/conformance/`
passes.

| ACD | Violates | Status | Resolution |
|-----|----------|--------|------------|
| ACD-001 | INV-CTRL-11 (loop termination conditions) | ✅ RESOLVED | `ExecutionState.pending_count` added; `Runtime.decide` propagates `budget_remaining`; `Runtime.act` completion guard filters already-output-bound nodes; `RulePolicy._is_all_modules_complete` requires a non-empty module set so a bare ES(t) does not terminate prematurely. Closed by `tests/conformance/runtime/test_control_loop.py` (P0B). |
| ACD-002 | INV-STATE-4 (checkpoint immutability / no aliasing) | ✅ RESOLVED | `ExecutionState.to_dict` now deep-isolates W/M/C/H at capture time; `ExecutionState.from_dict` deep-isolates on restore; `Runtime._execute_replan` snapshots via `es.copy()`. Closed by `tests/conformance/runtime/test_replay_and_rollback.py` (P0B). |

## Specification State Machine

Documents progress through: Draft → Review → Frozen → Amended → Superseded → Archived

## Version Format

- Draft: `Draft DR-<n>` (e.g., Draft DR-1, Draft DR-2)
- Frozen baseline: `Baseline v<n>`
- Amended: `Baseline v<n> + AMEND-<nnn>`

## Implementation Phases (from mvp-roadmap.md)

1. **Phase 0**: Specification freeze (8-12 weeks)
2. **Phase 1**: Core execution engine (16-24 weeks)
3. **Phase 2**: Dynamic planning and scheduling (20-32 weeks)
4. **Phase 3**: Observability and self-improvement (24-40 weeks)
5. **Phase 4**: Production hardening (12-20 weeks)

Total estimated: 80-128 weeks for a team of 3-5 engineers.

## Governance Principles (PR-1 to PR-16)

- PR-1: Single-Ownership Rule
- PR-2: Single-Vocabulary Rule
- PR-3: Single-Notation Rule
- PR-4: Lower-Layers-Only Rule (enforced by --verify)
- PR-5: Verification-Mechanism Rule
- PR-6: No-Undefined-Behavior Rule
- PR-7: Normative-Wording Rule (enforced by --rfc2119)
- PR-8: Preservation-under-Extension Rule
- PR-9: Evidence Principle
- PR-10: Version Consistency Rule
- PR-11: External Authority Structure (regulated deployments)
- PR-12: Minimum Safety Bounds
- PR-13: Namespace Extension Mechanism
- PR-14: Algorithmic Transparency
- PR-15: Bias and Fairness Evaluation
- **PR-16: Principle Conflict Resolution** (CONFIG_OVERRIDE mechanism for PR-10 vs PR-12 tension)

## Work State

### Phase 1: COMPLETE (30/30 tests passing)

**Test suites:**
- `tests/phase1_exit_criteria.py` — 9 exit criteria (EC-1 through EC-9)
- `tests/test_integration.py` — 6 integration tests (full pipeline, diamond DAG, edge cases)
- `tests/test_invariant_violations.py` — 15 regression tests (INV-1 through INV-11)

**Implementation artifacts:****
- `src/dnc/__init__.py` — Package init, version
- `src/dnc/runtime/__init__.py` — Runtime types export
- `src/dnc/runtime/types.py` — `ModuleInstanceID`, `ModuleTypeID`, `UNBOUND` (singleton), `PENDING` (singleton), `Buffer` (frozen dataclass), `ModuleContract`, all custom exceptions
- `src/dnc/state/__init__.py` — State types export
- `src/dnc/state/working_memory.py` — `WorkingMemory` (copy-on-write per DEF-2), `HistoryLog` (append-only per INV-STATE-10)
- `src/dnc/state/checkpoint.py` — `Checkpoint` (validated per DEF-FM-11 conditions 1-5), `CheckpointRecord` (MAX_CHECKPOINTS=100 per INV-STATE-3)
- `src/dnc/state/execution_state.py` — `ExecutionState` with ES(t) = (W, M, C, H, R), step index, deterministic RNG per DEF-FM-2
- `src/dnc/state/registry.py` — `ModuleRegistry` enforcing single-ownership per INV-4
- `src/dnc/scheduler/__init__.py` — Scheduler export
- `src/dnc/scheduler/scheduler.py` — Kahn's algorithm topological sort, `get_runnable()` (INV-3), `set_graph()` with cycle detection (INV-2), `dispatch()`
- `src/dnc/invariants/__init__.py` — Invariant checkers export
- `src/dnc/invariants/runtime_invariants.py` — `RuntimeInvariantSet` checking INV-1 through INV-11; raises `StateComponentViolation` for null ES(t) components per DEF-1
- `src/dnc/invariants/verifier.py` — `BootstrapVerifier` (G-12.3 INV-8 verified verifier); checks all 7 runtime invariants at bootstrap, raises no exceptions (results in report)
- `src/dnc/modules/__init__.py` — Module types export
- `src/dnc/modules/base.py` — `BaseModule` ABC + `validate_contract()`
- `src/dnc/modules/standard.py` — `SourceModule`, `TransformModule`, `AggregateModule`, `SinkModule`, `FaultInjectorModule`

**Phase 1 scope (per mvp-roadmap.md Section 3):**
- Module registry (INV-4 single-ownership) ✅
- Execution state machine (ES(t) = W, M, C, H, R) ✅
- State management (copy-on-write W, append-only H, checkpoints) ✅
- Scheduler (topological dispatch, precondition enforcement) ✅
- Module contract validation ✅
- Runtime invariant enforcement (INV-1 to INV-11) ✅

**NOT in Phase 1 scope:** planning/replanning, replanning loop, continual learning, control loop, cost semantics

### Phase 2: COMPLETE (9/9 tests passing)

**Test suites:**
- `tests/test_phase2_planner.py` — 9 exit criteria (EC-1 through EC-9 per mvp-roadmap.md Section 4.C)

**Phase 2 implementation artifacts:**
- `src/dnc/planner/__init__.py` — Planner package init
- `src/dnc/planner/pipeline.py` — `Planner` (4-phase pipeline: TaskAnalysis, ModuleSelection, GraphConstruction, Validation), `ExecutionGraph`, `PlanningTask`, `PlanningResult`, `ReplanContext`; `compute_graph_diff()` for RETAINED/RETIRED_EARLY/NEW per DEF-REPLAN-2
- `src/dnc/cost/__init__.py` — Cost semantics init
- `src/dnc/cost/semantics.py` — `CostBudget` (resource accounting), `CostForecaster` (forecast-based replan trigger per INV-REPLAN-4), `StagedCheckpointBudget` (INV-COST-8)
- `src/dnc/runtime/runtime.py` — `Runtime` class: `initiate()`, `observe()`, `decide()`, `act()`, `assess()`, `step()` implementing DEF-CTRL-1 (O→D→A→Assess), `LatencyConfig` (DEF-CTRL-8), `Decision` enum, `AssessmentKind` enum; replan frequency bounded per INV-REPLAN-7; critical section blocking per INV-REPLAN-8; backpressure per INV-CTRL-9c

**Phase 2 scope (per mvp-roadmap.md Section 4):**
- Planner pipeline (4 phases, O(|V|²) worst case per INV-PLANNER-10) ✅
- Replanning protocol (INV-REPLAN-1 through INV-REPLAN-12) ✅
- Control loop O→D→A→Assess (INV-CTRL-1 through INV-CTRL-14) ✅
- Cost semantics with forecast-triggered replan (INV-REPLAN-4) ✅
- Scheduler backpressure for ASYNC_PENDING (INV-CTRL-9c) ✅
- Planner version tracking in execution header (INV-PLANNER-9) ✅

**NOT in Phase 2 scope:** provenance model, failure taxonomy, evaluation suite, continual learning

### Phase 3: COMPLETE (12/12 tests passing)

**Test suites:**
- `tests/test_phase3_observability.py` — 12 exit criteria (EC-1 through EC-12 per mvp-roadmap.md Section 5.C)

**Phase 3 implementation artifacts:**
- `src/dnc/observability/__init__.py` — Observability package init
- `src/dnc/observability/provenance.py` — `ProvenanceRecorder` (hash chain per INV-PROV-4), `ExecutionEvent` (DEF-PROV-3), `CausalChain`; event recording, causal chain query, hash integrity verification
- `src/dnc/observability/failure.py` — `FailureClassifier` (INV-FAIL-5 tracking), `FailureSignal`, `FailureClassification`, `FailureRecord`, `FailureDatabase`; classify(), record_failure() with cumulative invocation tracking
- `src/dnc/observability/evaluation.py` — `EvaluationSuite` (DEF-EVAL-3), `MetricSpec`, `TrialResult`; run_trials() (MIN_TRIAL_COUNT=30 per INV-EVAL-6), statistical significance (paired t-test, INV-EVAL-7), degradation_within_tolerance()
- `src/dnc/learning/__init__.py` — Learning package init
- `src/dnc/learning/continual.py` — `DriftChecker` (DEF-CL-9 k-means normalized Euclidean distance), `KnowledgeBase` (DEF-CL-3 version tracking), `InvariantKB`; compute_drift(), is_within_drift_bound(), cluster_profiles(), rollback_to_version() (INV-CL-13 root-cause rollback)

**Phase 3 scope (per mvp-roadmap.md Section 5):**
- Provenance event recording with causal chains and hash chain integrity ✅
- Failure classification (INVALID_OUTPUT, GPU_RECOVERY, PARTIAL_FAILURE per INV-FAIL-5) ✅
- Failure rate tracking per module type with cumulative invocations ✅
- Evaluation suite with MIN_TRIAL_COUNT=30, paired t-test statistical significance ✅
- Regression detection (updated metrics vs baseline, degradation tolerance) ✅
- Drift bounds checking (k-means normalized Euclidean, INV-CL-10) ✅
- Knowledge base versioning and root-cause rollback (INV-CL-13) ✅
- Rollback circuit-breaker (INV-CL-17: 3 consecutive rollbacks trigger cooldown) ✅

**NOT in Phase 3 scope:** distributed handoffs (Phase 7), performance optimization

### Phase 4: COMPLETE (10/10 tests passing)

**Test suites:**
- `tests/test_phase4_production.py` — 10 exit criteria (EC-1 through EC-10 per mvp-roadmap.md Section 6.F)

**Phase 4 implementation artifacts:**
- `src/dnc/runtime/runtime.py` — `RegressionMonitor` (Class 1 regression detection, configurable rollback threshold), integrated into `Runtime` class
- `src/dnc/observability/bias_evaluation.py` — `BiasEvaluationFramework` (PR-15), `BiasEvaluationResult`, `GroupedPredictions`, `BiasViolationException`; 4 fairness metrics:
  - Demographic parity difference (≤ 0.05 per PR-15)
  - Equalized odds difference (≤ 0.05 per PR-15)
  - Disparate impact ratio (0.8–1.25 per PR-15)
  - Individual fairness consistency score (≥ 0.85 per PR-15)
  - `block_if_failing()` raises `BiasViolationException` when thresholds violated

**Phase 4 scope (per mvp-roadmap.md Section 6.F):**
- RegressionMonitor with automated rollback trigger ✅
- BiasEvaluationFramework with 4 PR-15 fairness metrics ✅
- Runtime integration of RegressionMonitor ✅
- Bias evaluation blocks deployment/KB update when thresholds violated ✅

**NOT in Phase 4 scope:** distributed handoffs (Phase 7)

### Phase 5: COMPLETE (37/37 tests passing)

**Test suites:**
- `tests/test_phase5b.py` — 20 exit criteria (EC-1 through EC-20: DecisionPolicy, ExecutionProvider, ExecutionTrace, ReplayEngine)
- `tests/test_phase5_providers.py` — 17 exit criteria (EC-1 through EC-17: Ollama, vLLM, OpenAI, Anthropic, Gemini providers + ComputationMonitor)

**Phase 5 implementation artifacts:**
- `src/dnc/execution/` — Execution layer package
- `src/dnc/execution/decision_policy.py` — DecisionPolicy abstract interface + RulePolicy reference impl
- `src/dnc/execution/execution_provider.py` — ExecutionProvider interface + ReferenceExecutionProvider
- `src/dnc/execution/execution_trace.py` — ExecutionTrace, ExecutionRecord, DecisionRecord, ObservationRecord, ModuleInvocationRecord
- `src/dnc/execution/replay_engine.py` — ReplayEngine for deterministic replay
- `src/dnc/providers/` — Provider package (5 execution providers)
- `src/dnc/providers/ollama.py` — OllamaProvider (CAP_REASONING, CAP_EMBEDDING, local)
- `src/dnc/providers/vllm.py` — vLLMProvider (CAP_REASONING, CAP_EMBEDDING, local)
- `src/dnc/providers/openai.py` — OpenAIProvider (CAP_REASONING, CAP_EMBEDDING)
- `src/dnc/providers/anthropic.py` — AnthropicProvider (CAP_REASONING)
- `src/dnc/providers/gemini.py` — GeminiProvider (CAP_REASONING)
- `src/dnc/evaluation/` — Evaluation package
- `src/dnc/evaluation/computation_aware.py` — ComputationMonitor with Level 0-2 metrics (DCI, CCG, Budget Elasticity, Graph Entropy, Planning Stability, Tool Diversity)

**Phase 5 scope (per mvp-roadmap.md Section 7):**
- DecisionPolicy interface + RulePolicy ref impl (5B) ✅
- ExecutionProvider interface + ReferenceProvider (5B) ✅
- ExecutionTrace schema with full record structure (5B) ✅
- ReplayEngine for deterministic replay (5B) ✅
- OllamaProvider for local inference (5C) ✅
- vLLMProvider for local inference (5C) ✅
- OpenAIProvider for cloud inference (5E) ✅
- AnthropicProvider for cloud inference (5E) ✅
- GeminiProvider for cloud inference (5E) ✅
- ComputationMonitor with Level 2 Adaptivity metrics (5D) ✅
- DCI (Dynamic Compute Index), CCG (Counterfactual Compute Gain) (5D) ✅
- Graph Entropy, Planning Stability, Tool Diversity (5D) ✅

**NOT in Phase 5 scope:** none (Phase 5 fully complete)

### Phase 7: COMPLETE (22/22 tests passing)

**Test suites:**
- `tests/test_phase7_distributed.py` — 22 exit criteria (EC-1 through EC-22: IdempotentReceiver, DistributedCoordinator, DistributedHandoffConfig, partition handling, coordinator failover, single-hop validation)

**Phase 7 implementation artifacts:**
- `src/dnc/distributed/` — Distributed handoffs package
- `src/dnc/distributed/protocol.py` — IdempotentReceiver, DistributedCoordinator, DistributedHandoffConfig, DistributedHandoffMessage, HandoffMessageType, HandoffStatus, handoff_needs_distribution(), retry_with_backoff(), mark_failed()

**Phase 7 scope (per distributed-handoff-protocol.md INV-DIST-1 through INV-DIST-6):**
- At-least-once delivery with acknowledgment and retry ✅
- Idempotent receiver with deduplication window ✅
- Atomic handoff (INV-DIST-2): ACK only sent after successful processing ✅
- Handoff status tracking (PENDING → COMMITTED/ABORTED/FAILED) ✅
- Handoff message type enum (PREPARE, COMMIT, ABORT, STATE_TRANSFER, ACK, NACK, HEARTBEAT) ✅
- Content hash for integrity verification ✅
- Module distribution model detection (handoff_needs_distribution) ✅
- DistributedHandoffConfig with timeout/retry/heartbeat defaults (INV-DIST-6) ✅
- Partition handling: retry_with_backoff() with exponential/jitter/fail-fast (INV-DIST-3) ✅
- Coordinator failover: mark_failed() with error reporting to control loop (INV-DIST-4) ✅
- Single-hop constraint: validate direct sender->receiver only (INV-DIST-5) ✅

### Active
- None — all planned work complete

### Blocked
- None