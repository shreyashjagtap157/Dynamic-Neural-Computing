# Cost Semantics

## Metadata

| Field | Value |
|---|---|
| Document | cost-semantics.md |
| Title | Cost Semantics |
| Document ID | SPEC-COST |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 4 |
| Owner Question | How are computational resources accounted? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

The DNC runtime operates under resource constraints: CPU cycles, memory, I/O bandwidth, accelerator time. The cost semantics system assigns precise numerical costs to every operation — module executions, inter-module handoffs, checkpoint operations, planning invocations, and the control loop phases — so that the planner can produce resource-aware execution graphs and the scheduler can enforce resource budgets.

Cost semantics serves three purposes:
1. **Planning input**: The planner uses cost estimates to select among module alternatives and to produce graphs that fit within the available resource budget
2. **Budget enforcement**: The scheduler uses cost accounting to prevent execution from exceeding its resource budget
3. **Provenance**: Every execution's cost profile is recorded in the provenance log, enabling retrospective analysis and billing

Cost is not the same as time. Some operations are expensive in time but cheap in CPU cycles (I/O-bound operations); some are expensive in memory but cheap in CPU (memory-copy operations). Cost semantics unifies these into a single numerical model for planning purposes, while preserving per-resource accounting for detailed analysis.

---

## Section 2 — Resource Model

### DEF-COST-1 — Resource Types

**Definition:**

The DNC runtime tracks the following resource types:

```
ResourceType = {CPU_CYCLES, MEMORY_BYTES, IO_BYTES, ACCELERATOR_TIME, WALL_CLOCK_MS}
```

Each resource type has an independent unit and budget.

### DEF-COST-2 — Cost Vector

**Definition:**

A **cost vector** is a 5-tuple of resource costs:

```
c = (c_cpu, c_mem, c_io, c_accel, c_wall) ∈ ℝ_{\ge 0}^5
```

Individual cost components MAY be zero for operations that do not use that resource.

### DEF-COST-3 — Total Cost

**Definition:**

The **total cost** of a cost vector c is:

```
total(c) = α_cpu * c_cpu + α_mem * c_mem + α_io * c_io + α_accel * c_accel + α_wall * c_wall
```

Where the α coefficients are the configured resource weight vector, set at runtime initialization. The default weights are application-specific; a latency-critical workload might set α_wall high, while a throughput-critical workload might set α_cpu high.

### DEF-COST-4 — Budget

**Definition:**

A **budget** B is a cost vector representing the maximum allowable resource consumption for an execution or a portion thereof.

---

## Section 3 — Module Cost Specification

### DEF-COST-5 — Module Cost Parameters

**Definition:**

Each module contract (per `module-lifecycle.md`) includes cost parameters:

```
CostParams = (cpu_per_invocation, mem_per_invocation, io_per_invocation,
              accel_per_invocation, wall_per_invocation, memory_footprint)
```

Where:
- `cpu_per_invocation` is the cost vector per module execution
- `mem_per_invocation` is the additional memory allocated per invocation
- `io_per_invocation` is the I/O cost for data transfer
- `accel_per_invocation` is the accelerator time per invocation
- `wall_per_invocation` is the wall-clock time per invocation
- `memory_footprint` is the static memory reserved for the module

### INV-COST-1 — Cost Parameters Immutable After Registration

**Statement:** The cost parameters in a module contract are immutable after registration, per INV-LIFECYCLE-1 (contract immutability). A cost parameter change requires a new module version.

**Verification:** Contract hash verification. A modified cost parameter changes the contract hash, which is prohibited for registered modules.

---

## Section 4 — Execution Cost Accounting

### DEF-COST-6 — Step Cost

**Definition:**

The **step cost** for step s_i executing module instance n_i is:

```
cost(s_i) = CostParams[n_i.ModuleTypeID] + handoff_cost(pred_G(n_i), n_i)
```

Where `handoff_cost` is the inter-module communication cost defined in Section 5.

### DEF-COST-7 — Accumulated Cost

**Definition:**

The **accumulated cost** at step index t is:

```
AccCost(t) = Σ_{i=0}^{t-1} cost(s_i)
```

### INV-COST-2 — Budget Enforcement at Dispatch

**Statement:** The scheduler MUST verify that `AccCost(t) + cost(s_t) ≤ B_execution` (remaining execution budget) before dispatching step s_t. If the step would exceed the budget, the scheduler MUST NOT dispatch and MUST trigger resource exhaustion handling per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-4.

**Verification:** Budget check per INV-SCHED-4 (scheduler.md).

### DEF-COST-8 — Cost Forecast

**Definition:**

The **cost forecast** for completing the remaining steps in the current execution graph is computed by the planner as:

```
ForecastCost(G_remaining) = Σ_{s ∈ G_remaining} cost(s)
```

If `AccCost(t) + ForecastCost(G_remaining) > B_execution`, resource exhaustion is forecast.

### INV-COST-3 — Forecast Triggers Replan

**Statement:** If the cost forecast indicates that the remaining steps will exceed the execution budget, the runtime MUST trigger replanning per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-4 before the exhaustion actually occurs.

**Verification:** Forecast check at each step boundary. If forecast crosses budget threshold, REPLAN trigger is emitted.

---

## Section 5 — Inter-Module Handoff Costs

### DEF-COST-9 — Handoff Cost

**Definition:**

The **handoff cost** for transferring the output of module instance A to the input of module instance B is:

```
handoff_cost(A, B) = (data_size(A.output) * io_cost_per_byte) + (serialization_cost + deserialization_cost)
```

Where `data_size` is the size in bytes of the output value, and the serialization costs account for any required format conversion.

### INV-COST-4 — Handoff Cost Included in Step Cost

**Statement:** The handoff cost is attributed to the consumer step B (not the producer A), since B initiates the data transfer. The handoff cost is included in `cost(B)` per DEF-COST-6.

**Verification:** Cost attribution check in the scheduler's cost accounting. The consumer step's cost includes the full handoff cost.

---

## Section 6 — Control Loop Cost Accounting

### DEF-COST-10 — Control Loop Phase Costs

**Definition:**

Each control loop phase has an associated cost:

```
cost(Observe) = cpu_cost_observe + io_cost_observe
cost(Decide) = cpu_cost_decide + wall_cost_decide
cost(Act) = sum of dispatched step costs in this iteration
cost(Assess) = cpu_cost_assess + wall_cost_assess
```

### INV-COST-5 — Loop Budget Tracking

**Statement:** The scheduler MUST track the accumulated control loop phase costs against the configured LOOP_BUDGET. The Observe and Decide phases are charged against the loop iteration; dispatched steps are charged against the Act phase; Assess is charged against the loop iteration.

**Verification:** Cost accumulation per `../layer-3-execution/control-loop.md` INV-CTRL-9 (loop iteration budget).

---

## Section 7 — Checkpoint Costs

### DEF-COST-11 — Checkpoint Cost

**Definition:**

The **checkpoint cost** is the resource cost of taking a checkpoint of ES(t):

```
cost(checkpoint) = (size_of(ES(t)) * mem_cost_per_byte) + cpu_cost_checkpoint + io_cost_checkpoint
```

Where `size_of(ES(t))` is the total memory footprint of the execution state.

### INV-COST-6 — Checkpoint Cost Included in Budget

**Statement:** Checkpoint costs are charged against the execution budget. The runtime MUST account for checkpoint costs when computing cost forecasts. Omitting checkpoint costs from forecasts is a COST_FORECAST_ERROR.

**Verification:** Checkpoint cost inclusion in cost forecast per INV-COST-3.

### INV-COST-8 — Checkpoint Overhead Budget

**Statement:** The checkpoint cost for a single checkpoint operation MUST NOT exceed 5% of the configured ACT_BUDGET. If the computed checkpoint cost exceeds this threshold, the runtime MUST use a **staged checkpoint protocol**: the checkpoint is taken asynchronously and the checkpoint completion is confirmed in the background before the next Act phase begins. The staged protocol MUST NOT block the control loop.

For staged checkpoint:
1. The checkpoint snapshot is initiated and a checkpoint_in_progress marker is recorded
2. The control loop continues (INV-CTRL-9 and INV-CTRL-9b are unaffected)
3. When the snapshot is fully written, the checkpoint record is atomically committed
4. If the snapshot is not committed within 3 × ACT_BUDGET, the checkpoint is abandoned and a CHECKPOINT_STALLED event is emitted. The runtime MUST:
   1. Record CHECKPOINT_STALLED as a PROV_ERROR event in the provenance log with severity P2 (per failure-taxonomy.md alert thresholds)
   2. Flag the next successful checkpoint as HIGH_PRIORITY to recover checkpoint coverage
   3. If the execution encounters a failure requiring rollback before a successful checkpoint completes, treat the absence of a recent checkpoint as a contributing factor in the failure classification (per failure-taxonomy.md)
   4. Increment a CHECKPOINT_STALLED counter; if CHECKPOINT_STALLED occurs 3 or more times within a single execution, emit a CHECKPOINT_RELIABILITY_DEGRADED event and notify the External Authority

**Note:** Proceeding without a recent checkpoint means the replan rollback capability is degraded for this cycle. The planner's INV-PLANNER-8 state preservation guarantee is weakened until the next successful checkpoint is taken.

**Verification:** Checkpoint cost accounting. The checkpoint cost estimator MUST compute cost(checkpoint) before the operation and compare against 0.05 × ACT_BUDGET. Staged checkpoint activation is triggered if exceeded.

**Rationale:** For large working memories (e.g., 500MB of neural activation state), synchronous checkpoint serialization could consume 200ms+ against ACT_BUDGET=1000ms. The staged protocol allows checkpoint overhead to be amortized across multiple loop iterations without blocking responsiveness. The 5% threshold ensures checkpoints remain a small fraction of the act budget in the common case.

---

## Section 8 — Learning Costs

### DEF-COST-12 — Learning Cost

**Definition:**

The **learning cost** is the resource cost of the continual learning system processing a learning event and verifying a candidate update:

```
cost(learning_per_event) = cpu_cost_learn + accel_cost_learn + mem_cost_learn
cost(verification_per_update) = Σ_{eval ∈ evaluation_suite} cost(eval)
```

### INV-COST-7 — Learning Budget Separate from Execution Budget

**Statement:** The learning system has a separate LEARNING_BUDGET from the execution budget. Learning costs are charged against LEARNING_BUDGET, not B_execution. The two budgets are independent.

**Verification:** Separate budget tracking. Learning costs do not count against execution budget.

---

## Section 9 — Glossary

| Term | Definition | Document |
|---|---|---|
| ResourceType | CPU_CYCLES, MEMORY_BYTES, IO_BYTES, ACCELERATOR_TIME, WALL_CLOCK_MS | cost-semantics.md |
| Cost Vector | 5-tuple of resource costs | cost-semantics.md |
| Total Cost | Weighted sum of cost vector components | cost-semantics.md |
| Budget | Maximum allowable cost vector | cost-semantics.md |
| Step Cost | cost(s_i) = module cost params + handoff cost | cost-semantics.md |
| Accumulated Cost | Sum of step costs up to step t | cost-semantics.md |
| Cost Forecast | Predicted total cost of remaining steps | cost-semantics.md |
| Handoff Cost | Cost to transfer output between modules | cost-semantics.md |
| Checkpoint Cost | Cost of taking a checkpoint | cost-semantics.md |
| Learning Cost | Cost of processing learning events and verification | cost-semantics.md |
| COST_FORECAST_ERROR | Error when checkpoint costs omitted from forecast | cost-semantics.md |
| CHECKPOINT_STALLED | Event when staged checkpoint exceeds 3× ACT_BUDGET; triggers P2 alert, HIGH_PRIORITY next checkpoint flagging, failure contributing factor tracking, and External Authority notification if ≥3 per execution | cost-semantics.md |
| CHECKPOINT_RELIABILITY_DEGRADED | Event when CHECKPOINT_STALLED occurs ≥3 times per execution | cost-semantics.md |

---

## Section 10 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| COST-AMEND-002 | cost-semantics.md | 2026-07-10 | Elevated CHECKPOINT_STALLED from informational event to recovery action: P2 alert, HIGH_PRIORITY next checkpoint flagging, failure contributing factor tracking, External Authority notification at ≥3 occurrences. Addresses systems engineer final review finding on CHECKPOINT_STALLED recovery semantics. | No |
| — | — | — | No amendments yet | — |