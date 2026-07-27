# Q1: What Exactly Is DNC?

**Date**: 2026-07-22  
**Status**: THEORETICAL DEFINITION  
**Depends on**: Execution Core v1.x Freeze  
**Depended on by**: Q2 (Computational Substrate), Q3 (State Model), DNC-IR, Mutation Semantics

---

## 1. The Question

What exactly is Dynamic Neural Computation?

This is the most consequential question in the entire specification. Every subsequent decision — state model, mutation semantics, learning model, evaluation — flows from how we define DNC here.

---

## 2. What DNC Is Not

Before defining what DNC *is*, we must disambiguate from concepts that are related but distinct:

| Concept | What It Does | Why It Is Not DNC |
|---------|--------------|-------------------|
| Static computation graph | Fixed structure, executed as-is | No dynamic structure |
| Dynamic execution | Runtime decisions about *execution order* within a fixed graph | Graph structure unchanged |
| Dynamic routing | Runtime decisions about *which path* through a fixed graph | Graph structure unchanged |
| Neural architecture search | Offline search for optimal fixed architecture | Not runtime; not dynamic |
| Dynamic neural networks | Networks that change structure during training | Changes happen *between* tasks, not *within* a task |
| Adaptive computation | Networks that skip layers or adjust depth | Predefined adaptation rules; not structural mutation |
| Mixture of Experts | Routes inputs to different subnetworks | Routing is fixed after training; structure does not change |

**DNC is distinct from all of these.** DNC is defined by the system's ability to dynamically change its own computational structure *during execution*, in response to task demands, execution experience, resource conditions, and learned information.

---

## 3. The Core Property

**Dynamic Neural Computation** is characterized by one core property:

> **The system can modify its own computational structure — what computation exists, how it is composed, and how it is routed — during execution, subject to explicit constraints.**

This property has degrees. A system that can add a node is less dynamic than one that can add a node, remove a node, and rewire edges. A system that does this based on rules is less dynamic than one that learns to do it from experience.

Therefore, DNC is not a single capability but a **spectrum of capabilities** organized into maturity levels.

---

## 4. DNC Maturity Levels

```
DNC-0    Static Computation
         ├── Graph is fixed before execution
         ├── No runtime structural changes
         └── Example: Standard neural network, static pipeline

DNC-1    Dynamic Execution
         ├── Runtime decisions about execution order within fixed graph
         ├── Conditional branching, early exit, adaptive computation
         ├── Graph structure unchanged
         └── Example: Adaptive computation, early exit networks

DNC-2    Dynamic Routing
         ├── Runtime decisions about which path through graph
         ├── Input-dependent routing, attention mechanisms
         ├── Graph structure unchanged; only traversal changes
         └── Example: Mixture of Experts (post-training), conditional computation

DNC-3    Dynamic Structural Mutation
         ├── Runtime decisions about what computation exists
         ├── Add/remove computational units, rewire connections
         ├── Structural changes are possible but not yet informed by experience
         ├── Based on rules, heuristics, or external directives
         └── Example: Dynamic DAG with rule-based structural mutations

DNC-4    Dynamic Structural Adaptation
         ├── Structural mutations informed by execution feedback
         ├── System observes outcomes and adjusts structure accordingly
         ├── Adaptation is reactive (responds to observed performance)
         └── Example: System that adds capacity when cost budget allows

DNC-5    Structural Learning
         ├── Structural mutations are learned from experience
         ├── System learns *what structure to build* for given task classes
         ├── Learns generalizable structural patterns
         └── Example: System that learns to compose task-specific subgraphs

DNC-6    Structural Consolidation and Reuse
         ├── Recurring structural patterns are extracted and stored as reusable units
         ├── Specialized computational units emerge from experience
         ├── Consolidated units can be composed, refined, and shared
         └── Example: System that learns reusable "modules" from repeated subgraph patterns
```

---

## 5. Formal Definition

**Dynamic Neural Computation (DNC)** is a computational architecture defined by:

### 5.1 Minimum DNC Capability (DNC-3)

A system qualifies as DNC (at the minimum level) if and only if:

1. **Structural Mutability**: The system can modify its computational graph during execution — adding, removing, or reconnecting computational units.

2. **Constraint Preservation**: All structural mutations preserve a set of explicit invariants (DAG property, dependency enforcement, state consistency, provenance integrity).

3. **Transactional Safety**: Structural mutations are atomic — either fully applied or fully rolled back — with no partial state visible to execution.

4. **Observability**: All structural mutations are recorded in an append-only provenance log with tamper-evident hash chains.

### 5.2 Advanced DNC Capabilities (DNC-4 through DNC-6)

Beyond the minimum, DNC systems may exhibit:

- **DNC-4**: Feedback-driven adaptation (mutations respond to execution outcomes)
- **DNC-5**: Learned structural policies (mutations are generated by learned models)
- **DNC-6**: Structural consolidation (recurring patterns become reusable units)

### 5.3 DNC Architecture vs. DNC Capability Levels

**DNC Architecture** is the *framework* that defines:
- The interfaces through which structural mutations occur
- The constraints that mutations must satisfy
- The state model that captures structural state
- The provenance model that records structural changes
- The evaluation model that assesses structural quality

**DNC Capability Level** is the *specific algorithms* that:
- Decide what structural mutations to make
- Learn from execution experience
- Consolidate recurring patterns

A DNC Architecture can support any capability level from DNC-3 to DNC-6. The architecture is defined by the interfaces; the capability level is defined by the algorithms plugged into those interfaces.

---

## 6. The Key Distinction: Architecture vs. Capability

This distinction is critical:

```
DNC Architecture (what we are specifying)
    │
    ├── Defines: interfaces, constraints, state model, provenance
    ├── Does NOT specify: how mutations are decided
    ├── Does NOT specify: what is learned
    └── Does NOT specify: how consolidation works
         │
         └── Capability Level (what the implementation provides)
                │
                ├── DNC-3: rule-based mutations
                ├── DNC-4: feedback-driven mutations
                ├── DNC-5: learned mutations
                └── DNC-6: consolidated reusable units
```

**The DNC v2.x specification defines the architecture.**  
**The capability level is an implementation choice.**

This means:
- We can specify DNC-3 first (rule-based structural mutations) and validate the architecture
- We can then specify DNC-4 and DNC-5 as extensions
- The architecture does not change between capability levels — only the algorithms do

---

## 7. Does DNC Require Learning?

**No.**

Learning (DNC-5) is an advanced capability, not a defining property.

A system that can dynamically mutate its computational graph based on rules — without learning — is still DNC. It is DNC-3. The architecture is the same; the algorithms are simpler.

This is a deliberate design choice. It means:
- We can build and validate a DNC-3 system (rule-based mutations) before attempting learning
- The architecture does not depend on the success of the learning algorithms
- Each capability level is independently testable
- The research hypotheses can be tested incrementally

**The research question is not "can we build DNC?" but "at what capability level does DNC become useful, and can we reach DNC-5 and DNC-6?"**

---

## 8. Relationship to Existing Concepts

### 8.1 Dynamic Neural Networks
Dynamic neural networks (e.g., SkipNet, BlockDrop, PonderNet) modify computation paths at runtime. These are **DNC-1 or DNC-2** systems: they decide *which computation to execute* but do not change *what computation exists*.

### 8.2 Neural Architecture Search (NAS)
NAS finds optimal fixed architectures offline. This is **not DNC** — it is architecture optimization, not dynamic structural mutation.

### 8.3 Adaptive Computation
Adaptive computation (e.g., early exit, dynamic depth) adjusts execution within a fixed graph. This is **DNC-1**.

### 8.4 Mixture of Experts
MoE routes inputs to different subnetworks. After training, the routing is fixed. This is **DNC-2** (static routing structure, dynamic execution).

### 8.5 Dynamic DAG Execution
DAG-based execution systems (e.g., TensorFlow, PyTorch) execute fixed computational graphs. They are **DNC-0**.

### 8.6 DNC v1.x (Current System)
The current DNC system is **DNC-1**: it makes runtime decisions about execution order within a fixed DAG, with checkpoint/rollback and provenance. It does not mutate structure.

**DNC v2.x targets DNC-3 at minimum, with research toward DNC-5 and DNC-6.**

---

## 9. Implications for Specification

### 9.1 What We Must Specify

1. **Structural Mutation Interface**: How the system adds/removes/reconnects computational units
2. **Constraint Model**: What invariants structural mutations must preserve
3. **State Model**: How structural state is represented in ES(t)
4. **Provenance Model**: How structural mutations are recorded
5. **Transaction Model**: How mutations are applied atomically
6. **Evaluation Model**: How structural quality is assessed

### 9.2 What We Must NOT Specify (Yet)

1. **Decision Algorithm**: How the system decides what mutations to make (rule-based for DNC-3, learned for DNC-5)
2. **Learning Model**: What the system learns and how (DNC-5)
3. **Consolidation Model**: How recurring patterns become reusable units (DNC-6)

### 9.3 The Dependency Chain

```
Q1: What is DNC? (this document)
    │
    ├──→ Q2: Computational Substrate (what exists to be mutated)
    ├──→ Q3: State Model (how structural state is represented)
    ├──→ Q4: Mutation Authority (who proposes, authorizes, applies mutations)
    └──→ Q5: Learning Model (what the system learns)
            │
            ├──→ DNC-IR (intermediate representation for mutations)
            ├──→ Mutation Semantics (how mutations transform state)
            ├──→ Transaction Semantics (how mutations are applied atomically)
            └──→ Evaluation Model (how structural quality is assessed)
```

---

## 10. Open Questions for Q2–Q5

This definition raises questions that Q2–Q5 must resolve:

1. **Q2**: What is the computational substrate? (Nodes? Modules? ComputationUnits? Subgraphs?)
2. **Q3**: Is structural state part of execution state, or a separate domain?
3. **Q4**: Who proposes mutations? Who authorizes them? Who applies them?
4. **Q5**: What does DNC learn? Parameters? Routing? Structure? Composition? All of these?

These are the next five documents.

---

## 11. Summary

| Property | Value |
|----------|-------|
| DNC is defined by | Dynamic structural mutation during execution |
| Minimum DNC capability | DNC-3 (rule-based structural mutations) |
| DNC requires learning? | No — learning is DNC-5, an advanced capability |
| DNC architecture vs. capability | Architecture = interfaces; Capability = algorithms |
| DNC v2.x targets | DNC-3 minimum, research toward DNC-5/DNC-6 |
| What we specify | Architecture (interfaces, constraints, state, provenance) |
| What we don't specify (yet) | Algorithms (decision, learning, consolidation) |
