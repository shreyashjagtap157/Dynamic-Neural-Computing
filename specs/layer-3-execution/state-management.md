# State Management

## Metadata

| Field | Value |
|---|---|
| Document | state-management.md |
| Title | State Management |
| Document ID | SPEC-STATE |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 3 |
| Owner Question | What state exists across execution steps, how is it checkpointed, and how does it migrate across replans? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

Every execution of the DNC runtime produces intermediate results that persist beyond a single execution step. These results — collectively called the **execution state** — must be managed with the same rigor applied to module definitions and execution graphs. This document specifies the state schema, checkpoint discipline, inter-module handoff protocols, and migration behavior when a replan occurs mid-execution.

The state management system exists at Layer 3 because it defines the semantic foundation upon which Layer 4 mechanisms (planner, scheduler) operate. It does not prescribe implementation; it constrains behavior that any compliant implementation MUST satisfy.

---

## Section 2 — Normative State Definition

### DEF-1 — Execution State

**Definition:**

The **execution state** (ES) at any instant `t` is the tuple:

```
ES(t) = (W(t), M(t), C(t), H(t), R(t))
```

Where:
- `W(t)` is the **working memory** — a mapping from module instance IDs to their current input-output buffers
- `M(t)` is the **module registry snapshot** — the set of all module instances currently registered and their interface signatures at time `t`
- `C(t)` is the **checkpoint record** — an ordered list of checkpoints taken at prior instants, each tagged with the step index and execution ID
- `H(t)` is the **history log** — a provenance-accessible append-only record of all state mutations that have occurred since the last checkpoint
- `R(t)` is the **RNG state** — the deterministic random number generator position, derived from the execution header's `Random Seed` at initialization and advanced by each stochastic module invocation

**Notation:** `ES(t)` follows the notation conventions defined in `formal-model.md`. All components MUST be non-null. `R(t)` is advanced deterministically by each stochastic module invocation. Any component found null at runtime is a **State-Component Violation** and MUST halt execution.

### DEF-2 — Working Memory

**Definition:**

**Working memory** `W(t)` is a total function:

```
W(t): ModuleInstanceID → Buffer
Buffer = (input: Value, output: Value, metadata: Metadata)
```

Each registered module instance at time `t` has exactly one `Buffer` entry in `W(t)`. A module instance with no computed output yet MUST have its `output` field set to a distinguished `UNBOUND` marker. A module instance that has received input but not yet produced output MUST have its `output` field set to `PENDING`.

**Constraints:**

- `W(t)` MUST contain exactly one entry per registered module instance at time `t`
- No two module instances share the same `ModuleInstanceID` within a single execution
- All `Buffer` fields are immutable once written — updates create new versions, never mutate in place

### DEF-3 — Checkpoint

**Definition:**

A **checkpoint** `Ck` is a point-in-time snapshot of `ES(t)` that is preserved for recovery. Formally:

```
Ck = (step_index, execution_id, timestamp, es_snapshot, provenance_ref)
```

Where `es_snapshot` is a serialized copy of `ES(t)` at the moment the checkpoint is taken, and `provenance_ref` is a traceable reference to the decision that triggered the checkpoint (per `../layer-5-observability/provenance-model.md`).

A checkpoint is **valid** if and only if:
1. `es_snapshot` is complete — no component of `ES(t)` is `NULL` or `UNBOUND`
2. `provenance_ref` resolves to a valid provenance record
3. `step_index` is a non-negative integer unique within the execution

---

## Section 3 — Checkpoint Discipline

### INV-STATE-1 — Checkpoint-After-Plan

**Statement:**

The runtime MUST take a checkpoint immediately after the planner produces a new execution graph and before the first step of that graph begins execution. No execution step MAY proceed without a preceding valid checkpoint.

**Verification:** Runtime assertion. The scheduler MUST invoke the checkpoint primitive before dispatching the first step of any newly produced execution graph.

**Rationale:** Without a checkpoint before execution, replanning has no stable state to fall back to. This invariant ensures recovery is always possible.

### INV-STATE-2 — Checkpoint-Before-Replan

**Statement:**

Before the planner is invoked to produce a new execution graph mid-execution, the runtime MUST take a checkpoint of the current `ES(t)`. The checkpoint MUST be valid per DEF-FM-11 (formal-model.md) before the replan trigger is processed. A checkpoint that satisfies DEF-3 (syntactic completeness) but fails DEF-FM-11 condition 5 (invariant-satisfaction) is insufficient for replanning.

**Verification:** Runtime assertion. The planner pipeline MUST confirm a valid checkpoint exists before accepting a replan request.

**Rationale:** Replanning mid-execution modifies the execution trajectory. If the replan produces an invalid graph or fails, rollback to the pre-replan checkpoint is the only safe recovery path.

### INV-STATE-3 — Checkpoint Boundedness

**Statement:**

The checkpoint record `C(t)` MUST NOT grow without bound within a single execution. The maximum number of checkpoints retained per execution is a runtime configuration parameter `MAX_CHECKPOINTS`. When `|C(t)|` equals `MAX_CHECKPOINTS`, the oldest checkpoint MAY be evicted only after a new checkpoint is successfully taken and validated.

**Verification:** Runtime assertion. The checkpoint manager MUST enforce `|C(t)| ≤ MAX_CHECKPOINTS + 1` at all times.

**Rationale:** Unbounded checkpoint growth defeats the purpose of memory management. The bounded buffer allows recovery without infinite memory consumption.

### INV-STATE-4 — Checkpoint Immutability

**Statement:**

Once taken, a checkpoint record `Ck` is immutable. No field of a valid checkpoint MAY be modified after creation. Rollback operations MUST NOT alter the checkpoint record; they restore `ES(t)` by replacing the current state with a copy of the checkpointed state.

**Verification:** Static analysis. The checkpoint manager implementation MUST be proven to contain no mutating operations on checkpoint records after creation.

**Rationale:** A checkpoint that can be modified is not a checkpoint — it is a named pointer to a mutable buffer, which violates the recovery guarantee.

---

## Section 4 — State Handoff Between Modules

### DEF-4 — State Handoff

**Definition:**

A **state handoff** is the transfer of the `output` value of one module instance `A` as the `input` value of a downstream module instance `B` within a single execution step. A handoff is **complete** when `W(t+1)[B].input = W(t)[A].output` and both modules have consistent `ModuleInstanceID` references in `M(t+1)`.

### INV-STATE-5 — Handoff Completeness

**Statement:**

Before any module instance `B` begins execution for a given step, all of its input buffers MUST contain either:
- (a) a bound value from a prior module's output handoff, or
- (b) an external input provided at execution initiation

No module instance MAY transition its `output` from `PENDING` to a computed value unless all input buffers are bound.

**Verification:** Runtime assertion in the scheduler. The scheduler MUST validate all input buffers are bound before dispatching a module for execution.

**Rationale:** A module that produces output based on partially-bound inputs produces unverified results. This is the state-management complement to the handoff protocol.

### INV-STATE-6 — Handoff Atomicity

**Statement:**

A state handoff between module instance `A` and module instance `B` MUST be atomic: either both `W(t)[A].output` is written and `W(t+1)[B].input` is read, or neither transfer is considered committed. The scheduler MUST use a two-phase commit discipline for all intra-step handoffs.

**Verification:** Model checking. The scheduler's handoff protocol MUST be verified to satisfy atomic-commit properties for all module pairs.

**Rationale:** Non-atomic handoffs create race conditions where a downstream module reads stale or null input while the upstream module has already produced new output.

---

## Section 5 — State Migration on Replan

### DEF-5 — State Migration

**Definition:**

**State migration** is the process of transforming `W(t)` from the pre-replan checkpoint into `W(t')` for use by a newly synthesized execution graph, where `t'` is the first step of the new plan. Modules that exist in both the old plan and the new plan are **reusable**; modules that exist only in the old plan are **retired**; modules that exist only in the new plan are **new**.

### INV-STATE-7 — Reusable Module State Preservation

**Statement:**

When the planner produces a new execution graph that reuses a module instance `A` that existed in the prior graph, the runtime MUST preserve `W(pre_replan)[A]` and make it available as the initial `W(post_replan)[A]` for the new plan. The preserved state MUST be byte-exact — no transformation, compression, or reinterpretation is permitted without an explicit migration function registered in the module's contract.

**Verification:** Runtime assertion. The checkpoint restore operation MUST verify byte-exact preservation for all reusable module instances.

**Rationale:** Reusable modules represent work already completed. If their state is not preserved, the dynamic thinker loses the benefit of having done that work — effectively restarting rather than continuing.

### INV-STATE-8 — Retired Module State Archival

**Statement:**

When a module instance `A` is retired (exists only in the old plan), its final state `W(retirement_step)[A]` MUST be archived to the provenance log with a `MODULE_RETIRED` event before the new plan begins execution. The archival record MUST include the module instance ID, final output value, step index, and the rationale for retirement (if provided by the planner).

**Verification:** Runtime assertion. The planner MUST emit a `MODULE_RETIRED` provenance event for every retired module before the new plan is dispatched.

**Rationale:** Even retired modules carry computational history. Archiving ensures the full provenance chain is preserved for audit, debugging, and evidence requirements per PR-9.

### INV-STATE-9 — New Module State Initialization

**Statement:**

When a module instance `B` is new (exists only in the new plan), its initial `W(post_replan)[B]` MUST be initialized with either:
- (a) external input provided by the orchestrator, or
- (b) a default value specified in the module's contract

No new module instance MAY have an uninitialized `Buffer` entry.

**Verification:** Runtime assertion. The scheduler MUST confirm all new module instances have bound initial `Buffer` entries before dispatching the first step of the new plan.

**Rationale:** A new module with an unbound buffer is indistinguishable from a broken state. Initialization discipline prevents this class of error.

---

## Section 6 — History Log

### DEF-6 — History Log Entry

**Definition:**

A **history log entry** `H_i` is a tuple:

```
H_i = (index, timestamp, mutation_type, target_module, before_value, after_value, trigger_provenance_ref)
```

The history log `H(t)` is the ordered sequence `[H_0, H_1, ..., H_n]` of all mutations applied to `W` since the last checkpoint.

### INV-STATE-10 — Append-Only History

**Statement:**

The history log `H(t)` is append-only. No entry in `H(t)` MAY be deleted, modified, or reordered after creation. Each new mutation MUST be appended to the end of `H(t)` with a monotonically increasing `index`.

**Verification:** Static analysis. The history log implementation MUST be proven to contain no delete, update, or reorder operations.

**Rationale:** The history log is the audit trail for state mutations. If it can be modified, the provenance chain is compromised and evidence per PR-9 is unreliable.

### INV-STATE-11 — History Log Truncation on Checkpoint

**Statement:**

When a valid checkpoint `Ck` is taken at step `s`, the history log `H` is truncated to empty. All entries in `H` prior to `Ck` are considered incorporated into the checkpoint. Truncation MUST occur atomically with checkpoint finalization.

**Verification:** Runtime assertion. Checkpoint finalization and history-log truncation MUST occur in a single atomic transaction.

**Rationale:** Checkpoints already capture the state at a point in time. Maintaining redundant history entries that are already checkpointed wastes memory without adding information.

---

## Section 7 — Glossary

| Term | Definition | Document |
|---|---|---|
| Execution State (ES) | DEF-1 | state-management.md |
| Working Memory (W) | DEF-2 | state-management.md |
| Checkpoint (Ck) | DEF-3 | state-management.md |
| State Handoff | DEF-4 | state-management.md |
| State Migration | DEF-5 | state-management.md |
| History Log | DEF-6 | state-management.md |
| UNBOUND | Marker for uninitialized output | state-management.md |
| PENDING | Marker for in-progress computation | state-management.md |
| Reusable Module | Module in both old and new plan | state-management.md |
| Retired Module | Module only in old plan | state-management.md |
| New Module | Module only in new plan | state-management.md |

---

## Section 8 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |