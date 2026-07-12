# Replanning Protocol

## Metadata

| Field | Value |
|---|---|
| Document | replanning-protocol.md |
| Title | Replanning Protocol |
| Document ID | SPEC-REPLAN |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 3 |
| Owner Question | Under what conditions does the planner produce a new execution graph mid-execution, how is partial progress preserved, and how does the thinker continue without restarting? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

Static thinkers execute one pre-determined computation graph from input to output. Dynamic thinkers — the purpose of the DNC runtime — must be capable of revising their execution strategy mid-computation when conditions change, errors emerge, or new information invalidates the current plan. This revision process is called **replanning**, and this document specifies the protocol governing when, how, and under what constraints replanning occurs.

Replanning is not a failure mode. It is a first-class operational capability of the runtime, as central to dynamic computation as error handling is to reliable systems. This document specifies: (a) the conditions that trigger replanning, (b) the protocol for preserving partial progress, (c) the state migration process from old plan to new plan, (d) the conditions under which replanning is forbidden, and (e) the guarantees that hold during and after replanning.

Replanning operates at Layer 3 because it defines operational semantics of the execution model that are independent of any specific planner implementation.

---

## Section 2 — Trigger Classification

### DEF-REPLAN-1 — Replan Trigger

**Definition:**

A **replan trigger** is an event that, when observed by the runtime, causes the planner to be invoked for a new execution graph. Triggers are classified as **internal** (originating within the runtime) or **external** (originating from the environment or user).

### 2.A Internal Triggers

The following events MUST be treated as replan triggers:

**INV-REPLAN-1 — Step Deadline Exceeded**

If the wall-clock time since the current step began exceeds the step's configured time budget, the runtime MUST trigger replanning. The current step MAY be terminated early or allowed to complete, at the scheduler's discretion, but the planner MUST be invoked to produce a revised graph.

*Verification:* Runtime assertion on a timer. The timer MUST be checked after every atomic execution unit within a step.

**INV-REPLAN-2 — Module Failure**

If a module instance produces a failure classification (per `../layer-5-observability/failure-taxonomy.md`) of `FAILURE_FATAL` or `FAILURE_UNRECOVERABLE`, the runtime MUST trigger replanning immediately after the failure is classified. Execution of the failed module's downstream dependents MUST be halted.

*Verification:* Runtime assertion. The scheduler MUST subscribe to the failure classification system and invoke the replan trigger upon receiving a `FAILURE_FATAL` or `FAILURE_UNRECOVERABLE` event.

**INV-REPLAN-3 — Output Confidence Degradation**

If the output of a module instance falls below its configured confidence threshold (per the module's contract), the runtime SHOULD trigger replanning. This is a SHOULD-trigger (not MUST) because degraded confidence may be within acceptable bounds for the current task.

*Verification:* Runtime assertion on the confidence signal. The threshold value is per-module and specified in the module's registry entry.

**INV-REPLAN-4 — Resource Exhaustion Forecast**

If the cost semantics system (per `../layer-4-mechanisms/cost-semantics.md`) forecasts that the remaining execution steps will exceed available resource budget before completion, the runtime MUST trigger replanning to produce a lower-cost graph.

*Verification:* Forecast check at each step boundary. The cost estimator MUST emit a trigger when the forecast crosses the remaining budget threshold.

### 2.B External Triggers

**INV-REPLAN-5 — User Directive**

If the user or an external orchestrator issues a `REPLAN` directive with a rationale, the runtime MUST accept it as a replan trigger. The rationale MUST be recorded in the provenance log. The runtime MAY reject a `REPLAN` directive if it would violate INV-REPLAN-7 (replan frequency bound).

*Verification:* The orchestrator interface MUST validate that `REPLAN` directives are well-formed and carry a non-null rationale before passing them to the runtime.

**INV-REPLAN-6 — Environmental Change Signal**

If the runtime receives an environmental change signal indicating that a precondition of the current plan is no longer valid (e.g., data source unavailable, external service degraded), the runtime MUST treat this as a replan trigger. The signal MUST be validated before being treated as a trigger.

*Verification:* Signal validation. The runtime MUST confirm the environmental change is not a transient noise event before invoking the planner.

---

## Section 3 — Replan Prohibition

### INV-REPLAN-7 — Replan Frequency Bound

**Statement:**

The runtime MUST NOT trigger replanning more than `MAX_REPLANS_PER_EXECUTION` times within a single execution. If this bound is reached, the runtime MUST either (a) complete execution with the current plan, or (b) halt execution with a `REPLAN_EXHAUSTED` error classification per `../layer-5-observability/failure-taxonomy.md`. The value of `MAX_REPLANS_PER_EXECUTION` is a runtime configuration parameter with a default of 3.

*Verification:* Runtime assertion. The replan counter MUST be incremented atomically with each replan trigger and checked before accepting a new trigger.

*Rationale:* Without a bound, a malfunctioning or adversarial planner could trigger unbounded replan loops, consuming resources indefinitely without producing output.

### INV-REPLAN-8 — Replan During Critical Section

**Statement:**

The runtime MUST NOT accept a replan trigger while executing within a **critical section** — a sequence of steps designated as indivisible by the planner. A critical section is identified by a boolean flag on the execution graph nodes. While inside a critical section, all replan triggers MUST be queued and processed only after the critical section completes.

*Verification:* Runtime assertion. The scheduler MUST maintain a critical-section flag and block replan trigger processing while it is set.

*Rationale:* Replanning mid-critical-section would leave the execution in an indeterminate state — part of an indivisible operation would be undone while the rest would remain, violating atomicity expectations.

### INV-REPLAN-9 — Replan on Checkpoint Boundary Only

**Statement:**

Replanning MUST only be initiated at a checkpoint boundary. The runtime MUST NOT accept a replan trigger between steps within an execution graph unless a checkpoint exists at the current step. If no checkpoint is available at the current step, the runtime MUST first take a checkpoint of the current execution state (per `state-management.md` INV-STATE-2) before invoking the planner.

*Verification:* Runtime assertion. The planner pipeline MUST confirm a valid checkpoint exists per DEF-FM-11 (formal-model.md) before accepting a replan request.

*Rationale:* Without a checkpoint, there is no stable state to migrate from. Replanning mid-step without a checkpoint would require rolling back an incomplete step, which has no defined rollback semantics. DEF-FM-11 adds an invariant-satisfaction requirement (condition 5) beyond DEF-3's syntactic completeness. This ensures replanning checkpoints are taken only from sound states.

---

## Section 4 — Partial Progress Preservation

### DEF-REPLAN-2 — Execution Graph Diff

**Definition:**

An **execution graph diff** is the comparison between the old execution graph `G_old` and the new execution graph `G_new`, producing three disjoint sets:
- `RETAINED`: nodes present in both `G_old` and `G_new`
- `RETIRED_EARLY`: nodes present in `G_old` but not in `G_new`, where the node was not completed before the replan trigger
- `NEW`: nodes present in `G_new` but not in `G_old`

### INV-REPLAN-10 — Retained Node State Preservation

**Statement:**

For every node `n` in the `RETAINED` set, the execution state `W(n)` at the moment of the replan trigger MUST be preserved in the new execution state. The preserved state MUST be byte-exact. The new graph MUST initialize `n` with the preserved `W(n)` as its starting state; no re-execution of `n` is required unless `n`'s output in `W(n)` is `UNBOUND` or `PENDING`.

*Verification:* State comparison assertion. The planner MUST confirm for each retained node that `W(post_replan)[n]` equals `W(pre_replan)[n]` before the new graph begins execution.

*Rationale:* Retained nodes represent computation already done. Re-executing them wastes resources and may produce different results if stochastic. Preservation maintains both efficiency and determinism.

### INV-REPLAN-11 — Retired-Early Node Handling

**Statement:**

For every node `n` in `RETIRED_EARLY`, the runtime MUST archive the partial execution state to the history log with event type `RETIRED_EARLY` before the new graph begins execution. The archive MUST include the step index of the retirement, the node's partial output (if any), and the module instance ID.

*Verification:* Runtime assertion. The history log MUST contain a `RETIRED_EARLY` event for every node in `RETIRED_EARLY` before the first step of `G_new` executes.

*Rationale:* Partial results from retired nodes may contain useful information even if the node did not complete. Archiving preserves this for provenance and potential later use.

---

## Section 5 — Replan Protocol Sequence

### 5.1 Protocol Steps

When a replan trigger is accepted, the runtime MUST execute the following steps in order:

**Step 1 — Trigger Acceptance**

Validate the trigger against INV-REPLAN-7 (frequency), INV-REPLAN-8 (critical section), and INV-REPLAN-9 (checkpoint boundary). If all pass, accept the trigger and record it in the provenance log with type `REPLAN_TRIGGERED` and the trigger classification.

**Step 2 — Checkpoint Before Replan**

Per INV-STATE-2 in `state-management.md`, take a valid checkpoint of the current execution state `ES(t)`. If the checkpoint is invalid, halt execution with `CHECKPOINT_FAILED` error.

**Step 3 — Compute Graph Diff**

Invoke the planner to compare `G_old` and `G_new` and produce the `RETAINED`, `RETIRED_EARLY`, and `NEW` sets. Record the diff in the provenance log.

**Step 4 — State Migration**

Per INV-REPLAN-10, migrate preserved state for all `RETAINED` nodes. Per INV-REPLAN-11, archive `RETIRED_EARLY` nodes. Per `state-management.md` INV-STATE-9, initialize state for all `NEW` nodes.

**Step 5 — New Graph Validation**

Validate that `G_new` is well-formed: all input dependencies for all nodes are satisfied by either migrated state, archived partial results, or external inputs. If validation fails, roll back to the checkpoint taken in Step 2 and halt with `REPLAN_VALIDATION_FAILED`.

**Step 6 — Handoff to Scheduler**

Pass `G_new` to the scheduler for execution. The execution ID remains the same; only the execution graph is revised. Increment the replan counter.

### 5.2 Rollback

**INV-REPLAN-12 — Checkpoint Rollback**

If any step of the replan protocol fails after Step 2, the runtime MUST roll back to the checkpoint taken in Step 2, restoring `ES(t)` exactly. No partial state from the failed replan attempt is retained. After rollback, execution MAY resume from the checkpointed state or halt with an error classification, at the orchestrator's discretion.

*Verification:* Deterministic replay. The rollback operation MUST be verifiable by replaying the execution from the checkpoint.

*Rationale:* The checkpoint is the contractual guarantee that the runtime can always recover. A failed replan that corrupts the checkpoint breaks this guarantee and must be treated as a catastrophic error.

---

## Section 6 — Glossary

| Term | Definition | Document |
|---|---|---|
| Replan Trigger | DEF-REPLAN-1 | replanning-protocol.md |
| Execution Graph Diff | DEF-REPLAN-2 | replanning-protocol.md |
| RETAINED Nodes | Nodes in both old and new graph | replanning-protocol.md |
| RETIRED_EARLY Nodes | Incomplete nodes from old graph | replanning-protocol.md |
| NEW Nodes | Nodes only in new graph | replanning-protocol.md |
| Critical Section | Indivisible step sequence | replanning-protocol.md |
| REPLAN_EXHAUSTED | Error when replan bound reached | failure-taxonomy.md |
| CHECKPOINT_FAILED | Error when checkpoint invalid | state-management.md |
| REPLAN_VALIDATION_FAILED | Error when new graph invalid | replanning-protocol.md |

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |