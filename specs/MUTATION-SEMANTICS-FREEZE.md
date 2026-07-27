# Mutation Semantics — Freeze

**Date**: 2026-07-22  
**Status**: FROZEN — mutation semantics specification  
**Scope**: Canonical semantics of structural mutation in DNC v2.x  
**Depends on**: DNC-IR Freeze, Foundational Baseline Freeze (Q1–Q5)  
**Depended on by**: Transaction Semantics, Dynamic Computation Control Layer

---

## 1. What This Document Is

This document formally freezes the **Mutation Semantics** specification (`specs/mutation-semantics.md`). Mutation Semantics has been reviewed against the foundational baseline (Q1–Q5, seven axioms) and DNC-IR. All issues identified during review have been resolved. 

It now forms the **canonical rules** for how structural changes transform DNC computational structures and system states.

---

## 2. Review Summary

### 2.1 Traceability Matrix

| Mutation Semantics Concept | Q1 | Q2 | Q3 | Q4 | Q5 | Axiom | Status | Classification |
|---------------------------|----|----|----|----|----|----|--------|----------------|
| Mutation model M: Gₜ → Gₜ₊₁ | ✓ | ✓ | ✓ | | | A1/A4 | PASS | Derived |
| System transition Σ(t) → Σ(t+1) | | | ✓ | ✓ | | A3/A4 | PASS | Derived |
| Mutation taxonomy | ✓ | ✓ | | ✓ | | A1/A2/A5 | PASS | Derived |
| Structural boundary | ✓ | ✓ | | | | A1/A2 | PASS | Derived |
| Six-role pipeline | | | | ✓ | | A5 | PASS | Derived |
| Proposal semantics | | | | ✓ | | A5 | PASS | Derived |
| Authorization semantics | | | | ✓ | | A5 | PASS | Derived |
| Validation sequence | ✓ | ✓ | | ✓ | | A1/A2/A5 | PASS | Derived |
| Mutation algebra | ✓ | ✓ | | | | A1/A2 | PASS | Derived |
| Equivalence | ✓ | | | | | A1 | PASS | Derived |
| Failure semantics | | | | ✓ | | A5 | PASS | Derived |
| Identity and versioning | | | ✓ | ✓ | | A3/A4 | PASS | Derived |
| Provenance | | | | ✓ | | A5 | PASS | Derived |

**Traceability: 13/13 PASS**  
**Axiom Consistency: 7/7 PASS**  
**DNC-IR Consistency: 11/11 PASS**

### 2.2 Issues Found and Resolved During Review

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Overlap between "Structural Mutations" and "Structural Mutation Boundaries" | Merged boundary definition directly into §3.1; consolidated structure |
| 2 | Overlap between "Proposal Validity" and "Mutation Validation" | Clarified scopes: Proposal validity checks the proposal as a whole; Mutation validation checks each operation against current state |
| 3 | Inverse table missing EXTRACT, INLINE, UPDATE operations | Added EXTRACT/INLINE inverse pair; noted UPDATE operations have no automatic inverse |
| 4 | DECOMPOSE inverse ambiguity ("structure preserved") | Clarified: DECOMPOSE inverse (`COMPOSE`) exists only if original internal structure was preserved during decomposition |
| 5 | Working memory lifecycle when unit removed / composed / decomposed | Added explicit working memory cleanup/nesting rules for REMOVE, COMPOSE, and DECOMPOSE in §9.2 |

---

## 3. Key Decisions Frozen

### 3.1 The Mutation Function

A mutation transforms the DNC-IR Structural Graph:
```
M: Gₜ → Gₜ₊₁
```
And the complete system transition transforms unified state:
```
T_M: Σ(t) → Σ(t+1)
```

### 3.2 Structural vs. Non-Structural Mutations

- **Structural mutations** (ADD, REMOVE, CONNECT, DISCONNECT, REWIRE, REPLACE, COMPOSE, DECOMPOSE, EXTRACT, INLINE, SPECIALIZE) change graph topology or unit lifecycle and go through the **full six-role authority pipeline**.
- **Non-structural mutations** (parameter updates, routing adjustments, cost budget changes) stay within unit or execution boundaries.

### 3.3 Authority Preservation

The six-role pipeline (Generator → Controller → Engine → Execution → Assessment → Learning) is strictly enforced. No role may silently collapse proposal, authorization, application, execution, assessment, or learning into one operation.

### 3.4 Validation Sequence

Every mutation undergoes mechanical validation in a strict order:
1. Operation Validity (syntax/parameters)
2. Identity Validation (existence of targets)
3. Contract Validation (MutationContract capabilities)
4. Invariant Validation (absolute invariants)
5. Constraint Validation (negotiable constraints)
6. Resource Validation (cost budgets)
7. Authorization (Controller approval)

### 3.5 Algebraic Rigor

Mutations satisfy formal algebraic properties:
- **Composition**: `(M₂ ∘ M₁)(G)`
- **Inverse**: `M⁻¹(M(G)) = G` (defined for reversible structural operations)
- **Commutativity**: Disjoint operations commute (`M₁ ∘ M₂ = M₂ ∘ M₁`)
- **Idempotence**: Operations like `CONNECT` or `SPECIALIZE` are idempotent

### 3.6 Equivalence Concepts

Distinction maintained between:
- **Structural Equivalence**: Same units, same edges, same contracts (`G₁ ≡_structural G₂`)
- **Behavioral Equivalence**: Same execution output for all inputs (`G₁ ≡_behavioral G₂`)
- **Historical Equivalence**: Exact mutation provenance history

---

## 4. What This Freeze Establishes

- Formal definition of the mutation function `M: Gₜ → Gₜ₊₁` and system transition `Σ(t) → Σ(t+1)`
- Complete mutation taxonomy (Structural, Compositional, Lifecycle, Semantic)
- Primitive vs. Composite mutation separation
- Structural mutation boundary and pipeline routing
- The six-role lifecycle and non-collapse rule
- Proposal validity vs. mutation validation distinction
- Domain-specific effects on Computation, Execution, and Adaptation domains (including working memory cleanup)
- Identity, versioning, and provenance integrity requirements
- Cost semantics and impact on authorization/assessment
- Mutation algebra (composition, inverse, commutativity, idempotence)
- Equivalence definitions (structural, behavioral, historical)
- Failure semantics and error handling
- Conformance requirements across five nested levels

---

## 5. What This Freeze Does NOT Establish

- **Transaction semantics**: How mutations are applied atomically, how rollbacks work, or how concurrent mutations are resolved (delegated to Transaction Semantics)
- **Control layer mechanics**: How the loop runs in practice (delegated to Dynamic Computation Control Layer)
- **Implementation code**: Python classes or runtime execution details

---

## 6. Transition

Mutation Semantics is now frozen.

The next phase is **Transaction Semantics** — how mutations become atomic, how rollback works, how checkpoints coordinate with graph mutations, and how concurrent mutations are resolved.

```
DNC-IR (frozen)
    ↓
Mutation Semantics (frozen, this document)
    ↓
Transaction Semantics
    ↓
Dynamic Computation Control Layer
    ↓
Implementation
```
