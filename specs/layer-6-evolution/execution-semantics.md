# Execution Semantics

## Metadata

| Field | Value |
|---|---|
| Document | execution-semantics.md |
| Title | Execution Semantics |
| Document ID | SPEC-EXEC-SEM |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | What does DNC specify about execution, and what does it explicitly not specify? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md |
| Defines | EXECUTION SEMANTICS, REASONING SEMANTICS, execution model, capability interface |
| Referenced by | architecture.md, interfaces.md, evaluation-framework.md |

---

## Section 1 — Introduction

### 1.A Purpose

This document establishes the formal execution semantics of DNC — what DNC governs, what it manages, and what it deliberately leaves to the components it orchestrates.

The central thesis of DNC is that **execution semantics** (how computation is organized, scheduled, observed, verified, replayed, and evaluated) are distinct from **reasoning semantics** (how a component reaches its outputs internally). DNC governs the former; it is agnostic to the latter.

### 1.B Scope

DNC specifies execution semantics for adaptive AI computation. This means DNC formally defines:

- How execution graphs are synthesized and modified at runtime
- How computation is scheduled and dispatched
- How execution state is observed, checkpointed, and recovered
- How execution is verified and measured
- How execution traces are recorded and replayed
- How computation resources are accounted for

DNC does NOT specify:

- How an LLM generates text (reasoning semantics)
- How a retriever ranks documents (reasoning semantics)
- How a solver finds solutions (reasoning semantics)
- How a model is trained (learning semantics)
- The internal algorithms of any component

### 1.C The Core Distinction

The following analogy clarifies the execution/reasoning distinction:

> DNC is to AI computation what an operating system is to processes.

An OS governs:
- Process scheduling
- Memory allocation and protection
- System calls and device I/O
- Error handling and recovery
- Resource accounting

An OS does NOT govern:
- What a word processor does with CPU cycles
- What algorithm a compiler uses
- How a database indexes records

Similarly, DNC governs:
- Execution graph synthesis (planning)
- Module scheduling and dispatch
- State checkpoint and recovery
- Resource accounting and adaptation
- Trace recording and replay

DNC does NOT govern:
- The internal computation of LLMs
- The ranking algorithm of a retriever
- The solving strategy of a symbolic solver
- The architecture of any model

The reason for this distinction is stability. Reasoning paradigms (chain-of-thought, tree-of-thought, program synthesis, future approaches not yet invented) will evolve. DNC's execution semantics remain stable because they govern the orchestration layer, not the implementation layer.

---

## Section 2 — Execution Semantics (What DNC Specifies)

### 2.A Execution Model

DNC's execution model is:

```
Observation → DecisionPolicy → Planner → ExecutionGraph → ModuleSelector → Scheduler → [ExecutionProviders] → Output
                                                                                     ↓
                                                                               WorkingMemory
                                                                                     ↓
                                                                               Checkpointing
                                                                                     ↓
                                                                               ProvenanceLog
```

**Observations** arrive from the environment or from internal monitoring. They are the inputs to the control loop.

**DecisionPolicy** selects an action (CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK) based on the observation and current execution state.

**Planner** is invoked when DecisionPolicy selects REPLAN. The planner synthesizes a new execution graph (G_new) from the task description and available modules.

**ModuleSelector** selects which module instances will participate in G_new.

**Scheduler** dispatchs module instances in topological order, respecting preconditions (all input buffers COMPLETE before dispatch).

**ExecutionProviders** (LLM, retrieval, tool, simulation, etc.) implement the actual computation for each module instance.

**WorkingMemory** holds the input-output state of all module instances.

**Checkpointing** preserves execution state at defined points for recovery.

**ProvenanceLog** records all events, decisions, and state mutations for traceability.

### 2.B Execution State

The execution state ES(t) at step index t is the tuple ES(t) = (W(t), M(t), C(t), H(t), R(t)), where:

- W(t): Working memory — mapping from ModuleInstanceID to Buffer
- M(t): Module registry snapshot — available module types and their contracts
- C(t): Checkpoint record — ordered list of checkpoints
- H(t): History log — append-only record of state mutations
- R(t): Random state — RNG seed and state for deterministic replay

### 2.C Control Loop

The control loop executes continuously:

```
ControlLoop(t):
    O ← Observe(t)                        // collect signals
    D ← DecisionPolicy.decide(O, ES(t))   // select action
    if D == REPLAN:
        G_new ← Planner.plan(task, ES(t))
        ES ← StateMigration(ES, G_new)
    if D == CONTINUE:
        dispatched ← Scheduler.dispatch_runnable(ES.W)
        ES ← Assess(dispatched, ES)
    if D == ROLLBACK:
        ck ← SelectCheckpoint(ES.C)
        ES ← Restore(ck)
    t ← t + 1
```

### 2.D Execution Semantics Invariants

**INV-EXEC-1:** The control loop MUST execute the Observe → Decide → Act → Assess sequence at each step.

**INV-EXEC-2:** The DecisionPolicy MUST be invoked at every Decide phase.

**INV-EXEC-3:** The Planner MUST be invoked only when DecisionPolicy returns REPLAN.

**INV-EXEC-4:** The Scheduler MUST dispatch module instances only when all upstream input buffers are COMPLETE.

**INV-EXEC-5:** The execution trace MUST record every control loop iteration, decision, dispatch, and state mutation.

**INV-EXEC-6:** Checkpoints MUST be taken before every REPLAN action.

**INV-EXEC-7:** Rollback MUST restore ES(t) to exactly the state recorded at the selected checkpoint.

---

## Section 3 — Reasoning Semantics (What DNC Does Not Specify)

### 3.A Definition

**Reasoning semantics** are the formal specifications governing how a component — an LLM, a retriever, a solver, a model — reaches its outputs internally.

Reasoning semantics include:
- The internal computation steps of a language model
- The ranking algorithm of a retrieval system
- The search strategy of a SAT solver
- The optimization method of a mathematical solver
- Chain-of-thought prompting strategies
- Tree-of-thought expansion rules
- Program-of-thought synthesis methods
- Any future reasoning paradigm

### 3.B Why DNC Does Not Specify Reasoning Semantics

There are three reasons DNC remains agnostic to reasoning semantics:

**Stability:** Reasoning paradigms evolve rapidly. Chain-of-thought, tree-of-thought, and graph-of-thought have emerged in the past three years. Specifying reasoning semantics today would freeze the architecture to today's paradigms.

**Generality:** If DNC specified how LLMs generate text, it would become an LLM-specific framework. By remaining agnostic to reasoning semantics, DNC can orchestrate LLMs, vision models, retrieval systems, symbolic solvers, and future components using a single execution model.

**Separation of concerns:** DNC is responsible for organizing computation. The components DNC orchestrates are responsible for performing computation. These are different responsibilities that should not be混在一起 (mixed together).

### 3.C Implications

Because DNC does not specify reasoning semantics:

- **Providers may use any reasoning algorithm** — The same execution provider interface may wrap a CoT-enabled LLM, a tree-of-thought reasoner, or a symbolic solver. DNC does not prefer any of these.
- **Execution graphs are reasoning-agnostic** — A DNC execution graph may contain a reasoning module that uses CoT today and a different reasoning module that uses a future paradigm tomorrow. The graph structure is the same.
- **Evaluation measures execution, not reasoning** — Computation-aware evaluation (see `evaluation-framework.md`) measures how the execution runtime allocates computation. It does not evaluate the internal quality of reasoning steps within a component.
- **The execution trace is complete** — Because all computation within DNC is traceable, the full execution history is available for analysis. What happens inside a component is not DNC's concern, provided the component's interface contract is satisfied.

---

## Section 4 — The Execution/Reasoning Interface

### 4.A Provider Contract

The interface between DNC execution semantics and reasoning semantics is the **provider contract**:

```
ExecutionProvider
    execute(capability: ExecutionCapability, input: Any, config: Dict) → output: Any
    supports(capability: ExecutionCapability) → bool
    metadata: ProviderMetadata
```

DNC's scheduler dispatches module instances. The module instance calls `provider.execute()`. What happens inside `execute()` is the provider's responsibility — this is where reasoning semantics live, and DNC is agnostic to them.

### 4.B Capability as the Bridge

The bridge between execution semantics and reasoning semantics is the **ExecutionCapability**:

- DNC's execution graph is built from capabilities (CAP-REASONING, CAP-RETRIEVAL, CAP-VERIFICATION, etc.)
- The execution provider declares which capabilities it implements
- The scheduler binds capability nodes to provider implementations at runtime
- The reasoning algorithm used to fulfill a capability is the provider's choice

Example:
- An execution graph requests CAP-REASONING for a task decomposition node
- Provider A (OpenAI) implements CAP-REASONING using chain-of-thought
- Provider B (Anthropic) implements CAP-REASONING using constitutional AI
- DNC is agnostic to which reasoning strategy is used; it only knows the capability and the interface contract

---

## Section 5 — Conformance Clause

An implementation conforms to this specification if:

- **INV-EXEC-1 through INV-EXEC-7 are enforced** at runtime or verified by static analysis
- The execution model in Section 2.A is implemented as specified
- The control loop in Section 2.C is implemented as specified
- The provider contract in Section 4.A is implemented by all execution providers
- Reasoning semantics are explicitly declared out of scope — no implementation SHALL specify internal reasoning algorithms as part of the DNC runtime specification

Extensions are permitted only under `conformance-model.md` Section 3 (Extension Rules).

---

## Section 6 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| EXEC-SEM-AMEND-001 | execution-semantics.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of execution semantics vs reasoning semantics, execution model, control loop, provider contract. Establishes the fundamental architectural distinction for Phase 5. | No |