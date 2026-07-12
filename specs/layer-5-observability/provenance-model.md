# Provenance Model

## Metadata

| Field | Value |
|---|---|
| Document | provenance-model.md |
| Title | Provenance Model |
| Document ID | SPEC-PROV |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 5 |
| Owner Question | What provenance exists and how is it recorded? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

Every claim about runtime behavior in the DNC specification MUST be backed by evidence per PR-9 (Evidence Principle). The provenance model is the system that records, chains, and enables retrieval of that evidence. It is the DNC runtime's memory of what happened, why, and what changed as a result.

The provenance model operates as an append-only event log structured as a directed acyclic graph of causal events. Every event is timestamped, typed, and carries a reference to the causal antecedent that triggered it. The graph structure ensures that the causal chain from any runtime outcome (a decision, a step completion, a learning update) can be traced back to its originating trigger.

The provenance model depends on:
- Layer 3: execution state and step lifecycle (what events can occur)
- Layer 4: planner, scheduler, and module lifecycle (what causes events)
- Layer 6: continual learning (which uses provenance for learning event evidence)

It does not depend on Layer 5 (other documents at the same layer) per PR-4.

---

## Section 2 — Event Model

### DEF-PROV-1 — Provenance Event

**Definition:**

A **provenance event** e is a tuple:

```
e = (event_id, event_type, timestamp, execution_id, step_index,
     causal_ref, payload, integrity_hash)
```

Where:
- `event_id` is a globally unique identifier for this event
- `event_type` is the event classification (see Section 3)
- `timestamp` is the wall-clock time at event creation
- `execution_id` is the execution this event belongs to
- `step_index` is the step index at event creation (null if no step is active)
- `causal_ref` is the event_id of the immediate causal antecedent (null for initiating events)
- `payload` is a structured record containing event-specific data
- `integrity_hash` is a cryptographic hash of the event for tamper detection

### DEF-PROV-2 — Event Graph

**Definition:**

The **provenance event graph** for an execution is the directed graph G_prov = (V_prov, E_prov) where:
- V_prov is the set of events for the execution
- E_prov = {(e_causal, e_effect) | e_effect.causal_ref = e_causal.event_id}

By construction, G_prov is a DAG. The root nodes are initiating events (where causal_ref is null).

### INV-PROV-1 — Append-Only Provenance

**Statement:** The provenance log is append-only. No event MAY be deleted, modified, or reordered after creation. Each new event MUST be appended with a monotonically increasing event_id and timestamp. Tampering with any event (detected via integrity hash mismatch) is a PROVENANCE_TAMPERING_VIOLATION and MUST be logged as a FAILURE_CATASTROPHIC.

**Verification:** Integrity hash verification on read. The provenance subsystem MUST verify the integrity hash of every event on retrieval. Mismatch triggers PROVENANCE_TAMPERING_VIOLATION.

**Rationale:** The provenance log is the evidence chain for PR-9. If it can be modified, no claim about runtime behavior can be trusted.

### INV-PROV-2 — Causal Chain Completeness

**Statement:** For every event e with causal_ref ≠ null, the referenced event MUST exist in the provenance log and MUST belong to the same execution. An event with a null causal_ref that is not an initiating event type is an CAUSAL_CHAIN_BROKEN error.

**Verification:** Causal reference resolution. The provenance subsystem verifies every causal_ref resolves to an existing event in the same execution.

---

## Section 3 — Event Types

### STEP_DISPATCHED

**Payload:** `(step_index, module_instance_id, module_type_id, input_binding_summary, cost, time_budget)`

**Causal antecedent:** The DECISION event that produced CONTINUE or the execution initiation event.

### STEP_COMPLETED

**Payload:** `(step_index, module_instance_id, output_value_hash, execution_time_ms, cost_actual, outcome_classification)`

**Causal antecedent:** The STEP_DISPATCHED event for this step.

### STEP_FAILED

**Payload:** `(step_index, module_instance_id, failure_classification, failure_reason, recoverable)`

**Causal antecedent:** The STEP_DISPATCHED event for this step.

### CHECKPOINT_CREATED

**Payload:** `(checkpoint_id, step_index, es_snapshot_hash, provenance_ref)`

**Causal antecedent:** The step completion event that immediately preceded the checkpoint.

### REPLAN_TRIGGERED

**Payload:** `(trigger_type, trigger_subtype, step_index, trigger_rationale, replan_counter_before)`

**Causal antecedent:** The event that caused the trigger (e.g., STEP_FAILED, TIME_BUDGET_EXCEEDED, USER_DIRECTIVE).

### GRAPH Diff_COMPUTED

**Payload:** `(replan_id, retained_count, retired_early_count, new_count, preserved_state_summary)`

**Causal antecedent:** The REPLAN_TRIGGERED event.

### DECISION

**Payload:** `(decision_type, observe_summary, assessment_outcome, execution_state_hash)`

**Causal antecedent:** The preceding ASSESSMENT event.

### MODULE_REGISTERED

**Payload:** `(module_type_id, version, contract_hash, timestamp)`

**Causal antecedent:** null (initiating event).

### MODULE_DEREGISTERED

**Payload:** `(module_type_id, version, grace_period_used, affected_executions)`

**Causal antecedent:** null (initiating event).

### MODULE_RETIRED

**Payload:** `(module_instance_id, final_output_hash, retirement_step_index, retirement_rationale)`

**Causal antecedent:** The GRAPH_DIFF_COMPUTED event for the replan that retired this module.

### LEARNING_EVENT

**Payload:** `(event_id, trigger_execution_id, trigger_step, observed_outcome_hash, expected_outcome_hash, delta_quality, is_novel, candidate_update_summary)`

**Causal antecedent:** The STEP_COMPLETED event that produced the observed outcome.

### KB_UPDATE_COMMITTED

**Payload:** `(kb_version_before, kb_version_after, triggering_le_event_id, drift_metrics, evaluation_results)`

**Causal antecedent:** The final LEARNING_EVENT in the batch that triggered this update.

### KB_ROLLBACK

**Payload:** `(kb_version_rolled_back_to, kb_version_failed, failure_reason, preserved_history)`

**Causal antecedent:** The failure classification event that detected the invariant violation.

### EXECUTION_TERMINATED

**Payload:** `(final_step_index, total_execution_time_ms, termination_reason, outcome_summary)`

**Causal antecedent:** The DECISION event with decision_type = TERMINATE.

---

## Section 4 — Provenance Queries

### DEF-PROV-3 — Causal Chain Query

**Definition:**

A **causal chain query** for an event e returns the sequence [e_0, e_1, ..., e_n] where e_n = e, each e_i.causal_ref = e_{i-1}.event_id, and e_0.causal_ref = null (the initiating event).

### DEF-PROV-4 — Effect Query

**Definition:**

An **effect query** for an event e returns all events e' where e' is reachable from e in G_prov (i.e., there exists a path from e to e').

### DEF-PROV-5 — State Provenance Query

**Definition:**

A **state provenance query** for a working memory value W(t)[n_i].output returns the causal chain of events that produced that value, terminating at the STEP_COMPLETED event that set it.

### INV-PROV-3 — Query Determinism

**Statement:** Given the same provenance log and the same query, the provenance query MUST return the same result in all compliant implementations. The query algorithms are deterministic.

**Verification:** Deterministic query algorithm specification. Regression testing against canonical provenance graphs.

---

## Section 5 — Integrity and Tamper Detection

### INV-PROV-4 — Hash Chain Integrity

**Statement:** Each event's integrity_hash MUST incorporate the previous event's integrity_hash as part of its input. This creates a hash chain: modifying any event in the log breaks the chain from that event forward.

**Verification:** Hash chain verification on log read. The provenance subsystem traverses the log forward, verifying each integrity_hash against the previous hash.

### INV-PROV-5 — Retention Policy

**Statement:** Provenance logs MUST be retained for the lifetime of the runtime. Truncation of the provenance log is prohibited unless explicitly archived per the archival protocol. The full event graph MUST be queryable at any time.

**Verification:** Retention policy enforcement. The provenance subsystem MUST reject any truncation operation that is not an archival operation.

---

## Section 6 — Glossary

| Term | Definition | Document |
|---|---|---|
| Provenance Event | (event_id, event_type, timestamp, execution_id, step_index, causal_ref, payload, integrity_hash) | provenance-model.md |
| Event Graph | DAG of events linked by causal_ref | provenance-model.md |
| Causal Chain Query | Trace from event to initiating event | provenance-model.md |
| Effect Query | All events reachable from a given event | provenance-model.md |
| State Provenance Query | Causal chain for a specific value in working memory | provenance-model.md |
| PROVENANCE_TAMPERING_VIOLATION | Error when integrity hash mismatch detected | provenance-model.md |
| CAUSAL_CHAIN_BROKEN | Error when causal_ref does not resolve | provenance-model.md |

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |