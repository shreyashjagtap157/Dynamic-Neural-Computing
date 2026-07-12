# Planner Pipeline

## Metadata

| Field | Value |
|---|---|
| Document | planner-pipeline.md |
| Title | Planner Pipeline |
| Document ID | SPEC-PLANNER |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 4 |
| Owner Question | How does the planner produce execution graphs? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

The planner is the mechanism that synthesizes execution graphs — the DAGs of module instances that realize a given task. It is the primary source of dynamism in the DNC runtime: a static thinker would have a pre-compiled graph; a dynamic thinker invokes the planner at runtime to construct a graph tailored to the current task, available modules, and resource conditions.

The planner pipeline is Layer 4: it builds on the semantic foundations of Layer 3 (execution model, formal model) and the constitutional constraints of Layer 2 (invariants). It implements the planning policy — the rules by which graphs are synthesized — but does not itself make scheduling decisions (that is the scheduler's role).

The planner is invoked in two contexts:
1. **Initial planning**: at execution initiation, to produce G_0
2. **Replanning**: mid-execution, when triggered per `../layer-3-execution/replanning-protocol.md`

The planner produces a graph G = (V, E, w) where V is a set of module instances, E encodes data dependencies, and w assigns cost weights. The planner does not execute the graph; it passes G to the scheduler for dispatch.

---

## Section 2 — Planner Architecture

### DEF-PLANNER-1 — Planning Task

**Definition:**

A **planning task** is a tuple:

```
PT = (task_description, available_modules, resource_budget, constraints, replan_context)
```

Where:
- `task_description` is the goal to be achieved, expressed as an expected output specification
- `available_modules` is the set of module instances currently in the module registry (per `module-lifecycle.md`)
- `resource_budget` is the remaining resource budget from `cost-semantics.md`
- `constraints` are additional constraints (ordering, affinity, deadline)
- `replan_context` is null for initial planning, or (G_old, ES(t), trigger) for replanning per `../layer-3-execution/replanning-protocol.md`

### DEF-PLANNER-2 — Planning Phase

**Definition:**

The planner pipeline executes in four ordered phases:

```
1. Task Analysis
2. Module Selection
3. Graph Construction
4. Validation and Cost Estimation
```

Each phase is idempotent: running the same phase twice with the same inputs produces the same outputs (or an error).

### DEF-PLANNER-3 — Planning Result

**Definition:**

A **planning result** is either:
- `SUCCESS(G)` — a valid execution graph
- `FAIL(reason)` — planning failed with a documented reason

The planner MUST produce one of these two outcomes. It MUST NOT produce a partial or indeterminate result.

---

## Section 3 — Phase 1: Task Analysis

### 3.A Task Decomposition

The planner decomposes `task_description` into a set of sub-goals `{g_1, g_2, ..., g_n}`. Each sub-goal corresponds to a module capability required to achieve the task. The decomposition is recursive: a sub-goal g_i may itself be decomposed if no single module satisfies it.

### 3.B Dependency Analysis

For each sub-goal g_i, the planner identifies which other sub-goals must complete before g_i can be satisfied — i.e., the data-dependency structure among sub-goals. This produces a partial order on the sub-goals.

### INV-PLANNER-1 — Task Analysis Completeness

**Statement:** The planner MUST identify all sub-goals necessary to satisfy the task_description. A sub-goal that is necessary but not identified results in an incomplete graph, which is a PLANNING_INCOMPLETE error.

**Verification:** The validation phase checks that every output specified in task_description is produced by some node in G.

### INV-PLANNER-2 — Dependency Analysis Correctness

**Statement:** For every data dependency declared in the graph, the planner MUST verify that the source module's output type is compatible with the target module's input type.

**Verification:** Type compatibility check during graph construction. A type mismatch is a PLANNING_TYPE_ERROR.

---

## Section 4 — Phase 2: Module Selection

### 4.A Module Capability Matching

The planner matches each sub-goal g_i to the module instance(s) in `available_modules` that can satisfy it. The match is based on:
- Capability annotation: the module's declared capability set
- Output type: the module's output matches g_i's required output type
- Resource cost: the module's estimated cost (per `cost-semantics.md`) fits within resource_budget

### 4.B Conflict Resolution

When multiple module instances can satisfy the same sub-goal, the planner selects based on:
1. Preference: modules with higher preference scores are preferred
2. Resource efficiency: modules with lower estimated cost are preferred
3. Provenance: modules with more favorable execution history (per `../layer-5-observability/provenance-model.md`) are preferred

### DEF-PLANNER-4 — Selected Module Set

**Definition:**

The **selected module set** `V_sel` is the set of module instances selected for inclusion in G. Each v ∈ V_sel is assigned a unique ModuleInstanceID within the execution.

### INV-PLANNER-3 — Module Availability at Selection Time

**Statement:** Every module instance selected for V_sel MUST be in the REGISTERED state in the module registry at the time of selection. A module that is deregistered between selection and graph dispatch triggers replanning.

**Verification:** Registry timestamp check. The planner records the registry version at selection time and validates it again at dispatch.

---

## Section 5 — Phase 3: Graph Construction

### DEF-PLANNER-5 — Vertex Assignment

**Definition:**

Each selected module instance v ∈ V_sel is assigned to a vertex in G. The vertex label includes (ModuleTypeID, ModuleInstanceID, cost_estimate, preference_score).

### DEF-PLANNER-6 — Edge Construction

**Definition:**

An edge (v_i, v_j) ∈ E is created when v_j's input binding depends on v_i's output. The planner constructs E by:
1. For each input parameter of v_j, identifying the source module that produces the matching output type
2. If the source is another selected module v_i, creating edge (v_i, v_j)
3. If the source is an external input, creating no edge (the input is bound at execution initiation)

### INV-PLANNER-4 — No Unbound Inputs

**Statement:** Every module instance v ∈ V_sel MUST have all of its required input parameters bound to either (a) the output of another module in V_sel, or (b) an external input. An input that cannot be bound is UNBOUND_INPUT_ERROR.

**Verification:** Input binding completeness check after edge construction.

### INV-PLANNER-5 — Acyclicity Enforcement

**Statement:** The constructed graph G MUST be a DAG. The planner MUST verify acyclicity before returning SUCCESS(G). A cyclic graph is discarded and planning is re-attempted with a modified ordering constraint.

**Verification:** Topological sort attempt. If the sort fails, the graph contains a cycle and is rejected.

---

## Section 6 — Phase 4: Validation and Cost Estimation

### DEF-PLANNER-7 — Cost Estimate

**Definition:**

The **cost estimate** for graph G is:

```
Cost(G) = Σ_{v ∈ V} w(v) + Σ_{(u,v) ∈ E} w_edge(u, v)
```

Where w(v) is the module instance cost from `cost-semantics.md` and w_edge is the inter-module communication cost.

### INV-PLANNER-6 — Resource Budget Compliance

**Statement:** Cost(G) MUST NOT exceed the remaining resource_budget. If it does, the planner MUST either (a) produce a lower-cost graph through module substitution, or (b) return FAIL(RESOURCE_BUDGET_EXCEEDED) and trigger the resource exhaustion handler.

**Verification:** Budget comparison after cost estimation. FAIL(RESOURCE_BUDGET_EXCEEDED) is returned if the constraint cannot be satisfied.

### INV-PLANNER-7 — Graph Validation Checklist

**Statement:** Before returning SUCCESS(G), the planner MUST verify:
1. G is a DAG (INV-PLANNER-5)
2. All inputs are bound (INV-PLANNER-4)
3. Type compatibility on all edges (INV-PLANNER-2)
4. Resource budget compliance (INV-PLANNER-6)
5. All sub-goals from task analysis are satisfied (INV-PLANNER-1)

**Verification:** Automated checklist run. A graph that fails any check does not receive SUCCESS.

---

## Section 7 — Replanning Specific Behavior

### 7.A Replan Context

When invoked in replan context, the planner receives:
- `G_old`: the current execution graph
- `ES(t)`: the current execution state
- `trigger`: the replan trigger classification (per `../layer-3-execution/replanning-protocol.md`)

### 7.B Graph Diff Computation

The planner computes the graph diff:
- `RETAINED`: nodes in both G_old and G_new (state preserved per `../layer-3-execution/replanning-protocol.md` INV-REPLAN-10)
- `RETIRED_EARLY`: nodes in G_old not completed (archived per `../layer-3-execution/state-management.md` INV-STATE-8)
- `NEW`: nodes only in G_new (initialized per `../layer-3-execution/state-management.md` INV-STATE-9)

### 7.C Partial Reuse

The planner SHOULD reuse as many RETAINED nodes as possible to minimize wasted computation. It MUST NOT reuse nodes that are incompatible with the new task_description (e.g., capability mismatch discovered after environmental change signal).

### INV-PLANNER-8 — Replan Preserves Retained State

**Statement:** When a module instance v is in the RETAINED set, the planner MUST include v in G_new with its preserved state from ES(t). The planner MUST NOT re-execute a RETAINED node unless W(t)[v].output is UNBOUND or PENDING.

**Verification:** State check against W(t) before including v in G_new.

---

## Section 8 — Planner Versioning

### INV-PLANNER-9 — Planner Version Tracking

**Statement:** The planner version is recorded in the execution header per PR-10. Two executions with different planner versions and identical task descriptions MAY produce different graphs. The planner version MUST be immutable for the duration of a single execution.

**Verification:** Execution header validation at planning initiation. The planner version is committed to H_exec and MUST NOT change mid-execution.

---

## Section 9 — Planning Phase Complexity

### INV-PLANNER-10 — Planning Phase Complexity Bounds

**Statement:**

Each phase of the planner pipeline (per DEF-PLANNER-2) has a bounded worst-case computational complexity:

| Phase | Complexity | Notes |
|---|---|---|
| Task Analysis | O(task_desc_tokens × log \|available_modules\|) | Token-count linear in input; binary search over module registry |
| Module Selection | O(\|available_modules\| × \|sub_goals\|) | Scoring each module against each sub-goal |
| Graph Construction | O(\|V\| + \|E\|) | Single pass using Kahn's algorithm for topological ordering |
| Validation | O(\|V\| + \|E\|) | Checklist walk; includes topological sort verification |

**Total worst-case:** O(\|V\|²) for dense module graphs where each module could match each sub-goal.

**DECIDE_BUDGET MUST be configured ≥ worst-case planning time** for the target module registry size. An implementation MUST measure the 99th-percentile planning time for the target registry and configure DECIDE_BUDGET to at least 3× that value to handle variance.

**KB_plans Cache Hit:** When the task_description matches a template in KB_plans (per continual-learning.md DEF-CL-5), Phase 1-4 are skipped and the cached graph is returned in O(1). Cache lookup is exact-match on the content-addressable store.

**Verification:** Implementation benchmarks. The runtime MUST log PLANNING_TIME_HISTOGRAM for each planner invocation to verify DECIDE_BUDGET compliance statistically.

**Rationale:** Without complexity bounds, the planner could consume unbounded time, violating the control loop's latency requirements (formal-model.md THM-FM-L3). Bounded complexity enables bounded planning time.

---

## Section 10 — Glossary

| Term | Definition | Document |
|---|---|---|
| Planning Task | PT = (task_description, available_modules, resource_budget, constraints, replan_context) | planner-pipeline.md |
| Planning Phase | Four-phase pipeline: Task Analysis, Module Selection, Graph Construction, Validation | planner-pipeline.md |
| Planning Result | SUCCESS(G) or FAIL(reason) | planner-pipeline.md |
| Selected Module Set | V_sel — modules chosen for the execution graph | planner-pipeline.md |
| Graph Diff | RETAINED / RETIRED_EARLY / NEW classification | planner-pipeline.md |
| PLANNING_INCOMPLETE | Error when sub-goals are missing | planner-pipeline.md |
| PLANNING_TYPE_ERROR | Error when type compatibility fails | planner-pipeline.md |
| UNBOUND_INPUT_ERROR | Error when input binding fails | planner-pipeline.md |
| RESOURCE_BUDGET_EXCEEDED | Error when graph cost exceeds budget | planner-pipeline.md |

---

## Section 11 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| PLANNER-AMEND-001 | planner-pipeline.md | 2026-07-10 | Added INV-PLANNER-10 (planning phase complexity bounds), resolving systems engineer review finding that planner has no performance guarantees. | No |