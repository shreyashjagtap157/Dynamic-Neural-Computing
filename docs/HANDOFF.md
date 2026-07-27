# DNC v2.x — Agent Handoff

**Date**: 2026-07-22  
**Status**: Live  
**Purpose**: Enable any agent to resume work without re-reading the full conversation history

---

## 1. What Is DNC?

DNC (Dynamic Neural Computation) is a computation orchestration engine that can **modify its own computational structure at runtime**. It evolved from a dynamic execution runtime (v1.x) into a specification-driven architecture (v2.x) that distinguishes what a system *is* from what a system *does*.

- **Execution Core v1.x** (frozen): executes a fixed DAG of computational units — Observe, Decide, Act, Assess
- **Dynamic Computation Control Layer v2.x** (being specified): proposes, authorizes, and applies structural mutations to the graph during execution

**Core research question**: *Can a system learn what computation to build, rather than being told what computation to perform?*

**Maturity levels**: DNC-0 (static) → DNC-1 (dynamic execution) → DNC-2 (dynamic routing) → DNC-3 (dynamic structural mutation, minimum DNC) → DNC-4 (structural adaptation) → DNC-5 (structural learning) → DNC-6 (consolidation + reuse)

---

## 2. Development Path (Theory-First)

```
CODEBASE AUDIT (complete)
    ↓
EXECUTION CORE FREEZE (complete — specs/EXECUTION-CORE-v1.x-FREEZE.md)
    ↓
FOUNDATIONAL THEORY — Q1–Q5 answered, reviewed, cross-checked
    ↓
FOUNDATIONAL BASELINE FREEZE (complete — specs/FOUNDATIONAL-BASELINE-FREEZE.md)
    ↓
DNC-IR SPECIFICATION + FREEZE (complete — specs/dnc-ir.md, specs/DNC-IR-FREEZE.md)
    ↓
MUTATION SEMANTICS + FREEZE (complete — specs/mutation-semantics.md, specs/MUTATION-SEMANTICS-FREEZE.md)
    ↓
TRANSACTION SEMANTICS + FREEZE (complete — specs/transaction-semantics.md, specs/TRANSACTION-SEMANTICS-FREEZE.md)
    ↓
DYNAMIC COMPUTATION CONTROL LAYER + FREEZE (complete — specs/dynamic-computation-control-layer.md, specs/DCCL-FREEZE.md)
    ↓
THEORETICAL ARCHITECTURE REVIEW (complete — specs/DNC-V2-ARCHITECTURE-COMPLETENESS-REVIEW.md)
    ↓
ARCHITECTURE FREEZE (complete — specs/DNC-V2-ARCHITECTURE-FREEZE.md)
    ↓
IMPLEMENTATION  ← YOU ARE HERE
```

---

## 3. What Has Been Completed

### 3.1 Foundational Theory (Q1–Q5)

Five foundational questions answered and cross-reviewed for consistency (14/14 checks PASS):

| Doc | Question | Key Answer |
|-----|----------|------------|
| `specs/Q1-what-is-dnc.md` | What is DNC? | Defined by dynamic structural mutation; min level DNC-3; architecture ≠ capability |
| `specs/Q2-computational-substrate.md` | What is the computational substrate? | ComputationalUnit with 3 orthogonal dimensions: structure, visibility, lifecycle |
| `specs/Q3-state-model.md` | What is system state? | Unified Σ(t) with 3 logical domains: Execution, Computation, Adaptation |
| `specs/Q4-mutation-authority.md` | Who can mutate computation? | 6 roles: Generator → Controller → Engine → Execution → Assessment → Learning |
| `specs/Q5-learning-model.md` | What does DNC learn? | 5 independent dimensions (Parameters, Routing, Structure, Composition, Consolidation) |

### 3.2 Seven Axioms (Frozen)

The answers to Q1–Q5 produced 7 axioms (`specs/FOUNDATIONAL-BASELINE-FREEZE.md`):

1. **Axiom 1**: DNC is defined by dynamic structural mutation (min DNC-3)
2. **Axiom 2**: ComputationalUnit has 3 orthogonal dimensions (structure, visibility, lifecycle)
3. **Axiom 3**: System state is unified Σ(t) with 3 logical domains
4. **Axiom 4**: Transitions are atomic transformations of Σ(t)
5. **Axiom 5**: Proposal ≠ Authorization ≠ Application ≠ Execution (6 roles, no bypass)
6. **Axiom 6**: Learning dimensions are independent; DNC levels are architectural
7. **Axiom 7**: Research hypotheses are not architectural facts

### 3.3 DNC-IR Specification (Frozen)

`specs/dnc-ir.md` — 18 sections, 22/22 traceability checks PASS.

Key frozen decisions:
- DNC-IR is the **structural component** of the Computation Domain (not the entire domain)
- **Structural Graph** (expressive, may be non-DAG) → **Executable Graph** (DAG projection) for execution
- Σ(t) contains the Structural Graph; Execution Core projects to Executable DAG
- Stable, immutable, mutation-tracked identity for all elements
- **MutationContract** as capability model (distinct from authorization, policy, constraint)
- **Three-tier enforcement**: Invariant (absolute) ≠ Constraint (negotiable) ≠ Policy (advisory)
- Operations vocabulary is abstract; mutations are proposed/authorized/applied separately
- Five nested conformance levels (Structural → Semantic → Identity → Mutation → Full)
- Conformance Level 4 implies Execution Core invariants (INV-1–9)

### 3.4 Mutation Semantics (Frozen)

`specs/mutation-semantics.md` — 20 sections, 13/13 traceability PASS, 7/7 axiom consistency PASS.

Key frozen decisions:
- **Mutation model**: M: Gₜ → Gₜ₊₁; system transition: Σ(t) → Σ(t+1)
- **Mutation taxonomy**: Structural (ADD, REMOVE, CONNECT, DISCONNECT, REWIRE, REPLACE), Compositional (COMPOSE, DECOMPOSE, EXTRACT, INLINE), Lifecycle (SPECIALIZE, DEPRECATE, ARCHIVE), Semantic (UPDATE_*)
- **Structural boundary**: Only structural mutations go through the full 6-role pipeline
- **Validation sequence**: Operation → Identity → Contract → Invariant → Constraint → Resource → Authorization
- **Mutation algebra**: Composition, Inverse, Commutativity (disjoint ops), Idempotence
- **Equivalence**: Structural (same graph), Behavioral (same output), Historical (same provenance)
- **Boundary**: WHAT changes (Mutation Semantics) vs. HOW changes become atomic (Transaction Semantics)

### 3.5 Execution Core v1.x (Frozen)

`specs/EXECUTION-CORE-v1.x-FREEZE.md` — 10 architectural invariants, source file inventory.

Source file classification (41 files across 14 packages):

| Category | Files | Action |
|----------|-------|--------|
| **KEEP** (frozen infrastructure) | runtime.py, types.py, execution_state.py, working_memory.py, checkpoint.py, registry.py, scheduler.py, semantics.py, runtime_invariants.py, verifier.py, execution_provider.py, execution_trace.py, replay_engine.py, decision_policy.py, llm_policy.py, provenance.py, failure.py, base.py, standard.py, protocol.py, providers/*.py | Keep as-is |
| **EXTEND** (v1.x interface, v2.x implementation) | execution_state.py, working_memory.py, runtime.py, scheduler.py, decision_policy.py, execution_trace.py, replay_engine.py, semantics.py, provenance.py, failure.py, base.py | Add v2.x capabilities |
| **MOVE TO RESEARCH LAYER** | planner/pipeline.py, planner/dag_planner.py, learning/continual.py, evaluation/computation_aware.py, observability/evaluation.py, observability/bias_evaluation.py | Move to research |
| **DEPRECATE/REPLACE** | planner/graph_builder.py, planner/dag_builder.py, planner/module_selector.py, planner/task_analyzer.py, planner/graph_validator.py, planner/replan_context.py | Replace with DNC-IR Generator |

---

## 4. What To Do Next

### 4.1 Immediate: Transaction Semantics

Write `specs/transaction-semantics.md` — how mutations become atomic.

**Core question**: Given a valid mutation M authorized by the Controller, how does the Mutation Engine apply it to Σ(t) such that:
- The transition is atomic (no partial application)
- Rollback is possible on failure
- Checkpoints capture pre- and post-mutation state
- Concurrent mutations are resolved deterministically

**Key sections to write**:
1. Atomicity model (unit of mutation)
2. Transaction lifecycle (begin → validate → apply → commit/rollback)
3. Checkpoint integration (checkpoint before mutation, restore on failure)
4. Composite mutation decomposition (REPLACE = REMOVE + ADD + rewire → primitives)
5. Rollback mechanics (inverse mutations, state restoration)
6. Concurrent mutation resolution (ordering, conflict detection)
7. Failure recovery (partial failure, compensation)
8. Conformance requirements

**Critical constraint from Mutation Semantics §18**: Mutation Semantics defines WHAT changes; Transaction Semantics defines HOW changes become atomic. Do not redefine mutation effects here.

### 4.2 After Transaction Semantics: Dynamic Computation Control Layer

The full control layer specification — the loop that connects Generator, Controller, Engine, Execution, Assessment, and Learning into a running system.

### 4.3 After Control Layer: Implementation

Extend the frozen v1.x codebase to implement v2.x capabilities.

---

## 5. Seven Foundational Axioms (Quick Reference)

| # | Axiom | Implication |
|---|-------|-------------|
| 1 | DNC defined by dynamic structural mutation | Min DNC-3; architecture ≠ capability |
| 2 | ComputationalUnit: 3 orthogonal dimensions | structure (PRIMITIVE/COMPOSITE), visibility (OPAQUE/INSPECTABLE), lifecycle (BASE/SPECIALIZED) |
| 3 | Unified Σ(t) with 3 logical domains | Execution (WM, H, C), Computation (G, R), Adaptation (policies, memory, history) |
| 4 | Atomic transitions of Σ(t) | Σ(t+1) = T(Σ(t), O(t), D(t), A(t)); no partial transitions |
| 5 | 6 roles, no bypass | Generator → Controller → Engine → Execution → Assessment → Learning |
| 6 | Learning dimensions independent | Parameters, Routing, Structure, Composition, Consolidation; DNC-3–6 are levels, not dimensions |
| 7 | Hypotheses ≠ facts | Architecture valid even if research predictions fail |

---

## 6. Key Design Decisions (Frozen)

| Decision | Value | Document |
|----------|-------|----------|
| DNC-IR scope | Structural component of Computation Domain only | DNC-IR §1 |
| Graph model | Structural Graph (non-DAG allowed) → Executable DAG projection | DNC-IR §3.2 |
| Unit identity | Stable, immutable, mutation-tracked; UnitIDs retired never reused | DNC-IR §6 |
| Capability model | MutationContract (what is technically permitted) | DNC-IR §8 |
| Enforcement tiers | Invariant (absolute) ≠ Constraint (negotiable) ≠ Policy (advisory) | DNC-IR §11 |
| Operations vocabulary | Abstract; mutations are proposed/authorized/applied separately | DNC-IR §12 |
| Mutation boundary | Structural mutations → full 6-role pipeline; others → lighter pipelines | Mutation Semantics §3.1 |
| Conformance levels | 5 nested levels (Structural → Full); Level 4 implies INV-1–9 | DNC-IR §17, Mutation Semantics §17 |
| Research vs. architecture | 4 hypotheses are predictions, not architectural facts | Q5, Axiom 7 |

---

## 7. Specification Document Inventory

| Document | Status | Location |
|----------|--------|----------|
| Execution Core v1.x Freeze | FROZEN | `specs/EXECUTION-CORE-v1.x-FREEZE.md` |
| Q1: What is DNC? | FROZEN | `specs/Q1-what-is-dnc.md` |
| Q2: Computational Substrate | FROZEN | `specs/Q2-computational-substrate.md` |
| Q3: State Model | FROZEN | `specs/Q3-state-model.md` |
| Q4: Mutation Authority | FROZEN | `specs/Q4-mutation-authority.md` |
| Q5: Learning Model | FROZEN | `specs/Q5-learning-model.md` |
| Foundational Baseline Freeze | FROZEN | `specs/FOUNDATIONAL-BASELINE-FREEZE.md` |
| DNC-IR Specification | FROZEN | `specs/dnc-ir.md` |
| DNC-IR Freeze | FROZEN | `specs/DNC-IR-FREEZE.md` |
| Mutation Semantics | FROZEN | `specs/mutation-semantics.md` |
| Mutation Semantics Review | COMPLETE | `specs/MUTATION-SEMANTICS-REVIEW.md` |
| Mutation Semantics Freeze | FROZEN | `specs/MUTATION-SEMANTICS-FREEZE.md` |
| Transaction Semantics | FROZEN | `specs/transaction-semantics.md` |
| Transaction Semantics Review | COMPLETE | `specs/TRANSACTION-SEMANTICS-REVIEW.md` |
| Transaction Semantics Freeze | FROZEN | `specs/TRANSACTION-SEMANTICS-FREEZE.md` |
| Dynamic Computation Control Layer | FROZEN | `specs/dynamic-computation-control-layer.md` |
| DCCL Review | COMPLETE | `specs/DCCL-REVIEW.md` |
| DCCL Freeze | FROZEN | `specs/DCCL-FREEZE.md` |
| Architecture Completeness Review | APPROVED | `specs/DNC-V2-ARCHITECTURE-COMPLETENESS-REVIEW.md` |
| Architecture Freeze | FROZEN | `specs/DNC-V2-ARCHITECTURE-FREEZE.md` |

---

## 8. Codebase Health

| Metric | Value |
|--------|-------|
| Tests passing | 298/298 (159 unit + 139 conformance) |
| Invariant coverage | 46/46 (100%) |
| Source files | 41 files across 14 packages (~8,000 LOC) |
| Architecture conformance | PASS (4/4 ACDs resolved) |
| Conformance report | `docs/conformance-report.md` |
| Registry | `docs/registry.md` (Baseline v1.1, 18 spec documents) |

---

## 9. How to Resume Work

1. Read this document (you're here)
2. Read `specs/DNC-V2-ARCHITECTURE-FREEZE.md` for the complete DNC v2.x baseline
3. **Phase 1 (DNC-IR Reference Implementation & Validator)**: COMPLETE (`src/dnc/ir/`)
4. **Phase 2A (Structural Graph → Executable DAG Projection)**: COMPLETE (`src/dnc/projection/`)
5. **Phase 2B (Mutation Engine & Rollback Compensation)**: COMPLETE (`src/dnc/mutation/`)
6. **Phase 3 (Transaction Manager Integration & OCC)**: COMPLETE (`src/dnc/transaction/`)
7. **Phase 4 (Structural Versioning + Provenance Integration)**: COMPLETE (`src/dnc/observability/provenance.py` extensions)
8. **Next**: Phase 5 — Structural Replay + Structural Rollback Verification (proving that structural history can deterministically reconstruct and recover canonical states via `Replay(G₀, T₁...Tₙ) = Gₙ`)

**Pattern for every new spec document**:
1. Write the specification answering the core question
2. Build a traceability matrix (concept → axiom/Q → status)
3. Check axiom consistency (7/7 must PASS)
4. Check DNC-IR consistency (all frozen concepts referenced correctly)
5. Identify and resolve issues
6. Produce freeze document
