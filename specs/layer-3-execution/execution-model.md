# Execution Model

## Metadata

| Field | Value |
|---|---|
| Document | execution-model.md |
| Title | Execution Model |
| Document ID | SPEC-EXEC |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 3 |
| Owner Question | How does execution proceed operationally? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

This document provides the operational semantics of the DNC runtime — what happens, step by step, from the moment an execution is initiated to the moment it terminates or fails. It defines the execution state machine, the step lifecycle, how the scheduler dispatches steps, and how the control loop interacts with execution.

The execution model builds on Layer 2 (invariants that constrain all executions) and Layer 1 (terminology that gives precise names to every concept). It is the bridge between the formal semantics of Layer 3 and the mechanisms of Layer 4, which implement this model.

The execution model does not prescribe a specific scheduler algorithm, module implementation, or hardware platform. It specifies what must happen, not how it is implemented.

---

## Section 2 — Execution State Machine

### DEF-EXEC-1 — Execution State

**Definition:**

An execution is in exactly one of four states: `RUNNING`, `IDLE`, `TERMINATED`, or `FAILED`. The execution state machine is deterministic: given the current state and an event, the next state is uniquely determined.

```
RUNNING → (decision = TERMINATE) → TERMINATED
RUNNING → (all steps complete) → TERMINATED
RUNNING → (failure classification = FAILURE_CATASTROPHIC) → FAILED
RUNNING → (decision = IDLE) → IDLE
IDLE → (external signal arrives) → RUNNING
IDLE → (decision = TERMINATE) → TERMINATED
IDLE → (failure classification = FAILURE_CATASTROPHIC) → FAILED
```

### DEF-EXEC-2 — Execution Header

**Definition:**

The execution header is the eight-field immutable tuple committed at execution initiation:

```
H_exec = (ExecutionID, SpecVersion, RuntimeVersion, PlannerVersion,
          RegistryVersion, ConfigHash, RandomSeed, Timestamp)
```

Per INV-1, all fields MUST be non-null and resolvable. The header is immutable for the lifetime of the execution.

### DEF-EXEC-3 — Execution Initiation

**Definition:**

**Execution initiation** is the process of:
1. Validating the execution header H_exec
2. Initializing ES(0) = (W(0), M(0), C(0), H(0)) with empty working memory, current module registry snapshot, empty checkpoint record, and empty history log
3. Taking the initial checkpoint Ck_0 (per `state-management.md` INV-STATE-1)
4. Transitioning the execution state to RUNNING
5. Invoking the planner to produce the initial execution graph G_0
6. Passing G_0 to the scheduler

The initiation sequence MUST complete atomically. If any step fails, the execution transitions to FAILED with an initiation error classification.

---

## Section 3 — Step Lifecycle

### DEF-EXEC-4 — Step

**Definition:**

A **step** is the smallest schedulable unit of execution. Each step s_i executes exactly one module instance n_i and produces exactly one output buffer update in working memory. A step is characterized by:

```
s_i = (step_index, module_instance_id, input_bindings, expected_output_type, cost_budget, time_budget)
```

Where `input_bindings` maps each formal parameter of the module's contract to a source (either an external input or the output of a prior step).

### DEF-EXEC-5 — Step Dispatch

**Definition:**

**Step dispatch** is the scheduler's invocation of a step s_i. The dispatch process:

1. Validate all input bindings are bound (per `state-management.md` INV-STATE-5)
2. Set W(t)[n_i].output = PENDING
3. Invoke the module instance n_i with the bound inputs
4. On module completion: set W(t+1)[n_i].output to the module's produced value (or FAILURE_* classification on error)
5. Record step completion in the history log H(t+1)

### DEF-EXEC-6 — Step Completion

**Definition:**

A step s_i is **complete** when W(t+1)[n_i].output is no longer PENDING — it is either a bound value or a failure classification. A completed step's output is available for handoff to downstream steps.

### DEF-EXEC-7 — Step Precondition

**Definition:**

A step s_i's **precondition** is satisfied when all of its input bindings are bound. A step MUST NOT be dispatched unless its precondition is satisfied.

**INV-EXEC-1 — Precondition Before Dispatch:** The scheduler MUST NOT dispatch a step whose precondition is unsatisfied. Attempting to do so is a PRECONDITION_VIOLATION and MUST halt execution.

---

## Section 4 — Execution Graph Dispatch

### DEF-EXEC-8 — Execution Graph Dispatch

**Definition:**

**Execution graph dispatch** is the process of the scheduler invoking steps of an execution graph G in topologically sorted order. The dispatch order is a topological sort of G such that all predecessors of a node are dispatched before the node itself.

### INV-EXEC-2 — Topological Order Enforcement

**Statement:** The scheduler MUST dispatch steps in a topological order of G. No step MAY be dispatched before all its input-producing predecessors have completed.

**Verification:** Predecessor completion check. The scheduler maintains a dispatch barrier for each step that is raised until all predecessor steps have completed.

### INV-EXEC-3 — Single-Step Atomicity

**Statement:** A step s_i is atomic with respect to dispatch — it is either fully dispatched and completed, or it is not dispatched at all. Partial dispatch is not permitted. If a step's execution is interrupted (by a time budget exceeded, a critical section exit, or a failure), the step is treated as failed, not partially complete.

**Verification:** Step completion assertion. The scheduler MUST confirm either full completion or a recorded failure before proceeding to the next step.

---

## Section 5 — Execution State Transitions

### INV-EXEC-4 — State Machine Transition Determinism

**Statement:** The execution state machine is deterministic. Given execution state ES(t) and an event E(t), the next state S(t+1) is uniquely determined. Non-deterministic state transitions are forbidden.

**Verification:** Formal proof. The state transition function MUST be proven deterministic in `formal-model.md`.

### INV-EXEC-5 — Halt on Catastrophic Failure

**Statement:** Upon classification of a failure as FAILURE_CATASTROPHIC, the execution MUST transition to FAILED state immediately, take a final checkpoint, archive all RETIRED_EARLY states, and emit a FAILURE_CATASTROPHIC event to the provenance log. No further steps MAY be dispatched after a FAILURE_CATASTROPHIC classification.

**Verification:** State assertion on failure classification. The failure classification handler MUST assert the state transition to FAILED before checkpoint finalization.

---

## Section 6 — Control Loop Integration

### DEF-EXEC-9 — Control Loop Integration Point

**Definition:**

The control loop (per `control-loop.md`) and the execution engine interact at defined points:

- The Assess phase of the control loop evaluates the outcome of steps dispatched since the last Assess phase
- The Decide phase receives the assessment and current execution state, and produces a decision D(i)
- If D(i) = CONTINUE, execution proceeds with the current graph
- If D(i) = REPLAN, the replanning protocol is invoked, G is replaced with G_new, and execution resumes
- If D(i) = IDLE, the execution transitions to IDLE state and awaits external signals
- If D(i) = TERMINATE, the execution transitions to TERMINATED state

### INV-EXEC-6 — Control Loop Does Not Interrupt Steps

**Statement:** The control loop's Assess and Decide phases MUST NOT interrupt a step that is currently executing. A step MUST complete (or fail) before the Assess phase runs. Replan triggers received during the Act phase are queued and processed at the next loop iteration's Decide phase.

**Verification:** Phase-order assertion. The Act phase MUST NOT return control to the control loop until the step is complete or a failure is classified.

---

## Section 7 — Glossary

| Term | Definition | Document |
|---|---|---|
| Execution State | RUNNING, IDLE, TERMINATED, FAILED | execution-model.md |
| Execution Header | 8-field immutable tuple | execution-model.md |
| Execution Initiation | Process of starting an execution | execution-model.md |
| Step | Smallest schedulable unit | execution-model.md |
| Step Dispatch | Scheduler invoking a step | execution-model.md |
| Step Completion | Step output is no longer PENDING | execution-model.md |
| Step Precondition | All input bindings are bound | execution-model.md |
| Execution Graph Dispatch | Topological ordering of steps | execution-model.md |
| PRECONDITION_VIOLATION | Error when step precondition unsatisfied | execution-model.md |
| FAILURE_CATASTROPHIC | Immediate halt classification | failure-taxonomy.md |

---

## Section 8 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |