# DNC-IR Specification — Freeze

**Date**: 2026-07-22  
**Status**: FROZEN — intermediate representation specification  
**Scope**: Canonical semantics of the DNC intermediate representation

---

## 1. What This Document Is

This document formally freezes the DNC-IR specification. The IR has been reviewed against the foundational baseline (Q1–Q5, seven axioms) and corrected. It now forms the **canonical language** in which DNC computational structure is described.

---

## 2. Review Summary

### 2.1 Traceability Matrix

| DNC-IR Concept | Q1 | Q2 | Q3 | Q4 | Q5 | Axiom | Status | Classification |
|----------------|----|----|----|----|----|----|--------|----------------|
| Structural Graph | ✓ | ✓ | ✓ | | | A3/A4 | PASS | Derived |
| ComputationalUnit dimensions | | ✓ | | | | A2 | PASS | Direct from Q2 |
| Edge model | | ✓ | | | | A2 | PASS | Derived |
| Graph identity (GraphID) | | | ✓ | ✓ | | A3/A4 | PASS | Derived |
| Unit identity (UnitID) | | ✓ | | ✓ | | A2/A4 | PASS | Derived |
| MutationID | | | | ✓ | | A4/A5 | PASS | Derived |
| Graph versioning | | | ✓ | | | A4 | PASS | Derived |
| Unit contract | | ✓ | | | | A2 | PASS | Extended from Q2 |
| MutationContract | | | | ✓ | | A5 | PASS | Derived from Q4 |
| State contract | | | ✓ | | | A3 | PASS | Derived (stateful units) |
| Execution contract | | | | | | | PASS | Derived (deterministic/idempotent guarantees) |
| Unit capabilities | | | | | | | PASS | Derived (extends mutation capabilities) |
| Graph capabilities | | | | | | | PASS | Derived (extends graph properties) |
| Three-tier model | ✓ | | | ✓ | | A4/A5 | PASS | Derived formalization |
| IR operations vocabulary | ✓ | ✓ | | ✓ | | A1/A5 | PASS | Derived |
| Operations ≠ mutations | | | | ✓ | | A5 | PASS | Direct from Q4 |
| Validation pipeline | ✓ | | | ✓ | | A1/A5 | PASS | Derived |
| Serialization | | | | | | | PASS | Implementation concern |
| Conformance levels | ✓ | | | ✓ | | | PASS | Derived |
| Boundary (entry/exit) | | ✓ | | | | A2 | PASS | Derived |
| Edge types | | ✓ | | | | A2 | PASS | Derived |

### 2.2 Issues Found and Resolved

| Issue | Resolution |
|-------|------------|
| Σ(t) graph representation: Structural vs. DAG | Clarified: Σ(t) contains Structural Graph; Execution Core uses Executable DAG projection |
| MutationContract missing operations | Added: may_be_split, may_be_merged, may_be_decomposed |
| ExecutionContract not in Q1–Q5 | Classified as DERIVED (enables deterministic/idempotent guarantees) |
| UnitCapabilities not in Q2–Q4 | Classified as DERIVED (extends mutation capabilities for Generator/Controller) |
| GraphCapabilities not in Q2–Q4 | Classified as DERIVED (extends graph properties) |
| Analysis Operations authorization | Explicitly noted as READ-ONLY; no authorization required |
| Capability ≠ Permission distinction | Made explicit in MutationContract section |
| DNC-IR conformance composition with v1.x | Made explicit: Level 4 implies Execution Core invariants (INV-1–9) |

---

## 3. Key Decisions Frozen

### 3.1 DNC-IR Is the Structural Component of Σ(t)

DNC-IR represents the structural component of the Computation Domain, not the entire domain. Unit state and registry are separate.

### 3.2 Structural Graph vs. Executable Graph

Σ(t) contains the Structural Graph (may be non-DAG). The Execution Core projects to an Executable DAG. This distinction enables representing recurrent structures while maintaining DAG execution.

### 3.3 Three Orthogonal Dimensions

ComputationalUnit identity is defined by three independent dimensions: structure (PRIMITIVE/COMPOSITE), visibility (OPAQUE/INSPECTABLE), lifecycle (BASE/SPECIALIZED). No flat type hierarchy.

### 3.4 Stable Identity

Every element has stable, immutable, mutation-tracked identity. UnitIDs are retired but never reused. Full provenance reconstruction is always possible.

### 3.5 MutationContract as Capability Model

The MutationContract defines what is *technically permitted* for a unit. This is distinct from authorization (Controller), policy (Generator), and constraints (validation pipeline).

### 3.6 Three-Tier Enforcement

Invariant (absolute) ≠ Constraint (negotiable) ≠ Policy (advisory). The Mutation Engine, Controller, and validation pipeline enforce different tiers.

### 3.7 Operations ≠ Mutations

DNC-IR operations are abstract transformation vocabulary. Mutations are proposed, authorized, and applied transactionally. The six-role authority model from Q4 is preserved.

### 3.8 Analysis Operations Are Read-Only

Validate, Inspect, Diff, Query are queries, not mutations. They do not require authorization.

---

## 4. Derived Concepts

The following concepts appear in DNC-IR but not in Q1–Q5. They are classified as **derived** — consequences of the foundational axioms, not new architectural decisions:

| Concept | Derivation |
|---------|------------|
| Boundary (entry/exit points) | Enables composition (Q2 Composite units) |
| Edge types (DATA/CONTROL/CONDITIONAL) | Extends Q2 edge model |
| State contract | Enables stateful units (Q3 state model) |
| Execution contract | Enables deterministic/idempotent guarantees |
| Unit capabilities | Extends mutation capabilities for Generator/Controller |
| Graph capabilities | Extends graph properties |
| Three-tier model | Formalizes existing invariant/constraint/policy distinction |
| Conformance levels | Defines implementation requirements |
| Serialization formats | Implementation concern |

---

## 5. What This Freeze Establishes

- The canonical semantics of DNC-IR
- The graph model (Structural → Executable)
- The ComputationalUnit representation (three orthogonal dimensions)
- The identity model (stable, immutable, mutation-tracked)
- The contract model (input, output, state, resource, execution, mutation)
- The three-tier enforcement model (invariant, constraint, policy)
- The operations vocabulary (structural, connection, composition, lifecycle, analysis)
- The validation pipeline (syntactic → semantic → structural → invariant → constraint)
- The conformance model (five nested levels)

---

## 6. What This Freeze Does NOT Establish

- Serialization format details (JSON schema, binary format)
- Python reference implementation
- Mutation semantics (how operations transform Σ)
- Transaction semantics (how mutations are atomic)
- The Dynamic Computation Control Layer

These are derived from DNC-IR and specified in downstream documents.

---

## 7. Transition

DNC-IR is now frozen.

The next phase is **Mutation Semantics** — how DNC-IR operations transform Σ(t) atomically.

```
DNC-IR (frozen)
    ↓
Mutation Semantics
    ↓
Transaction Semantics
    ↓
Dynamic Computation Control Layer
    ↓
Implementation
```

The chain so far:

**Codebase Audit → Execution Core Freeze → Foundational Theory (Q1–Q5) → Consistency Review → Foundational Baseline Freeze → DNC-IR → DNC-IR Freeze (this document) → ...**
