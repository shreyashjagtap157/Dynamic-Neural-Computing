# DNC v2.x Foundational Baseline — Freeze

**Date**: 2026-07-22  
**Status**: FROZEN — foundational theory layer  
**Scope**: What DNC v2.x *is*; the axioms from which all downstream specifications derive

---

## 1. What This Document Is

This document formally freezes the DNC v2.x foundational theory layer. The five foundational questions (Q1–Q5) have been answered, reviewed for consistency, and corrected. The answers now form the **axioms** of the entire v2.x architecture.

From this point forward, the architecture becomes increasingly concrete and increasingly difficult to change. The research layer remains free to experiment within these boundaries.

---

## 2. Review Summary

### 2.1 Consistency Matrix (Post-Correction)

| Check | Status | Resolution |
|-------|--------|------------|
| Q1 ↔ Q2 consistent? | PASS | — |
| Q1 ↔ Q3 consistent? | PASS | — |
| Q1 ↔ Q4 consistent? | PASS | — |
| Q1 ↔ Q5 consistent? | PASS | — |
| Q2 ↔ Q3 consistent? | PASS | Unit parameters in Computation Domain; learning state in Adaptation Domain |
| Q2 ↔ Q4 consistent? | PASS | Orthogonal dimensions (structure/visibility/lifecycle) replace flat type hierarchy |
| Q2 ↔ Q5 consistent? | PASS | — |
| Q3 ↔ Q4 consistent? | PASS | Learning System feeds knowledge to Generator; no bypass |
| Q3 ↔ Q5 consistent? | PASS | — |
| Q4 ↔ Q5 consistent? | PASS | Learning dimensions are independent; capability levels are architectural |
| All state transitions representable? | PASS | Every operation maps to domain transitions in Σ(t) |
| Authority boundaries complete? | PASS | Learning → Generator → Controller → Engine; no bypass |
| Capability vs. architecture separation? | PASS | Architecture = interfaces; Capability = algorithms |
| Hypothesis vs. specification separation? | PASS | Hypotheses are research predictions, not architectural facts |

### 2.2 Issues Found and Resolved

| Issue | Documents | Resolution |
|-------|-----------|------------|
| Unit parameters vs. learning state ambiguity | Q3, Q2 | Unit parameters live inside ComputationalUnits in Computation Domain; Adaptation Domain contains learning state (policies, optimizers, history) |
| ComputationalUnit type hierarchy conflated dimensions | Q2 | Replaced flat hierarchy with three orthogonal dimensions: structure (PRIMITIVE/COMPOSITE), visibility (OPAQUE/INSPECTABLE), lifecycle (BASE/SPECIALIZED) |
| Learning System could bypass Generator | Q4 | Removed `propose()` from Learning System interface; learning feeds knowledge to Adaptation Domain; Generator reads knowledge from Adaptation Domain |
| Learning levels conflated with dimensions | Q5 | Distinguished capability levels (DNC-3 through DNC-6) from learning dimensions (Parameters, Routing, Structure, Composition, Consolidation); dimensions are independent |

---

## 3. The Axioms

The following decisions are now **axiomatic**. They are not proposals; they are the foundation.

### Axiom 1: DNC Is Defined by Dynamic Structural Mutation

DNC is a computational architecture in which the system can modify its own computational structure during execution, subject to explicit constraints.

- Minimum DNC capability: DNC-3 (rule-based structural mutations)
- Learning is optional: DNC-3 works without learning
- Architecture ≠ capability level: architecture defines interfaces; capability level defines algorithms

### Axiom 2: ComputationalUnit Has Three Orthogonal Dimensions

Every computational unit is defined by its position in three independent dimensions:

- **Structure**: PRIMITIVE (atomic) | COMPOSITE (has parts)
- **Visibility**: OPAQUE (hidden) | INSPECTABLE (visible)
- **Lifecycle**: BASE (normal) | SPECIALIZED (consolidated)

Common combinations produce derived roles (Primitive, Module, Composite, Subgraph, Specialized), but these are shortcuts, not fundamental types.

### Axiom 3: System State Is Unified with Logical Domains

Σ(t) is a single unified state object with three logical domains:

- **Execution Domain**: working_memory, history, checkpoints, cost
- **Computation Domain**: graph (of ComputationalUnits), registry
- **Adaptation Domain**: learning_state (policies, optimizers), memory (consolidated units), history (adaptation outcomes)

Unit parameters live inside ComputationalUnits in the Computation Domain. The Adaptation Domain contains learning *state*, not unit parameters.

### Axiom 4: Transitions Are Atomic Transformations of Σ(t)

Every system transition transforms the entire Σ(t) atomically:

```
Σ(t+1) = T(Σ(t), O(t), D(t), A(t))
```

There are no partial transitions. There are no domain-independent transitions. Checkpoint captures full Σ(t); rollback restores full Σ(t).

### Axiom 5: Proposal ≠ Authorization ≠ Application ≠ Execution

Six distinct roles, no bypass:

1. **Computational Generator** → proposes mutations (reads knowledge from Adaptation Domain)
2. **Structural Controller** → authorizes/rejects/modifies proposals
3. **Mutation Engine** → applies mutations transactionally
4. **Execution Core** → executes the mutated graph
5. **Assessment** → evaluates outcomes
6. **Learning System** → updates knowledge in Adaptation Domain (does NOT produce proposals)

The feedback loop: Learning → Adaptation Domain → Generator → Controller → Engine → Σ(t+1) → Execution → Assessment → Learning.

### Axiom 6: Learning Dimensions Are Independent

Five learning dimensions, not a hierarchy:

- **Parameters**: How should this computation behave?
- **Routing**: Which computation should execute next?
- **Structure**: What computation should exist?
- **Composition**: Which computations should be combined?
- **Consolidation**: Should this recurring structure become reusable?

A system can learn in any dimension without requiring the others. Capability levels (DNC-3 through DNC-6) determine which dimensions are architecturally available; implementations choose which to activate.

### Axiom 7: Research Hypotheses Are Not Architectural Facts

The four research hypotheses (structural learning works, consolidation produces reusable units, composition scales, DNC outperforms fixed architecture) are predictions to be tested, not axioms to be preserved. The architecture remains valid even if a hypothesis is disproven.

---

## 4. Document Inventory

| Document | Content | Status |
|----------|---------|--------|
| `EXECUTION-CORE-v1.x-FREEZE.md` | Frozen Execution Core boundary, 10 architectural invariants, source file inventory | FROZEN |
| `Q1-what-is-dnc.md` | DNC definition, maturity levels DNC-0 through DNC-6, architecture vs. capability | FROZEN |
| `Q2-computational-substrate.md` | ComputationalUnit orthogonal dimensions, Graph structure, composition model | FROZEN |
| `Q3-state-model.md` | Unified Σ(t) with three logical domains, transition function, checkpoint model | FROZEN |
| `Q4-mutation-authority.md` | Six roles, mutation pipeline, safety properties, interfaces | FROZEN |
| `Q5-learning-model.md` | Five learning dimensions, capability levels, research hypotheses | FROZEN |

---

## 5. What This Freeze Establishes

- The definition of DNC (Q1)
- The computational substrate (Q2)
- The state model (Q3)
- The mutation authority model (Q4)
- The learning model (Q5)
- The Execution Core boundary (Freeze document)
- The architectural invariants (10 invariants)
- The safety properties (no unauthorized, partial, silent, unchecked, or unobserved mutations)

---

## 6. What This Freeze Does NOT Establish

- DNC-IR (intermediate representation)
- Mutation semantics (how mutations transform Σ)
- Transaction semantics (how mutations are atomic)
- The Dynamic Computation Control Layer (the v2.x layer above the Execution Core)
- Implementation details
- Algorithm choices for any capability level

These are derived from the axioms and specified in downstream documents.

---

## 7. Transition

The foundational theory layer is now frozen.

The next phase is **DNC-IR** — the intermediate representation that encodes the computational substrate, mutations, and graph structure into a formal syntactic representation.

From DNC-IR, we derive:

```
DNC-IR
    ↓
Mutation Semantics
    ↓
Transaction Semantics
    ↓
Dynamic Computation Control Layer
    ↓
Implementation
```

The chain is:

**Codebase Audit → Execution Core Freeze → Foundational Theory → Consistency Review → Foundational Baseline Freeze (this document) → DNC-IR → ...**

From here onward, the architecture becomes increasingly concrete. The foundational axioms are set.
