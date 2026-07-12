# Architecture

## Metadata

| Field | Value |
|---|---|
| Document | architecture.md |
| Title | DNC Runtime Architecture |
| Document ID | SPEC-ARCH |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | What are the major components and their relationships? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md |
| Defines | ControlLoop, DecisionPolicy, Planner, ModuleSelector, Scheduler, ExecutionProvider layering |
| Referenced by | interfaces.md, execution-trace-format.md, replay-semantics.md |

---

## Section 1 — Overview

### 1.A Architecture Identity

DNC's architecture is that of an **execution runtime**, not an agent framework, orchestrator, or LLM wrapper. The LLM is one execution primitive among many.

The architecture is organized around a clear separation between:
- **Control** — deciding what to do (DecisionPolicy)
- **Planning** — synthesizing how to do it (Planner, ModuleSelector)
- **Execution** — doing it (Scheduler, ExecutionProvider)
- **Observability** — recording what was done (ExecutionTrace, ProvenanceLog)
- **Evaluation** — measuring how well it was done (Computation-Aware Evaluation)

### 1.B Component Hierarchy

The following diagram shows the architectural layering:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Control Loop                             │
│              Observe → DecisionPolicy → Act → Assess              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    DecisionPolicy     │
                    │ CONTINUE / REPLAN /   │
                    │ PAUSE / TERMINATE /   │
                    │ ROLLBACK              │
                    └───────────────────────┘
                                │
                                ▼ (REPLAN only)
                    ┌───────────────────────┐
                    │       Planner        │
                    │ (synthesizes G_new)   │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   ModuleSelector      │
                    │ (selects candidates)  │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   ExecutionGraph      │
                    │   G = (V, E, w)      │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │     Scheduler         │
                    │ (topological dispatch)│
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  ExecutionProvider    │
                    │ (LLM / Retrieval /    │
                    │  Tool / Symbolic)     │
                    └───────────────────────┘
```

---

## Section 2 — Component Responsibilities

### 2.A Control Loop

**Responsibility:** Execute theObserve → DecisionPolicy → Act → Assess cycle continuously while the runtime is in RUNNING state.

The control loop is the outermost orchestration layer. It does not perform computation itself; it directs other components.

**Key properties:**
- The control loop is the only component that calls DecisionPolicy
- The control loop owns the decision to terminate, pause, or continue
- The control loop enforces latency budgets (OBSERVE_BUDGET, DECIDE_BUDGET, ACT_BUDGET, LOOP_BUDGET)

### 2.B DecisionPolicy

**Responsibility:** Select the next action (CONTINUE, REPLAN, PAUSE, TERMINATE, ROLLBACK) based on the current observation and execution state.

**Key properties:**
- DecisionPolicy is a **service invoked by** the control loop. It is NOT a replacement for the planner.
- DecisionPolicy receives the output of Observe(t) and the current ES(t)
- DecisionPolicy returns one of five actions
- The specific logic of how decisions are made is encapsulated in the policy implementation
- Multiple policy implementations may coexist (RulePolicy, LLMPolicy, RLPolicy)

**Interface (per decision-policy.md):**
```
DecisionPolicy
    decide(observation: Observation, es: ExecutionState) → Decision
    can_replan() → bool
    version: str
```

### 2.C Planner (Service)

**Responsibility:** Synthesize or modify an execution graph G in response to a REPLAN decision.

**Key properties:**
- The planner is a **service invoked by** the control loop when DecisionPolicy returns REPLAN
- The planner is NOT a DecisionPolicy implementation — it does not decide when to replan; it performs the replanning when asked
- The planner produces an ExecutionGraph G_new from a task description, available modules, and constraints
- Multiple planner implementations may coexist (rule-based, learned, RL-trained)

**Interface (per planner-pipeline.md):**
```
Planner
    plan(task: PlanningTask) → PlanningResult
    compute_graph_diff(g_old, g_new, es) → (RETAINED, RETIRED_EARLY, NEW)
    version: str
```

### 2.D ModuleSelector

**Responsibility:** Select which module instances (candidates) will participate in the execution graph for each sub-goal.

**Key properties:**
- ModuleSelector operates within the Planner's Graph Construction phase
- ModuleSelector is invoked by the Planner, not by the control loop
- ModuleSelector matches sub-goals to available module contracts based on capability requirements and resource constraints
- ModuleSelector is NOT a DecisionPolicy — it does not decide whether to continue or replan; it decides which modules go into the graph

### 2.E Scheduler

**Responsibility:** Dispatch module instances in topological order, respecting preconditions and DAG invariants.

**Key properties:**
- Scheduler receives a complete ExecutionGraph G from the Planner
- Scheduler dispatches nodes only when all upstream input buffers are COMPLETE (INV-EXEC-4)
- Scheduler enforces DAG invariants (INV-2: no cycles, INV-3: preconditions)
- Scheduler is invoked by the control loop during the Act phase
- Scheduler binds module instances to ExecutionProviders at dispatch time

### 2.F ExecutionProvider

**Responsibility:** Implement the actual computation for a module instance. The ExecutionProvider is the interface to external computational resources.

**Key properties:**
- An ExecutionProvider implements one or more ExecutionCapabilities
- The scheduler dispatches to a module instance; the module instance delegates to its bound ExecutionProvider
- ExecutionProviders are swappable — the same module interface may bind to OpenAI, Anthropic, Ollama, vLLM, or any conformant provider
- ExecutionProviders are the layer at which reasoning semantics live (see `execution-semantics.md` Section 3)

---

## Section 3 — Data Flow

### 3.A Normal Execution Path

```
1. Input arrives at Observe phase
2. DecisionPolicy.decide() → CONTINUE
3. Scheduler dispatches runnable module instances
4. Each module instance calls its bound ExecutionProvider.execute()
5. Provider returns output → module output buffer updated
6. Scheduler advances to next ready nodes
7. Assess phase evaluates outcomes
8. Repeat from step 1
```

### 3.B Replan Path

```
1. DecisionPolicy.decide() → REPLAN
2. Checkpoint taken (INV-EXEC-6)
3. Planner.plan() → ExecutionGraph G_new
4. compute_graph_diff(G_old, G_new) → RETAINED, RETIRED_EARLY, NEW
5. State migration: RETAINED state preserved, RETIRED_EARLY archived, NEW initialized
6. Scheduler updated with new graph
7. Continue with step 3.A using new graph
```

### 3.C Rollback Path

```
1. DecisionPolicy.decide() → ROLLBACK
2. Checkpoint selected (most recent valid)
3. Restore(ES, checkpoint) → ES(t) reverted to checkpoint state
4. Continue with step 3.A from restored state
```

---

## Section 4 — Design Principles

### 4.A Single Responsibility

Each component has one primary responsibility:
- DecisionPolicy: choose action
- Planner: synthesize graphs
- ModuleSelector: select candidates
- Scheduler: dispatch in order
- ExecutionProvider: perform computation

No component encroaches on another's responsibility.

### 4.B Policy/Service Separation

The planner is a service invoked by DecisionPolicy. DecisionPolicy is never a planner. This separation is fundamental:

```
DecisionPolicy.decide() → "REPLAN"
       ↓
Planner.plan() → G_new
```

The decision to replan and the act of replanning are separate.

### 4.C Provider Independence

ExecutionProviders implement capabilities. The scheduler does not know or care which provider implements a capability. This enables:

- Provider swapping without graph changes
- Multi-provider graphs (OpenAI for reasoning, FAISS for retrieval, Z3 for verification)
- Future providers without architecture changes

### 4.D Deterministic Observability

All computation paths pass through the trace interface. The ExecutionTrace is the complete record of what happened, enabling deterministic replay and computation-aware evaluation.

---

## Section 5 — Conformance Clause

An implementation conforms to this specification if:

- The component hierarchy in Section 1.B is implemented as specified
- DecisionPolicy is invoked only from the control loop's Decide phase
- Planner is invoked only when DecisionPolicy returns REPLAN
- ModuleSelector operates within the Planner's execution only
- Scheduler dispatches only when preconditions are met (INV-EXEC-4)
- ExecutionProviders are bound at dispatch time, not at graph construction time
- The data flows in Section 3 are implemented as specified

Extensions are permitted only under `conformance-model.md` Section 3.

---

## Section 6 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| ARCH-AMEND-001 | architecture.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of DNC runtime architecture, component hierarchy, responsibilities, data flows, and design principles. Establishes DecisionPolicy/Planner/Scheduler/ExecutionProvider layering. | No |