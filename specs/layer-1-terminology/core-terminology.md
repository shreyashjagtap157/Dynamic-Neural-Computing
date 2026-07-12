# Core Terminology

## Metadata

| Field | Value |
|---|---|
| Document | core-terminology.md |
| Title | Core Terminology |
| Document ID | SPEC-TERM |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 1 |
| Owner Question | What does every term mean? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Introduction

This document is the single authoritative source for all terminology used in DNC specification documents. Per PR-1 and PR-2, every significant term MUST appear here before its first use in any other document, and no term MAY be redefined in any downstream document.

The layer ordering (Layer 1 before all others) ensures that the vocabulary is stable before it is referenced. This document has no normative dependencies on any other specification document, per PR-4.

Terms are organized into nine concept classes. Within each class, terms are ordered alphabetically. Each entry contains: the term itself, its definition in RFC 2119-neutral language, any aliases or deprecated synonyms, and references to the owning document if the term is further constrained there.

---

## Section 2 — Governance Terms

### ACTIVE-INVARIANT

**Definition:** An invariant statement (INV-*) from `../layer-2-invariants/runtime-invariants.md` that is currently enforced by the runtime. The set of active invariants defines the behavioral envelope per DEF-CL-1 in `../layer-6-evolution/continual-learning.md`.

**Note:** Invariants transition from draft to active when their containing document reaches Frozen state.

### BREAKING-REVISION

**Definition:** A specification revision that modifies an existing Invariant or introduces a new Invariant in a way that is not backward-compatible. Breaking revisions are declared explicitly and require acceptance by explicit review ballot per PR-8.

### DOCUMENT-STATE

**Definition:** The lifecycle status of a specification document. The complete state machine is: Draft → Review → Frozen → Amended → Superseded → Archived, defined in `../../registry.md`.

### LAYER

**Definition:** A numbered tier in the document dependency graph, where higher layers may reference lower layers but not vice versa. Layer 0 is governance; Layer 6 is evolution. The full layer structure is defined in Section 3 of `../layer-0-foundation/specification-foundation.md`.

### OWNING-DOCUMENT

**Definition:** The single specification document that has authoritative control over a concept's definition. No concept SHALL be defined in more than one document per PR-1.

### SPECIFICATION-VERSION

**Definition:** The version identifier of the specification governing a given execution. Format is either Draft DR-\<n\> (for Draft state) or Baseline v\<n\> (+AMEND-\<nnn\> if amended), per the Version Definitions in `../../registry.md`.

---

## Section 3 — Execution Terms

### ASSESSMENT

**Definition:** The runtime's evaluation of whether the actions taken in a control loop iteration produced the intended outcome, producing one of OUTCOME_MET, OUTCOME_DEGRADED, or OUTCOME_FAILED. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-5.

### ACT

**Definition:** The phase of the control loop in which the runtime executes the action prescribed by the decision D(i), either continuing the current execution graph, initiating a replan, or transitioning to idle or terminated state. Defined in `../layer-3-execution/control-loop.md` Section 2.C.

### CHECKPOINT

**Definition:** A point-in-time snapshot of the execution state ES(t) that is preserved for recovery. A checkpoint is valid if and only if it is complete, has a resolvable provenance reference, and has a unique step index. Defined in `../layer-3-execution/state-management.md` DEF-3.

### CONTROL-LOOP

**Definition:** The repeating four-phase operational pattern Observe → Decide → Act → Assess that a dynamic thinker executes continuously while in the RUNNING state. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-1.

### DECIDE

**Definition:** The phase of the control loop in which the runtime selects an action (CONTINUE, REPLAN, IDLE, or TERMINATE) based on the observation O(i) and the current execution state ES(i). Defined in `../layer-3-execution/control-loop.md` Section 2.B.

### EXECUTION

**Definition:** A single invocation of the DNC runtime, identified by an ExecutionID, governed by an immutable specification version tuple, and consisting of one or more steps dispatched by the scheduler. An execution is either RUNNING, IDLE, TERMINATED, or FAILED.

### EXECUTION-GRAPH

**Definition:** A directed acyclic graph G = (V, E, w) where V is the set of module instances, E is the set of data-dependency edges, and w assigns a cost weight to each node and edge. Produced by the planner. Defined in `../layer-4-mechanisms/planner-pipeline.md`.

**Neural-Circuit Analogy:** The structure G = (V, E, w) parallels a neural circuit: V (module instances) analogous to neurons, E (data-dependency edges) analogous to synaptic connections, w (cost weights) analogous to connection strength, and the topological ordering analogous to activation flow. This is a structural analogy only. See EXECUTION-GRAPH-AS-NEURAL-CIRCUIT in Section 11.

### EXECUTION-STATE

**Definition:** The tuple ES(t) = (W(t), M(t), C(t), H(t)) representing the complete runtime state at step index t: working memory, module registry snapshot, checkpoint record, and history log. Defined in `../layer-3-execution/state-management.md` DEF-1.

### OBSERVE

**Definition:** The phase of the control loop that collects all input signals that have arrived since the last loop iteration, producing the observation O(i). Defined in `../layer-3-execution/control-loop.md` Section 2.A.

### STEP

**Definition:** A single atomic unit of execution dispatch by the scheduler. A step executes one module instance and produces one output buffer update in working memory. Steps are totally ordered within an execution graph by the topological sort of G.

### WORKING-MEMORY

**Definition:** The mapping W(t): ModuleInstanceID → Buffer that holds the current input-output state of every registered module instance. Part of ES(t). Defined in `../layer-3-execution/state-management.md` DEF-2.

---

## Section 4 — Planning Terms

### CONTINUE

**Definition:** A decision D(i) = CONTINUE, meaning the runtime will proceed with the current execution graph without modification. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-3.

### DECISION

**Definition:** The runtime's choice of action in response to an observation, D(i) ∈ {CONTINUE, REPLAN, IDLE, TERMINATE}. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-3.

### GRAPH-DIFF

**Definition:** The comparison between an old execution graph G_old and a new execution graph G_new, producing three disjoint sets: RETAINED (nodes in both), RETIRED_EARLY (nodes in G_old not completed), and NEW (nodes in G_new). Defined in `../layer-3-execution/replanning-protocol.md` DEF-REPLAN-2.

### IDLE

**Definition:** A decision D(i) = IDLE, meaning the runtime will enter the idle state and await new signals without executing the current plan. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-3.

### NEW-MODULE

**Definition:** A module instance that appears in the new execution graph G_new but not in the prior graph G_old. A new module's state is initialized per `../layer-3-execution/state-management.md` INV-STATE-9.

### OBSERVATION

**Definition:** The set O(i) of all input signals received by the runtime since the last control loop iteration, O(i) = {(signal_type, signal_value, timestamp, source)}. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-2.

### REPLAN

**Definition:** A decision D(i) = REPLAN, meaning the runtime will invoke the planner to produce a new execution graph. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-3.

### REPLAN-TRIGGER

**Definition:** An event that causes the planner to be invoked for a new execution graph. Classified as internal (step deadline, module failure, confidence degradation, resource exhaustion) or external (user directive, environmental change). Defined in `../layer-3-execution/replanning-protocol.md` DEF-REPLAN-1.

### RETAINED-MODULE

**Definition:** A module instance present in both the old execution graph G_old and the new execution graph G_new. Its state W(n) is preserved byte-exact across the replan per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-10.

### RETIRED-MODULE

**Definition:** A module instance present in the old execution graph G_old but not in the new graph G_new. Its final state is archived to the provenance log with MODULE_RETIRED per `../layer-3-execution/state-management.md` INV-STATE-8.

### TERMINATE

**Definition:** A decision D(i) = TERMINATE, meaning the control loop transitions to the TERMINATED state. Defined in `../layer-3-execution/control-loop.md` DEF-CTRL-3.

---

## Section 5 — Module Terms

### BUFFER

**Definition:** The triple (input: Value, output: Value, metadata: Metadata) associated with a module instance in working memory. The output field takes the marker UNBOUND before computation and PENDING during computation. Defined in `../layer-3-execution/state-management.md` DEF-2.

### CONTRACT

**Definition:** The declared interface of a module, consisting of its input signature, output signature, capability annotations, cost parameters, and confidence thresholds. Stored in the module registry. Defined in `../layer-4-mechanisms/module-lifecycle.md`.

### MODULE

**Definition:** A computational unit registered in the module registry, identified by a ModuleTypeID and instantiated with a ModuleInstanceID at runtime. A module implements a defined transformation from input to output.

### MODULE-INSTANCE

**Definition:** A specific invocation of a module at runtime, identified by a unique ModuleInstanceID within an execution. Multiple instances of the same ModuleTypeID may coexist in one execution.

### MODULE-REGISTRY

**Definition:** The runtime's authoritative record of all available module types, their contracts, version information, and registration state. The registry is referenced by M(t) in ES(t). Defined in `../layer-4-mechanisms/module-lifecycle.md`.

### PENDING

**Definition:** The marker assigned to W(t)[A].output when module instance A has received input but has not yet produced output. Defined in `../layer-3-execution/state-management.md` DEF-2.

### REGISTERED-MODULE

**Definition:** A module that has been added to the module registry and is available for instantiation in execution graphs. Opposite: unregistered (removed from registry, unavailable for new instantiations).

### UNBOUND

**Definition:** The marker assigned to W(t)[A].output when module instance A has not yet received input. A module with UNBOUND output cannot be dispatched. Defined in `../layer-3-execution/state-management.md` DEF-2.

---

## Section 6 — State Terms

### CHECKPOINT-BOUNDEDNESS

**Definition:** The invariant that the checkpoint record C(t) does not grow without bound; its size is capped at MAX_CHECKPOINTS. Defined in `../layer-3-execution/state-management.md` INV-STATE-3.

### HISTORY-LOG

**Definition:** The append-only record H(t) of all state mutations since the last checkpoint, H(t) = [H_0, H_1, ..., H_n]. Each entry records the mutation type, target module, before/after values, and trigger provenance reference. Defined in `../layer-3-execution/state-management.md` DEF-6.

### STATE-HANDOFF

**Definition:** The atomic transfer of the output value of module instance A as the input value of module instance B within a single step. Defined in `../layer-3-execution/state-management.md` DEF-4.

### STATE-MIGRATION

**Definition:** The process of transforming W(t) from the pre-replan checkpoint into the initial state for the new plan, preserving state for RETAINED modules, archiving RETIRED modules, and initializing NEW modules. Defined in `../layer-3-execution/state-management.md` DEF-5.

---

## Section 7 — Learning Terms

### BEHAVIORAL-DRIFT

**Definition:** The maximum deviation Δ(i, j) = max_{m ∈ Metrics} |m(i) - m(j)| between two executions i and j over all evaluation metrics. Defined in `../layer-6-evolution/continual-learning.md` DEF-CL-2.

### BEHAVIORAL-ENVELOPE

**Definition:** The region of all execution behaviors that satisfy the conjunction of all active runtime invariants. Defined in `../layer-6-evolution/continual-learning.md` DEF-CL-1.

### BOUNDED-DRIFT

**Definition:** A continual learning update is bounded drift iff for all prior executions p in the history, Δ(p, p') ≤ DRIFT_BOUND and p' satisfies all active invariants. Defined in `../layer-6-evolution/continual-learning.md` DEF-CL-3.

### CATASTROPHIC-FORGETTING

**Definition:** A failure mode of continual learning in which a learning update causes a previously learned capability (measured by a metric in the evaluation suite) to degrade beyond DEGRADATION_TOLERANCE relative to its pre-update baseline. Defined in `../layer-6-evolution/continual-learning.md` INV-CL-7.

### DRIFT-BOUND

**Definition:** The configured maximum allowable behavioral drift DRIFT_BOUND between any prior execution and the updated execution. A learning update that exceeds this bound MUST be rejected. Defined in `../layer-6-evolution/continual-learning.md`.

### KNOWLEDGE-BASE

**Definition:** The runtime's accumulated learned representations, KB = (KB_modules, KB_plans, KB_costs). The KB is versioned immutably per PR-10 and is separate from execution state ES(t). Defined in `../layer-6-evolution/continual-learning.md` DEF-CL-5.

### LEARNING-EVENT

**Definition:** A provenance-tracked record of an experience from which the runtime improves, structured as (event_id, trigger_execution_id, trigger_step, observed_outcome, expected_outcome, delta_quality, is_novel, candidate_update). Defined in `../layer-6-evolution/continual-learning.md` DEF-CL-4.

### NOVELTY-DETECTION

**Definition:** The runtime's ability to identify when a new execution scenario has not been previously observed, as measured by plan-space distance exceeding NOVELTY_THRESHOLD. Defined in `../layer-6-evolution/continual-learning.md` INV-CL-10.

---

## Section 8 — Cost and Resource Terms

### ACT-BUDGET

**Definition:** The maximum wall-clock time in milliseconds that the Act phase of a control loop iteration may consume. Exceeding this budget triggers a replan or logs ACT_BUDGET_EXCEEDED. Defined in `../layer-3-execution/control-loop.md`.

### COST-SEMANTICS

**Definition:** The formal system for assigning and accounting computational resource costs (CPU-cycles, memory, I/O, accelerator-time) to module executions, execution graphs, and the overall runtime. Defined in `../layer-4-mechanisms/cost-semantics.md`.

### DECIDE-BUDGET

**Definition:** The maximum wall-clock time in milliseconds that the Decide phase may consume. Exceeding this budget causes the decision to default to CONTINUE. Defined in `../layer-3-execution/control-loop.md`.

### LOOP-BUDGET

**Definition:** The maximum average wall-clock time for a control loop iteration (Observe through Assess) measured over any sliding window of 10 iterations. Defined in `../layer-3-execution/control-loop.md` INV-CTRL-9.

### OBSERVE-BUDGET

**Definition:** The maximum wall-clock time in milliseconds that the Observe phase may consume. Exceeding this budget causes the iteration to proceed with whatever signals were collected. Defined in `../layer-3-execution/control-loop.md`.

### RESP-BUDGET

**Definition:** The maximum event-response latency T_resp(e) in milliseconds, from event arrival to action commitment. Events that cannot be responded to within this budget require a fallback policy. Defined in `../layer-3-execution/control-loop.md`.

### RESOURCE-EXHAUSTION

**Definition:** The condition in which the cost semantics system forecasts that remaining execution steps will exceed the available resource budget before completion. This triggers a replan per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-4.

---

## Section 9 — Provenance and Failure Terms

### FAILURE-CATASTROPHIC

**Definition:** A failure classification indicating a runtime state from which recovery is not possible and the execution MUST halt immediately. Defined in `../layer-5-observability/failure-taxonomy.md`.

### FAILURE-FATAL

**Definition:** A failure classification indicating a module instance has failed in a way that is unrecoverable within the current execution graph and triggers immediate replanning. Defined in `../layer-5-observability/failure-taxonomy.md`.

### FAILURE-RECOVERABLE

**Definition:** A failure classification indicating a module instance has failed but the failure can be contained, worked around, or retried without triggering a replan. Defined in `../layer-5-observability/failure-taxonomy.md`.

### FAILURE-TRANSIENT

**Definition:** A failure classification indicating a module instance has failed due to a temporary condition that is likely to resolve, permitting retry without a replan. Defined in `../layer-5-observability/failure-taxonomy.md`.

### FAILURE-UNRECOVERABLE

**Definition:** A failure classification indicating the module instance has failed in a way that cannot be retried or worked around, triggering replan. Synonymous in effect with FAILURE_FATAL for scheduler purposes. Defined in `../layer-5-observability/failure-taxonomy.md`.

### PROVENANCE-CHAIN

**Definition:** The unbroken trace of causal connections between decisions, actions, state mutations, and outcomes in an execution, recorded in the provenance log per `../layer-5-observability/provenance-model.md`. PR-9 requires all runtime behavior claims to be backed by a provenance chain.

### PROVENANCE-LOG

**Definition:** The append-only, provenance-traceable record of all significant events in an execution: state mutations, decisions, handoffs, checkpoints, module lifecycle events, and learning events. Defined in `../layer-5-observability/provenance-model.md`.

---

## Section 10 — Evaluation Terms

### BASELINE

**Definition:** A fixed reference execution (or set of executions) against which new executions are compared in the evaluation suite. Baselines are version-locked per PR-10 and MUST NOT be modified after creation. Defined in `../layer-5-observability/evaluation-suite.md`.

### DEGRADATION-TOLERANCE

**Definition:** The maximum percentage by which any evaluation metric may degrade relative to the baseline before a continual learning update is rejected as catastrophic forgetting. Defined in `../layer-5-observability/evaluation-suite.md`.

### EVALUATION-METRIC

**Definition:** A measurable property of an execution (e.g., latency, accuracy, resource efficiency) that is recorded in the evaluation suite. Defined in `../layer-5-observability/evaluation-suite.md`.

### EVALUATION-PROTOCOL

**Definition:** The standardized procedure for running the evaluation suite: inputs, baselines, statistical tests, significance thresholds, and reporting format. Defined in `../layer-5-observability/evaluation-suite.md`.

---

## Section 11 — Neural Computation Terms

### DYNAMIC-NEURAL-COMPUTATION

**Definition:** The field of study concerning computation systems that synthesize and execute dynamically-structured computation graphs — graphs whose topology (node composition, edge connectivity, and execution ordering) is determined at runtime based on task demands, available resources, and environmental context. The term "neural" in this definition refers to the structural analogy with biological neural circuits (dynamic topology, data-driven activation, sparse connectivity) rather than a specific implementation using artificial neurons or connectionist architectures.

**Note:** A DNC runtime is a specific implementation of a dynamic neural computation system. The specification does NOT claim that the runtime simulates biological neurons, implements synaptic plasticity rules, or produces emergent behavior characteristic of connectionist models. It claims only that the execution graph structure — dynamically synthesized, topology-dependent execution ordering, data-dependent routing — parallels the structural properties of neural computation in the sense of dynamic circuit reconfiguration.

### NEURAL-MODULE

**Definition:** A module whose contract annotation includes `computation_type: neural`. Neural modules are dispatched asynchronously — the control loop's Act phase dispatches them and returns immediately without blocking CONTROL_LOOP_BUDGET. Their wall-clock execution time is tracked separately from the control loop budget in cost-semantics.md. See also: EXECUTION-GRAPH-AS-NEURAL-CIRCUIT.

### EXECUTION-GRAPH-AS-NEURAL-CIRCUIT

**Definition:** The structural analogy between a DNC execution graph G=(V,E,w) and a neural circuit: V (module instances) analogous to neurons, E (data-dependency edges) analogous to synaptic connections, w (cost weights) analogous to connection strength, and the topological ordering analogous to activation flow. This is a structural analogy, not an implementation claim.

---

## Section 12 — Cross-Reference Consistency Note

This section acknowledges the findings of the cognitive science review and provides an explicit clarification.

The DNC specification uses the term "neural" in the sense defined above: computation with dynamically-structured graphs that parallels the structural properties of neural circuits. This is a legitimate research framing supported by established literature on dynamic circuit reconfiguration (e.g., work on reconfigurable neural architectures, liquid state machines, and adaptive computation graphs).

The specification explicitly does NOT claim to model:
- Individual neuron biophysics or membrane dynamics
- Synaptic weight update rules (STDP, etc.)
- Spiking neural network topologies
- Emergent computation from distributed simple units

If future research extends DNC to include these properties, Layer 7 (Distributed) or a new layer would be the appropriate location to specify them.

---

## Section 13 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| TERM-AMEND-001 | core-terminology.md | 2026-07-10 | Added Section 11 (Neural Computation Terms): DYNAMIC-NEURAL-COMPUTATION, NEURAL-MODULE, EXECUTION-GRAPH-AS-NEURAL-CIRCUIT definitions. Added Section 12 (Cross-Reference Consistency Note). | No |

## Section 14 — Execution Provider Terms (Phase 5)

### EXECUTION-CAPABILITY

**Definition:** An abstract capability that an execution provider may implement, representing a class of computation that can be invoked within an execution graph. Capabilities are stable across time; they do not change when providers change. Defined in `../layer-6-evolution/execution-provider.md` DEF-CAP-1.

**Aliases:** CAP-* (namespace for specific capability identifiers: CAP-REASONING, CAP-RETRIEVAL, CAP-PLANNING, CAP-VERIFICATION, CAP-SIMULATION, CAP-OPTIMIZATION, CAP-EXECUTION)

**Note:** Capabilities are to execution providers what instruction set architectures (ISA) are to CPUs. The ISA is stable; the microarchitecture implementing it changes. CAP-REASONING remains CAP-REASONING whether implemented by OpenAI, Anthropic, or Ollama.

### EXECUTION-PROVIDER

**Definition:** A concrete implementation of one or more execution capabilities, providing the actual computational machinery for an execution graph node. Execution providers are the runtime's interface to external computational resources (LLMs, databases, solvers, simulators). Defined in `../layer-6-evolution/execution-provider.md` DEF-CAP-3.

**Aliases:** Provider, Backend (deprecated — do not use, carries infrastructure connotations that conflate the abstraction with specific companies)

**Note:** An execution provider may implement multiple capabilities. A reasoning provider may also implement retrieval. A simulation provider may implement both execution and optimization.

### EXECUTION-PROVIDER-INTERFACE

**Definition:** The abstract interface that all execution providers implement, consisting of: `execute(capability, input, config) → output`, `supports(capability) → bool`, and provider metadata (version, latency_estimate, cost_estimate). Defined in `../layer-6-evolution/execution-provider.md` DEF-CAP-2.

### PROVIDER-CONFORMANCE

**Definition:** The property of an execution provider whereby it correctly implements all requirements of its declared capabilities and conforms to the execution-provider interface specification. Provider conformance is verified independently of runtime conformance. Defined in `../layer-6-evolution/conformance-model.md`.

---

## Section 15 — Control and Decision Terms (Phase 5)

### DECISION-POLICY

**Definition:** The component of the runtime that selects the next control loop action (CONTINUE, REPLAN, PAUSE, TERMINATE, or ROLLBACK) based on the current observation and execution state. The DecisionPolicy is invoked at each control loop iteration during the Decide phase. Defined in `../layer-6-evolution/decision-policy.md` DEF-POL-1.

**Note:** DecisionPolicy replaces the fixed decision logic previously embedded in Runtime.decide(). The policy is swappable: a rule-based policy may be replaced by an LLM-driven policy or an RL-trained policy without modifying the control loop or scheduler.

### DECISION-POLICY-INTERFACE

**Definition:** The abstract interface that all decision policies implement, consisting of: `decide(observation, execution_state) → Decision`, `can_replan() → bool`, and `version: str`. Defined in `../layer-6-evolution/decision-policy.md` DEF-POL-2.

### RULE-POLICY

**Definition:** A DecisionPolicy implementation that applies fixed, pre-defined rules (e.g., if resource_forecast < threshold: REPLAN). The rule policy is the reference implementation. Defined in `../layer-6-evolution/decision-policy.md`.

### LLM-POLICY

**Definition:** A DecisionPolicy implementation that uses a language model to select the next action based on the execution context. The LLM receives a structured prompt describing the current state and available actions and returns a decision. Defined in `../layer-6-evolution/decision-policy.md`.

### RL-POLICY

**Definition:** A DecisionPolicy implementation trained via reinforcement learning on execution traces, optimizing for a reward function that balances task completion, resource efficiency, and adaptive computation. Defined in `../layer-6-evolution/decision-policy.md`.

### PAUSE

**Definition:** A decision D(i) = PAUSE, meaning the runtime will suspend execution of the current graph and await resumption signals without terminating or replanning. Distinct from IDLE (waiting for new input) and CONTINUE (proceeding with current graph). Defined in `../layer-6-evolution/decision-policy.md`.

### ROLLBACK

**Definition:** A decision D(i) = ROLLBACK, meaning the runtime will revert execution state to a prior checkpoint and resume from there. Distinct from REPLAN (which synthesizes a new graph) and TERMINATE (which ends execution). Defined in `../layer-6-evolution/decision-policy.md`.

---

## Section 16 — Execution Trace and Replay Terms (Phase 5)

### EXECUTION-TRACE

**Definition:** A complete, exportable record of a single execution's computational history, including all observations, decisions, execution graphs, module invocations, state mutations, failures, recoveries, and resource consumption. The trace is the primary artifact for computation-aware evaluation and learned policy training. Defined in `../layer-6-evolution/execution-trace-format.md` DEF-TRC-1.

**Note:** An execution trace records not just input-output pairs but the entire computational path taken, including alternative paths considered and rejected, resource budgets consumed, replanning events, and rollback recoveries.

### TRACE-SCHEMA

**Definition:** The canonical structural definition of an ExecutionTrace, specifying all required and optional fields, their types, and their relationships. The trace schema is DNC-native but exportable to external formats (JSON, Protocol Buffers) for interoperability. Defined in `../layer-6-evolution/execution-trace-format.md` DEF-TRC-2.

**Conformance:** A conformant trace MUST satisfy all REQUIRED fields of the trace schema. OPTIONAL fields may be present or absent without affecting conformance.

### REPLAY-ENGINE

**Definition:** The runtime component that deterministically re-executes a recorded execution trace, producing a bit-identical replay of the original execution. The ReplayEngine is used for debugging learned policies, reproducing failures, and verifying behavioral properties. Defined in `../layer-6-evolution/replay-semantics.md` DEF-REP-1.

### DETERMINISTIC-REPLAY

**Definition:** A replay that produces bit-identical results to the original execution, given the same initial state and the same trace. Deterministic replay requires that all sources of non-determinism (random seeds, timestamps, external inputs) be recorded in the trace or controlled during replay. Defined in `../layer-6-evolution/replay-semantics.md` DEF-REP-2.

**Note:** Deterministic replay does not require that the execution be deterministic. Non-deterministic execution (e.g., probabilistic LLM outputs) is replayed identically if the random state is captured in the trace.

### REPLAY-VERIFIER

**Definition:** A component that compares a replay execution against the original trace and produces a diff report identifying any divergences. The ReplayVerifier checks: decision sequence, execution graph topology, module outputs, resource consumption, and final outcome. Defined in `../layer-6-evolution/replay-semantics.md`.

---

## Section 17 — Evaluation Terms (Phase 5)

### COMPUTATION-AWARE EVALUATION

**Definition:** The DNC evaluation paradigm that measures not just what output was produced, but what execution path, resources, adaptations, and recovery behaviors produced it. Computation-aware evaluation goes beyond output accuracy to assess how intelligently computation was allocated. Defined in `../layer-6-evolution/evaluation-framework.md`.

**Note:** Computation-aware evaluation is the umbrella research contribution of DNC. It encompasses dynamic compute allocation, verification, recovery, rollback, observability, provenance, and counterfactual efficiency — not merely adaptive computation.

### COUNTERFACTUAL COMPUTE GAIN

**Definition:** The metric measuring how much better the selected execution graph performed compared to simpler alternative graphs for the same task. Defined as: CCG = Score(selected) - Score(simplest_alternative_that_achieves_comparable_score). A higher CCG indicates that additional computation was justified; a CCG near zero indicates that the extra graph structure contributed little. Defined in `../layer-6-evolution/evaluation-framework.md` MET-CCG-1.

**Note:** This is the signature metric of computation-aware evaluation. It answers: "Was the compute path justified, or could a simpler path have done equally well?"

### DYNAMIC COMPUTE INDEX

**Definition:** The metric measuring how effectively compute budget is allocated relative to output quality, defined as: DCI = (OutputQuality / ComputeBudgetSpent) normalized against a fixed baseline. A DCI > 1.0 indicates more efficient computation than the baseline; DCI < 1.0 indicates less efficient. Defined in `../layer-6-evolution/evaluation-framework.md` MET-DCI-1.

### ADAPTIVITY METRIC

**Definition:** A class of evaluation metrics that measure how dynamically a system allocates computation. Adaptivity metrics include: Planning Stability (variance in graph structure across inputs), Budget Elasticity (sensitivity of output quality to budget changes), Graph Entropy (diversity of execution paths), and Tool Diversity (distribution of module types used). Defined in `../layer-6-evolution/evaluation-framework.md`.

### RUNTIME METRIC

**Definition:** An objective, infrastructure-level measurement of an execution: latency, tokens, memory, graph depth, graph width, parallelism, replan count, rollback count. Runtime metrics require no judgment; they are directly observable. Defined in `../layer-6-evolution/evaluation-framework.md`.

### OUTCOME METRIC

**Definition:** A metric measuring the quality of the final output: task accuracy, verifier score, human preference rating, benchmark score. Outcome metrics are the traditional focus of model evaluation but represent only one dimension of computation-aware evaluation. Defined in `../layer-6-evolution/evaluation-framework.md`.

### METRIC HIERARCHY

**Definition:** The four-level classification of DNC evaluation metrics:
- **Level 0 (Infrastructure):** latency, tokens, memory, cost
- **Level 1 (Execution):** graph depth, graph width, parallelism, replans, rollbacks
- **Level 2 (Adaptivity):** Dynamic Compute Index, Counterfactual Compute Gain, Budget Elasticity, Graph Entropy
- **Level 3 (Outcome):** accuracy, robustness, human preference, benchmark score

Defined in `../layer-6-evolution/evaluation-framework.md`.

---

## Section 18 — Execution Semantics Terms (Phase 5)

### EXECUTION SEMANTICS

**Definition:** The formal specification of how DNC governs computation: how computation is organized, scheduled, observed, verified, replayed, and evaluated. Execution semantics define the operational behavior of the runtime without prescribing the internal algorithms of the components it manages. Defined in `../layer-6-evolution/execution-semantics.md`.

### REASONING SEMANTICS

**Definition:** The formal specification of how a component (an LLM, a solver, a model) reaches its outputs internally. Reasoning semantics cover chain-of-thought, tree-of-thought, graph-of-thought, ReAct, program-of-thought, and future reasoning paradigms. DNC does NOT specify reasoning semantics; they are payload executed by execution providers. Defined in `../layer-6-evolution/execution-semantics.md`.

**Note:** The separation of execution semantics from reasoning semantics is a deliberate architectural choice. DNC defines the operating system; it does not dictate the algorithms running on it. This independence ensures DNC remains stable as reasoning paradigms evolve.

### ARCHITECTURE v1.0

**Definition:** The frozen baseline specification for the DNC execution runtime architecture, encompassing all Phase 5 definitions. Architecture v1.0 is immutable; future architectural changes require Architecture v2.0 via a formal breaking revision process. Defined in `../layer-0-foundation/specification-foundation.md`.

### CONFORMANCE CLAUSE

**Definition:** A normative statement in a specification document that defines the minimum requirements an implementation must satisfy to be considered conformant to that specification. Each normative document in DNC contains a Conformance Clause listing mandatory requirements and permitted extensions. Defined in `../layer-6-evolution/conformance-model.md`.

### TRACEABILITY MATRIX

**Definition:** A cross-reference table mapping every normative requirement to the document that defines it, the invariant that verifies it, and the test that validates it. The traceability matrix ensures that every requirement is verifiable and that verification is traceable to its source. Defined in `../layer-6-evolution/conformance-model.md`.

---

## Section 19 — Extension and Namespace Terms (Phase 5)

### EXTENSION NAMESPACE

**Definition:** A reserved prefix for experimental or vendor-specific extensions that are not part of the normative DNC specification. All extension identifiers use the EXT-* namespace. Extensions MUST NOT modify normative semantics; they are permitted only within the bounds defined in the conformance model. Defined in `../layer-6-evolution/conformance-model.md`.

**Namespaces:** EXT-* (vendor/experimental extensions)

### NORMATIVE REQUIREMENT

**Definition:** A specification statement that uses RFC 2119 keyword forms (MUST, SHALL, MUST NOT, SHOULD, MAY) to express a binding obligation. All normative requirements originate in specification documents. Implementations MAY reference them by identifier but MUST NOT redefine them. Defined in `../layer-6-evolution/conformance-model.md`.

**Permanent Rule:** Normative requirements SHALL NOT appear in implementation documentation. All normative requirements originate in the specification and implementations may only reference them by identifier.

---

## Section 20 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| TERM-AMEND-001 | core-terminology.md | 2026-07-10 | Added Section 11 (Neural Computation Terms). | No |
| TERM-AMEND-002 | core-terminology.md | 2026-07-11 | Added Sections 14-19 (Phase 5 terms): Execution Provider Terms (EXECUTION-CAPABILITY, EXECUTION-PROVIDER, PROVIDER-CONFORMANCE), Control and Decision Terms (DECISION-POLICY, RULE-POLICY, LLM-POLICY, RL-POLICY, PAUSE, ROLLBACK), Execution Trace and Replay Terms (EXECUTION-TRACE, TRACE-SCHEMA, REPLAY-ENGINE, DETERMINISTIC-REPLAY, REPLAY-VERIFIER), Evaluation Terms (COMPUTATION-AWARE EVALUATION, COUNTERFACTUAL COMPUTE GAIN, DYNAMIC COMPUTE INDEX, ADAPTIVITY METRIC, RUNTIME METRIC, OUTCOME METRIC, METRIC HIERARCHY), Execution Semantics Terms (EXECUTION SEMANTICS, REASONING SEMANTICS, ARCHITECTURE v1.0, CONFORMANCE CLAUSE, TRACEABILITY MATRIX), Extension and Namespace Terms (EXTENSION NAMESPACE, NORMATIVE REQUIREMENT). Freezes Phase 5 vocabulary per Architecture v1.0. | No |