# Scheduler

## Metadata

| Field | Value |
|---|---|
| Document | scheduler.md |
| Title | Scheduler |
| Document ID | SPEC-SCHED |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 4 |
| Owner Question | How are execution graphs scheduled? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

The scheduler is the Layer 4 mechanism responsible for dispatching execution graph steps in the correct order, at the correct time, respecting resource budgets and latency constraints. It receives a validated execution graph G from the planner and produces a sequence of step dispatches that realize the execution.

The scheduler operates between the planning layer (which produces graphs) and the execution model (which defines what a step is). Its primary responsibilities:
1. Maintain the dispatch order (topological sort of G)
2. Enforce step preconditions (all inputs bound before dispatch)
3. Enforce resource budgets (per `cost-semantics.md`)
4. Handle step completion, handoff, and checkpointing
5. Integrate with the control loop (`../layer-3-execution/control-loop.md`) for Assess/Decide phases
6. Route failures to the failure taxonomy (`../layer-5-observability/failure-taxonomy.md`)

The scheduler does not decide what to execute (that's the planner's job) — it only decides when to execute each step given G and current runtime conditions.

**Key changes from Draft DR-1:**
- Added complete scheduler state machine (DEF-SCHED-6, DEF-SCHED-7) with all states, events, guards, and transitions
- Added threading model (Section 9): single-threaded dispatch, scheduler loop architecture, timer implementation
- Added two-phase commit handoff protocol (Section 10): scoped to single-address-space, coordinator assignment, timeout values, abort/rollback

---

## Section 2 — Scheduler State

### DEF-SCHED-1 — Scheduler State

**Definition:**

The scheduler maintains per-execution state:

```
SS = (graph, dispatch_queue, ready_set, completed_set, blocked_set, cost_remaining, step_timer)
```

Where:
- `graph` is the current execution graph G
- `dispatch_queue` is the ordered list of steps ready to dispatch
- `ready_set` is the set of steps whose preconditions are satisfied
- `completed_set` is the set of steps that have fully dispatched and completed
- `blocked_set` is the set of steps whose preconditions are not yet satisfied
- `cost_remaining` is the remaining resource budget
- `step_timer` tracks wall-clock time for the currently executing step

### INV-SCHED-1 — Scheduler State Invariants

**Statement:** The scheduler state MUST satisfy:
- `ready_set ∪ blocked_set ∪ completed_set = V` (all vertices are in exactly one set)
- `ready_set ∩ blocked_set = ∅`, `ready_set ∩ completed_set = ∅`, `blocked_set ∩ completed_set = ∅` (disjointness)
- `cost_remaining ≥ 0` (budget is never negative)

**Verification:** State invariant check after every scheduler state transition.

---

## Section 3 — Dispatch Order

### DEF-SCHED-2 — Dispatch Order Algorithm

**Definition:**

The scheduler computes dispatch order by repeatedly selecting from `ready_set`:
1. Compute the topological ordering of G restricted to ready_set
2. Select the step with the highest priority from ready_set (priority is defined below)
3. Dispatch the selected step
4. Upon completion, update ready_set by moving newly-ready steps from blocked_set
5. Move the completed step to completed_set
6. Repeat until ready_set is empty and blocked_set is empty (all done) or blocked_set is non-empty and ready_set is empty (deadlock)

### DEF-SCHED-3 — Step Priority

**Definition:**

When multiple steps are in ready_set, priority is evaluated in this order:
1. **Critical path priority**: steps that are predecessors of the largest number of unfinished steps (maximizes parallelism)
2. **Deadline priority**: steps with the earliest associated deadline (per cost semantics)
3. **Module preference priority**: steps from modules with higher preference scores (per module contract)
4. **FIFO**: if still tied, dispatch in order of step_index

### INV-SCHED-2 — No Dispatch from Blocked Set

**Statement:** The scheduler MUST NOT dispatch a step that is in blocked_set. A step in blocked_set has unmet preconditions and dispatching it would violate INV-EXEC-1 (precondition before dispatch).

**Verification:** blocked_set membership check immediately before dispatch.

### INV-SCHED-3 — Topological Order Compliance

**Statement:** The scheduler MUST NOT dispatch a step until all of its predecessors have been moved to completed_set. This is a stricter condition than ready_set: a predecessor completing may make a blocked step ready, but dispatch cannot occur until the predecessor is fully completed and its output is committed.

**Verification:** Predecessor completion check before each dispatch.

---

## Section 4 — Step Dispatch Protocol

### DEF-SCHED-4 — Step Dispatch Protocol

**Definition:**

The step dispatch protocol:

```
1. Select step s from ready_set by priority (DEF-SCHED-3)
2. Verify preconditions: all input bindings are bound (per ES(t))
3. Set step_timer = 0; begin wall-clock timer
4. Invoke ES(t) ⊢ s ⇝ ES(t+1) (step transition per formal-model.md)
5. Record completion in history log H(t+1)
6. Stop step_timer; record step cost against cost_remaining
7. If step failed (output is FAILURE_*), classify failure and invoke failure handler
8. Update ready_set, blocked_set, completed_set
9. Check for newly ready steps; if found, move to ready_set
10. Emit STEP_COMPLETED event to provenance log
```

### INV-SCHED-4 — Cost Budget Enforcement

**Statement:** The scheduler MUST verify that cost_remaining ≥ cost(s) before dispatching step s. If cost_remaining < cost(s), the scheduler MUST NOT dispatch s and MUST trigger a resource exhaustion replan per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-4.

**Verification:** Budget check before dispatch. The cost check is atomic with the dispatch decision.

### INV-SCHED-5 — Step Timer Monitoring

**Statement:** The scheduler MUST monitor step_timer against the step's configured time_budget. If time_budget is exceeded, the scheduler MUST either (a) interrupt the step if interruptible, or (b) allow the step to complete if non-interruptible. In either case, a TIME_BUDGET_EXCEEDED event is recorded. If interrupted, a replan is triggered per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-1.

**Verification:** Timer assertion checked at each scheduler loop iteration. The interrupt decision is logged with the step's interruptibility status from the module contract.

---

## Section 5 — Handoff Management

### INV-SCHED-6 — Handoff Before Downstream Dispatch

**Statement:** Before a step s_j is dispatched, the scheduler MUST verify that the handoff from each predecessor s_i is complete — i.e., W(t)[s_j].input is bound for all inputs. If any predecessor's output is not yet committed, s_j remains in blocked_set.

**Verification:** Input binding check per `../layer-3-execution/state-management.md` INV-STATE-5 before each dispatch.

### INV-SCHED-7 — Handoff Atomicity

**Statement:** The scheduler MUST implement the two-phase commit protocol for all handoffs. Phase 1 (prepare): the producing step's output is marked committed. Phase 2 (commit): the consuming step's input is bound to the committed output. Both phases MUST complete atomically or the handoff is rolled back.

**Verification:** Handoff protocol verification per `../layer-3-execution/state-management.md` INV-STATE-6. Model checking of the two-phase commit implementation.

---

## Section 6 — Control Loop Integration

### INV-SCHED-8 — Control Loop Phase Coordination

**Statement:** The scheduler integrates with the control loop as follows:
- The Act phase of the control loop calls the scheduler to dispatch steps for one loop iteration
- The Assess phase receives step completion events from the scheduler
- The scheduler blocks dispatch during the Decide phase (critical section per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-8)
- Replan triggers from the Decide phase cause the scheduler to abort the current dispatch sequence and await a new graph from the planner

**Verification:** Phase-order assertion in the scheduler state machine. The scheduler transitions between DISPATCHING and DECIDE_WAIT states.

### INV-SCHED-9 — Checkpoint Coordination

**Statement:** The scheduler MUST invoke the checkpoint primitive per `../layer-3-execution/state-management.md` INV-STATE-1 immediately after the planner produces a new graph and before the first step is dispatched. The scheduler MUST NOT dispatch any step until the checkpoint is validated.

**Verification:** Checkpoint confirmation check before the first dispatch of any new graph.

---

## Section 7 — Failure Handling

### DEF-SCHED-5 — Failure Routing

**Definition:**

When a step produces a failure classification f ∈ FAILURE_*, the scheduler:
1. Records f in W(t)[n_i].output
2. Routes f to `../layer-5-observability/failure-taxonomy.md` for classification
3. If f ∈ {FAILURE_FATAL, FAILURE_UNRECOVERABLE}, triggers replanning per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-2
4. If f ∈ {FAILURE_RECOVERABLE, FAILURE_TRANSIENT}, applies the recovery policy defined in `../layer-5-observability/failure-taxonomy.md`

### INV-SCHED-10 — No Dispatch After Catastrophic Failure

**Statement:** Upon receiving FAILURE_CATASTROPHIC, the scheduler MUST halt all dispatch immediately, transition the execution to FAILED, and refuse to dispatch any further steps.

**Verification:** State assertion on FAILURE_CATASTROPHIC classification. The scheduler enters a terminal HALTED state.

---

## Section 8 — Scheduler State Machine

### DEF-SCHED-6 — Scheduler Operational States

**Definition:**

The scheduler operates in exactly one of the following states:

```
SCHED_STATE ::= INIT | IDLE_WAIT | DECIDE_WAIT | DISPATCHING
             | ACTIVE_STEP | CHECKPOINTING | REPLAN_WAIT
             | TERMINATED | HALTED | ERROR(err_class)
```

| State | Meaning |
|---|---|
| INIT | Scheduler initialized, no graph loaded |
| IDLE_WAIT | Graph loaded, no active execution, awaiting control loop signal |
| DECIDE_WAIT | Control loop is in Decide phase — dispatch is blocked |
| DISPATCHING | Act phase active, scheduler dispatching steps |
| ACTIVE_STEP | A step is currently executing (step_timer running) |
| CHECKPOINTING | Checkpoint operation in progress |
| REPLAN_WAIT | Replan triggered, awaiting new graph from planner |
| TERMINATED | All steps complete, execution terminated normally |
| HALTED | FAILURE_CATASTROPHIC received, scheduler has shut down |
| ERROR(err_class) | Non-catastrophic error, execution failed with error classification |

### DEF-SCHED-7 — State Transition Table

**Definition:**

The scheduler state machine transitions are defined as `(source, event, guard, action, target)`:

| # | Source | Event | Guard | Action | Target |
|---|---|---|---|---|---|
| T1 | INIT | graph_received | valid_graph(G) | initialize_SS(G) | IDLE_WAIT |
| T2 | IDLE_WAIT | control_loop_act | execution.state=RUNNING | critical_section=true | DISPATCHING |
| T3 | IDLE_WAIT | decision_TERMINATE | decision=TERMINATE | checkpoint, archive, emit TERMINATED | TERMINATED |
| T4 | IDLE_WAIT | decision_IDLE | decision=IDLE | execution.state=IDLE | IDLE_WAIT |
| T5 | IDLE_WAIT | external_signal | signal arrives | execution.state=RUNNING | IDLE_WAIT |
| T6 | DISPATCHING | next_step | ready_set≠∅ ∧ cost_remaining≥cost(s) | dispatch(s), arm timer | ACTIVE_STEP |
| T7 | DISPATCHING | all_complete | ready_set=∅ ∧ blocked_set=∅ | emit EXECUTION_TERMINATED | TERMINATED |
| T8 | DISPATCHING | deadlock | ready_set=∅ ∧ blocked_set≠∅ | emit DEADLOCK_DETECTED, trigger FAILURE_RECOVERABLE | REPLAN_WAIT |
| T9 | DISPATCHING | decision_TERMINATE | decision=TERMINATE | emit EXECUTION_TERMINATED | TERMINATED |
| T10 | DISPATCHING | control_loop_decide | decide phase begins | critical_section=true | DECIDE_WAIT |
| T11 | ACTIVE_STEP | step_complete | result=SUCCESS | stop timer, update cost_remaining, emit STEP_COMPLETED | DISPATCHING |
| T12 | ACTIVE_STEP | step_failed_TRANSIENT | retry_count < MAX_TRANSIENT_RETRIES | retry | ACTIVE_STEP |
| T13 | ACTIVE_STEP | step_failed_TRANSIENT | retry_count ≥ MAX_TRANSIENT_RETRIES | emit STEP_FAILED, trigger replan | REPLAN_WAIT |
| T14 | ACTIVE_STEP | step_failed_RECOVERABLE | recovery_possible | attempt recovery | DISPATCHING |
| T15 | ACTIVE_STEP | step_failed_UNRECOVERABLE | true | emit STEP_FAILED, halt dependents, trigger replan | REPLAN_WAIT |
| T16 | ACTIVE_STEP | step_failed_FATAL | true | emit STEP_FAILED, halt all, trigger replan, flag audit | REPLAN_WAIT |
| T17 | ACTIVE_STEP | step_failed_CATASTROPHIC | true | halt all, checkpoint, emit FAILURE_CATASTROPHIC | HALTED |
| T18 | ACTIVE_STEP | time_budget_exceeded | interruptible(s) | interrupt, emit TIME_BUDGET_EXCEEDED, trigger replan | REPLAN_WAIT |
| T19 | ACTIVE_STEP | time_budget_exceeded | ¬interruptible(s) | allow completion, emit TIME_BUDGET_EXCEEDED | ACTIVE_STEP |
| T20 | REPLAN_WAIT | graph_received | valid_graph(G_new) | checkpoint, graph_diff, migrate, validate | DISPATCHING |
| T21 | REPLAN_WAIT | replan_failed | checkpoint_valid | rollback to checkpoint | DISPATCHING |
| T22 | REPLAN_WAIT | replan_exhausted | MAX_REPLANS reached | emit REPLAN_EXHAUSTED | TERMINATED |
| T23 | DECIDE_WAIT | control_loop_decided | decision=CONTINUE | critical_section=false | DISPATCHING |
| T24 | DECIDE_WAIT | control_loop_decided | decision=REPLAN | trigger replan | REPLAN_WAIT |
| T25 | DECIDE_WAIT | control_loop_decided | decision=IDLE | execution.state=IDLE | IDLE_WAIT |
| T26 | DECIDE_WAIT | control_loop_decided | decision=TERMINATE | emit EXECUTION_TERMINATED | TERMINATED |
| T27 | ANY | INVALID_CONFIG | config violates INV-CTRL-13 | emit CONFIG_ERROR | ERROR(INVALID_LATENCY_CONFIG) |
| T28 | ANY | FAILURE_CATASTROPHIC | true | halt all, checkpoint, emit FAILURE_CATASTROPHIC | HALTED |

### INV-SCHED-11 — State Machine Determinism

**Statement:** The scheduler state machine is deterministic. For any `(source_state, event, guard)` triple, there is exactly one `(action, target_state)` pair.

**Verification:** Transition table verification at implementation time. A deterministic state machine is required for reproducibility (PR-10) and for formal verification of liveness (THM-FM-L1 in formal-model.md).

### INV-SCHED-12 — Error States Are Terminal

**Statement:** Once the scheduler enters `HALTED` or `ERROR(err_class)`, no further transitions are possible. The execution is in a terminal state.

**Verification:** Terminal state assertion. After entering HALTED or ERROR, any dispatch attempt is rejected and logged as `SCHEDULER_ALREADY_HALTED`.

### INV-SCHED-13 — Guard Definitions

**Statement:** Guards in DEF-SCHED-7 are:
- `valid_graph(G)`: G is a DAG, all inputs bound, all modules registered
- `ready_set≠∅`: ∃s ∈ ready_set
- `ready_set=∅ ∧ blocked_set=∅`: all vertices in completed_set (normal completion)
- `ready_set=∅ ∧ blocked_set≠∅`: deadlock configuration (formal-model.md DEF-FM-21)
- `interruptible(s)`: module contract InterruptibilityFlag = true
- `recovery_possible`: a recovery policy exists in failure-taxonomy.md for the failure type

**Verification:** Guard evaluation is part of the transition check; each guard is a deterministic boolean function on SS.

---

## Section 9 — Threading Model

### DEF-SCHED-8 — Single-Threaded Dispatch

**Definition:**

The DNC runtime uses **single-threaded step dispatch**: at most one step executes at a time. The scheduler loop runs in a single OS thread. No two steps execute concurrently.

**Rationale:** The formal model (formal-model.md Section 10) proves liveness and deadlock freedom under sequential execution. Concurrent dispatch would introduce data races on ready_set, blocked_set, completed_set that are not in the formal model. This is a deliberate scope constraint.

**INV-SCHED-14 — No Concurrent Step Dispatch:**
The scheduler MUST NOT dispatch a step s_j while a prior step s_i is in ACTIVE_STEP. Concurrent step execution is not permitted.

**Verification:** The state machine (DEF-SCHED-6) permits only one ACTIVE_STEP at a time. T6 is blocked if current state is ACTIVE_STEP.

### DEF-SCHED-9 — Scheduler Loop

**Definition:**

The scheduler runs one OS thread executing:

```
scheduler_loop():
    state = INIT
    while state ∉ {TERMINATED, HALTED, ERROR(_)}:
        event = wait_for_next_event()     # blocks until event
        transition(state, event)           # deterministic state machine
```

`wait_for_next_event()` returns on: step completion, control loop command, timer interrupt, failure signal, or configuration error.

### DEF-SCHED-10 — Control Loop Concurrency

**Definition:**

The control loop runs in a **separate OS thread** from the scheduler. They communicate via:
- **Command queue** (scheduler receives): dispatch requests, replan triggers, HALT commands
- **Event queue** (control loop receives): step completion events, failure events, assessment data
- **Shared state**: `execution.state` and `execution.ES` — protected by a mutex

**INV-SCHED-15 — Mutual Exclusion on Shared State:**
All reads and writes to `execution.state` and `ES` by either thread MUST be protected by a mutex. The mutex is acquired for the full duration of any read or write operation.

**INV-SCHED-16 — Critical Section Blocks Replan:**
The `critical_section` flag is set by the scheduler when entering DECIDE_WAIT and cleared when leaving. Replan triggers from the control loop are queued (not processed) while `critical_section = true` (INV-REPLAN-8).

**INV-SCHED-17 — No Preemption During Act Phase:**
During the Act phase, the scheduler's ACTIVE_STEP runs to completion or time_budget_exceeded. The control loop's Assess/Decide phases do not interrupt the scheduler thread.

### DEF-SCHED-11 — Timer Thread

**Definition:**

A separate timer thread:
1. Arms when scheduler transitions to ACTIVE_STEP (T6)
2. Fires after `time_budget` milliseconds
3. Sends `TIMER_EXPIRED` event to scheduler if step is still in ACTIVE_STEP
4. Disarms when step completes (T11)

**INV-SCHED-18 — Timer Race Safety:**
The timer thread never modifies scheduler state directly; it only sends events via the scheduler event queue. If the timer fires after step completion (race), the event is discarded because the scheduler has already transitioned out of ACTIVE_STEP.

---

## Section 10 — Two-Phase Commit Handoff Protocol

**Scope:** This section specifies intra-process handoffs only (producer and consumer in the same address space). Inter-process handoffs require a separate IPC specification.

### DEF-SCHED-12 — Handoff Coordinator

**Definition:**

The **scheduler is the handoff coordinator**. All handoff transactions are managed by the scheduler, not by individual modules.

### DEF-SCHED-13 — Handoff Transaction States

**Definition:**

```
HANDOFF_STATE ::= INIT → PHASE1_PREPARING → PHASE1_PREPARED → PHASE2_COMMITTING → COMMITTED
                                                       ↘
                                                         ABORTED
```

### DEF-SCHED-14 — Two-Phase Commit Protocol

**Definition:**

**Phase 1 — Prepare:**
1. When module `A` completes (output o_A available), handoff transitions to `PHASE1_PREPARING`
2. Scheduler atomically marks `W[A].output = COMMITTED` — the output is now immutable
3. Handoff transitions to `PHASE1_PREPARED`
4. If a timeout `PREPARE_TIMEOUT` (default: 100ms) expires without reaching `PHASE1_PREPARED`, the handoff transitions to `ABORTED` and the step is treated as failed with `FAILURE_TRANSIENT`

**Phase 2 — Commit:**
5. When consumer `B`'s preconditions are satisfied (all inputs bound), scheduler transitions handoff to `PHASE2_COMMITTING`
6. Scheduler atomically binds `W[B].input = W[A].output` — consumer sees committed output
7. Handoff transitions to `COMMITTED`
8. If `COMMIT_TIMEOUT` (default: 50ms) expires during Phase 2, the handoff is rolled back: `W[A].output` is reverted to `PENDING`, `B` returns to `blocked_set`, and the step is retried

**Rollback:** If Phase 2 fails (timeout or validation error), the scheduler:
- Resets `W[A].output = PENDING`
- Returns `B` to `blocked_set` (unbound input)
- Requeues `B` for dispatch when `A` next completes

**INV-SCHED-19 — Handoff Coordinator Authority:**
The scheduler as coordinator has the final say in all handoff decisions. Modules do not autonomously commit their outputs — they signal completion to the scheduler, which manages the commit.

**INV-SCHED-20 — Timeout Configuration:**
`PREPARE_TIMEOUT` and `COMMIT_TIMEOUT` are configuration parameters with default values. They MUST satisfy `PREPARE_TIMEOUT + COMMIT_TIMEOUT < ACT_BUDGET` to prevent handoff protocol timeouts from causing Act phase budget overruns.

---

## Section 11 — Glossary

| Term | Definition | Document |
|---|---|---|
| Scheduler State | SS = (graph, dispatch_queue, ready_set, completed_set, blocked_set, cost_remaining, step_timer) | scheduler.md |
| Step Priority | Critical path > deadline > preference > FIFO | scheduler.md |
| Step Dispatch Protocol | 10-step protocol for executing a step | scheduler.md |
| Failure Routing | Routing step failures to failure taxonomy | scheduler.md |
| TIME_BUDGET_EXCEEDED | Event when step exceeds time budget | scheduler.md |
| STEP_COMPLETED | Provenance event on step completion | scheduler.md |
| SCHED_STATE | INIT, IDLE_WAIT, DECIDE_WAIT, DISPATCHING, ACTIVE_STEP, CHECKPOINTING, REPLAN_WAIT, TERMINATED, HALTED, ERROR | scheduler.md |
| State Transition | (source, event, guard, action, target) — one per row of T1-T28 | scheduler.md |
| Single-Threaded Dispatch | At most one step executes at a time | scheduler.md |
| Scheduler Loop | Single OS thread running the event-driven state machine | scheduler.md |
| Handoff Coordinator | The scheduler manages all handoffs as transaction coordinator | scheduler.md |
| Two-Phase Commit | Prepare then Commit or Abort per HANDOFF_STATE machine | scheduler.md |
| PREPARE_TIMEOUT | Default 100ms — max time to mark output committed | scheduler.md |
| COMMIT_TIMEOUT | Default 50ms — max time to bind consumer input | scheduler.md |
| INVALID_LATENCY_CONFIGURATION | Error when latency budget parameters violate INV-CTRL-13 | control-loop.md |

---

## Section 12 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| SCHED-AMEND-001 | scheduler.md | 2026-07-09 | Draft DR-2: Added complete scheduler state machine (DEF-SCHED-6, DEF-SCHED-7, T1-T28), state machine determinism (INV-SCHED-11), error terminal states (INV-SCHED-12), guard definitions (INV-SCHED-13), threading model (Section 9: single-threaded dispatch, scheduler loop, control loop concurrency with mutex, timer thread), two-phase commit protocol (Section 10: coordinator, timeout values, rollback) | No |