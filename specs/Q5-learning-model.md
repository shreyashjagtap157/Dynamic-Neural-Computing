# Q5: What Exactly Does DNC Learn?

**Date**: 2026-07-22  
**Status**: THEORETICAL DEFINITION  
**Depends on**: Q1 (What Is DNC?), Q2 (Computational Substrate), Q3 (State Model), Q4 (Mutation Authority)  
**Depended on by**: DNC-IR, Structural Learning, Computational Memory, Consolidation, Evaluation

---

## 1. The Question

What does DNC learn?

This question separates a sophisticated dynamic runtime from a genuinely new computational architecture. A system that dynamically mutates its graph based on rules is interesting. A system that *learns what structure to build* is revolutionary.

But learning in DNC is not one thing. It has two orthogonal axes: **capability levels** (what the architecture supports) and **learning dimensions** (what the algorithms can learn).

---

## 2. Two Axes: Capability Levels vs. Learning Dimensions

### 2.1 Capability Levels (from Q1)

These define what the architecture *supports*:

```
DNC-3    Rule-based mutations (no learning)
DNC-4    Feedback-driven mutations (reactive adaptation)
DNC-5    Learned mutations (structural policies)
DNC-6    Consolidated + reused (recurring patterns become units)
```

### 2.2 Learning Dimensions (new)

These define what the algorithms can *learn*:

```
Parameters    "How should this computation behave?"
Routing       "Which computation should execute next?"
Structure     "What computation should exist?"
Composition   "Which computations should be combined?"
Consolidation "Should this recurring structure become reusable?"
```

### 2.3 The Distinction

**Capability levels are architectural.** They define which interfaces are active and which roles exist.

**Learning dimensions are algorithmic.** They define what knowledge the system acquires.

A DNC-5 system *can* learn in all five dimensions, but it doesn't *have to*. A DNC-3 system *cannot* learn in any dimension — it uses rules, not learned policies.

The dimensions are **independent**. A system could:
- Learn routing without learning parameters (DNC-2 with a learned router)
- Learn structure without learning composition (DNC-5 with a structural policy but no compositional policy)
- Consolidate without having a sophisticated parameter-learning system (DNC-6 with pattern extraction but simple parameters)

This is not a hierarchy. It is a **space of capabilities**.

---

## 3. The Learning Dimensions

### 3.1 Dimension: Parameters

**Question**: "How should this computation behave?"

Standard neural network learning. Each computational unit has internal parameters (weights, biases, embeddings). Learning adjusts these parameters to improve task performance.

**DNC relevance**: DNC does not replace parameter learning. DNC systems still contain units that learn parameters. The units are the ComputationalUnits defined in Q2.

**What changes**: In DNC, parameter learning operates *within* ComputationalUnits, not across a fixed graph. The graph itself is mutable; parameters are local to units.

**Formal model**:

```
For each unit u in graph G:
    θ_u(t+1) = θ_u(t) - α ∇L(θ_u, task)
```

**Applicable at**: DNC-3 and above (parameter learning is orthogonal to structural mutation).

### 3.2 Dimension: Routing

**Question**: "Which computation should execute next?"

Routing learning decides how inputs flow through the graph. Given a graph with multiple paths, routing learning determines which path to take for each input.

**Examples**:
- Mixture of Experts: route inputs to different expert modules
- Adaptive computation: skip layers that are not needed
- Dynamic branching: choose between different processing pipelines

**DNC relevance**: DNC v1.x makes routing decisions via `DecisionPolicy`. DNC v2.x extends this to structural routing — not just "which existing path" but "which path should exist."

**Formal model**:

```
For each decision point d in graph G:
    policy_d(input, context) → path_distribution
    sample path from path_distribution
    execute chosen path
```

**Applicable at**: DNC-2 and above (routing is independent of structural mutation).

### 3.3 Dimension: Structure

**Question**: "What computation should exist?"

This is the core of DNC. Structural learning decides what nodes should be in the graph, what edges should connect them, and how the graph should be organized.

**What is learned**:
- **Node creation**: When should a new computational unit be added?
- **Node removal**: When should an existing unit be removed?
- **Edge creation**: When should a new connection be made?
- **Edge removal**: When should a connection be severed?
- **Unit replacement**: When should a unit be replaced with a different type?

**DNC relevance**: This is what makes DNC fundamentally different from dynamic neural networks. Dynamic neural networks choose from existing paths. DNC creates new paths.

**Formal model**:

```
structural_policy(Σ(t), task, history) → MutationProposal
```

The structural policy is learned from the outcomes of past mutations. If adding a node improved performance, the policy learns to propose similar mutations in similar situations.

**Applicable at**: DNC-5 and above (learned structural policies).

### 3.4 Dimension: Composition

**Question**: "Which computations should be combined?"

Compositional learning decides how computational units should be composed into larger structures. It learns:

- **Pipeline composition**: Which units should be chained together?
- **Parallel composition**: Which units can execute simultaneously?
- **Hierarchical composition**: Which units should be grouped into composites?
- **Abstraction**: What interfaces should composites expose?

**DNC relevance**: DNC v2.x defines COMPOSITE units (Q2). Compositional learning decides what composites should exist.

**Formal model**:

```
compositional_policy(Σ(t), recurring_patterns) → CompositionProposal
```

**Applicable at**: DNC-5 and above (learned compositional policies).

### 3.5 Dimension: Consolidation

**Question**: "Should this recurring structure become reusable?"

Consolidation learning identifies recurring structural patterns and extracts them into reusable units.

**What is learned**:
- **Pattern extraction**: What subgraph patterns appear frequently?
- **Abstraction**: What is the minimal interface for this pattern?
- **Specialization**: Can this pattern be specialized for specific task classes?
- **Reuse**: When should a consolidated unit be used instead of rebuilding the structure?

**DNC relevance**: This is what produces SPECIALIZED lifecycle units (Q2). Consolidation is how DNC builds a library of reusable computational components from experience.

**Formal model**:

```
consolidation_policy(pattern_history) → ConsolidationProposal
```

**Applicable at**: DNC-6 (consolidation requires both structural and compositional learning).

---

## 4. The Learning Space

```
                    LEARNING DIMENSIONS
                         
          Parameters   Routing   Structure   Composition   Consolidation
              │            │          │            │              │
    DNC-3     │            │          │            │              │
   (rules)    │            │          │            │              │
              │            │          │            │              │
    DNC-4     │            │          │            │              │
  (feedback)  ◄────────────┤          │            │              │
              │            │          │            │              │
    DNC-5     │            │          │            │              │
  (learned)   ◄────────────┼──────────┼────────────┤              │
              │            │          │            │              │
    DNC-6     │            │          │            │              │
(consolidate) ◄────────────┼──────────┼────────────┼──────────────┤
              │            │          │            │              │
```

**Reading the diagram**: Each capability level enables certain learning dimensions. DNC-3 has none. DNC-4 enables feedback-driven adaptation (a form of routing). DNC-5 enables learned routing, structure, and composition. DNC-6 enables consolidation.

**But the dimensions are independent within each level.** A DNC-5 system could implement learned routing without learned structure, or learned structure without learned composition. The architecture defines the interfaces; the implementation chooses which dimensions to activate.

---

## 5. What Is Stored

| Learning Dimension | Stored In | What Is Stored |
|--------------------|-----------|----------------|
| Parameters | Unit parameters (inside ComputationalUnits in Computation Domain) | Weights, biases, embeddings |
| Routing | Adaptation Domain (learning_state: routing_policies) | Decision point → policy mapping |
| Structure | Adaptation Domain (learning_state: structural_policy) | State → mutation proposal mapping |
| Composition | Adaptation Domain (learning_state: compositional_policy) | Pattern → composition mapping |
| Consolidation | Adaptation Domain (memory: consolidated_units) | Extracted reusable units |

**Note**: Unit parameters live inside ComputationalUnits in the Computation Domain, not in the Adaptation Domain. The Adaptation Domain contains the *learning state* (policies, optimizers, history) that governs how learning operates.

---

## 6. What Is Learned From

| Learning Dimension | Input | Source |
|--------------------|-------|--------|
| Parameters | Task loss | Execution outcome |
| Routing | Routing outcomes | Execution trace |
| Structure | Mutation outcomes | Assessment reports |
| Composition | Recurring patterns | Mutation history |
| Consolidation | Repeated subgraph patterns | Graph history |

---

## 7. The Fundamental Research Question

The deepest question is:

> **Can a system learn to build the right computation for a given task, rather than being told what computation to perform?**

This is what separates DNC from all prior work:

| System | What It Learns |
|--------|----------------|
| Neural network | Parameters |
| Mixture of Experts | Routing |
| Neural Architecture Search | Fixed architecture (offline) |
| Dynamic Neural Networks | Routing within fixed graph |
| **DNC** | **Parameters, Routing, Structure, Composition, Consolidation** |

DNC is the first architecture that aims to learn *what computation should exist*, not just *how existing computation should behave*.

---

## 8. The Research Hypotheses

### Hypothesis 1: Structural Learning Works
A system can learn to propose structural mutations that improve task performance, given sufficient experience.

**Testable prediction**: A DNC-5 system with learned structural policies outperforms a DNC-3 system (rule-based mutations) on tasks that require task-specific computation structures.

### Hypothesis 2: Consolidation Produces Reusable Units
A system can learn to extract recurring subgraph patterns into reusable units that generalize across tasks.

**Testable prediction**: Consolidated units (DNC-6 SPECIALIZED lifecycle) improve performance on new tasks that share structural patterns with training tasks.

### Hypothesis 3: Composition Scales
Compositional learning can build complex computations from simple units, scaling to tasks that require multi-step reasoning.

**Testable prediction**: A DNC-6 system can solve tasks that require composing 10+ computational steps, where each step is a learned or consolidated unit.

### Hypothesis 4: DNC Outperforms Fixed Architecture
For tasks that require task-specific computation structures, DNC outperforms fixed-architecture systems of comparable size.

**Testable prediction**: On tasks where the optimal computation structure varies by input, DNC achieves higher accuracy with fewer parameters than a fixed-architecture baseline.

**These are research hypotheses, not architectural facts.** The architecture remains valid even if an experiment disproves one of these hypotheses. The architecture defines *interfaces for learning*; the hypotheses predict *whether learning will succeed*.

---

## 9. What DNC Does NOT Learn

DNC does not learn:

1. **Physics**: DNC does not discover physical laws. It learns computational structures.

2. **Logic**: DNC does not learn logical reasoning from scratch. It can learn to compose logical operations.

3. **Semantics**: DNC does not learn language from scratch. It can learn to compose semantic operations.

4. **Consciousness**: DNC does not learn self-awareness. It learns computational structures.

DNC is a computational architecture, not a theory of mind. It learns *how to compute*, not *what to think*.

---

## 10. Relationship to DNC v1.x

The current DNC v1.x system has:

- `DecisionPolicy` → Routing dimension (routing decisions within fixed graph)
- `LLMPolicy` → Routing dimension (LLM-based routing)
- `RLPolicy` → Routing dimension (RL-based routing)
- No structural, compositional, or consolidation learning

**DNC v2.x extends**:
- `DecisionPolicy` → Routing + Structure dimensions (routing + structural decisions)
- New `StructuralPolicy` → Structure dimension (learned structural mutations)
- New `CompositionalPolicy` → Composition dimension (learned compositions)
- New `ConsolidationPolicy` → Consolidation dimension (learned consolidation)

---

## 11. The Capability Progression

```
DNC-3: Rule-based mutations
    │   No learning. Rules define what mutations are possible.
    │   Example: "If cost > budget, add a cheaper module."
    │
    ├──→ DNC-4: Feedback-driven mutations
    │       Rules adapt based on execution outcomes.
    │       Example: "If adding a module helped last time, try it again."
    │
    ├──→ DNC-5: Learned mutations
    │        Structural policy learned from experience.
    │        Can activate: Routing, Structure, Composition dimensions.
    │        Example: "For task class X, the optimal structure is Y."
    │
    └──→ DNC-6: Consolidated + reused
             Recurring patterns become reusable units.
             Can activate: all five dimensions including Consolidation.
             Example: "The pattern 'embed → classify → route' is now a single unit."
```

Each level is independently valuable. A DNC-3 system is useful without learning. A DNC-5 system is more powerful. A DNC-6 system is the most powerful.

---

## 12. Open Questions

1. **Credit assignment**: When a mutation improves performance, how do we attribute the improvement to the specific mutation? This is the structural credit assignment problem.

2. **Exploration vs. exploitation**: Should the system explore new structural mutations or exploit known good ones? This is the structural exploration dilemma.

3. **Sample efficiency**: How many mutation trials does the system need to learn good structural policies? Can we use meta-learning or transfer learning?

4. **Catastrophic structural change**: Can a sequence of mutations irreversibly damage the system's ability to perform? How do we prevent this?

5. **Scalability**: Does structural learning scale to graphs with hundreds or thousands of units? Or does it only work for small graphs?

These are research questions that will be answered by implementation and experimentation. The theoretical framework above is sufficient to begin specification.

---

## 13. Summary

| Property | Value |
|----------|-------|
| Learning dimensions | Parameters, Routing, Structure, Composition, Consolidation (independent) |
| Capability levels | DNC-3 (no learning) through DNC-6 (all dimensions) |
| Dimensions are independent? | Yes — a system can learn routing without parameters, structure without composition |
| Core research question | Can a system learn what computation to build? |
| Research hypotheses | 4 testable predictions (hypotheses, not architectural facts) |
| What DNC does NOT learn | Physics, logic, semantics, consciousness |
