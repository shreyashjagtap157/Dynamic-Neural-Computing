# Failure Taxonomy

## Metadata

| Field | Value |
|---|---|
| Document | failure-taxonomy.md |
| Title | Failure Taxonomy |
| Document ID | SPEC-FAILURE |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 5 |
| Owner Question | How are runtime failures classified and handled? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

Failures in the DNC runtime are inevitable. A dynamic system that operates under uncertainty — processing real-time inputs, invoking external services, managing constrained resources — will encounter failures. The failure taxonomy specifies how failures are classified, the semantics of each failure class, the prescribed handling policy for each class, and the conditions under which a failure triggers replanning.

The taxonomy is hierarchical: there are four primary failure classifications, each with specific subtypes. The classification determines the response: some failures are transient and retryable; others are unrecoverable and trigger replanning; one (catastrophic) halts the entire execution.

The failure taxonomy is Layer 5 (Observability) because it observes and classifies failures that originate in the lower layers (mechanism failures from Layer 4 modules, semantic failures from Layer 3 execution, constitutional failures from Layer 2 invariant violations). It does not prescribe how modules are implemented; it prescribes how their failures are interpreted and handled.

---

## Section 2 — Failure Classifications

### FAILURE_TRANSIENT

**Definition:**

A **transient failure** is a module failure caused by a temporary condition that is likely to resolve without intervention. Examples: a network timeout to an external service that is responding slowly; a memory allocation temporarily denied due to memory pressure; a lock temporarily held by a concurrent operation.

**Handling policy:** The scheduler MAY retry the same step with the same module instance, up to MAX_TRANSIENT_RETRIES times. Each retry creates a RETRY event in the provenance log. If MAX_TRANSIENT_RETRIES is exceeded, the failure is reclassified as FAILURE_RECOVERABLE.

**Planner implications:** Does NOT trigger replanning. The planner's graph G is not modified.

### FAILURE_RECOVERABLE

**Definition:**

A **recoverable failure** is a module failure that cannot be retried with the same inputs but can be worked around without changing the execution graph. Examples: a module produces an output that is type-correct but out of range; a module produces a result that can be corrected by a downstream error-correction module; a planner produces a graph that has a minor structural issue discovered at dispatch time.

**Handling policy:** The scheduler attempts recovery by:
1. Attempting alternative input bindings (if multiple sources are available)
2. Invoking an error-correction module if one is registered for this module type
3. If recovery fails, escalating to FAILURE_UNRECOVERABLE

**Planner implications:** Does NOT trigger replanning. The current graph G remains valid.

### FAILURE_UNRECOVERABLE

**Definition:**

An **unrecoverable failure** is a module failure that cannot be retried or worked around within the current execution graph. The failure is contained to the affected module and its immediate dependents; it does not corrupt global state. Examples: a module produces an output that violates its contract's output signature (type mismatch); a module enters an infinite loop (detected by time budget exceeded, classified as FAILURE_UNRECOVERABLE); a planner produces a graph that violates a resource constraint.

**Handling policy:** The scheduler:
1. Halts all dependents of the failed module (they cannot proceed without this module's output)
2. Archives the failed module's state per `../layer-3-execution/state-management.md` INV-STATE-8
3. Emits a REPLAN_TRIGGERED event with trigger_type = MODULE_FAILURE per `../layer-3-execution/replanning-protocol.md`
4. Triggers replanning to produce a new graph G_new that excludes the failed module

**Planner implications:** Triggers replanning per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-2.

### FAILURE_FATAL

**Definition:**

A **fatal failure** is a module failure that is unrecoverable and also indicates a systemic problem that may affect other modules. The distinction from FAILURE_UNRECOVERABLE is intent: FAILURE_FATAL signals that the failure should be treated as indicative of a broader problem, not just an isolated module issue.

**Examples:** A module produces output that contradicts an invariant (this is both a failure and an invariant violation); a module's output causes a downstream module to violate an invariant; a planner produces a graph that is invalid per the formal model.

**Handling policy:** Same as FAILURE_UNRECOVERABLE — triggers replanning. The additional semantics of FAILURE_FATAL are in the provenance annotation: a FAILURE_FATAL event is flagged as potentially systemic and triggers a post-execution review of the module registry.

**Planner implications:** Triggers replanning. Additionally, a FAILURE_FATAL event triggers a module registry audit after execution terminates.

### FAILURE_CATASTROPHIC

**Definition:**

A **catastrophic failure** is a runtime state from which recovery is not possible and continued execution would produce undefined behavior or data corruption. Examples: memory corruption detected in working memory; a checkpoint restoration produces an invalid ES(t); the provenance log integrity check fails (PROVENANCE_TAMPERING_VIOLATION); an invariant violation is detected that cannot be safely contained.

**Handling policy:** The scheduler:
1. Halts all dispatch immediately per INV-SCHED-10
2. Takes a final checkpoint if possible
3. Transitions the execution to FAILED state
4. Emits FAILURE_CATASTROPHIC to the provenance log
5. Retains the execution state and provenance log for diagnostic analysis

**Planner implications:** Execution is terminated. No replanning occurs.

### INVALID_OUTPUT

**Definition:**

An **invalid output** is a signal emitted by a module indicating that the module produced an output that is type-correct (matches the output signature) but is **semantically incorrect** — it fails a content validation check (e.g., output range sanity check, checksum mismatch, or plausibility heuristic). This is distinct from a type mismatch (CONTRACT_VIOLATION → FAILURE_FATAL) and distinct from a crash (PANIC → FAILURE_FATAL). The module is functioning but producing wrong results.

**Examples:** A classification module outputs a valid class index but the confidence score is implausibly high; a generation module's output fails a structural checksum; a numerical module's output is outside any plausible range for the domain.

**Handling policy:** The scheduler immediately triggers replanning (FAILURE_RECOVERABLE). Unlike FAILURE_TRANSIENT, retry is not appropriate since the module is not malfunctioning — its contract is satisfied but its output is wrong. Replan to a different module or graph structure.

**Planner implications:** Triggers replanning immediately. The module type is flagged for post-execution review; the module itself is not deregistered (it may work correctly for other inputs).

**Rationale:** Silent data corruption (SDC) produces type-correct but semantically wrong outputs that are not caught by contract validation. This gap was identified in the systems engineer review. The immediate replan prevents SDC from propagating silently through subsequent steps.

### PARTIAL_FAILURE (Replicated Module Group Failure)

**Definition:**

A **partial failure** occurs when a fault-tolerant module group (where multiple instances of the same module type are instantiated for redundancy) has some instances succeed and others fail. This indicates a non-systemic issue affecting a subset of the execution.

**Examples:** 3-way replicated module: 2 succeed, 1 fails (could be hardware, data partition, or scheduling issue). A probabilistic retry may resolve it.

**Handling policy:**
1. The scheduler awaits all group members (up to MAX_TRANSIENT_RETRIES per instance)
2. If a majority (≥ ceil(N/2)+1) succeed, the group's output is determined by majority vote
3. The failed instances are treated as FAILURE_TRANSIENT (retry the minority)
4. If majority cannot be achieved, escalate to FAILURE_UNRECOVERABLE and trigger replan

**Planner implications:** Does NOT trigger replan if majority succeeds. Triggers replan if majority fails.

**Rationale:** Partial failure in replicated groups is typically recoverable via redundancy. The majority-vote mechanism is a standard fault-tolerance pattern.

---

## Section 3 — Failure Detection and Classification

### DEF-FAIL-1 — Failure Detection

**Definition:**

Failure detection occurs at the scheduler level when a step's output is classified as a failure. The detection mechanism:
1. The module instance returns a result or a failure signal
2. The result is validated against the module's output signature
3. If validation fails, FAILURE_FATAL is assigned
4. If the module emits a failure signal, the signal is mapped to a classification per the mapping table

### DEF-FAIL-2 — Failure Signal Mapping

**Definition:**

The mapping from module failure signals to failure classifications:

| Module Signal | Classification |
|---|---|
| TIMEOUT | FAILURE_TRANSIENT (first MAX_TRANSIENT_RETRIES), then FAILURE_UNRECOVERABLE |
| RESOURCE_EXHAUSTED | FAILURE_RECOVERABLE (resource-specific recovery) |
| INVALID_OUTPUT | FAILURE_RECOVERABLE (immediate replan) |
| CONTRACT_VIOLATION | FAILURE_FATAL |
| PANIC | FAILURE_FATAL |
| RETRY_EXHAUSTED | FAILURE_RECOVERABLE |
| ERROR_CORRECTION_SUCCEEDED | FAILURE_RECOVERABLE |
| ERROR_CORRECTION_FAILED | FAILURE_UNRECOVERABLE |

**Note:** RESOURCE_EXHAUSTED → FAILURE_RECOVERABLE with resource-specific sub-classification (GPU_MEMORY uses retry-with-defragmentation). INVALID_OUTPUT → FAILURE_RECOVERABLE with immediate replan (not retry).

**Note:** If resource is GPU_MEMORY and recovery succeeds within MAX_TRANSIENT_RETRIES, the classification remains FAILURE_TRANSIENT. If MAX_TRANSIENT_RETRIES is exceeded or recovery fails, escalate to FAILURE_UNRECOVERABLE.

### INV-FAIL-1 — Classification Required Before Handling

**Statement:** Every failure signal from a module MUST be classified before any handling policy is applied. Unclassified failures are HANDLING_PROTOCOL_ERROR.

**Verification:** Classification assertion in the scheduler's failure handler. Every failure signal MUST match one of the signals in DEF-FAIL-2.

---

## Section 4 — Failure Handling Protocol

### INV-FAIL-2 — Handling Policy Compliance

**Statement:** For each failure classification, the prescribed handling policy in Section 2 MUST be followed. Deviation from the prescribed policy is HANDLING_POLICY_VIOLATION.

**Verification:** Policy compliance check in the failure handler. The handler implementation MUST match the policy specification per classification.

### INV-FAIL-3 — No Cascade to Unrelated Modules

**Statement:** A failure in module instance A MUST NOT cause a halt or state corruption in any module instance B that is not a successor of A in the execution graph (i.e., B does not depend on A's output).

**Verification:** State isolation assertion per `../layer-3-execution/state-management.md` INV-STATE-5. The failure is contained to the failed module and its dependent subgraph.

### INV-FAIL-4 — Failure Provenance Recording

**Statement:** Every failure event MUST be recorded in the provenance log with the full failure classification chain: the initial module signal, the assigned classification, the handling policy invoked, and the outcome. The provenance record MUST be complete before the execution state transitions.

**Verification:** Provenance completeness assertion. The failure handler MUST emit the provenance event before any state transition.

---

## Section 5 — Failure Metrics

### DEF-FAIL-3 — Failure Rate

**Definition:**

The **failure rate** for a module type MT over a time window W is:

```
failure_rate(MT, W) = count_of_FAILURES(MT, W) / total_invocations(MT, W)
```

### DEF-FAIL-4 — Recovery Rate

**Definition:**

The **recovery rate** for a module type MT is:

```
recovery_rate(MT) = count_of_FAILURE_TRANSIENT(MT) resolved by retry / count_of_FAILURE_TRANSIENT(MT)
```

### INV-FAIL-5 — Failure Rate Tracking

**Statement:** The runtime MUST track failure rate per module type and expose it to the planner via the module registry. Modules with failure_rate above a configured threshold MUST be flagged in the registry, and the planner SHOULD prefer alternative module implementations when available.

**Verification:** Registry annotation check. The planner receives the failure rate annotation during module selection per `../layer-4-mechanisms/planner-pipeline.md`.

### Section 5.A — Operational Alert Thresholds

**This section defines concrete alert thresholds and runbook triggers for production deployment. These convert the failure taxonomy into an operational playbook.**

### DEF-FAIL-5 — Alert Severity Levels

**Definition:**

| Severity | Condition | On-Call Action |
|---|---|---|
| **P1 — CRITICAL** | failure_rate(module) > 5% in any 60-minute window | Immediate on-call page; engage incident response |
| **P1 — CRITICAL** | Any FAILURE_CATASTROPHIC event | Immediate on-call page; halt affected executions |
| **P1 — CRITICAL** | Provenance integrity hash mismatch (PROVENANCE_TAMPERING_VIOLATION) | Immediate security team page; halt all executions |
| **P2 — HIGH** | failure_rate(module) > 1% in any 60-minute window | On-call page within 15 minutes |
| **P2 — HIGH** | 3+ FAILURE_UNRECOVERABLE or FAILURE_FATAL in 10 consecutive minutes | On-call page within 15 minutes |
| **P2 — HIGH** | Retry rate > 50% for FAILURE_TRANSIENT (retries / total invocations) | Investigate within 2 hours |
| **P3 — MEDIUM** | failure_rate(module) > 0.1% in any 60-minute window | Investigate within next business day |
| **P3 — MEDIUM** | Recovery success rate < 80% for any module type | Investigate within 48 hours |
| **P4 — LOW** | failure_rate(module) > baseline + 0.05% | Log for scheduled review |

### DEF-FAIL-6 — Runbook Trigger Matrix

**Definition:**

Each failure classification has an associated runbook trigger:

| Failure Event | Runbook Trigger | Escalation |
|---|---|---|
| FAILURE_TRANSIENT | TRANSIENT_RETRY_RUNBOOK: Check if failure rate is trending up; if RETRY_EXHAUSTED, escalate to FAILURE_RECOVERABLE path | If > 3 retries in 1 hour for same module, escalate to P2 |
| FAILURE_RECOVERABLE | RECOVERABLE_RUNBOOK: Identify root cause; if recoverable with alternative input binding, retry; if persists, escalate to FAILURE_UNRECOVERABLE | If > 5 recoveries in 1 hour for same module, escalate to P2 |
| FAILURE_UNRECOVERABLE | UNRECOVERABLE_RUNBOOK: Archive module state; trigger replan; flag module for post-execution review | Auto-escalate to P1 if > 2 occurrences in 1 hour |
| FAILURE_FATAL | FATAL_RUNBOOK: Halt dependents; trigger replan; flag module for mandatory post-execution audit; notify External Authority | Auto-page P1; mandatory post-mortem within 24 hours |
| FAILURE_CATASTROPHIC | CATASTROPHIC_RUNBOOK: Halt all dispatch; take final checkpoint; emit FAILURE_CATASTROPHIC event; isolate execution; begin DR procedure | Auto-page P1; mandatory post-mortem within 4 hours; regulatory notification if required |

### INV-FAIL-6 — Alert Suppression

**Statement:**

During planned maintenance windows, P1 and P2 alerts MAY be suppressed and converted to P4 informational logs, subject to approval by the on-call manager. All suppressed alerts MUST be reviewed within 24 hours of the maintenance window ending.

**Verification:** Maintenance window flag in the on-call scheduling system. Suppressed alerts are clearly labeled in the provenance log.

### INV-FAIL-7 — On-Call Runbook Availability

**Statement:**

A runbook MUST exist for each failure classification before the system is deployed. The absence of a runbook for any failure classification is a deployment blocker.

**Verification:** Runbook audit before Phase 4 exit criteria. The deployment checklist includes a runbook existence check for each defined failure event type.

### DEF-FAIL-7 — Post-Mortem Trigger

**Definition:**

A post-mortem review is triggered for any of:

| Trigger | Severity | Deadline |
|---|---|---|
| FAILURE_CATASTROPHIC | Mandatory | 4 hours |
| FAILURE_FATAL | Mandatory | 24 hours |
| P1 incident > 30 minutes duration | Mandatory | 24 hours |
| Regression in Class 1 evaluation metrics | Mandatory | 5 business days |
| Novel failure mode (unseen in prior 90 days) | Mandatory | 5 business days |

### INV-FAIL-8 — Post-Mortem Procedure

**Statement:**

Every post-mortem MUST produce a written report containing:
1. Root cause analysis (using the provenance event graph)
2. Timeline of events
3. Contributing factors
4. Impact assessment (affected executions, data subjects)
5. Remediation actions with owner and deadline
6. Preventative actions to avoid recurrence

The report MUST be reviewed by the External Authority and retained for a minimum of 3 years.

---

## Section 6 — Glossary

| Term | Definition | Document |
|---|---|---|
| FAILURE_TRANSIENT | Temporary condition, retryable | failure-taxonomy.md |
| FAILURE_RECOVERABLE | Cannot retry but can be worked around | failure-taxonomy.md |
| FAILURE_UNRECOVERABLE | Cannot be worked around, triggers replan | failure-taxonomy.md |
| FAILURE_FATAL | Unrecoverable + systemic indicator, triggers replan + audit | failure-taxonomy.md |
| FAILURE_CATASTROPHIC | Unrecoverable, halts execution immediately | failure-taxonomy.md |
| HANDLING_PROTOCOL_ERROR | Failure not classified before handling | failure-taxonomy.md |
| HANDLING_POLICY_VIOLATION | Deviation from prescribed handling policy | failure-taxonomy.md |
| MAX_TRANSIENT_RETRIES | Configured retry limit for transient failures | failure-taxonomy.md |
| Alert Severity P1/P2/P3/P4 | Operational severity levels for failure alerts | failure-taxonomy.md |
| Runbook Trigger | Predefined response procedure for each failure event | failure-taxonomy.md |
| Post-Mortem Trigger | Conditions that require written post-incident review | failure-taxonomy.md |
| PROVENANCE_TAMPERING_VIOLATION | Alert severity P1 — provenance hash chain broken | failure-taxonomy.md |
| TRANSIENT_RETRY_RUNBOOK | Runbook for FAILURE_TRANSIENT handling | failure-taxonomy.md |
| RECOVERABLE_RUNBOOK | Runbook for FAILURE_RECOVERABLE handling | failure-taxonomy.md |
| UNRECOVERABLE_RUNBOOK | Runbook for FAILURE_UNRECOVERABLE handling | failure-taxonomy.md |
| FATAL_RUNBOOK | Runbook for FAILURE_FATAL handling | failure-taxonomy.md |
| CATASTROPHIC_RUNBOOK | Runbook for FAILURE_CATASTROPHIC handling | failure-taxonomy.md |

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| FAILURE-AMEND-001 | failure-taxonomy.md | 2026-07-09 | Draft DR-2: Added operational alert thresholds (DEF-FAIL-5: P1-P4 severity with concrete failure_rate triggers), runbook trigger matrix (DEF-FAIL-6), alert suppression (INV-FAIL-6), on-call runbook availability requirement (INV-FAIL-7), post-mortem trigger (DEF-FAIL-7) and procedure (INV-FAIL-8). Addresses MLOps reviewer's runbook gap and governance reviewer's incident response gap. | No |
| FAILURE-AMEND-002 | failure-taxonomy.md | 2026-07-10 | Added INVALID_OUTPUT failure class (semantically wrong output, type-correct), extended RESOURCE_EXHAUSTED with GPU_MEMORY recovery sub-path, added PARTIAL_FAILURE for replicated module groups with majority-vote handling. Addresses systems engineer review gaps on SDC and partial replication. | No |