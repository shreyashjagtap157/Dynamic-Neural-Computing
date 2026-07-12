# Runtime Invariants

## Metadata

| Field | Value |
|---|---|
| Document | runtime-invariants.md |
| Title | Runtime Invariants |
| Document ID | SPEC-INVAR |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 2 |
| Owner Question | What properties must never be violated? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

This document is Layer 2 — the constitutional layer — of the DNC specification. All statements in this document are invariants: properties that MUST hold for every execution of the DNC runtime, regardless of configuration, workload, or operational conditions. Invariants are the most constrained concept class in the specification; per PR-8, any change to an invariant is a Breaking Revision.

Every invariant in this document is verified by at least one mechanism: formal proof, runtime assertion, static analysis, model checking, deterministic replay, or benchmark evaluation, per PR-5. The verification mechanism is stated for each invariant.

Invariant identifiers (INV-1 through INV-10) are permanently allocated and MUST NOT be reassigned. New invariants MUST use the next available identifier from the namespace registry (INV-11, INV-12, ...).

Layer 2 documents MUST NOT reference any document above Layer 2. This document references only Layer 0 (governance) and Layer 1 (terminology).

---

## Section 2 — Invariant Statements

### INV-1 — Execution Header Immutability

**Statement:**

Every execution SHALL be governed by exactly one immutable eight-field execution header: ExecutionID, Specification Version, Runtime Version, Planner Version, Registry Version, Configuration Hash, Random Seed, Timestamp. No execution MAY proceed if any field of this header cannot be resolved to a non-null value. The header is immutable for the lifetime of the execution; module updates MUST NOT be visible to any in-flight execution.

**Verification:** Runtime assertion at execution initiation. The execution header MUST be validated and committed before the first step is dispatched.

**Rationale:** Reproducible execution requires version-fixed dependencies. This is the Layer 2 expression of PR-10 (Version Consistency Rule).

### INV-2 — DAG Acyclicity of Execution Graphs

**Statement:**

Every execution graph G produced by the planner MUST be a directed acyclic graph. The scheduler MUST verify G is acyclic before dispatching any step. An execution graph containing a cycle is a GRAPH_CYCLE_VIOLATION and MUST cause the planner to be reinvoked to produce an acyclic graph.

**Verification:** Cycle detection by the scheduler before dispatch. Topological sort MUST succeed; if it fails, the graph contains a cycle.

**Rationale:** A cyclic execution graph has no defined step order. Execution would deadlock or produce undefined ordering-dependent results. This is the runtime enforcement of the document dependency acyclicity requirement (PR-4) applied to execution.

### INV-3 — No Undefined Behavior

**Statement:**

Every behavior of the runtime SHALL be either explicitly defined, explicitly permitted, or explicitly forbidden. No behavior SHALL be left undefined, unspecified, or described as "implementation-defined" without a documented rationale. Any behavior classified as Undefined MUST be revisited in a subsequent specification revision.

**Verification:** Document review. Every behavioral description in every specification document MUST be classified as Defined, Permitted, Forbidden, or Undefined (with rationale). Linter: each normative statement carries the four-class classification.

**Rationale:** Undefined behavior is an ownership gap. It delegates decisions to implementers in ways that are unaudited and non-reproducible. This is the Layer 2 expression of PR-6 (No-Undefined-Behavior Rule).

### INV-4 — Single-Ownership of Module Semantics

**Statement:**

Every module type registered in the module registry MUST have exactly one owning document that defines its computational semantics. No module type's behavior SHALL be defined, modified, or ambiguously described across multiple documents.

**Verification:** Registry consistency check. Each ModuleTypeID maps to exactly one document in the registry.

**Rationale:** Without single-ownership, module semantics drift. Two documents that define the same module type inevitably diverge on edge cases.

### INV-5 — State Isolation Between Executions

**Statement:**

The working memory W(t), checkpoint record C(t), and history log H(t) of one execution MUST be completely isolated from the working memory, checkpoint record, and history log of any concurrent or sequential execution. State from one execution MUST NOT be accessible to or influence the execution state of another execution unless explicitly shared through the module contract's inter-execution communication interface.

**Verification:** Runtime assertion. The execution state data structures MUST be namespaced by ExecutionID. Cross-execution state access MUST be mediated by the module registry's inter-execution communication channel.

**Rationale:** Parallel or sequential executions must not interfere. Without isolation, one execution's replanning could corrupt another's state.

### INV-6 — Checkpoint Validity Before Replan

**Statement:**

Before the planner is invoked to produce a new execution graph mid-execution, the runtime MUST have a valid checkpoint of the current execution state ES(t). A checkpoint is valid if and only if it is complete (no null components in ES(t)), has a resolvable provenance reference, and has a unique step index. If no valid checkpoint exists, the runtime MUST take one before invoking the planner.

**Verification:** Runtime assertion in the planner pipeline. The planner MUST confirm a valid checkpoint exists before accepting a replan request.

**Rationale:** Replanning without a checkpoint leaves no stable recovery point. If the replan fails, the runtime cannot roll back to a known-good state.

### INV-7 — Handoff Atomicity

**Statement:**

A state handoff between module instance A and module instance B — where W(t)[A].output becomes W(t+1)[B].input — MUST be atomic: either both the write and the read commit, or neither is considered committed. The scheduler MUST use a two-phase commit discipline for all intra-step handoffs.

**Verification:** Model checking of the scheduler's handoff protocol. The protocol MUST satisfy atomic-commit properties for all module pairs.

**Rationale:** Non-atomic handoffs create race conditions where a downstream module reads stale or null input while the upstream has produced new output.

### INV-8 — All Invariants Verified Before Execution

**Statement:**

Every invariant in this document MUST be verified before the runtime accepts its first execution request after a module registry update. If any invariant is violated after a registry update, the runtime MUST refuse to initiate new executions until the violation is resolved.

**Verification:** Pre-execution invariant check. The runtime MUST run the full invariant verification suite before accepting new executions after any registry mutation.

**Rationale:** A module registry update that introduces an invariant violation must not be allowed to corrupt future executions.

### INV-9 — No Behavioral Drift Beyond Bound

**Statement:**

After a continual learning update, the updated runtime's behavioral drift Δ(p, p') from any prior execution p in the execution history MUST NOT exceed the configured DRIFT_BOUND. Additionally, the updated runtime MUST satisfy all active invariants (INV-1 through INV-8 and any subsequently added invariants).

**Verification:** Evaluation suite run and formal invariant check before any knowledge base commit. The verification protocol is defined in `../layer-6-evolution/continual-learning.md` INV-CL-8.

**Rationale:** This is the Layer 2 expression of the bounded-drift principle from `../layer-6-evolution/continual-learning.md`. It ensures that learning improves capability without eroding reliability.

### INV-10 — Normative Statement Keyword Discipline

**Statement:**

Every normative statement in every DNC specification document SHALL use at least one RFC 2119 keyword (MUST, SHALL, MUST NOT, SHOULD, MAY) to express its requirement level. Explanatory text MUST use lowercase forms without normative implication. A normative statement without an RFC 2119 keyword is a Normative-Wording Violation.

**Verification:** Linter. Every normative statement in every document MUST contain at least one RFC 2119 keyword in all-caps.

**Rationale:** This is the Layer 2 enforcement of PR-7 (Normative-Wording Rule). Without machine-checkable normative language, compliance cannot be verified.

---

## Section 3 — Invariant Preservation Under Extension

### INV-11 — Preservation Under Extension (from PR-8)

**Statement:**

Any change to a DNC specification document at Layer 2 or higher that modifies an existing Invariant or introduces a new Invariant MUST either preserve all previously established Invariants or explicitly declare a Breaking Revision, update the specification version, provide a migration rationale, and require acceptance by explicit review ballot. No Breaking Revision is permitted without declaring itself as such.

**Verification:** Amendment log review. Any amendment modifying an INV-* statement MUST include either a compatibility confirmation or a Breaking Revision declaration.

**Rationale:** Invariants are the constitutional layer. They cannot be silently eroded by extensions. This is the formal statement of PR-8 at Layer 2.

---

## Section 4 — Glossary

| Term | Definition | Document |
|---|---|---|
| Execution Header | The 8-field immutable tuple governing each execution | runtime-invariants.md |
| GRAPH_CYCLE_VIOLATION | Error when execution graph contains a cycle | runtime-invariants.md |
| Breaking Revision | Explicitly declared backward-incompatible change | specification-foundation.md |
| Active Invariant | An INV-* currently enforced by the runtime | core-terminology.md |
| Behavioral Envelope | Region of behaviors satisfying all active invariants | continual-learning.md |

---

## Section 5 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |