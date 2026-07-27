# Mutation Semantics: Specification

**Date**: 2026-07-22  
**Status**: SPECIFICATION  
**Depends on**: DNC-IR Freeze, Foundational Baseline Freeze (Q1–Q5)  
**Depended on by**: Transaction Semantics, Dynamic Computation Control Layer

---

## 1. Purpose and Scope

### 1.1 What This Document Defines

**Given a valid DNC-IR computational structure and a proposed structural change, precisely what does it mean for that change to occur?**

Mutation Semantics defines the formal meaning of structural change in DNC. It specifies:

- What operations can modify computational structure
- What each operation does to Σ(t)
- What preconditions must hold before a mutation
- What postconditions must hold after a mutation
- What invariants are preserved
- How identity and provenance are tracked
- What algebraic properties mutations satisfy

### 1.2 What This Document Does NOT Define

| Mutation Semantics Defines | Transaction Semantics Defines |
|---------------------------|------------------------------|
| Semantic effect of each operation | How mutations become atomic |
| Preconditions and postconditions | Rollback mechanics |
| State transition semantics | Checkpoint coordination |
| Identity implications | Concurrent mutation resolution |
| Provenance requirements | Failure recovery |
| Cost implications | Transaction isolation |

### 1.3 Design Principles

1. **Semantic precision**: Every operation has exact preconditions, effects, and postconditions.
2. **Domain awareness**: Every operation specifies which Σ(t) domains it affects.
3. **Authority preservation**: Operations are vocabulary; mutations are proposed/authorized/applied.
4. **Algebraic rigor**: Mutations have formal properties (composition, equivalence, etc.).
5. **Boundary preservation**: Mutation Semantics defines structure change; Execution Core defines execution.

---

## 2. Formal Mutation Model

### 2.1 The Mutation Function

A mutation M transforms a valid computational structure:

```
M: Gₜ → Gₜ₊₁
```

Where:
- `Gₜ` = valid DNC-IR Structural Graph at time t
- `Gₜ₊₁` = valid DNC-IR Structural Graph at time t+1
- `M` = mutation operation

### 2.2 The System Transition

The actual system transition is broader than just the graph:

```
Σ(t) ──M──> Σ(t+1)
```

Because changing structure can affect:

- **Computation Domain**: graph structure changes
- **Execution Domain**: working_memory may grow/shrink, cost changes
- **Adaptation Domain**: mutation may be recorded in adaptation history

The mutation function M is defined on the graph; the system transition T is defined on Σ(t). M is a component of T.

### 2.3 Mutation as Σ(t) Transition

Formally:

```
T_M: Σ(t) → Σ(t+1)
```

Where:
- `Σ(t)` = complete system state
- `T_M` = transition induced by mutation M
- `Σ(t+1)` = resulting system state

Every mutation M has a corresponding system transition T_M that transforms the complete state.

---

## 3. Mutation Taxonomy

### 3.1 Structural Mutations

Operations that change the graph topology:

| Operation | Effect | Domain |
|-----------|--------|--------|
| `ADD` | Add a new ComputationalUnit | Computation |
| `REMOVE` | Remove a ComputationalUnit and its edges | Computation |
| `CONNECT` | Add an edge between units | Computation |
| `DISCONNECT` | Remove an edge | Computation |
| `REWIRE` | Change an edge's source or target | Computation |
| `REPLACE` | Replace a unit with a different unit | Computation |

**What counts as structural mutation**: A mutation is structural if it changes the set of ComputationalUnits or their connections in the graph. This includes adding/removing units, adding/removing/changing edges, composing/decomposing units, and replacing units.

**What does NOT count as structural mutation**:

| Change | Classification | Reason |
|--------|---------------|--------|
| Changing a unit's parameters | Parameter mutation | Internal unit state, not graph structure |
| Changing a unit's internal computation | Semantic mutation | Meaning change, not topology change |
| Changing routing decisions | Routing mutation | Execution-time decision, not structure |
| Changing cost budgets | Resource mutation | Resource allocation, not structure |

**Why the boundary matters**: Structural mutations go through the full six-role pipeline (Generator → Controller → Engine → Execution → Assessment → Learning). Other mutations use different pipelines:
```
Structural Mutation → Full authority pipeline
Parameter Mutation  → Execution Core pipeline (within unit)
Routing Mutation    → DecisionPolicy pipeline (within execution)
```

### 3.2 Composition Mutations

Operations that change the hierarchical structure:

| Operation | Effect | Domain |
|-----------|--------|--------|
| `COMPOSE` | Group units into a COMPOSITE | Computation |
| `DECOMPOSE` | Flatten a COMPOSITE into its internals | Computation |
| `EXTRACT` | Extract a subgraph into a separate unit | Computation |
| `INLINE` | Inline a unit's internals into the parent graph | Computation |

### 3.3 Lifecycle Mutations

Operations that change a unit's lifecycle state:

| Operation | Effect | Domain |
|-----------|--------|--------|
| `SPECIALIZE` | Change lifecycle from BASE to SPECIALIZED | Computation + Adaptation |
| `DEPRECATE` | Mark a unit as deprecated | Computation |
| `ARCHIVE` | Remove a unit from active use but preserve identity | Computation |

### 3.4 Semantic Mutations

Operations that change a unit's meaning without changing topology:

| Operation | Effect | Domain |
|-----------|--------|--------|
| `UPDATE_CONTRACT` | Change a unit's contract | Computation |
| `UPDATE_CAPABILITIES` | Change a unit's capabilities | Computation |
| `UPDATE_METADATA` | Change a unit's metadata | Computation |

### 3.5 Mutation Classification

```
Mutation
│
├── Structural
│       Changes graph topology
│       ADD, REMOVE, CONNECT, DISCONNECT, REWIRE, REPLACE
│
├── Compositional
│       Changes hierarchical structure
│       COMPOSE, DECOMPOSE, EXTRACT, INLINE
│
├── Lifecycle
│       Changes unit lifecycle state
│       SPECIALIZE, DEPRECATE, ARCHIVE
│
└── Semantic
        Changes unit meaning without topology change
        UPDATE_CONTRACT, UPDATE_CAPABILITIES, UPDATE_METADATA
```

---

## 4. Primitive vs. Composite Mutations

### 4.1 Primitive Mutations

Primitive mutations are atomic, irreducible operations. They cannot be decomposed into smaller mutations:

| Primitive | Definition |
|-----------|------------|
| `ADD_UNIT` | Create a new ComputationalUnit |
| `REMOVE_UNIT` | Destroy a ComputationalUnit |
| `ADD_EDGE` | Create a new Edge |
| `REMOVE_EDGE` | Destroy an Edge |
| `UPDATE_UNIT` | Modify a unit's properties |

### 4.2 Composite Mutations

Composite mutations are composed from primitives:

| Composite | Primitives |
|-----------|------------|
| `REPLACE` | REMOVE_UNIT + ADD_UNIT + rewire edges |
| `REWIRE` | REMOVE_EDGE + ADD_EDGE |
| `COMPOSE` | ADD_UNIT (COMPOSITE) + ADD edges + rewire internals |
| `DECOMPOSE` | REMOVE_UNIT (COMPOSITE) + ADD units + ADD edges |
| `EXTRACT` | ADD_UNIT + ADD edges + REMOVE edges from parent |
| `INLINE` | ADD units + ADD edges + REMOVE_UNIT |
| `SPECIALIZE` | UPDATE_UNIT (lifecycle) |

### 4.3 Why This Distinction Matters

- **Primitive mutations** are the最小 vocabulary. The Mutation Engine must support exactly these.
- **Composite mutations** are convenience operations. They can be decomposed for transaction mechanics.
- **Transaction Semantics** will define how composite mutations are applied atomically from primitives.

---

## 5. Mutation Lifecycle

### 5.1 The Six-Role Pipeline

Every structural mutation follows the full lifecycle:

```
Computational Generator
    │
    │ produces MutationProposal
    │ (reads knowledge from Adaptation Domain)
    ▼
Structural Controller
    │
    │ evaluates against:
    │   • MutationContract (capability)
    │   • Invariants (absolute)
    │   • Constraints (negotiable)
    │   • Policies (advisory)
    │
    │ produces AuthorizationDecision
    │ (APPROVE / REJECT / MODIFY)
    ▼
Mutation Engine
    │
    │ applies mutation transactionally
    │ (see Transaction Semantics)
    │
    │ produces Σ(t+1)
    ▼
Execution Core
    │
    │ executes the mutated graph
    │ (Observe → Decide → Act → Assess)
    │
    │ produces ExecutionOutcome
    ▼
Assessment
    │
    │ evaluates: did the mutation help?
    │
    │ produces AssessmentReport
    ▼
Learning System
    │
    │ updates knowledge in Adaptation Domain
    │ (does NOT produce proposals)
    ▼
Adaptation Domain
    (updated policies, optimizers, history)
```

### 5.2 No Role Collapse

The critical rule:

> **No role may silently collapse proposal, authorization, application, execution, assessment, or learning into one operation.**

Each role is distinct. The Generator cannot authorize. The Controller cannot apply. The Engine cannot assess. The Assessment cannot learn. The Learning System cannot propose.

---

## 6. Proposal Semantics

### 7.1 MutationProposal

A proposal is produced by the Computational Generator:

```
MutationProposal
│
├── proposal_id: ProposalID
│       Unique identifier for this proposal
│
├── operations: List[MutationOperation]
│       The proposed operations
│
├── rationale: str
│       Why this mutation is proposed
│
├── expected_outcome: ExpectedOutcome
│       Predicted effect on performance, cost, latency
│
├── priority: Priority
│       How urgent this mutation is
│
├── source: ProposalSource
│       Who/what generated this proposal
│       (rule-based, feedback-driven, learned, consolidation)
│
└── knowledge_snapshot: Optional[KnowledgeRef]
        Reference to the Adaptation Domain knowledge
        used to generate this proposal
```

### 6.2 Proposal Validity

A proposal is **valid** if:

1. All operations are well-formed (valid operation type, valid parameters)
2. All target units exist in the current graph
3. The proposal does not violate any invariant
4. The proposal satisfies all preconditions for each operation

A proposal may be **invalid** if it violates constraints or policies — these are caught during authorization, not proposal validity.

**Distinction from Mutation Validation (§8)**: Proposal validity checks the proposal as a whole (are all operations well-formed, do all targets exist). Mutation Validation checks each operation individually against the current state (are preconditions still met, do contracts allow it). Proposal validity is checked once at proposal time; mutation validation is checked again at application time (state may have changed).

---

## 7. Authorization Semantics

### 7.1 AuthorizationDecision

The Structural Controller produces:

```
AuthorizationDecision
│
├── decision: APPROVE | REJECT | MODIFY
│
├── modified_proposal: Optional[MutationProposal]
│       The controller's adjusted version (if MODIFY)
│
├── reasoning: str
│       Why this decision was made
│
├── checks_performed: List[AuthorizationCheck]
│       Which checks were evaluated
│
└── cost_analysis: Optional[CostAnalysis]
        Resource impact assessment
```

### 7.2 Authorization Checks

The Controller performs these checks in order:

| Check | Question | Result |
|-------|----------|--------|
| **Capability** | Does the unit's MutationContract allow this operation? | PASS/FAIL |
| **Invariant** | Will this operation preserve all invariants? | PASS/FAIL (absolute) |
| **Constraint** | Will this operation satisfy all constraints? | PASS/FAIL (may be relaxed) |
| **Policy** | Does this operation align with system policies? | PASS/WARN (advisory) |
| **Resource** | Does this operation fit within resource budgets? | PASS/FAIL |
| **Duplicativity** | Does this operation duplicate existing computation? | PASS/WARN |
| **Utility** | Is the expected improvement worth the cost? | PASS/WARN |

### 7.3 Authorization Outcomes

| Outcome | Meaning | Next Step |
|---------|---------|-----------|
| `APPROVE` | Mutation is authorized as proposed | Proceed to Engine |
| `REJECT` | Mutation is not authorized | Return to Generator |
| `MODIFY` | Mutation is authorized with changes | Modified proposal proceeds to Engine |

---

## 8. Mutation Validation

### 8.1 Validation Sequence

Every mutation is validated in this order:

```
1. Operation Validity
       Is this a valid operation with valid parameters?
       → If FAIL: reject (syntactic error)

2. Identity Validation
       Do all target units exist? Are IDs valid?
       → If FAIL: reject (invalid reference)

3. Contract Validation
       Do all unit contracts allow this operation?
       → If FAIL: reject (capability violation)

4. Invariant Validation
       Will this operation preserve all invariants?
       → If FAIL: reject (absolute violation)

5. Constraint Validation
       Will this operation satisfy all constraints?
       → If FAIL: Controller may reject or modify

6. Resource Validation
       Does this operation fit within resource budgets?
       → If FAIL: Controller may reject or modify

7. Authorization
       Has the Controller approved this mutation?
       → If REJECT: return to Generator
       → If MODIFY: apply modifications
```

### 8.2 Validation vs. Authorization

| Concept | When | What |
|---------|------|------|
| **Validation** | Before authorization | Technical correctness (invariants, constraints) |
| **Authorization** | After validation | Approval decision (capability, policy, utility) |

Validation is mechanical; authorization involves judgment.

---

## 9. Mutation Application

### 9.1 Application Semantics

When a mutation is authorized, the Mutation Engine applies it:

```
For each operation in the authorized proposal:
    1. Verify preconditions (one more time)
    2. Apply the operation to the graph
    3. Update identity records
    4. Update provenance
    5. Record in mutation history
    6. Increment graph version
```

### 9.2 Domain Effects

Each mutation affects specific domains:

| Mutation | Computation Domain | Execution Domain | Adaptation Domain |
|----------|-------------------|------------------|-------------------|
| `ADD` | `graph += unit` | `working_memory += entry (state: UNBOUND)` | — |
| `REMOVE` | `graph -= unit` | `working_memory -= entry (cleanup state & bindings)` | — |
| `CONNECT` | `graph += edge` | — | — |
| `DISCONNECT` | `graph -= edge` | — | — |
| `REWIRE` | `graph.edge changed` | — | — |
| `REPLACE` | `graph.unit replaced` | `working_memory updated (old removed, new added)` | — |
| `COMPOSE` | `graph += COMPOSITE` | `working_memory updated (sub-units nested, composite entry added)` | — |
| `DECOMPOSE` | `graph -= COMPOSITE, += units` | `working_memory updated (composite removed, sub-units unnested)` | — |
| `SPECIALIZE` | `lifecycle changed` | — | `memory += specialized unit reference` |

### 9.3 Postconditions

After a successful mutation:

1. The graph is valid (all invariants hold)
2. All contracts are satisfied
3. Identity records are updated
4. Provenance is recorded
5. Graph version is incremented
6. The system is in a consistent state

---

## 10. State Transition Semantics

### 10.1 The Transition Function

For each mutation M, the system transition is:

```
T_M(Σ(t)) = Σ(t+1)
```

Where Σ(t+1) differs from Σ(t) only in the domains affected by M.

### 10.2 Domain-Specific Transitions

```
Computation Domain:
    Gₜ₊₁ = M(Gₜ)

Execution Domain:
    WMₜ₊₁ = WMₜ ⊕ (Δ from M)
    Hₜ₊₁ = Hₜ ⊕ mutation_record
    Cₜ₊₁ = cost_of(M)

Adaptation Domain:
    AHₜ₊₁ = AHₜ ⊕ mutation_outcome (if recorded)
```

### 10.3 Invariant Preservation

Every valid mutation preserves all invariants:

```
∀M ∈ ValidMutations:
    Invariants(Σ(t)) ⟹ Invariants(T_M(Σ(t)))
```

If a mutation would violate an invariant, it is rejected before application.

---

## 11. Identity and Versioning

### 11.1 Mutation Identity

Every mutation has a durable identity:

```
MutationRecord
│
├── mutation_id: MutationID (globally unique, immutable)
│
├── graph_id: GraphID
│       Which graph this mutation affects
│
├── parent_version: GraphVersion
│       The version before this mutation
│
├── result_version: GraphVersion
│       The version after this mutation
│
├── operations: List[MutationOperation]
│       What operations were applied
│
├── author: RoleID
│       Who authorized this mutation
│
├── authority: AuthorizationDecision
│       The authorization record
│
├── timestamp: Timestamp
│       When the mutation was applied
│
├── reason: str
│       Why this mutation was made
│
├── cost: CostRecord
│       Resource cost of this mutation
│
└── provenance_hash: Hash
        Tamper-evident hash of the mutation record
```

### 11.2 Version Chain

Mutations form a chain:

```
Version 0 → M₁ → Version 1 → M₂ → Version 2 → ... → Mₙ → Version n
```

Every version is reachable from its predecessor via exactly one mutation.

### 11.3 Provenance Reconstruction

Given any mutation record, we can:

1. Determine what the graph looked like before the mutation
2. Determine what the mutation changed
3. Determine what the graph looks like after the mutation
4. Trace back to the original proposal and authorization

---

## 12. Provenance

### 12.1 Provenance Requirements

Every mutation must record:

| Field | Description |
|-------|-------------|
| MutationID | Unique identity |
| GraphID | Which graph |
| ParentVersion | Before state |
| ResultVersion | After state |
| Operations | What changed |
| Author | Who authorized |
| Timestamp | When applied |
| Reason | Why made |
| Cost | Resource cost |
| ProvenanceHash | Tamper-evident |

### 12.2 Provenance Integrity

The provenance hash is computed over:

```
hash(MutationID, GraphID, ParentVersion, Operations, Timestamp)
```

This ensures:
- No mutation record can be altered without detection
- The mutation history is tamper-evident
- Replay can verify provenance integrity

---

## 13. Cost Semantics

### 13.1 Mutation Cost

Every mutation has a computational cost:

```
MutationCost
│
├── structural_cost: Cost
│       Cost of modifying the graph structure
│
├── validation_cost: Cost
│       Cost of validating the mutation
│
├── provenance_cost: Cost
│       Cost of recording provenance
│
└── total_cost: Cost
        Sum of all costs
```

### 13.2 Cost and Authorization

The Controller considers cost during authorization:

- Does the mutation fit within the resource budget?
- Is the expected improvement worth the cost?
- Are there cheaper alternatives?

### 13.3 Cost and Assessment

Assessment compares:
- Actual cost vs. estimated cost
- Actual improvement vs. expected improvement
- Cost-effectiveness ratio

---

## 14. Mutation Algebra

### 14.1 Composition

Mutations can be composed:

```
(M₂ ∘ M₁)(G) = M₂(M₁(G))
```

Composition is associative:

```
M₃ ∘ (M₂ ∘ M₁) = (M₃ ∘ M₂) ∘ M₁
```

But not necessarily commutative:

```
M₂ ∘ M₁ ≠ M₁ ∘ M₂ (in general)
```

### 14.2 Inverse

Some mutations have inverses:

```
M⁻¹(M(G)) = G
```

| Mutation | Inverse | Condition |
|----------|---------|-----------|
| `ADD(unit)` | `REMOVE(unit)` | Always |
| `REMOVE(unit)` | `ADD(unit)` | If unit definition is preserved in registry |
| `CONNECT(a, b)` | `DISCONNECT(a, b)` | Always |
| `DISCONNECT(a, b)` | `CONNECT(a, b)` | Always |
| `REWIRE(edge, new)` | `REWIRE(edge, old)` | Always |
| `COMPOSE(units)` | `DECOMPOSE(composite)` | Always |
| `DECOMPOSE(composite)` | `COMPOSE(units)` | Only if the original internal structure was preserved during decomposition |
| `EXTRACT(subgraph)` | `INLINE(unit)` | Always |
| `INLINE(unit)` | `EXTRACT(subgraph)` | Only if extraction boundaries were preserved |

Not all mutations have inverses:
- `SPECIALIZE` has no inverse (lifecycle cannot be undone)
- `DEPRECATE` has no inverse (deprecation is permanent)
- `ARCHIVE` has no inverse (archived units are removed from active use)
- `UPDATE_*` (contracts, capabilities, metadata) have no automatic inverse (state changes are non-reversible without explicit history)

### 14.3 Commutativity

Two mutations are **compatible** (commutative) if:

```
M₁ ∘ M₂ = M₂ ∘ M₁
```

Mutations are compatible if they operate on disjoint parts of the graph:

```
DISCONNECT(a, b) ∘ ADD(c) = ADD(c) ∘ DISCONNECT(a, b)
    (different targets; compatible)
```

Mutations are incompatible if they operate on overlapping parts:

```
REMOVE(a) ∘ CONNECT(a, b) ≠ CONNECT(a, b) ∘ REMOVE(a)
    (same target; incompatible)
```

### 14.4 Idempotence

A mutation is **idempotent** if:

```
M ∘ M = M
```

Examples:
- ADD(unit) is NOT idempotent (adding twice creates duplicates)
- CONNECT(a, b) IS idempotent if the edge already exists (no duplicate edges)
- SPECIALIZE is idempotent (already SPECIALIZED stays SPECIALIZED)

### 14.5 Algebraic Properties Summary

| Property | Definition | Importance |
|----------|------------|------------|
| Composition | M₂ ∘ M₁ | Mutation batching, sequences |
| Associativity | (M₃ ∘ M₂) ∘ M₁ = M₃ ∘ (M₂ ∘ M₁) | Grouping doesn't matter |
| Commutativity | M₁ ∘ M₂ = M₂ ∘ M₁ | Parallel execution, optimization |
| Inverse | M⁻¹(M(G)) = G | Rollback, undo |
| Idempotence | M ∘ M = M | Retries, deduplication |

---

## 15. Equivalence

### 15.1 Structural Equivalence

Two graphs are **structurally equivalent** if they represent the same computational structure:

```
G₁ ≡_structural G₂
```

Meaning: same units, same edges, same contracts (ignoring identity and metadata).

### 15.2 Mutation Sequence Equivalence

Two mutation sequences are **structurally equivalent** if they produce structurally equivalent graphs:

```
[M₁, M₂, M₃] ≡_structural [M₄, M₅]
    if M₃ ∘ M₂ ∘ M₁ and M₅ ∘ M₄ produce structurally equivalent graphs
```

### 15.3 Behavioral Equivalence

Two graphs are **behaviorally equivalent** if they produce the same execution behavior:

```
G₁ ≡_behavioral G₂
    if executing G₁ and G₂ produces identical outputs for all inputs
```

### 15.4 Why Equivalence Matters

| Equivalence | Use Case |
|-------------|----------|
| Structural | Consolidation (same pattern, different history) |
| Behavioral | Optimization (different structure, same behavior) |
| Historical | Provenance (exact mutation history) |

These should not be conflated. Structural equivalence does not imply behavioral equivalence (different structures may behave differently). Behavioral equivalence does not imply structural equivalence (different structures may behave the same).

---

## 16. Failure Semantics

### 16.1 Mutation Failure

A mutation can fail at several points:

| Failure Point | Cause | Response |
|---------------|-------|----------|
| Proposal validity | Malformed proposal | Return to Generator |
| Identity validation | Invalid unit reference | Return to Generator |
| Contract validation | Capability violation | Return to Generator |
| Invariant validation | Absolute violation | Reject; system error |
| Constraint validation | Constraint violation | Controller rejects or modifies |
| Resource validation | Budget exceeded | Controller rejects or modifies |
| Authorization | Controller rejects | Return to Generator |
| Application | Engine cannot apply | Rollback (Transaction Semantics) |

### 16.2 Failure Recording

Every failure is recorded:

```
MutationFailure
│
├── failure_id: FailureID
├── mutation_id: Optional[MutationID]
├── failure_point: str
├── reason: str
├── timestamp: Timestamp
└── provenance_hash: Hash
```

### 16.3 Failure and Learning

Failures are fed to the Learning System via Assessment. The Learning System uses failure information to improve future proposals.

---

## 17. Conformance

### 17.1 Conformance Requirements

A conformant mutation semantics implementation must:

1. Support all primitive mutations (ADD_UNIT, REMOVE_UNIT, ADD_EDGE, REMOVE_EDGE, UPDATE_UNIT)
2. Validate all preconditions before applying mutations
3. Preserve all invariants across mutations
4. Record provenance for every mutation
5. Increment graph version for every mutation
6. Support the full authorization pipeline

### 17.2 Conformance Levels

| Level | Requirements |
|-------|-------------|
| **Level 1: Primitive** | Support primitive mutations with validation |
| **Level 2: Composite** | Support composite mutations decomposed to primitives |
| **Level 3: Algebraic** | Support composition, inverse, and commutativity checks |
| **Level 4: Equivalence** | Support structural and behavioral equivalence checking |
| **Level 5: Full** | All above plus provenance integrity and cost tracking |

---

## 18. Relationship to Transaction Semantics

### 18.1 What Mutation Semantics Defines

- Semantic effect of each operation
- Preconditions and postconditions
- Identity and provenance requirements
- Algebraic properties
- Equivalence concepts

### 18.2 What Transaction Semantics Defines

- How mutations are applied atomically
- How composite mutations are decomposed to primitives
- How rollback works
- How concurrent mutations are resolved
- How checkpoint coordination works

### 18.3 The Boundary

```
Mutation Semantics:    WHAT changes
Transaction Semantics: HOW changes become atomic
```

Mutation Semantics defines the meaning; Transaction Semantics defines the mechanics.

---

## 19. Examples

### 19.1 Adding a Unit

```
Before: Gₜ = {units: {A, B}, edges: {A→B}}
Mutation: ADD(unit C, connect A→C)
After: Gₜ₊₁ = {units: {A, B, C}, edges: {A→B, A→C}}

System transition:
    Computation Domain: graph updated
    Execution Domain: working_memory[C] = UNBOUND
    Provenance: MutationRecord created
```

### 19.2 Composing Units

```
Before: Gₜ = {units: {A, B, C}, edges: {A→B, B→C}}
Mutation: COMPOSE({B, C}, name="pipeline")
After: Gₜ₊₁ = {units: {A, pipeline}, edges: {A→pipeline}}
       pipeline = {internal: {B, C}, internal_edges: {B→C}}

System transition:
    Computation Domain: graph restructured
    Execution Domain: working_memory updated
    Provenance: MutationRecord created
```

### 19.3 Specializing a Unit

```
Before: Gₜ = {units: {A}, A.lifecycle = BASE}
Mutation: SPECIALIZE(A, params={task: "classification"})
After: Gₜ₊₁ = {units: {A'}, A'.lifecycle = SPECIALIZED}
       A' = Specialized version of A

System transition:
    Computation Domain: lifecycle changed
    Adaptation Domain: memory += specialized unit
    Provenance: MutationRecord created
```

---

## 20. Summary

| Property | Value |
|----------|-------|
| Central question | What does it mean for a structural change to occur? |
| Mutation model | M: Gₜ → Gₜ₊₁; system transition: Σ(t) → Σ(t+1) |
| Mutation vocabulary | Structural, Compositional, Lifecycle, Semantic |
| Primitive mutations | ADD_UNIT, REMOVE_UNIT, ADD_EDGE, REMOVE_EDGE, UPDATE_UNIT |
| Authority preservation | Full six-role pipeline; no role collapse |
| Validation sequence | Operation → Identity → Contract → Invariant → Constraint → Resource → Authorization |
| Algebraic properties | Composition, Inverse, Commutativity, Idempotence |
| Equivalence | Structural, Behavioral, Historical |
| Boundary | WHAT changes (Mutation Semantics) vs. HOW changes become atomic (Transaction Semantics) |
