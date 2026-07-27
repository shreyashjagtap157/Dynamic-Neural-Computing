# Q3: Is the Dynamic Graph Part of State?

**Date**: 2026-07-22  
**Status**: THEORETICAL DEFINITION  
**Depends on**: Q1 (What Is DNC?), Q2 (Computational Substrate)  
**Depended on by**: Q4 (Mutation Authority), Q5 (Learning Model), DNC-IR

---

## 1. The Question

How should DNC system state be organized?

The current system has ES(t) = (W, M, G, C, H, R). DNC v2.x adds structural mutation, learning, and memory. The question is whether these are:

- Fields appended to the existing tuple
- Separate state objects managed independently
- Logical domains within a unified state transition system

The wrong answer here becomes permanent ontology. We must get this right.

---

## 2. The Core Principle

> **A DNC system transition is a transformation from one complete system state to another complete system state.**

Formally:

```
Σ(t+1) = T(Σ(t), O(t), D(t), A(t))
```

Where:
- `Σ(t)` = complete system state at time t
- `O(t)` = observations at time t
- `D(t)` = decisions at time t
- `A(t)` = actions at time t
- `T` = transition function

The transition function T transforms the *entire* system state. There is no partial state transition. There is no domain-independent transition. Every transition affects the complete state, even if only one domain changes.

This principle determines the state model.

---

## 3. Why Not Append to ES(t)?

The naive approach is:

```
ES(t) = (W, M, G, C, H, R, S, L, Mem)
```

This has problems:

1. **Tuple identity**: Python tuples are positional. Adding fields changes the meaning of every position. This is fragile.

2. **Domain confusion**: Structural state (S) and execution state (W, M) are logically distinct. Mixing them in one tuple obscures the boundary.

3. **Transition coupling**: If S and W are in the same tuple, every function that reads W must accept S. This creates unnecessary coupling.

4. **Checkpoint complexity**: Checkpointing a 9-tuple is harder than checkpointing 3 independent domains.

5. **Ontology trap**: The tuple becomes the definition. If we later discover S should be two fields, we break every function that touches ES(t).

---

## 4. Why Not Independent State Objects?

The opposite approach is:

```
ExecutionState = (W, M, C, H, R)
StructuralState = (G, S)
LearningState = (L)
MemoryState = (Mem)
```

Managed by independent state managers.

This also has problems:

1. **Atomic transitions are impossible**: If state objects are independent, a transition that spans domains cannot be atomic.

2. **Consistency is the programmer's problem**: The programmer must manually ensure that ExecutionState and StructuralState are consistent after every transition.

3. **Checkpointing is complex**: Must checkpoint all state objects atomically, which requires coordination.

4. **Cross-domain transitions are awkward**: "Add a node, execute it, and record the outcome" spans three domains. With independent objects, this requires explicit coordination.

---

## 5. The Correct Answer: Unified State with Logical Domains

The correct model is a **single unified state object** with **logically distinct domains**:

```
                 Global System State Σ(t)
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 Execution Domain   Computational      Adaptation
                    Domain             Domain
        │                │                │
        ▼                ▼                ▼
      (W, M, C,        (G)             (L, Mem)
       H, R)
```

### 5.1 Why Unified

- **Atomic transitions**: Σ(t) is one object. T transforms it atomically.
- **Consistency by construction**: There is one state; consistency is automatic.
- **Checkpoint simplicity**: Checkpoint Σ(t); restore Σ(t). One object.
- **Cross-domain transitions**: Natural. T can modify G and W in the same transition.

### 5.2 Why Logical Domains

- **Conceptual clarity**: Execution, computation, and adaptation are conceptually distinct.
- **Interface boundaries**: Functions that modify G don't need to know about L.
- **Debugging**: When something goes wrong, you can identify which domain is affected.
- **Extensibility**: New domains can be added without restructuring existing domains.

### 5.3 The Distinction

**Physical unity, logical separation.**

Σ(t) is one object. But it has internal structure that reflects the conceptual domains of DNC.

```
Σ(t) = {
    execution: ExecutionDomain(t),
    computation: ComputationDomain(t),
    adaptation: AdaptationDomain(t)
}
```

Each domain is a structured object, not a tuple position. The domains are accessed through named attributes, not positional indices.

---

## 6. Domain Definitions

### 6.1 Execution Domain

What is happening right now?

```
ExecutionDomain
    │
    ├── working_memory: WorkingMemory
    │       Current values of all computational nodes
    │       Keys correspond to active graph nodes
    │
    ├── history: HistoryLog
    │       Append-only record of all execution events
    │       Never mutated after append
    │
    ├── checkpoints: CheckpointStore
    │       Saved system states for rollback
    │       Each checkpoint captures full Σ(t)
    │
    └── cost: CostState
            Current resource consumption
            Budget limits and forecasts
```

### 6.2 Computation Domain

What computation exists?

```
ComputationDomain
    │
    ├── graph: Graph
    │       Current DAG of ComputationalUnits
    │       The structure that mutations modify
    │
    └── registry: ModuleRegistry
            Registry of available module types
            ModuleTypeID → ModuleContract mapping
```

### 6.3 Adaptation Domain

What has been learned? What can be reused?

**Note**: Unit parameters (θ_u — weights, biases, embeddings) live *inside* ComputationalUnits in the Computation Domain. The Adaptation Domain contains *learning state* — the policies, optimizers, and history that govern how the system learns. These are distinct:

- **Unit parameters** (Computation Domain): the values that define how a unit behaves
- **Learning state** (Adaptation Domain): the knowledge about *how to learn* and *what to try next*

```
AdaptationDomain
    │
    ├── learning_state: LearningState
    │       Routing policies (decision point → policy mapping)
    │       Structural policies (state → mutation proposal mapping)
    │       Compositional policies (pattern → composition mapping)
    │       Consolidation policies (pattern → reusable unit mapping)
    │       Optimizer states (for any learned policies)
    │
    ├── memory: StructuralMemory
    │       Consolidated structural patterns
    │       Reusable computational units
    │       Specialized units
    │
    └── history: AdaptationHistory
            Record of past structural mutations
            Outcomes of past adaptations
```

---

## 7. Transition Function

The transition function T transforms Σ(t) atomically:

```
T: Σ(t) × O(t) × D(t) × A(t) → Σ(t+1)
```

A single transition can:

- **Execute a computation unit**: Modifies working_memory, history, cost (Execution Domain)
- **Mutate the graph**: Modifies graph (Computation Domain)
- **Record a structural outcome**: Modifies history, learning_state (Adaptation Domain)
- **All three at once**: Any combination

The transition function is defined per-action. Each action type specifies which domains it modifies:

| Action Type | Domains Modified |
|-------------|-----------------|
| `execute` | Execution Domain |
| `structural_mutate` | Computation Domain (+ possibly Execution Domain) |
| `consolidate` | Computation Domain + Adaptation Domain |
| `specialize` | Computation Domain + Adaptation Domain |
| `checkpoint` | Execution Domain (snapshot of full Σ) |
| `rollback` | Full Σ (restore from checkpoint) |

---

## 8. Checkpoint: Capturing Full State

A checkpoint captures the *entire* Σ(t):

```
Checkpoint
    │
    ├── timestamp: Time
    ├── sigma: Σ(t)           (complete system state)
    ├── provenance_hash: Hash (tamper-evident)
    └── metadata: Dict
```

This is why the unified model matters. If state were distributed across independent objects, checkpointing would require coordinating multiple stores. With a unified Σ(t), checkpointing is a single atomic snapshot.

**Rollback** restores the entire Σ(t). There is no partial rollback. This is a safety property: the system is always in a consistent state.

---

## 9. Relationship to DNC v1.x ES(t)

The current ES(t) = (W, M, G, C, H, R) maps to the new model:

| v1.x Field | v2.x Domain | v2.x Field |
|-------------|-------------|------------|
| W (WorkingMemory) | Execution Domain | working_memory |
| M (ModuleRegistry) | Computation Domain | registry |
| G (Graph) | Computation Domain | graph |
| C (Checkpoints) | Execution Domain | checkpoints |
| H (History) | Execution Domain | history |
| R (Cost/Resources) | Execution Domain | cost |

**The v1.x ES(t) is a flat representation of the Execution Domain + Computation Domain.** The v2.x model adds the Adaptation Domain and structures the existing fields into domains.

**Backward compatibility**: The v1.x ES(t) can be represented as a v2.x Σ(t) with an empty AdaptationDomain.

---

## 10. Implications for Mutation Semantics (Q4)

The state model determines how mutations are expressed:

- A mutation is a function: `Σ(t) → Σ(t+1)`
- Mutations specify which domain(s) they modify
- The Computation Domain is the primary target of structural mutations
- But mutations can also affect the Execution Domain (e.g., adding a node adds a WorkingMemory entry)
- And the Adaptation Domain (e.g., recording the mutation outcome)

This is specified in Q4.

---

## 11. Implications for Learning (Q5)

The state model determines what learning modifies:

- Learning modifies the Adaptation Domain
- Learning reads from the Execution Domain (execution outcomes) and Computation Domain (current structure)
- Learning produces: new learning state, new memory entries, new structural proposals

This is specified in Q5.

---

## 12. Formal Properties

The state model must satisfy:

1. **Completeness**: Σ(t) contains all information needed to determine the system's behavior at time t.

2. **Atomicity**: Transitions transform Σ(t) atomically. No partial transitions.

3. **Reversibility**: For every transition Σ(t) → Σ(t+1), there exists a rollback that restores Σ(t) from the checkpoint.

4. **Determinism**: Given the same Σ(t), O(t), D(t), A(t), the transition produces the same Σ(t+1). (Assuming deterministic providers; non-determinism is captured in O(t).)

5. **Domain independence**: Transitions in one domain do not implicitly affect other domains. Cross-domain effects are explicit in the transition function.

---

## 13. Open Questions

1. **Domain granularity**: Are three domains (execution, computation, adaptation) the right decomposition? Could there be fewer or more?

2. **Domain coupling**: How tightly coupled are the domains? Can the Computation Domain be modified without touching the Execution Domain?

3. **State versioning**: Should Σ(t) have a version number? This would enable efficient delta-computation for checkpoints.

4. **Partial checkpoints**: Should the system support checkpointing individual domains? This would enable more granular rollback but violates the atomicity principle.

These are design decisions that can be resolved during implementation. The state model above is sufficient to proceed to Q4.

---

## 14. Summary

| Property | Value |
|----------|-------|
| State model | Unified Σ(t) with logical domains |
| Domains | Execution, Computation, Adaptation |
| Transitions | Atomic transformations of Σ(t) |
| Checkpoint | Full Σ(t) snapshot |
| Rollback | Full Σ(t) restore |
| v1.x compatibility | v1.x ES(t) = Execution + Computation domains |
| Key principle | Physical unity, logical separation |
