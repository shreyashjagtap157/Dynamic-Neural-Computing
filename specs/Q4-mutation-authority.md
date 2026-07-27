# Q4: Who Can Mutate Computation?

**Date**: 2026-07-22  
**Status**: THEORETICAL DEFINITION  
**Depends on**: Q1 (What Is DNC?), Q2 (Computational Substrate), Q3 (State Model)  
**Depended on by**: Q5 (Learning Model), DNC-IR, Mutation Semantics, Transaction Semantics

---

## 1. The Question

Who proposes structural mutations? Who authorizes them? Who applies them? Who assesses their outcomes?

This is the most important architectural question for DNC v2.x. The answer determines the system's safety, modularity, and extensibility.

---

## 2. The Core Principle

> **Proposal ≠ Authorization ≠ Application ≠ Execution**

These are four distinct operations performed by four distinct roles. Conflating them is the most common source of architectural failure in dynamic systems.

| Role | Responsibility | Question It Answers |
|------|----------------|---------------------|
| Computational Generator | Proposes structural mutations | "What computation should exist?" |
| Structural Controller | Evaluates and authorizes mutations | "Is this mutation safe and useful?" |
| Mutation Engine | Applies mutations transactionally | "How do we change the graph atomically?" |
| Execution Core | Executes the mutated graph | "What happens when we run this?" |

Plus two feedback roles:

| Role | Responsibility | Question It Answers |
|------|----------------|---------------------|
| Assessment | Evaluates execution outcomes | "Did the mutation help?" |
| Learning System | Proposes future mutations based on experience | "What should we try next time?" |

---

## 3. The Mutation Pipeline

```
                    ┌─────────────────────────┐
                    │ Computational Generator  │
                    │                          │
                    │ "What computation should │
                    │  exist?"                 │
                    │                          │
                    │ Reads knowledge from:    │
                    │  • Adaptation Domain     │
                    │  • Execution Domain      │
                    │  • Task description      │
                    └───────────┬──────────────┘
                                │
                          MutationProposal
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Structural Controller    │
                    │                          │
                    │ "Is this mutation safe   │
                    │  and useful?"            │
                    └───────────┬──────────────┘
                                │
                     AuthorizationDecision
                       (APPROVE / REJECT / MODIFY)
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Mutation Engine          │
                    │                          │
                    │ "Apply the mutation      │
                    │  atomically"             │
                    └───────────┬──────────────┘
                                │
                          Σ(t) → Σ(t+1)
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Execution Core           │
                    │                          │
                    │ "Execute the mutated     │
                    │  graph"                  │
                    └───────────┬──────────────┘
                                │
                          ExecutionOutcome
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Assessment               │
                    │                          │
                    │ "Did the mutation help?" │
                    └───────────┬──────────────┘
                                │
                         AssessmentReport
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Learning System          │
                    │                          │
                    │ "Update knowledge based  │
                    │  on this outcome"        │
                    └───────────┬──────────────┘
                                │
                         LearningUpdate
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Adaptation Domain        │
                    │                          │
                    │ Updated policies,        │
                    │ optimizers, history      │
                    │                          │
                    │ (read by Generator on    │
                    │  next proposal)          │
                    └─────────────────────────┘
```

**The feedback loop**: Learning → Adaptation Domain → Generator → Controller → Engine → Σ(t+1) → Execution → Assessment → Learning.

The Learning System never bypasses the Generator. It updates knowledge; the Generator reads that knowledge.

---

## 4. Role Definitions

### 4.1 Computational Generator

**Question**: "What computation should exist?"

**Inputs**: Task description, current state Σ(t), resource constraints, historical outcomes

**Outputs**: `MutationProposal`

```
MutationProposal
    │
    ├── operations: List[MutationOperation]
    │       What to change in the graph
    │
    ├── rationale: str
    │       Why this mutation is proposed
    │
    ├── expected_outcome: ExpectedOutcome
    │       Predicted effect on performance, cost, latency
    │
    └── priority: Priority
            How urgent this mutation is
```

**Implementations** (by capability level):

| Level | Generator Implementation |
|-------|-------------------------|
| DNC-3 | Rule-based generator (if cost > threshold, add capacity) |
| DNC-4 | Feedback-driven generator (if task fails, try different structure) |
| DNC-5 | Learned generator (neural model that proposes mutations) |
| DNC-6 | Consolidation generator (extract recurring patterns) |

**Key property**: The generator *proposes* but does not *decide*. Proposals are suggestions, not commands.

### 4.2 Structural Controller

**Question**: "Is this mutation safe and useful?"

**Inputs**: `MutationProposal`, current state Σ(t), constraints

**Outputs**: `AuthorizationDecision`

```
AuthorizationDecision
    │
    ├── decision: APPROVE | REJECT | MODIFY
    │
    ├── modified_proposal: MutationProposal (if MODIFY)
    │       The controller's adjusted version
    │
    └── reasoning: str
            Why this decision was made
```

**Authorization checks**:

| Check | Question | Constraint |
|-------|----------|------------|
| DAG preservation | Does the mutation create cycles? | INV-3 |
| Dependency enforcement | Are all preconditions satisfied? | INV-4 |
| Resource bounds | Does the mutation fit within budget? | CostConstraint |
| Type compatibility | Do the types match across new edges? | TypeConstraint |
| Duplicativity | Does this duplicate existing computation? | StructuralConstraint |
| Utility | Is the expected improvement worth the cost? | UtilityConstraint |
| Safety | Does this mutation introduce unsafe states? | SafetyConstraint |

**Key property**: The controller can *approve*, *reject*, or *modify* the proposal. It is an active filter, not a passive gate.

### 4.3 Mutation Engine

**Question**: "How do we change the graph atomically?"

**Inputs**: Authorized `MutationProposal`, current state Σ(t)

**Outputs**: Σ(t+1)

```
MutationEngine
    │
    ├── checkpoint(Σ(t))         Save current state
    ├── apply(operations)         Apply mutation operations
    ├── validate(Σ(t+1))         Verify invariants hold
    ├── commit()                  Make mutation permanent
    └── rollback()                Revert to checkpoint on failure
```

**Transaction model**:

```
BEGIN TRANSACTION
    checkpoint = save(Σ(t))
    FOR each operation in proposal:
        apply(operation)
        IF invariant_violation:
            rollback(checkpoint)
            RETURN failure
    commit()
RETURN success
```

**Key property**: The engine *applies* but does not *decide*. It executes authorized mutations transactionally.

### 4.4 Execution Core

**Question**: "What happens when we run this?"

**Inputs**: Σ(t+1) (post-mutation state)

**Outputs**: `ExecutionOutcome`

The Execution Core is the v1.x system, frozen. It executes the mutated graph using the existing control loop:

```
Observe → Decide → Act → Assess
```

**Key property**: The Execution Core does not know about mutations. It receives a graph and executes it. Mutations are invisible to execution.

### 4.5 Assessment

**Question**: "Did the mutation help?"

**Inputs**: `ExecutionOutcome`, `MutationProposal`, Σ(t), Σ(t+1)

**Outputs**: `AssessmentReport`

```
AssessmentReport
    │
    ├── outcome: SUCCESS | FAILURE | PARTIAL
    │
    ├── metrics: Dict[str, float]
    │       Performance, cost, latency, quality
    │
    ├── comparison: Comparison
    │       Before vs. after metrics
    │
    └── causal_attribution: str
            Whether the improvement is attributable to the mutation
```

**Key property**: Assessment is *retrospective*. It evaluates what happened, not what should happen.

### 4.6 Learning System

**Question**: "What should we try next time?"

**Inputs**: `AssessmentReport`, history of past mutations and outcomes

**Outputs**: Updated learning state (policies, optimizers, adaptation history)

**Key property**: The Learning System (DNC-5) is the *feedback loop* that makes structural mutations improve over time. It is optional for DNC-3 and DNC-4.

**Critical safety property**: The Learning System does **not** produce `MutationProposal`s directly. It updates *knowledge* (learning state, policies). The Computational Generator reads this knowledge when proposing mutations. This ensures:

```
Learning System
    │
    │ updates knowledge
    ▼
Adaptation Domain
    │
    │ knowledge read by
    ▼
Computational Generator
    │
    │ produces MutationProposal
    ▼
Structural Controller
    │
    ▼
Mutation Engine
    │
    ▼
Σ(t+1)
```

The Learning System cannot bypass the Generator, Controller, or Engine. It influences proposals through knowledge, not through direct action.

---

## 5. The Critical Distinction

### 5.1 Proposal ≠ Authorization

A generator may propose mutations that are unsafe, redundant, or wasteful. The controller catches these.

Example:
- **Generator**: "Add a third copy of the embedding module for parallelism."
- **Controller**: "REJECT — the resource budget cannot support three copies. MODIFIED: add one copy instead."

### 5.2 Authorization ≠ Application

A controller may approve a mutation that fails to apply. The engine handles this gracefully.

Example:
- **Controller**: "APPROVE — add edge from A.output to B.input."
- **Engine**: "ROLLBACK — adding this edge creates a cycle. Invariant INV-3 violated."

### 5.3 Application ≠ Execution

The engine may apply a mutation successfully, but execution may reveal the mutation was harmful.

Example:
- **Engine**: "COMMIT — mutation applied successfully."
- **Execution**: "Task failed. The new structure does not support the required computation."
- **Assessment**: "FAILURE — the mutation degraded performance."

### 5.4 Execution ≠ Learning

Execution produces outcomes. Learning produces future proposals. They are distinct.

Example:
- **Execution**: "Task completed with 95% accuracy."
- **Assessment**: "The new structure improved accuracy by 5%."
- **Learning**: "When similar tasks appear, propose similar structural mutations."

---

## 6. DNC Capability Levels and Roles

| Level | Generator | Controller | Engine | Assessment | Learning |
|-------|-----------|------------|--------|------------|----------|
| DNC-3 | Rule-based | Constraint checker | Transactional | Metric comparison | None |
| DNC-4 | Feedback-driven | Constraint checker | Transactional | Metric comparison | Reactive (adjust rules) |
| DNC-5 | Learned model | Constraint checker | Transactional | Metric comparison | Learned (predict outcomes) |
| DNC-6 | Learned + consolidation | Constraint checker | Transactional | Metric comparison | Learned + consolidated patterns |

**The architecture supports all levels.** The roles are defined; the implementations vary by capability level.

---

## 7. Interface Specifications

### 7.1 Computational Generator Interface

```python
class ComputationalGenerator(ABC):
    @abstractmethod
    def propose(
        self,
        sigma: SystemState,
        task: TaskDescription,
        constraints: Set[Constraint],
        history: MutationHistory,
    ) -> MutationProposal:
        """Propose a structural mutation."""
        ...
```

### 7.2 Structural Controller Interface

```python
class StructuralController(ABC):
    @abstractmethod
    def evaluate(
        self,
        proposal: MutationProposal,
        sigma: SystemState,
        constraints: Set[Constraint],
    ) -> AuthorizationDecision:
        """Evaluate and authorize/reject/modify a proposal."""
        ...
```

### 7.3 Mutation Engine Interface

```python
class MutationEngine(ABC):
    @abstractmethod
    def apply(
        self,
        proposal: MutationProposal,
        sigma: SystemState,
    ) -> MutationResult:
        """Apply a mutation transactionally."""
        ...
```

### 7.4 Assessment Interface

```python
class Assessment(ABC):
    @abstractmethod
    def assess(
        self,
        outcome: ExecutionOutcome,
        proposal: MutationProposal,
        sigma_before: SystemState,
        sigma_after: SystemState,
    ) -> AssessmentReport:
        """Assess the outcome of a mutation."""
        ...
```

### 7.5 Learning System Interface

```python
class LearningSystem(ABC):
    @abstractmethod
    def update(
        self,
        report: AssessmentReport,
        history: MutationHistory,
    ) -> LearningUpdate:
        """Update learning state based on assessment.
        
        This updates the Adaptation Domain (policies, optimizers).
        The Computational Generator reads this knowledge when proposing mutations.
        The Learning System does NOT produce MutationProposals directly.
        """
        ...
```

**Note**: The Learning System has no `propose()` method. Proposals come exclusively from the Computational Generator. The Generator may use knowledge from the Learning System's policies when making proposals, but the Learning System itself never bypasses the Controller or Engine.

---

## 8. Relationship to DNC v1.x

The current DNC v1.x system has:

- `DecisionPolicy` → Maps to **Computational Generator** (for execution decisions, not structural mutations)
- `Runtime.act()` → Maps to **Mutation Engine** (for execution actions, not structural mutations)
- `Runtime._assess_and_record()` → Maps to **Assessment**

**DNC v2.x extends**:
- `DecisionPolicy` gains structural decision variants → **Computational Generator**
- New `StructuralController` role → Authorization
- New `MutationEngine` role → Transactional structural mutation
- `Runtime.act()` gains mutation branches → Delegates to Mutation Engine
- Assessment gains structural outcomes → **Assessment**

---

## 9. Safety Properties

The separation of roles enables safety guarantees:

1. **No unauthorized mutations**: The Structural Controller must approve every mutation. No component can mutate the graph unilaterally.

2. **No partial mutations**: The Mutation Engine applies mutations atomically. No partial state is visible to execution.

3. **No silent failures**: Every mutation is checkpointed. If a mutation fails, the system rolls back to the last consistent state.

4. **No unchecked mutations**: The Structural Controller validates invariants before the Mutation Engine applies the mutation. Invariant violations are caught before they occur.

5. **No unobserved mutations**: Every mutation is recorded in provenance. Every outcome is assessed. No mutation is invisible.

---

## 10. Open Questions

1. **Generator autonomy**: Can the generator propose mutations without being asked? Or does it only propose when triggered?

2. **Controller speed**: The controller must evaluate proposals quickly. How complex can the authorization checks be?

3. **Nested mutations**: Can a mutation proposal contain sub-proposals? Can the controller approve some and reject others?

4. **Concurrent mutations**: Can multiple mutations be proposed simultaneously? How are conflicts resolved?

5. **Learning integration**: At what point does the Learning System feed back into the Generator? After every assessment? After a batch of assessments?

These are design decisions that can be resolved during implementation. The role definitions above are sufficient to proceed to Q5.

---

## 11. Summary

| Property | Value |
|----------|-------|
| Core principle | Proposal ≠ Authorization ≠ Application ≠ Execution |
| Roles | Generator, Controller, Engine, Execution Core, Assessment, Learning |
| Pipeline | Generate → Authorize → Apply → Execute → Assess → Learn |
| Safety | No unauthorized, partial, silent, unchecked, or unobserved mutations |
| Capability levels | Same architecture; different implementations per level |
| v1.x mapping | DecisionPolicy → Generator; act() → Engine; assess → Assessment |
