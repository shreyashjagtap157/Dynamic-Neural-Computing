# Formal Model

## Metadata

| Field | Value |
|---|---|
| Document | formal-model.md |
| Title | Formal Model |
| Document ID | SPEC-FORMAL |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 3 |
| Owner Question | How is execution represented mathematically? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

This document provides the mathematical representation of the DNC runtime's execution semantics. It defines the formal notation used across all specification documents, the state transition semantics, the properties of execution graphs, and the proof obligations that must be satisfied by any compliant implementation.

The formalism chosen is **trace semantics** — each execution is modeled as a sequence of states and events, enabling reasoning about all possible executions. Trace semantics is appropriate for the DNC runtime because:
1. It handles nondeterminism (from input signals and scheduling choices) naturally
2. It supports refinement reasoning (comparing implementations against specifications)
3. It provides a basis for model checking (the state space can be explored exhaustively for finite configurations)
4. It aligns with the provenance model, where each event in a trace has a causal lineage

This document defines notation conventions (Section 2), the formal state model including clock (Section 3), event algebra (Section 4), execution traces (Section 5), graph-theoretic properties of execution graphs (Section 6), checkpoint and restore transitions (Section 7), failure-integrated step transitions (Section 8), metric-to-trace mapping (Section 9), liveness properties (Section 10), and the key theorems with proper proof plans (Section 11).

**Key changes from Draft DR-1:**
- Added wall-clock time formalization and Clock relation to step_index
- Extended step transition to handle the full five-class failure taxonomy
- Added checkpoint and restore as formal transition relations
- Added event algebra with typed constructors
- Added metric-to-trace mapping for evaluation
- Added liveness: progress, termination, deadlock freedom
- Extended graph refinement (DEF-FM-9) to include byte-exact state preservation
- Replaced "proof sketches" with structured proof plans

---

## Section 2 — Notation Conventions

### 2.A Sets and Functions

- `ℕ` denotes the set of non-negative integers `{0, 1, 2, ...}`
- `ℝ_{\ge 0}` denotes the set of non-negative real numbers
- `A → B` denotes the set of total functions from A to B
- `A × B` denotes the Cartesian product of A and B
- `⊆` denotes subset; `⊂` denotes strict subset
- `∈` denotes membership; `∉` denotes non-membership
- `∅` denotes the empty set
- `|S|` denotes the cardinality of set S
- `P(A)` denotes the power set of A

### 2.B Tuples and Records

- `(a, b, c)` denotes an ordered triple
- `π_i` denotes the projection of a tuple onto its i-th component
- `{a ↦ b}` denotes a function with domain `{a}` and value `b`
- `f[x ↦ y]` denotes function update: f' = f except f'(x) = y
- `dom(f)` denotes the domain of function f
- `ran(f)` denotes the range of function f

### 2.C Sequences

- `[s_0, s_1, ..., s_n]` denotes a finite sequence
- `ε` denotes the empty sequence
- `s ⌢ t` denotes sequence concatenation
- `s[i]` denotes the i-th element (0-indexed)
- `|s|` denotes the length of sequence s

### 2.D Time

- `Clock` denotes the wall-clock time in milliseconds since epoch, `Clock ∈ ℝ_{\ge 0}`
- `step_index ∈ ℕ` denotes the logical step count
- `ClockRel(σ, t_c)` denotes the relation between step_index σ and wall-clock time t_c

### 2.E Graphs

- `G = (V, E, w)` denotes a directed graph with vertices V, edges E ⊆ V × V, and weight function `w: V → ℝ_{\ge 0}`
- `pred_G(v) = {u ∈ V | (u, v) ∈ E}` denotes the set of predecessors of v
- `succ_G(v) = {w ∈ V | (v, w) ∈ E}` denotes the set of successors of v
- A **topological ordering** of G is a total order ≤ on V such that for every (u, v) ∈ E, u ≤ v

### 2.F Execution State

- `ES(t)` denotes the execution state at step index t (see `state-management.md` DEF-1)
- `W(t)`, `M(t)`, `C(t)`, `H(t)`, `R(t)` denote the components of `ES(t)` as defined in `state-management.md` DEF-1
- `R(t)` is the RNG state, derived from the execution header's `Random Seed` at initialization. It is advanced deterministically by each stochastic module invocation.
- `ES(t) ⊑ ES(t')` denotes that ES(t') is reachable from ES(t) by a valid sequence of transitions (defined in Section 5)
- `ES ⊨ INV-k` denotes that invariant INV-k holds at configuration ES

---

## Section 3 — Formal State Model

### DEF-FM-1 — Runtime Configuration

**Definition:**

A **runtime configuration** `κ` is a tuple:

```
κ = (Registry, KB, Executions, Clock)
```

Where:
- `Registry` is the module registry — a total function `ModuleTypeID → Contract`
- `KB` is the knowledge base — a versioned tuple `(KB_state, KB_version)` per `../layer-6-evolution/continual-learning.md` DEF-CL-5
- `Executions` is the set of active executions — a set of execution records `{Exec_1, ..., Exec_n}`
- `Clock` is the current wall-clock time in milliseconds since epoch

### DEF-FM-2 — Execution Record

**Definition:**

An **execution record** `ε` is a tuple:

```
ε = (ExecutionID, H_exec, ES, G, step_index, state, provenance_log, R)
```

Where:
- `ExecutionID` is the unique identifier
- `H_exec` is the execution header (per `execution-model.md` DEF-EXEC-2)
- `ES` is the execution state ES(0) at initialization
- `G` is the current execution graph
- `step_index` is the current step number, `step_index ∈ ℕ`
- `state` ∈ {RUNNING, IDLE, TERMINATED, FAILED}
- `provenance_log` is the append-only provenance record
- `R(t)` is the RNG state, tracking the random number generator position for reproducibility. `R(t)` is initialized from the `Random Seed` field of `H_exec` at execution start and is advanced deterministically by each stochastic module invocation.

**Note:** `R(t)` is part of `ES(t)` indirectly through the execution state, enabling deterministic replay per INV-CTRL-3. The trace is fully deterministic given the execution header's `Random Seed`.

### DEF-FM-3 — Clock Relation

**Definition:**

The **clock relation** defines the relationship between logical step count and physical time:

```
ClockRel(σ, t_c) ⟺ there exists a trace τ of length σ such that the i-th step in τ
                   completes at wall-clock time t_c(i) and t_c = (t_c(0), ..., t_c(σ-1))
```

**Axiom AX-1 — Clock Monotonicity:** Step completion times are monotonically non-decreasing:

```
∀i, j ∈ ℕ: i ≤ j ⟹ t_c(i) ≤ t_c(j)
```

**Axiom AX-2 — Step Index Advancement:** Each step takes at least one unit of logical time:

```
∀i ∈ ℕ: step_index after step i = i + 1
```

This axiom separates logical ordering (step_index) from physical time (Clock). Latency budget invariants in `control-loop.md` constrain t_c values, not σ values.

---

## Section 4 — Event Algebra

### DEF-FM-4 — Event Type System

**Definition:**

Events are classified by a **typed event algebra**. Each event constructor carries a typed payload:

```
EventConstructor ::= STEP_DISPATCHED(module_instance_id, step_index, cost, time_budget)
                    | STEP_COMPLETED(module_instance_id, step_index, output_value, cost_actual, outcome)
                    | STEP_FAILED(module_instance_id, step_index, failure_classification, recoverable)
                    | CHECKPOINT_CREATED(checkpoint_id, step_index, provenance_ref)
                    | CHECKPOINT_RESTORED(checkpoint_id, step_index_before, step_index_after)
                    | REPLAN_TRIGGERED(trigger_type, trigger_subtype, step_index, replan_counter)
                    | DECISION(decision_type, observe_summary_hash, execution_state_hash)
                    | MODULE_REGISTERED(module_type_id, version, contract_hash)
                    | MODULE_DEREGISTERED(module_type_id, version)
                    | LEARNING_EVENT(event_id, trigger_execution_id, trigger_step, delta_quality)
                    | KB_UPDATE_COMMITTED(kb_version_before, kb_version_after)
                    | EXECUTION_TERMINATED(final_step_index, termination_reason)
```

Each event `e` has:
- `e.event_type`: the constructor name
- `e.event_id`: globally unique identifier
- `e.timestamp`: wall-clock time of creation
- `e.execution_id`: the execution this event belongs to
- `e.causal_ref`: event_id of immediate causal antecedent (null for initiating events)
- `e.payload`: the typed payload per the constructor
- `e.integrity_hash`: cryptographic hash for tamper detection

**Note:** This event algebra satisfies the requirement in the prior formal model review that events be typed rather than generic. Every transition in the formal model is labeled with a specific event constructor.

---

## Section 5 — Execution Traces

### DEF-FM-5 — Execution Trace

**Definition:**

An **execution trace** `τ` is a finite sequence alternating between execution states and events:

```
τ = [ES(0), e_0, ES(1), e_1, ES(2), ..., ES(n)]
```

Where:
- `ES(0)` is the initial execution state, initialized per `execution-model.md` DEF-EXEC-3
- `ES(i)` is the execution state after i transitions
- `e_i` is the event that caused the transition from `ES(i)` to `ES(i+1)`, drawn from the event algebra (DEF-FM-4)
- `e_i.causal_ref` is either null (for initiating events) or references `e_j` where `j < i`

The trace is **valid** (`ValidTrace(τ)`) if and only if:
1. `ES(0)` is initialized per `execution-model.md` DEF-EXEC-3 with non-null execution header
2. For each `i ∈ [0, n-1]`, the transition `ES(i) ⊢ e_i ⇝ ES(i+1)` is a **valid transition** (defined in Section 8)
3. All invariants from `../layer-2-invariants/runtime-invariants.md` hold at every `ES(i)` — i.e., `∀i ∈ [0, n]: ES(i) ⊨ ∧_{k=1}^{11} INV-k`
4. The causal chain is unbroken: for every `e_i` with `e_i.causal_ref ≠ null`, there exists `j < i` such that `e_j.event_id = e_i.causal_ref`
5. The clock relation holds: `ClockRel(n, (e_0.timestamp, ..., e_{n-1}.timestamp))`

### DEF-FM-6 — Trace Reachability

**Definition:**

`ES(t) ⊑ ES(t')` (ES(t') is reachable from ES(t)) if and only if there exists a valid trace `τ = [ES(t), ..., ES(t')]`.

This is the standard reachability definition in trace semantics. The empty trace (zero steps) is a valid trace: `ES ⊑ ES` holds trivially.

### DEF-FM-7 — Invariant Satisfaction

**Definition:**

A trace `τ` **satisfies invariant INV-k** if and only if INV-k holds at every configuration in τ:

```
τ ⊨ INV-k ⟺ ∀i ∈ [0, |τ|-1]: ES(i) ⊨ INV-k
```

Where `ES(i) ⊨ INV-k` denotes that invariant INV-k evaluates to true at `ES(i)`.

### DEF-FM-8 — Invariant Preservation

**Definition:**

A transition `ES(t) ⊢ e ⇝ ES(t+1)` **preserves invariant INV-k** if and only if:

```
(ES(t) ⊨ INV-k) ⟹ (ES(t+1) ⊨ INV-k)
```

The transition **strictly preserves** INV-k if the converse also holds (no new invariant holds that wasn't already true).

---

## Section 6 — Execution Graph Formal Properties

### DEF-FM-9 — Execution Graph as Annotated DAG

**Definition:**

An execution graph `G = (V, E, w)` where:
- `V` is the set of module instances (vertices), each labeled with a `(ModuleTypeID, ModuleInstanceID)` pair
- `E ⊆ V × V` is the set of data-dependency edges (handoffs)
- `w: V → ℝ_{\ge 0}` assigns a cost weight to each vertex

**Axiom AX-3 — DAG Acyclicity:** `G` is a DAG — there is no cycle in the edge relation E. This is verified by topological sort before dispatch (INV-2 in `../layer-2-invariants/runtime-invariants.md`).

### DEF-FM-10 — Graph Refinement with State Preservation

**Definition:**

`G_new` is a **refinement** of `G_old` with state preservation if and only if:

1. `V_old ⊆ V_new` (all original nodes are retained or superseded by compatible replacements)
2. `E_old ⊆ E_new` (all original edges are retained)
3. For every `v ∈ V_old ∩ V_new` (retained node), `w_new(v) ≤ w_old(v)` (no more expensive)
4. For every `v ∈ V_old ∩ V_new` (retained node), the working memory `W(v)` is preserved byte-exact from `ES(t)` to `ES(t')`

**Clause 4** addresses the formal methods reviewer's concern: the original DEF-FM-9 (graph refinement) did not capture byte-exact state preservation. This extended definition adds it as a formal clause. "Byte-exact preservation" means: for each retained node `v`, the memory address range of `W(t')[v]` is identical to the memory address range of `W(t)[v]`, and all bytes in that range are identical in value.

### THM-EXEC-1 — Topological Sort Existence

**Theorem:** Every execution graph G produced by the planner is a DAG, and therefore admits a topological ordering.

**Proof Plan:**
1. The planner is required per `../layer-4-mechanisms/planner-pipeline.md` INV-PLANNER-5 to verify acyclicity before returning SUCCESS(G)
2. INV-2 (runtime-invariants.md) requires the scheduler to verify acyclicity before dispatch
3. Therefore any G that reaches the scheduler satisfies acyclicity by construction
4. By graph theory (Kahn's algorithm), a finite directed acyclic graph always admits at least one topological ordering ∎

### THM-EXEC-2 — Step Precondition Implication

**Theorem:** In a topologically sorted execution, for any step s_i with input bindings from predecessors `pred_G(s_i)`, all predecessors have completed and their outputs are committed before s_i is dispatched.

**Proof Plan:**
1. Topological sort produces total order ≤ on V such that for all (u, v) ∈ E, u ≤ v
2. Dispatch order follows this order: nodes are dispatched in non-decreasing order of their position in the sort
3. For an edge (u, v), dispatch(u) < dispatch(v) by (1)
4. A node's output is committed to working memory upon completion of its step transition (Section 8)
5. v's precondition requires all inputs bound — by (3), u's output is committed before dispatch(v)
6. Therefore all predecessors have completed and delivered outputs before v is dispatched ∎

---

## Section 7 — Checkpoint and Restore Transitions

### DEF-FM-11 — Checkpoint Transition

**Definition:**

A **checkpoint transition** `ES(t) ⊢ checkpoint(Ck) ⇝ ES(t)` captures a snapshot of the current execution state without advancing the step index:

```
checkpoint(Ck) produces Ck = (step_index, execution_id, timestamp, es_snapshot, provenance_ref)
where:
  es_snapshot = ES(t)  -- complete copy of current state
  timestamp = Clock   -- current wall-clock time
  step_index = ε.step_index   -- current step index (unchanged by checkpoint)
  provenance_ref = event_id of the CHECKPOINT_CREATED event
```

The transition relation is:

```
ES(t) ⊢ checkpoint(Ck) ⇝ ES(t)   -- state unchanged, checkpoint recorded
```

The checkpoint is **valid** (`ValidCheckpoint(Ck, ES(t))`) if and only if:
1. `es_snapshot = ES(t)` — complete and unmodified
2. `provenance_ref` resolves to a valid CHECKPOINT_CREATED event in the provenance log
3. `step_index = ε.step_index` — matches the execution record's step index
4. All fields of `ES(t)` are non-null (no UNBOUND or PENDING in W(t) except for nodes not yet dispatched)
5. `ES(t) ⊨ ∧_{k=1}^{11} INV-k` — all active invariants hold at the checkpoint source configuration. This prevents restoration of an invariant-violating state.

**Well-definedness:** The validity conditions are mutually independent and collectively necessary. Conditions 1–4 ensure syntactic well-formedness; condition 5 ensures semantic correctness. A checkpoint satisfying conditions 1–4 but violating condition 5 is syntactically valid but restores an invariant-violating state — which is why condition 5 is required.

### DEF-FM-12 — Restore Transition

**Definition:**

A **restore transition** `Ck ⊢ restore ⇝ ES(t)` recovers a prior execution state from a checkpoint:

```
Ck ⊢ restore ⇝ ES'(t')
where:
  ES'(t') = Ck.es_snapshot   -- byte-exact copy of the checkpointed state
  t' = Ck.step_index          -- step index restored
  ε'.step_index = t'          -- execution record updated
  ε'.state = ε.state          -- execution state preserved through restore
```

**INV-FM-1 — Restore Does Not Modify Checkpoint:** The checkpoint record `Ck` is immutable. The restore operation does not alter `Ck`; it creates a copy of `es_snapshot` as the current `ES'`.

**INV-FM-2 — Restore Advances Step Index Linearly:** After restore, `step_index` is set to `Ck.step_index`. Subsequent steps continue from that index. No step index is repeated or skipped.

---

## Section 8 — Step Transitions with Failure Taxonomy

### DEF-FM-13 — Failure Classification Integration

**Definition:**

The step transition (DEF-FM-3) is extended to incorporate the full five-class failure taxonomy from `../layer-5-observability/failure-taxonomy.md`:

The step transition result is a tagged union:

```
StepResult ::= SUCCESS(o_i, cost_actual, metadata)
             | FAILURE_TRANSIENT(retry_count, max_retries, failure_reason)
             | FAILURE_RECOVERABLE(recovery_used, failure_reason)
             | FAILURE_UNRECOVERABLE(module_instance_id, failure_reason)
             | FAILURE_FATAL(module_instance_id, failure_reason, systemic_indicator)
             | FAILURE_CATASTROPHIC(detection_context, corruption_assessed)
```

### DEF-FM-14 — Full Step Transition Relation

**Definition:**

A **step transition** `ES(t) ⊢ s_i ⇝ ES(t+1)` with step result `r` is defined as:

**Precondition:** For `ES(t) ⊢ s_i ⇝ ES(t+1)` to be valid:
1. `s_i` is in the ready set (all predecessors completed, all inputs bound)
2. `ES(t) ⊨ INV-EXEC-1` (precondition before dispatch)
3. `ES(t).state = RUNNING`

**Transition:**
1. Assert precondition(s_i) satisfied
2. Set `W(t)[n_i].output = PENDING`
3. Record step start time `t_start = Clock`
4. Invoke module `n_i` with inputs B, producing result `r`
5. If `r = SUCCESS(o, c, m)`: set `W(t+1)[n_i] = (input: B, output: o, metadata: m)`; increment step_index; record STEP_COMPLETED event
6. If `r = FAILURE_TRANSIENT`: apply retry policy per `../layer-5-observability/failure-taxonomy.md`; if retry succeeds, transition as SUCCESS; if MAX_TRANSIENT_RETRIES exceeded, reclassify as FAILURE_RECOVERABLE
7. If `r = FAILURE_RECOVERABLE`: halt dependent dispatch; emit STEP_FAILED with FAILURE_RECOVERABLE; trigger replanning per `replanning-protProtocol.md` INV-REPLAN-2
8. If `r = FAILURE_UNRECOVERABLE`: halt all dependents; emit STEP_FAILED with FAILURE_UNRECOVERABLE; trigger replanning
9. If `r = FAILURE_FATAL`: halt all dependents; emit STEP_FAILED with FAILURE_FATAL; trigger replanning; flag for post-execution audit
10. If `r = FAILURE_CATASTROPHIC`: halt all dispatch immediately; transition execution to FAILED; emit FAILURE_CATASTROPHIC event; archive checkpoint if possible
11. Append step record to `H(t+1)` with step start time, end time, cost, and result classification

**Well-definedness:** Every execution of the step transition produces exactly one result `r` from the tagged union. There are no other cases.

---

## Section 9 — Metric-to-Trace Mapping

### DEF-FM-15 — Evaluation Metric Function

**Definition:**

An **evaluation metric** `m` is a total function from execution traces to real numbers:

```
m: Traces → ℝ
```

The set of all evaluation metrics is denoted `Metrics`. Per `../layer-5-observability/evaluation-suite.md` DEF-EVAL-1, `Metrics` is partitioned into four classes:

- `Metrics_1` (Functional Correctness): task completion, output quality, invariant satisfaction rate
- `Metrics_2` (Dynamic Adaptability): replan frequency, state preservation rate, recovery success rate
- `Metrics_3` (Resource Efficiency): total cost, latency, memory efficiency, energy efficiency
- `Metrics_4` (Continual Learning): capability retention, novel task acquisition, drift bound compliance, learning cost efficiency

### DEF-FM-16 — Metric Value of a Trace

**Definition:**

The **metric value** of a trace `τ` for metric `m` is `m(τ)`. This is defined recursively:

- For a trace with a single step: `m(τ)` is computed from `ES(0)` and `ES(1)` by applying `m` to the step result
- For a trace with multiple steps: `m(τ)` is computed from the aggregate of all step results in the trace

The formal specification does not define the specific functional form of each metric (these are in `../layer-5-observability/evaluation-suite.md`); it only establishes that every `m ∈ Metrics` is a total computable function on traces.

### DEF-FM-17 — Behavioral Drift Between Traces

**Definition:**

The **behavioral drift** between two traces `τ` and `τ'` is:

```
Δ(τ, τ') = max_{m ∈ Metrics} |m(τ) - m(τ')|
```

This formalizes `../layer-6-evolution/continual-learning.md` DEF-CL-2 with the metric function domain explicitly defined as traces.

**Note:** `Metrics` is finite (bounded by the four classes defined in DEF-EVAL-1). The max is well-defined.

### DEF-FM-18 — Trace Satisfaction of a Metric Threshold

**Definition:**

A trace `τ` **satisfies metric threshold** `(m, threshold, op)` if and only if `m(τ) op threshold`, where `op ∈ {≤, <, ≥, >, =}`.

This enables formal statements like: "trace τ satisfies DEGRADATION_TOLERANCE" meaning for all `m ∈ Metrics_1`: `|m(τ) - m(baseline)| ≤ DEGRADATION_TOLERANCE × |m(baseline)|`.

---

## Section 10 — Liveness Properties

The formal model has so far addressed safety (invariant preservation). This section addresses **liveness** — that the system eventually does something good.

### DEF-FM-19 — Enabled Step

**Definition:**

A step `s` is **enabled** at `ES(t)` if and only if:
1. `s` is in the ready set — all predecessor steps have completed and all input bindings are bound
2. `ES(t).state = RUNNING`
3. The step's resource cost `cost(s) ≤ cost_remaining` (INV-SCHED-4)

### DEF-FM-20 — Progress

**Definition:**

The runtime **makes progress** at `ES(t)` if and only if there exists an enabled step `s` such that a valid transition `ES(t) ⊢ s ⇝ ES(t+1)` exists.

**Axiom AX-4 — Progress:** If `ES(t).state = RUNNING` and the ready set is non-empty, then progress is enabled. Formally:

```
ES(t).state = RUNNING ∧ ready_set(ES(t)) ≠ ∅ ⟹ ∃s: Enabled(s, ES(t)) ∧ ValidTransition(ES(t), s, ES(t+1))
```

### DEF-FM-21 — Deadlock

**Definition:**

`ES(t)` is a **deadlock configuration** if and only if:
1. `ES(t).state = RUNNING`
2. `ready_set(ES(t)) ≠ ∅` (there are enabled steps)
3. But no step transition is enabled — every step in the ready set fails its precondition check

**Note:** Deadlock is distinct from the scheduler reaching `ready_set = ∅ ∧ blocked_set = ∅` (normal completion). A deadlock configuration has non-empty ready set but no valid transitions.

### DEF-FM-22 — Starvation Freedom

**Definition:**

A trace `τ` is **starvation-free** if and only if every enabled step eventually completes or fails (is reclassified as a terminal result):

```
∀t, ∀s: Enabled(s, ES(t)) ⟹ ∃t' ≥ t: step s is not pending at ES(t')
```

That is, no enabled step remains pending indefinitely.

### THM-FM-L1 — Termination

**Theorem:** Every valid trace `τ` with `ES(0).state = RUNNING` terminates in a terminal state (`TERMINATED` or `FAILED`) after a finite number of steps.

**Proof Plan:**
1. The execution graph G is finite (a finite set of module instances per execution initiation)
2. Each step in G is dispatched at most once (steps are not re-executed unless a replan creates a new graph with RETAINED nodes already at completion)
3. The step index `ε.step_index` is a natural number that strictly increases with each successful step completion (INV-FM-2)
4. By well-ordering of ℕ, there cannot be an infinite strictly increasing sequence of step indices
5. The only terminal states are TERMINATED (all steps complete) and FAILED (FAILURE_CATASTROPHIC or unhandled error)
6. Therefore any valid trace must reach a terminal state after a finite number of steps ∎

### THM-FM-L2 — No Pure Deadlock Under Valid Preconditions

**Theorem:** If every step in the ready set has its precondition satisfied, there is no deadlock configuration reachable from a valid trace.

**Proof Plan:**
1. A deadlock configuration requires `ready_set ≠ ∅` but no valid transitions (DEF-FM-21)
2. A step has a valid transition iff its precondition is satisfied (DEF-FM-14, precondition (1))
3. If all steps in `ready_set` have preconditions satisfied, all are enabled (DEF-FM-19)
4. By AX-4 (Progress), every enabled step has a valid transition
5. Therefore a configuration with `ready_set ≠ ∅` where all preconditions are satisfied cannot be a deadlock configuration ∎

**Corollary:** Deadlock can only arise from a precondition failure that is itself a symptom of a prior step failure. This justifies why `../layer-5-observability/failure-taxonomy.md` routes all non-TRANSIENT failures to replanning rather than trying to recover in place.

### THM-FM-L3 — Event-Response Latency Bound

**Theorem:** If an event `e` arrives at wall-clock time `t_e` and the runtime makes progress continuously, then the response action for `e` is committed no later than `t_e + RESP_BUDGET`.

**Proof Plan:**
1. Event `e` is captured in `Observe(i)` where `Observe(i)` runs in the loop iteration with `t(i) ≥ t_e` and `t(i) - t_e < OBSERVE_BUDGET` (INV-CTRL-2)
2. The Observe phase completes by `t(i) + OBSERVE_BUDGET`
3. The Decide phase completes by `t(i) + OBSERVE_BUDGET + DECIDE_BUDGET` (INV-CTRL-4), producing decision D(i)
4. If D(i) = CONTINUE, the Act phase dispatches steps; if D(i) = REPLAN, the replan protocol runs (bounded by REPLAN_BUDGET = DECIDE_BUDGET by convention)
5. The response action is committed when the triggered step or replan is dispatched, which by (2)-(4) is bounded by `t_e + OBSERVE_BUDGET + DECIDE_BUDGET`
6. By configuration: `OBSERVE_BUDGET + DECIDE_BUDGET ≤ RESP_BUDGET` (this must hold for the configuration to be valid)
7. Therefore the action is committed by `t_e + RESP_BUDGET` ∎

**Configuration obligation:** This theorem requires that `OBSERVE_BUDGET + DECIDE_BUDGET ≤ RESP_BUDGET`. This is a configuration constraint that must hold for any deployed configuration.

---

## Section 11 — Key Theorems with Proof Plans

### THM-FM-1 — Invariant Preservation Under Valid Step

**Theorem:** If `ES(t)` satisfies all active invariants and a step `s` is dispatched with its precondition satisfied, then `ES(t+1)` also satisfies all active invariants.

**Structured Proof Plan:**

We prove `ES(t) ⊨ INV-k ⟹ ES(t+1) ⊨ INV-k` for each invariant `k = 1..11` by case analysis on the result `r` of the step transition:

**INV-1 (Execution Header Immutability):**
- The step transition (DEF-FM-14) does not modify `H_exec`
- `ES(t+1).ε.H_exec = ES(t).ε.H_exec`
- Therefore INV-1 is preserved regardless of step result ∎

**INV-2 (DAG Acyclicity):**
- The step adds a completed node to `completed_set`; it does not modify the edge set E
- The dispatch precondition requires topological order (all predecessors completed)
- No new edges are created by step completion; the graph structure is unchanged
- Since G was a DAG at ES(t), it remains a DAG at ES(t+1) ∎

**INV-3 (No Undefined Behavior):**
- Every possible result `r` in the step transition is classified into one of the six cases in DEF-FM-13
- There are no unclassified cases; the result space is exhaustive
- Each case has a defined handling policy (retry, recovery, replan, halt)
- Therefore no step transition produces undefined behavior ∎

**INV-4 (Single-Ownership of Module Semantics):**
- The step transition invokes a module; it does not register or modify module contracts
- `ES(t+1).Registry = ES(t).Registry`
- Therefore INV-4 is preserved ∎

**INV-5 (State Isolation Between Executions):**
- Working memory updates are `W(t+1)[n_i] = ...` (single assignment, DEF-FM-14)
- All working memory modifications are namespaced by ExecutionID (part of ES, which is per-execution)
- The step transition does not access or modify working memory of other executions
- Therefore INV-5 is preserved ∎

**INV-6 (Checkpoint Before Replan):**
- The step transition does not invoke the planner (planner invocation is a separate transition type)
- The step transition is defined to run during the Act phase, which (per INV-CTRL-6) does not include replanning
- Therefore INV-6 is unaffected by the step transition ∎

**INV-7 (Handoff Atomicity):**
- The step transition produces a committed output for the dispatched module `n_i`
- Handoff atomicity (two-phase commit) is enforced at the scheduler level (INV-SCHED-7), not during module execution
- The step transition records the output; the scheduler's handoff protocol handles atomic commit separately
- Therefore INV-7 is preserved independently of step execution ∎

**INV-8 (All Invariants Verified Before Execution):**
- This invariant applies at execution initiation, not during step execution
- It constrains the pre-execution check, not individual step transitions
- The step transition does not invalidate the pre-execution verification ∎

**INV-9 (Bounded Drift):**
- The step transition does not modify the knowledge base `KB`
- The step transition does not modify the execution history `H` in a way that changes prior metric values
- Drift is a function of traces (DEF-FM-17); the step transition extends the trace but does not alter prior trace metric values
- Therefore bounded drift is preserved ∎

**INV-10 (Normative Statement Keyword Discipline):**
- This invariant concerns specification documents, not runtime state
- Runtime state transitions do not affect specification text
- Therefore INV-10 is outside the scope of step transition analysis ∎

**INV-11 (Preservation Under Extension):**
- This invariant constrains the amendment process, not runtime execution
- The step transition does not modify the specification
- Therefore INV-11 is outside the scope of step transition analysis ∎

∎ **QED** — All 11 invariants are preserved by a valid step transition.

### THM-FM-2 — Checkpoint Recovery Correctness

**Theorem:** Restoring ES(t) from a valid checkpoint Ck(t) produces a configuration that satisfies all invariants and is reachable from the original execution.

**Structured Proof Plan:**

Let `Ck(t)` be a valid checkpoint and let `ES'(t') = Ck(t).es_snapshot` after restore.

**Invariant satisfaction:**
1. A valid checkpoint (DEF-FM-11) requires that all components of `ES(t)` are non-null (condition 4 of ValidCheckpoint)
2. By definition of a valid trace, `ES(t) ⊨ ∧_{k=1}^{11} INV-k`
3. `ES'(t')` is a byte-exact copy of `ES(t)` (DEF-FM-12)
4. Byte-exact copy preserves the truth value of all invariants (each invariant is a predicate on state components)
5. Therefore `ES'(t') ⊨ ∧_{k=1}^{11} INV-k` ∎

**Reachability:**
1. The empty trace `ε = []` is a valid trace (zero transitions, zero steps)
2. The restore operation creates `ES'(t')` from `Ck(t).es_snapshot`
3. The checkpoint itself was produced by a valid `checkpoint(Ck) ⇝` transition from `ES(t)` (DEF-FM-11)
4. Therefore the trace `[ES(t), checkpoint(Ck), ES(t)]` is a valid trace
5. The restore creates `ES'(t') = ES(t)` (byte-exact copy), so `ES'(t') ⊑ ES(t)` and `ES(t) ⊑ ES'(t')`
6. Since `ES'(t') = ES(t)` by byte-exact copy, reachability holds trivially ∎

**Note:** This proof requires that `Ck` is taken when `ES(t)` is invariant-satisfying. A checkpoint taken at a moment when invariants are violated would be "valid" by DEF-FM-11's syntactic criteria but would restore a violating state. INV-STATE-2 in state-management.md now explicitly requires DEF-FM-11 validation (including condition 5) before replanning, ensuring alignment between the formal model and operational definition.

### THM-FM-3 — Replan State Migration Correctness

**Theorem:** After a successful replan with state migration per `replanning-protocol.md`, the new execution state ES'(t') satisfies all invariants and is reachable from ES(t) via a valid replan sequence.

**Structured Proof Plan:**

Let `τ_replan = [ES(t), e_check, ES(t), e_diff, ES(t), e_migrate, ES(t), e_validate, ES(t), e_handoff, ES'(t')]` be the 6-step replan sequence from `replanning-protocol.md` Section 5.1.

**Checkpoint existence (Step 2):**
1. `e_check` is a CHECKPOINT_CREATED event produced by the checkpoint transition `ES(t) ⊢ checkpoint ⇝ ES(t)` (DEF-FM-11)
2. By INV-REPLAN-9, this checkpoint must be valid before Step 3 proceeds
By condition 5 of DEF-FM-11, the checkpoint source ES(t) is invariant-satisfying, satisfying the syntactic completeness assumption without additional justification.

**State migration (Step 4):**
1. For each RETAINED node `v`: `W(t')[v] = W(t)[v]` byte-exact (INV-REPLAN-10 / INV-STATE-7)
2. Byte-exact state preservation means all working memory for retained nodes is unchanged
3. For each RETIRED_EARLY node: state is archived to provenance log (INV-REPLAN-11 / INV-STATE-8) — this removes it from active state but does not affect invariants
4. For each NEW node: initialized per INV-STATE-9 — all buffers are bound, satisfying preconditions

**Graph validation (Step 5):**
1. INV-PLANNER-5 verifies G_new is a DAG (topological sort succeeds)
2. INV-PLANNER-4 verifies all inputs are bound
3. INV-PLANNER-7 verifies all checklist items including type compatibility and resource budget

**Combined:**
- All invariants are preserved through each step of the replan sequence (THM-FM-1 applied to each transition)
- If any validation fails, INV-REPLAN-12 triggers rollback to the checkpoint, producing `ES(t)` again
- Only successful validation commits `ES'(t')`
- Therefore `ES'(t') ⊨ ∧ INV-k` for all k ∎

**Reachability:**
- The full replan sequence consists of valid transitions (each step in Section 5.1 is a valid transition per its definition)
- Therefore `ES(t) ⊑ ES'(t')` via the replan trace ∎

**Limitation:** This proof assumes the refinement definition (DEF-FM-10) is satisfied by the graph diff. The proof does not verify clause 4 of DEF-FM-10 — it assumes byte-exact preservation holds. Formal verification of byte-exact preservation requires a memory model that is outside the scope of trace semantics (it requires a lower-level operational semantics).

### THM-FM-4 — Bounded Drift Under Continual Learning

**Theorem:** If a knowledge base update passes the verification protocol (INV-CL-8), then the updated runtime's execution p' has bounded drift from all prior executions: `∀p ∈ H: Δ(p, p') ≤ DRIFT_BOUND`.

**Structured Proof Plan:**

Let `p` be any execution in the history `H` and let `p'` be the updated execution.

**Step 1 (Simulation):** By INV-CL-8 Step 1, the verification protocol simulates the candidate update against the 10 most recent learning events. This does not directly establish drift bounds against all `p ∈ H`.

**Step 2 (Evaluation Suite):** By INV-CL-8 Step 2, the full evaluation suite is run against `p'`, producing metric values `m(p')` for all `m ∈ Metrics`. The evaluation suite is run with MIN_TRIAL_COUNT trials, producing statistically significant metric values.

**Step 3 (Drift Check):** By INV-CL-8 Step 3, the protocol computes `Δ(p, p') = max_{m ∈ Metrics} |m(p) - m(p')|` for each `p ∈ H`. The update is **rejected** if any `Δ(p, p') > DRIFT_BOUND`.

**Conclusion:** Since the verification protocol enforces `Δ(p, p') ≤ DRIFT_BOUND` as a gate (INV-CL-1), and this gate is enforced by runtime assertion before any KB commit, any committed update necessarily satisfies the bounded-drift condition.

**Formal dependency:** This theorem requires that `m(p)` and `m(p')` are formally defined — this is established by DEF-FM-15 and DEF-FM-16. The theorem holds formally given these definitions.

∎ **QED**

---

## Section 12 — Known Formal Gaps

The following gaps are acknowledged and require resolution before Baseline v1:

**G-12.1 — Checkpoint Validity Does Not Require Invariant Satisfaction:** RESOLVED: condition 5 added to ValidCheckpoint in DEF-FM-11 (ES(t) ⊨ ∧_{k=1}^{11} INV-k). Additionally, INV-STATE-2 in state-management.md now explicitly references DEF-FM-11 for replanning checkpoints, resolving the DEF-3 vs DEF-FM-11 inconsistency identified in the review.

**G-12.2 — Byte-Exact Preservation Is Not Formally Verified:** DEF-FM-10 Clause 4 requires byte-exact state preservation, but the formal model does not include a memory model that can express byte-exactness. Resolution: extend the model with a memory address model or accept this as an implementation constraint verified by testing rather than formal proof.

**G-12.3 — INV-8 Bootstrapping:** INV-8 (All Invariants Verified Before Execution) cannot be formally verified within the formal model itself — it is a runtime assertion. This is a fundamental limitation acknowledged in the formal methods review. Resolution: use a verified verifier (proof assistant) for the invariant verification implementation, per PR-5's "formal proof" option.

**G-12.4 — Stochastic Module Interaction with Determinism:** RESOLVED: `R(t)` added to Execution Record (DEF-FM-2) and RNG state formally defined in Section 2.F. The trace is deterministic given the execution header's `Random Seed`.

**G-12.5 — Incremental Replanning:** The formal model only supports full graph replacement (G_new replaces G_old). Incremental graph modification (preserving partial substructure of G_old) is not formalized. This is an extension, not a gap.

---

## Section 13 — Glossary Additions

| Term | Definition | Document |
|---|---|---|
| ClockRel | Relation between step_index and wall-clock time | formal-model.md |
| Event Constructor | Typed event producer (STEP_DISPATCHED, etc.) | formal-model.md |
| ValidTrace | Trace satisfying initialization, transition validity, invariants, causal chain, clock | formal-model.md |
| ValidCheckpoint | Checkpoint satisfying completeness, provenance, step_index, non-null state | formal-model.md |
| Restore Transition | Ck ⊢ restore ⇝ ES' recovering checkpointed state | formal-model.md |
| Failure-Tagged Result | SUCCESS / FAILURE_TRANSIENT / FAILURE_RECOVERABLE / FAILURE_UNRECOVERABLE / FAILURE_FATAL / FAILURE_CATASTROPHIC | formal-model.md |
| Enabled Step | Step whose preconditions are satisfied at a given ES | formal-model.md |
| Deadlock Configuration | RUNNING state with non-empty ready set but no valid transitions | formal-model.md |
| Starvation Freedom | No enabled step remains pending indefinitely | formal-model.md |
| Evaluation Metric | Total function m: Traces → ℝ | formal-model.md |
| Metric Value | m(τ) — the real value of metric m for trace τ | formal-model.md |
| Behavioral Drift | Δ(τ, τ') = max_m |m(τ) - m(τ')| | formal-model.md |

---

## Section 14 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| FM-AMEND-001 | formal-model.md | 2026-07-09 | Draft DR-2: Added clock formalization (AX-1, AX-2, DEF-FM-3), event algebra (DEF-FM-4), failure taxonomy integration (DEF-FM-13, DEF-FM-14), checkpoint/restore transitions (DEF-FM-11, DEF-FM-12), metric-to-trace mapping (DEF-FM-15 to DEF-FM-18), liveness theorems (THM-FM-L1 to THM-FM-L3), extended graph refinement with state preservation (DEF-FM-10), replaced proof sketches with structured proof plans, added Section 12 (Known Formal Gaps) | No |