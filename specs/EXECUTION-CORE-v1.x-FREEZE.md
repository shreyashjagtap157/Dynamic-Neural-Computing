# DNC Execution Core v1.x — Boundary Freeze

**Date**: 2026-07-22  
**Status**: FROZEN — architectural boundary, not implementation lock  
**Scope**: What DNC v1.x *is*; what DNC v2.x *adds*

---

## 1. Definition

**DNC Execution Core v1.x** is the stable execution substrate responsible for:

- Observing execution state
- Making execution decisions (which computation unit to execute next)
- Executing computational units
- Maintaining execution state (WorkingMemory, History, Checkpoints)
- Enforcing structural and runtime invariants (INV-1–9)
- Managing checkpoints and rollback
- Scheduling DAG computation (Kahn's algorithm)
- Recording provenance (append-only, tamper-evident)
- Replaying execution traces
- Interfacing with execution providers (LLM, rule-based, RL)

The Execution Core is **not** responsible for:

- Defining what computation should exist
- Mutating computational structure at runtime
- Learning to modify its own graph
- Consolidating recurring patterns into reusable units
- Generating computation proposals

Those responsibilities belong to **DNC v2.x layers**.

---

## 2. Architectural Boundary

```
                         DNC v2.x
                  Dynamic Computation Layer
                   (proposes, mutates, learns)
                             │
                             │ DNC-IR / mutation directives
                             ▼
                 ┌────────────────────────────┐
                 │    DNC EXECUTION CORE      │
                 │         v1.x               │
                 │                            │
                 │  ┌──────────────────────┐  │
                 │  │ Observe              │  │
                 │  │ Decide               │  │
                 │  │ Act                  │  │
                 │  │ Assess               │  │
                 │  └──────────────────────┘  │
                 │                            │
                 │  ┌──────────────────────┐  │
                 │  │ State (ES(t))        │  │
                 │  │ Scheduler            │  │
                 │  │ Invariants (INV-1–9) │  │
                 │  │ Checkpoint/Rollback  │  │
                 │  │ Replay               │  │
                 │  │ Provenance           │  │
                 │  │ Cost                 │  │
                 │  │ Providers            │  │
                 │  └──────────────────────┘  │
                 └───────────┬────────────────┘
                             │
                             ▼
                      LLM / Tool / External
                         Execution
```

**Upward interface (to v2.x)**:
- Accepts mutation directives (add/remove/reconnect nodes)
- Exposes state for structural analysis
- Provides execution feedback for structural learning
- Supports checkpoint/rollback across mutations

**Downward interface (to providers)**:
- Sends ModuleTypeID, input data, context
- Receives output data, token counts, latency
- Provider-specific; orthogonal to graph structure

---

## 3. Source File Inventory

### KEEP (frozen infrastructure)

| File | Role | Status |
|------|------|--------|
| `runtime/runtime.py` | Runtime, ControlLoop, execution heartbeat | Frozen |
| `runtime/types.py` | UNBOUND, PENDING, Buffer, ModuleTypeID, ModuleInstanceID, ModuleContract | Frozen |
| `state/execution_state.py` | ES(t) = (W, M, G, C, H, R) | Frozen |
| `state/working_memory.py` | WorkingMemory, HistoryLog | Frozen |
| `state/checkpoint.py` | Checkpoint, CheckpointRecord | Frozen |
| `state/registry.py` | ModuleRegistry (INV-4) | Frozen |
| `scheduler/scheduler.py` | Kahn's topological sort | Frozen |
| `cost/semantics.py` | CostBudget, CostForecaster | Frozen |
| `invariants/runtime_invariants.py` | RuntimeInvariantSet INV-1–7 | Frozen |
| `invariants/verifier.py` | BootstrapVerifier INV-8 | Frozen |
| `execution/execution_provider.py` | ExecutionProvider ABC, ExecutionCapability | Frozen |
| `execution/execution_trace.py` | ExecutionTrace | Frozen |
| `execution/replay_engine.py` | ReplayEngine, ReplayVerifier | Frozen |
| `execution/decision_policy.py` | DecisionPolicy ABC, RulePolicy | Frozen |
| `execution/llm_policy.py` | LLMPolicy, RLPolicy | Frozen |
| `observability/provenance.py` | ProvenanceLog | Frozen |
| `observability/failure.py` | FailureClassifier | Frozen |
| `modules/base.py` | BaseModule ABC | Frozen |
| `modules/standard.py` | Source, Transform, Aggregate, Sink | Frozen |
| `distributed/protocol.py` | DistributedCoordinator | Frozen |
| `providers/*.py` | OpenAI, Anthropic, Ollama, Gemini, vLLM | Frozen |

### EXTEND (v1.x interface, v2.x implementation)

| File | Extension | Why |
|------|-----------|-----|
| `state/execution_state.py` | Add structural/learning/memory state domains | Structural state must be part of system state — *representation TBD* |
| `state/working_memory.py` | Dynamic register/deregister of nodes | v2.x may add/remove computational units |
| `runtime/runtime.py` | New Decision types, new act() branches | v2.x introduces mutation/consolidate/specialize decisions |
| `scheduler/scheduler.py` | mutate_graph() | v2.x needs to mutate DAG between steps |
| `execution/decision_policy.py` | Structural decision variants | v2.x proposes structural mutations |
| `execution/execution_trace.py` | Structural mutation records | v2.x traces must capture what changed structurally |
| `execution/replay_engine.py` | Structural mutation replay | Rebuild for structural replay |
| `cost/semantics.py` | Structural mutation costs | v2.x mutations have computational cost |
| `observability/provenance.py` | New event types | v2.x structural events need provenance |
| `observability/failure.py` | New failure signals | v2.x structural failures need classification |
| `modules/base.py` | Structural metadata on ModuleContract | v2.x needs to know module capabilities |

### MOVE TO RESEARCH LAYER (DNC v2.x)

| File | Destination | Reason |
|------|-------------|--------|
| `planner/pipeline.py` | DNC-IR Computation Generator | Planner internals are not core execution |
| `planner/dag_planner.py` | DNC-IR Computation Generator | Same |
| `learning/continual.py` | DNC v2.x Structural Learning | Not execution; adaptation |
| `evaluation/computation_aware.py` | DNC v2.x Evaluation | Evaluation, not execution |
| `observability/evaluation.py` | DNC v2.x Evaluation | Same |
| `observability/bias_evaluation.py` | Pluggable fairness module | Domain-specific |

### DEPRECATE / REPLACE

| File | Replacement | Reason |
|------|-------------|--------|
| `planner/graph_builder.py` | DNC-IR Computation Generator | Internal to planner |
| `planner/dag_builder.py` | DNC-IR Computation Generator | Internal to planner |
| `planner/module_selector.py` | DNC-IR Computation Generator | Internal to planner |
| `planner/task_analyzer.py` | DNC-IR Computation Generator | Internal to planner |
| `planner/graph_validator.py` | DNC-IR Computation Generator | Internal to planner |
| `planner/replan_context.py` | DNC-IR Computation Generator | Internal to planner |

---

## 4. Architectural Invariants (Preserved Unless Explicitly Superseded)

These invariants are now part of the **DNC v2.x architectural contract**:

| # | Invariant | Status |
|---|-----------|--------|
| 1 | ES(t) is authoritative system state | Preserved — representation TBD |
| 2 | Observe → Decide → Act → Assess is the execution heartbeat | Preserved |
| 3 | Graph is always a DAG (no cycles) | Preserved |
| 4 | Module preconditions/enabling conditions enforced | Preserved |
| 5 | Checkpoint captures full system state; rollback restores it | Preserved — scope TBD |
| 6 | History is append-only; never mutated | Preserved |
| 7 | Module registry owns module-type namespace; no duplicate types | Preserved |
| 8 | Provenance is append-only with tamper-evident hash chain | Preserved |
| 9 | Provider abstraction is orthogonal to graph structure | Preserved |
| 10 | WorkingMemory keys correspond 1:1 with executable graph nodes | Preserved — may extend |

---

## 5. What This Freeze Does NOT Establish

- The exact decomposition of ES(t) — whether (W, M, G, C, H, R, S, L, Mem) or a structured object or nested domains
- Whether structural state, learning state, and memory state are independent domains or components of one unified transition system
- The specific representation of DNC-IR
- The mutation semantics or transaction model
- The learning model or what DNC learns
- The consolidation or specialization mechanisms
- The evaluation framework

These are determined by the **five fundamental questions** and the theoretical specification that follows.

---

## 6. Transition

The Execution Core boundary is now frozen.

The next phase is theoretical definition:

```
Q1: What exactly is DNC?
Q2: What is the computational substrate?
Q3: Is the dynamic graph part of state?
Q4: Who can mutate computation?
Q5: What exactly does DNC learn?
```

From these five answers, the complete DNC v2.x theoretical specification set is derived.
