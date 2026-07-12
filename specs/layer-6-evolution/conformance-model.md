# Conformance Model

## Metadata

| Field | Value |
|---|---|
| Document | conformance-model.md |
| Title | Conformance Model |
| Document ID | SPEC-CONF |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | What does it mean for an implementation to be DNC-conformant? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md, interfaces.md, execution-trace-format.md, replay-semantics.md |
| Defines | DNC-Conformant implementation, mandatory invariants, extension rules, traceability matrix |
| Referenced by | evaluation-framework.md, mvp-roadmap.md |

---

## Section 1 — Overview

### 1.A Purpose

This document defines what it means for an implementation to be DNC-conformant. It establishes the contract between the specification and every implementation, enabling objective conformance verification.

Conformance in DNC is modeled on established standards practice: the specification defines *what* must be done; the conformance model defines *how* compliance is determined.

### 1.B Architecture v1.0

Architecture v1.0 is the frozen baseline for DNC Phase 5. All implementations targeting Phase 5 MUST conform to Architecture v1.0.

The Architecture v1.0 version identifier appears in every execution trace header.

---

## Section 2 — Architecture Version Policy

### 2.A Version Lifecycle

| Status | Meaning |
|---|---|
| **Architecture v1.0 Draft** | Specification under development; may change |
| **Architecture v1.0** | Frozen; all normative documents final |
| **Architecture v1.1** | Backward-compatible additions only |
| **Architecture v2.0** | Breaking revision; requires explicit migration |

### 2.B Change Classification

| Change Type | Version Action | Example |
|---|---|---|
| **Editorial clarification** | No version increment | Fixing ambiguous wording, adding examples |
| **Backward-compatible addition** | Architecture v1.x | Adding new OPTIONAL fields to trace schema, new capability flags |
| **Breaking architectural change** | Architecture v2.0 | Modifying execution semantics, changing invariant meanings, removing fields |

### 2.C Breaking Revision Process

A breaking architectural change (Architecture v2.0) requires:

1. Formal proposal identifying the breaking change
2. Impact analysis: what breaks and how
3. Migration path: how v1.0 implementations transition to v2.0
4. External Authority vote (if deployed in regulated contexts)
5. 60-day public review period
6. Explicit version increment declaration

---

## Section 3 — Extension Rules

### 3.A Permitted Extensions

An implementation MAY add:

- New ExecutionCapabilities (CAP-*) — via the capability registration mechanism
- New ExecutionProviders — as long as they conform to the provider interface
- New DecisionPolicies — as long as they implement the DecisionPolicy interface
- New metrics (MET-*) — as long as they don't conflict with existing metrics
- New module types — as long as they conform to the module contract
- New OPTIONAL fields in the ExecutionTrace — via EXT-* namespace

### 3.B Prohibited Modifications

An implementation MUST NOT modify:

- **Execution semantics** — The execution model in `execution-semantics.md` is immutable for a given Architecture version
- **Replay semantics** — Deterministic replay requirements in `replay-semantics.md` are immutable
- **Trace semantics** — The REQUIRED and CONDITIONAL fields in the ExecutionTrace schema are immutable
- **Invariant meanings** — The interpretation of INV-* identifiers is frozen per Architecture version
- **Conformance Clause requirements** — The mandatory requirements in each document's conformance clause

### 3.C Experimental Extensions

Experimental extensions use the **EXT-*** namespace:

```
EXT-<provider_name>-<feature>
EXT-<policy_name>-<feature>
EXT-<metric_name>
EXT-<capability_name>
```

Experimental extensions:
- MUST NOT modify normative behavior
- MUST be declared in the execution trace as `extension: EXT-*`
- MAY be promoted to normative (Architecture v1.x) via the amendment process
- MUST be clearly documented as experimental

### 3.D Extension Registry

All active extensions are registered in the extension registry:

| Extension ID | Type | Owner | Status |
|---|---|---|---|
| (none yet) | — | — | — |

---

## Section 4 — Conformance Requirements by Component

### 4.A Runtime Conformance

An implementation claiming DNC-runtime conformance MUST satisfy:

| Requirement | Invariant | Verification |
|---|---|---|
| Control loop executes Observe→Decide→Act→Assess | INV-EXEC-1 | Runtime assertion |
| DecisionPolicy invoked at every Decide phase | INV-EXEC-2 | Trace verification |
| Planner invoked only when REPLAN selected | INV-EXEC-3 | Trace verification |
| Scheduler dispatches only when preconditions met | INV-EXEC-4 | Invariant test |
| Execution trace records every iteration | INV-EXEC-5 | Trace completeness check |
| Checkpoint taken before every REPLAN | INV-EXEC-6 | Trace verification |
| Rollback restores exact state | INV-EXEC-7 | Replay verification |

### 4.B Execution Provider Conformance

An implementation claiming DNC-provider conformance for a specific ExecutionProvider MUST satisfy:

| Requirement | Verification |
|---|---|
| implements ExecutionProvider interface (Section 3.A of interfaces.md) | Interface test |
| supports() returns True only for genuinely implemented capabilities | Capability test |
| execute() produces ProviderResult with all required fields | Interface test |
| All declared capabilities are functional (not stubs) | Integration test |

### 4.C DecisionPolicy Conformance

An implementation claiming DNC-policy conformance for a specific DecisionPolicy MUST satisfy:

| Requirement | Verification |
|---|---|
| implements DecisionPolicy interface | Interface test |
| decide() returns one of: CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK | Interface test |
| can_replan() returns bool | Interface test |
| version is declared | Interface test |
| Trace records every decision with policy_version | Trace verification |

### 4.D ReplayEngine Conformance

An implementation claiming DNC-replay conformance MUST satisfy:

| Requirement | Verification |
|---|---|
| ReplayEngine interface fully implemented | Interface test |
| INV-REP-1 through INV-REP-5 satisfied | Determinism test |
| ReplayVerifier correctly identifies divergences | Verification test |
| Bit-identical replay for conformant traces | Replay comparison test |

---

## Section 5 — Traceability Matrix

The traceability matrix maps every normative requirement to its specification source and verification method.

### 5.A Complete Traceability Matrix

| Requirement | Spec Document | Invariant | Verification Method | Test Location |
|---|---|---|---|---|
| Control loop sequence | execution-semantics.md §2.C | INV-EXEC-1 | Runtime assertion | test_control_loop |
| DecisionPolicy invocation | execution-semantics.md §2.C | INV-EXEC-2 | Trace check | test_decision_policy |
| Planner invocation condition | execution-semantics.md §2.C | INV-EXEC-3 | Trace check | test_replan |
| Scheduler precondition enforcement | architecture.md §2.E | INV-EXEC-4 | Invariant test | test_scheduler_precondition |
| Trace recording completeness | execution-semantics.md §2.C | INV-EXEC-5 | Trace validation | test_trace_completeness |
| Checkpoint before REPLAN | execution-semantics.md §2.C | INV-EXEC-6 | Trace check | test_checkpoint_replan |
| Rollback state restoration | execution-semantics.md §2.C | INV-EXEC-7 | Replay verification | test_rollback |
| ExecutionProvider interface | interfaces.md §3.A | INV-CP-1 | Interface test | test_provider_interface |
| DecisionPolicy interface | decision-policy.md §3.A | INV-POL-1 | Interface test | test_policy_interface |
| Replay determinism | replay-semantics.md §2.A | INV-REP-1 | Replay comparison | test_replay_determinism |
| Replay step ordering | replay-semantics.md §3 | INV-REP-2 | Step order check | test_replay_order |
| Metric hierarchy | evaluation-framework.md §3 | INV-EV-1 | Metric classification check | test_metric_hierarchy |
| Counterfactual Compute Gain | evaluation-framework.md §4 | MET-CCG-1 | Metric computation test | test_ccg |
| Dynamic Compute Index | evaluation-framework.md §4 | MET-DCI-1 | Metric computation test | test_dci |

### 5.B Invariant Namespaces (Reserved)

| Namespace | Purpose |
|---|---|
| INV-RT-* | Runtime invariants (currently INV-EXEC-*) |
| INV-CP-* | ExecutionProvider/Capability invariants |
| INV-POL-* | DecisionPolicy invariants |
| INV-EV-* | Evaluation invariants |
| INV-REP-* | Replay invariants |

---

## Section 6 — Conformance Testing

### 6.A Conformance Test Suite

DNC provides a **conformance test suite** that objectively tests whether an implementation satisfies the conformance requirements. The test suite is the authoritative reference for conformance verification.

### 6.B Conformance Levels

| Level | Description | Requirements |
|---|---|---|
| **Level 1: Interface Conformance** | All interfaces implemented correctly | All interface tests pass |
| **Level 2: Runtime Conformance** | Execution semantics correctly implemented | All INV-EXEC-* tests pass |
| **Level 3: Provider Conformance** | All providers satisfy provider interface | All INV-CP-* tests pass |
| **Level 4: Evaluation Conformance** | Evaluation framework correctly computes metrics | All MET-* tests pass |
| **Level 5: Full Conformance** | Complete DNC implementation | All tests pass, replay is bit-identical |

An implementation MUST achieve Level 1 before claiming any DNC conformance. Higher levels are additive.

### 6.C Conformance Declaration

An implementation declares conformance as:

```
DNC-Conformant (Architecture v1.0, Level N)
```

where N is the highest conformance level achieved.

The declaration MUST appear in all documentation and source files for the implementation.

---

## Section 7 — Permanent Rule

> **Normative requirements SHALL NOT appear in implementation documentation. All normative requirements originate in the specification and implementations may only reference them by identifier.**

This rule prevents specification drift between documentation and code. If a conformance requirement is described in implementation documentation, the specification remains the authoritative source. The implementation may not redefine or narrow a normative requirement.

---

## Section 8 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| CONF-AMEND-001 | conformance-model.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of conformance model, Architecture v1.0 version policy, extension rules, traceability matrix, conformance levels, permanent rule. | No |