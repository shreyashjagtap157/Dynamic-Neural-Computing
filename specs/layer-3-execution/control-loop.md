# Control Loop

## Metadata

| Field | Value |
|---|---|
| Document | control-loop.md |
| Title | Control Loop |
| Document ID | SPEC-CTRL |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 3 |
| Owner Question | How does the dynamic thinker observe its environment, decide on actions, execute them, and handle the latency and reactivity constraints of real-time operation? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

A dynamic thinker that computes one answer and stops is a static thinker with a replanning feature. True dynamism requires the runtime to maintain an ongoing relationship with its environment: sensing changes, evaluating the significance of those changes, deciding whether to act, executing actions, and observing the results. This continuous cycle is the **control loop**.

This document specifies the control loop as a Layer 3 semantic foundation. It defines the loop phases (Observe, Decide, Act, Assess), the latency contracts governing each phase, the conditions under which the loop terminates, and the reactive guarantees that hold during continuous operation. The control loop builds on `state-management.md` (working memory as state), `replanning-protocol.md` (deciding to revise the plan), and `../layer-4-mechanisms/cost-semantics.md` (resource-constrained decision-making).

The control loop is not a mechanism specification — it is a semantic description of the thinker's operational pattern. Implementations MAY realize it through any scheduler architecture that satisfies the constraints specified here.

---

## Section 2 — The Four Phases

### DEF-CTRL-1 — Control Loop

**Definition:**

The **control loop** is the repeating operational pattern of a dynamic thinker:

```
ControlLoop(t) ::= Observe(t) → Decide(t) → Act(t) → Assess(t) → ControlLoop(t+1)
```

The loop is invoked continuously while the runtime is in the `RUNNING` state. Each iteration `i` operates on the execution state `ES(i)` and produces either a revised execution state `ES(i+1)` or a termination signal.

### 2.A Observe Phase

**DEF-CTRL-2 — Observation**

An **observation** `O(i)` is the set of all input signals received by the runtime since the last loop iteration `i-1`. Formally:

```
O(i) = { (signal_type, signal_value, timestamp, source) | signal arrives in [t(i-1), t(i)) }
```

**INV-CTRL-1 — Observation Completeness**

The Observe phase MUST collect all signals that arrived in the observation window before the Decide phase begins. No signal MAY be omitted, filtered, or reordered by the implementation during the observation window. Signals that arrive after the observation window are captured in the next iteration's observation.

*Verification:* Signal accounting assertion. The number of signals in `O(i)` MUST equal the number of signals that arrived in the observation window. A mismatch is an `OBSERVATION_INCOMPLETE` error.

**INV-CTRL-2 — Observation Latency Bound**

The Observe phase MUST complete within `OBSERVE_BUDGET` milliseconds. If it does not complete within this budget, the loop iteration proceeds with whatever signals have been collected, and the missing signals are treated as arriving in the next iteration.

*Verification:* Timer assertion. The Observe phase start and end times are recorded in the execution state. If `OBSERVE_BUDGET` is exceeded, a `OBSERVE_BUDGET_EXCEEDED` warning is emitted to the provenance log.

### 2.B Decide Phase

**DEF-CTRL-3 — Decision**

A **decision** `D(i)` is the runtime's choice of action to take in response to `O(i)`. The decision is produced by the planner and is one of:
- `CONTINUE`: Continue execution of the current plan
- `REPLAN`: Trigger a replan per `replanning-protocol.md`
- `IDLE`: Enter the idle state and await new signals
- `TERMINATE`: Halt the control loop and transition to `TERMINATED` state

**INV-CTRL-3 — Decision Determinism**

Given identical `O(i)` and identical execution state `ES(i)`, the Decide phase MUST produce the same decision `D(i)` in all compliant implementations. The decision function is deterministic.

*Verification:* Formal proof. The planner's decision function MUST be proven deterministic in `formal-model.md`. Regression testing against canonical decision trees.

**INV-CTRL-4 — Decision Latency Bound**

The Decide phase MUST complete within `DECIDE_BUDGET` milliseconds. If this budget is exceeded, the runtime MUST default to `CONTINUE` (proceed with the current plan) and log a `DECIDE_BUDGET_EXCEEDED` warning. The decision to default to `CONTINUE` is itself a decision — it is recorded in the provenance log.

*Verification:* Timer assertion. If `DECIDE_BUDGET` is exceeded, a `DECIDE_BUDGET_EXCEEDED` event is logged and the decision defaults to `CONTINUE`.

### 2.C Act Phase

**DEF-CTRL-4 — Action**

An **action** is the execution of one or more steps of the current execution graph, or the initiation of a replan, as prescribed by the decision `D(i)`.

**INV-CTRL-5 — Action Commitment**

Once the Decide phase produces a decision, the Act phase MUST execute that decision without revision until the next loop iteration begins. The Act phase MUST NOT be interrupted by signals that arrive mid-action.

*Verification:* Runtime assertion. The critical-section flag (per `replanning-protocol.md` INV-REPLAN-8) MUST be set during the Act phase. Replan triggers received during the Act phase are queued per INV-REPLAN-8.

**INV-CTRL-6 — Action Latency Bound**

The Act phase for a single iteration MUST complete within `ACT_BUDGET` milliseconds. If a step's execution exceeds this budget, the scheduler MAY either (a) interrupt the step and trigger replanning, or (b) allow the step to complete if interruptibility is not supported by the step's contract. The choice MUST be recorded in the provenance log.

*Verification:* Timer assertion. If `ACT_BUDGET` is exceeded, the scheduler MUST either invoke the replan trigger or log `ACT_BUDGET_EXCEEDED` with the step's interruptibility status.

### 2.D Assess Phase

**DEF-CTRL-5 — Assessment**

An **assessment** `A(i)` is the runtime's evaluation of whether the actions taken in `Act(i)` produced the intended outcome. The assessment compares the observed post-action state against the expected state encoded in the current plan's success criteria.

**INV-CTRL-7 — Assessment Always Runs**

The Assess phase MUST run at every loop iteration, even when the decision was `IDLE` or `TERMINATE`. The Assess phase MUST compute `A(i)` and record it in the history log before `Observe(i+1)` begins.

*Verification:* Phase-order assertion. The Assess phase completion timestamp MUST precede the next Observe phase start timestamp in the execution state.

**INV-CTRL-8 — Assessment Result Classification**

The assessment `A(i)` MUST be classified as one of:
- `OUTCOME_MET`: The action produced the expected result within tolerance
- `OUTCOME_DEGRADED`: The action produced a result outside tolerance but within operational bounds
- `OUTCOME_FAILED`: The action produced a result outside operational bounds or triggered a `FAILURE_FATAL`

*Verification:* Runtime assertion. The assessment classifier MUST assign one of the three classifications per INV-CTRL-8. An unclassified assessment is an `ASSESSMENT_ERROR`.

---

## Section 3 — Reactive Latency Contracts

### DEF-CTRL-6 — Loop Iteration Time

The **loop iteration time** `T_iter(i)` is the wall-clock duration of a single control loop iteration from the start of `Observe(i)` to the end of `Assess(i)`.

### INV-CTRL-9 — Control Loop Iteration Budget

**Statement:**

The sum `T_iter(i)` — the wall-clock duration from Observe start to Assess end — MUST NOT exceed `CONTROL_LOOP_BUDGET` milliseconds on average over any sliding window of 10 consecutive iterations. A single iteration MAY exceed `CONTROL_LOOP_BUDGET` by at most `CONTROL_LOOP_GRACE` milliseconds without triggering an error.

*Verification:* Runtime assertion on a sliding window counter. The scheduler MUST track `T_iter` for the last 10 iterations and assert the rolling average is within `CONTROL_LOOP_BUDGET`.

*Note:* This budget applies only to the **control loop coordination overhead** (Observe, Decide, Assess phases, plus scheduling decisions). Neural execution steps dispatched via the Act phase run asynchronously and do NOT count toward `CONTROL_LOOP_BUDGET`. Their completion is tracked by the scheduler; their wall-clock time is tracked separately per cost-semantics.md.

*Rationale:* A dynamic thinker that cannot maintain reactive responsiveness is functionally equivalent to a batch processor. The loop budget enforces interactivity. Neural inference (50–500ms per forward pass) would make the default 50ms budget impossible to satisfy; the async exclusion resolves this tension.

---

INV-CTRL-9b — Neural Execution Async Exclusion

**Statement:**

Steps dispatched as part of a neural computation (modules whose contract annotates `computation_type: neural`) are executed asynchronously and do not block the control loop. The Act phase dispatches these steps and returns immediately; the scheduler tracks their completion asynchronously. `CONTROL_LOOP_BUDGET` and `DECISION_LATENCY_BUDGET` apply to the **dispatch** latency (time from decision to commitment of the async task), not the **execution** latency of the task itself.

*Verification:* Module contract annotation check. The scheduler MUST verify `computation_type` annotation at dispatch time. Neural computation steps are tracked in a separate `ASYNC_PENDING` set.

*Rationale:* Real neural network inference can consume 50–500ms per forward pass on commodity hardware. The control loop cannot be latency-budgeted at that scale. The two-tier model (fast coordination, async execution) is the standard pattern for real-time systems handling slow operations (e.g., ROS action servers, distributed compute clusters).

INV-CTRL-9c — Async Pending Set Boundedness and Backpressure

**Statement:**

The ASYNC_PENDING set (neural modules dispatched but not yet completed) MUST NOT exceed MAX_ASYNC_PENDING (default: 50). The following backpressure semantics apply when |ASYNC_PENDING| = MAX_ASYNC_PENDING:

1. **Backpressure Signal:** New neural module dispatches are PAUSED. The Act phase records PAUSED_ASYNC_BACKPRESSURE in the provenance log and does not dispatch the step.

2. **Pause Response:** The control loop iteration does NOT block waiting for an ASYNC_PENDING slot. Instead, the paused step is re-queued for the next loop iteration's Act phase. This preserves CONTROL_LOOP_BUDGET compliance — only the decision latency is affected, not the loop iteration time.

3. **Priority Override:** If a neural step's contract annotates `criticality: DECISION_LATENCY_BUDGET` (meaning its dispatch latency is latency-critical), the scheduler MAY override the backpressure and dispatch the step even when ASYNC_PENDING is full, displacing the least-recently-queued non-critical async step. Displacement is recorded in the provenance log.

4. **Failure Propagation Timeout:** If a neural step's failure is not propagated within ASYNC_COMPLETION_TIMEOUT (default: 500ms = 5 × DECISION_LATENCY_BUDGET), it is treated as FAILURE_UNRECOVERABLE and triggers replan per INV-REPLAN-2. The failed step is removed from ASYNC_PENDING on classification.

*Verification:* Runtime assertion. The scheduler MUST enforce |ASYNC_PENDING| ≤ MAX_ASYNC_PENDING before each neural dispatch, applying backpressure semantics if the bound is reached.

*Rationale:* Non-blocking pause preserves loop responsiveness. The priority override ensures that latency-critical neural steps (e.g., reactive safety checks) are not blocked by throughput-oriented bulk inference. The displacement policy is recorded for audit.

### DEF-CTRL-7 — Event-Response Latency

**Event-response latency** `T_resp(e)` is the wall-clock time from when an event `e` is observed in the environment to when the action triggered by that event has been committed to the execution state. It spans from the Observe phase that captured `e` through the Decide and Act phases that responded to `e`.

### INV-CTRL-10 — Event-Response Latency Bound

**Statement:**

The event-response latency `T_resp(e)` for any event `e` MUST NOT exceed `DECISION_LATENCY_BUDGET` milliseconds. Events that cannot be responded to within `DECISION_LATENCY_BUDGET` MUST be handled by a fallback policy (either default to `CONTINUE` or trigger a `REPLAN`), and the fallback decision MUST be recorded in the provenance log with the exceeded budget noted.

*Verification:* Per-event latency measurement. Every event in `O(i)` is tagged with its arrival timestamp. The provenance log records the commit timestamp of the response action. `T_resp(e)` is computed as the difference.

*Rationale:* Late responses to real-time events are functionally equivalent to no response. The `DECISION_LATENCY_BUDGET` enforces the temporal contract of the dynamic thinker. Neural execution steps run asynchronously and do not count toward this budget.

---

## Section 3.A — Latency Budget Constants

**This section assigns numerical default values and configuration obligations to all latency budget parameters. Each parameter is a configuration value that MAY be overridden at runtime initialization, but the invariant constraints in Sections 2 and 3 continue to apply at the configured values.**

### DEF-CTRL-8 — Latency Budget Configuration Table

**Definition:**

| Parameter | Default (ms) | Minimum (ms) | Maximum (ms) | Configuration Constraint |
|---|---|---|---|---|
| `OBSERVE_BUDGET` | 5 | 1 | 50 | `OBSERVE_BUDGET > 0` |
| `DECIDE_BUDGET` | 10 | 1 | 200 | `DECIDE_BUDGET > 0` |
| `ACT_BUDGET` | 1000 | 10 | 300000 | `ACT_BUDGET > OBSERVE_BUDGET + DECIDE_BUDGET` |
| `CONTROL_LOOP_BUDGET` | 50 | 10 | 500 | `CONTROL_LOOP_BUDGET ≥ OBSERVE_BUDGET + DECIDE_BUDGET` |
| `CONTROL_LOOP_GRACE` | 10 | 0 | `CONTROL_LOOP_BUDGET` | `CONTROL_LOOP_GRACE ≥ 0` |
| `DECISION_LATENCY_BUDGET` | 100 | 10 | 10000 | `DECISION_LATENCY_BUDGET ≥ OBSERVE_BUDGET + DECIDE_BUDGET` |
| `MAX_REPLANS_PER_EXECUTION` | 3 | 1 | 10 | `MAX_REPLANS_PER_EXECUTION ∈ ℕ` |
| `MAX_TRANSIENT_RETRIES` | 3 | 1 | 10 | `MAX_TRANSIENT_RETRIES ∈ ℕ` |
| `MAX_CHECKPOINTS` | 100 | 10 | 10000 | `MAX_CHECKPOINTS ∈ ℕ` |
| `MAX_ASYNC_PENDING` | 50 | 10 | 1000 | `MAX_ASYNC_PENDING ∈ ℕ` |
| `ASYNC_COMPLETION_TIMEOUT` | 500 | 50 | 50000 | `ASYNC_COMPLETION_TIMEOUT ≥ DECISION_LATENCY_BUDGET` |

### INV-CTRL-13 — Configuration Validity

**Statement:**

Every deployed configuration MUST satisfy all Configuration Constraints in DEF-CTRL-8. An invalid configuration (where any parameter violates its constraint) MUST cause the runtime to refuse to initiate new executions and transition to `FAILED` state with error classification `INVALID_LATENCY_CONFIGURATION`.

**Verification:** Configuration validation at runtime initialization. The validation runs before the first execution is initiated and before any execution header is committed.

**Rationale:** These constraints ensure that budget values are physically meaningful. For example, `DECISION_LATENCY_BUDGET ≥ OBSERVE_BUDGET + DECIDE_BUDGET` is required because `T_resp(e)` spans all three phases; if `DECISION_LATENCY_BUDGET` were smaller than the sum of the component budgets, the invariant would be impossible to satisfy.

### INV-CTRL-14 — Budget Values Are Immutable During Execution

**Statement:**

The latency budget values in DEF-CTRL-8 MUST NOT be modified while any execution is in the `RUNNING` or `IDLE` state. Changes to budget values take effect only during `TERMINATED` or `FAILED` state, or before the first execution initiation.

**Verification:** State check before configuration update. The configuration update operation MUST verify all executions are in `TERMINATED` or `FAILED` state before applying new budget values.

**Rationale:** Changing budgets mid-execution would invalidate the latency guarantees that downstream components (formal model, planning) rely on.

### AX-CTRL-1 — Default Configuration Preserves THM-FM-L3

**Statement:**

Under the default configuration values, `OBSERVE_BUDGET + DECIDE_BUDGET = 15ms ≤ DECISION_LATENCY_BUDGET = 100ms`. Therefore `OBSERVE_BUDGET + DECIDE_BUDGET ≤ DECISION_LATENCY_BUDGET` holds for the default configuration, satisfying the pre-condition of THM-FM-L3 (event-response latency bound).

**Note:** When deploying with non-default values, the operator MUST verify `OBSERVE_BUDGET + DECIDE_BUDGET ≤ DECISION_LATENCY_BUDGET` holds. This is enforced by INV-CTRL-13.

---

## Section 4 — Loop Termination

### INV-CTRL-11 — Loop Termination Conditions

**Statement:**

The control loop MUST transition to the `TERMINATED` state when any of the following conditions hold:
1. The planner produces a decision `D(i) = TERMINATE`
2. The execution reaches its maximum step count without a termination decision
3. A `FAILURE_CATASTROPHIC` error is classified per `../layer-5-observability/failure-taxonomy.md`
4. An external `HALT` directive is received and validated

The loop MUST NOT terminate for any other reason.

*Verification:* Runtime assertion at each Assess phase. All four termination conditions are checked and the decision is recorded in the history log.

### INV-CTRL-12 — Graceful Shutdown

**Statement:**

When the control loop transitions to `TERMINATED` via a `TERMINATE` decision, the runtime MUST:
1. Take a final checkpoint of `ES(t)` (per `state-management.md`)
2. Archive all `RETIRED_EARLY` module states to the provenance log
3. Emit a `EXECUTION_TERMINATED` event with the final step index, total execution time, and the decision rationale
4. Transition to `TERMINATED` state and release all resources

*Verification:* Runtime assertion. The termination sequence MUST be verified to complete all four steps atomically. If any step fails, the error is logged and the runtime transitions to `FAILED` state.

---

## Section 5 — Glossary

| Term | Definition | Document |
|---|---|---|
| Control Loop | DEF-CTRL-1 | control-loop.md |
| Observation O(i) | DEF-CTRL-2 | control-loop.md |
| Decision D(i) | DEF-CTRL-3 | control-loop.md |
| Action | DEF-CTRL-4 | control-loop.md |
| Assessment A(i) | DEF-CTRL-5 | control-loop.md |
| Loop Iteration Time | DEF-CTRL-6 | control-loop.md |
| Event-Response Latency | DEF-CTRL-7 | control-loop.md |
| OBSERVATION_INCOMPLETE | Error when observation is incomplete | control-loop.md |
| DECIDE_BUDGET_EXCEEDED | Warning when decide phase exceeds budget | control-loop.md |
| ACT_BUDGET_EXCEEDED | Warning when act phase exceeds budget | control-loop.md |
| ASSESSMENT_ERROR | Error when assessment is unclassified | control-loop.md |
| OUTCOME_MET | Assessment classification | control-loop.md |
| OUTCOME_DEGRADED | Assessment classification | control-loop.md |
| OUTCOME_FAILED | Assessment classification | control-loop.md |
| EXECUTION_TERMINATED | Final termination event | control-loop.md |
| PAUSED_ASYNC_BACKPRESSURE | Provenance event when neural dispatch is paused due to ASYNC_PENDING queue full | control-loop.md |
| ASYNC_DISPLACEMENT | Provenance event when a critical async step displaces a non-critical step in ASYNC_PENDING | control-loop.md |
| CRITICALITY_ANNOTATION | Module contract field indicating whether a neural module requires priority dispatch (DECISION_LATENCY_BUDGET) or normal dispatch | control-loop.md |
| ASYNC_PENDING | Set of dispatched neural computation steps not yet completed | control-loop.md |
| COMPUTATION_TYPE_NEURAL | Module contract annotation marking async-eligible computation | control-loop.md |
| CONTROL_LOOP_BUDGET | Maximum average wall-clock duration of a control loop iteration over a sliding window of 10 iterations | control-loop.md |

---

## Section 6 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| CTRL-AMEND-001 | control-loop.md | 2026-07-10 | Renamed LOOP_BUDGET→CONTROL_LOOP_BUDGET, RESP_BUDGET→DECISION_LATENCY_BUDGET; added INV-CTRL-9b (async neural execution exclusion from latency budget); addresses systems engineer review finding that 50ms budget is incompatible with neural inference workloads. | No |
| CTRL-AMEND-002 | control-loop.md | 2026-07-10 | Added INV-CTRL-9c (Async Pending Set Boundedness) with MAX_ASYNC_PENDING and ASYNC_COMPLETION_TIMEOUT; addresses backpressure and async failure propagation | No |
| CTRL-AMEND-003 | control-loop.md | 2026-07-10 | Replaced INV-CTRL-9c with full backpressure semantics: non-blocking pause (Act phase does not block), re-queue for next iteration, priority override for DECISION_LATENCY_BUDGET-critical steps with displacement logging. Addresses systems engineer final review finding on pause semantics ambiguity. | No |