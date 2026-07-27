# Q2: What Is the Computational Substrate?

**Date**: 2026-07-22  
**Status**: THEORETICAL DEFINITION  
**Depends on**: Q1 (What Is DNC?)  
**Depended on by**: Q3 (State Model), Q4 (Mutation Authority), DNC-IR

---

## 1. The Question

What are the fundamental units that make up a DNC computation?

This question defines the *vocabulary* of structural mutation. If we define the substrate too narrowly, we limit what DNC can express. If we define it too broadly, we make the system unnecessarily complex.

---

## 2. Current System: Module-Centric

The DNC v1.x system is module-centric:

```
Module
    ├── ModuleTypeID (unique type identifier)
    ├── ModuleInstanceID (unique instance identifier)
    ├── ModuleContract (preconditions, output contract)
    └── BaseModule ABC (standard interface)
```

Module types are: `Source`, `Transform`, `Aggregate`, `Sink`.

This works for DNC-0 and DNC-1, but has limitations for DNC-3+:

1. **Modules are opaque**: The system cannot inspect the internal structure of a module
2. **Modules are monolithic**: A module cannot contain other modules
3. **Modules are typed by convention**: ModuleTypeID is a string; no formal type system
4. **Modules cannot be partially mutated**: You cannot change one input of a module; you must replace the entire module

For DNC-3+, we need a substrate that supports hierarchical composition and fine-grained structural mutation.

---

## 3. Proposed Substrate: ComputationalUnit with Orthogonal Dimensions

The ComputationalUnit type hierarchy is defined by three **orthogonal dimensions**, not a single flat type hierarchy:

```
ComputationalUnit
    │
    ├── structure: PRIMITIVE | COMPOSITE
    │       PRIMITIVE = atomic; cannot be decomposed
    │       COMPOSITE = contains internal units and edges
    │
    ├── visibility: OPAQUE | INSPECTABLE
    │       OPAQUE = implementation hidden; treated as black box
    │       INSPECTABLE = internal structure visible; can be partially mutated
    │
    └── lifecycle: BASE | SPECIALIZED
            BASE = normal unit
            SPECIALIZED = created by consolidation (DNC-6)
```

### 3.1 Why Orthogonal Dimensions

The original flat hierarchy (Primitive, Module, Composite, Subgraph, Specialized) conflated three independent properties:

| Original Type | Structural Property | Visibility Property | Lifecycle Property |
|---------------|--------------------|--------------------|-------------------|
| PrimitiveUnit | PRIMITIVE | (any) | BASE |
| ModuleUnit | (any) | OPAQUE | BASE |
| CompositeUnit | COMPOSITE | INSPECTABLE | BASE |
| SubgraphUnit | COMPOSITE | (any) | BASE |
| SpecializedUnit | (any) | (any) | SPECIALIZED |

This conflation creates ambiguities:
- Is a Module PRIMITIVE or COMPOSITE? (It can be either — an opaque module may contain internal structure.)
- Is a Subgraph different from a Composite? (No — both are COMPOSITE with different visibility.)
- Is Specialized a type or a state? (It's a lifecycle state, not a structural type.)

The orthogonal model resolves these: a unit is defined by its position in three independent dimensions, not by a single type label.

### 3.2 Example Units

| Unit | Structure | Visibility | Lifecycle | Description |
|------|-----------|------------|-----------|-------------|
| `multiply` | PRIMITIVE | INSPECTABLE | BASE | Atomic math operation |
| `LLM_call` | PRIMITIVE | OPAQUE | BASE | Atomic LLM invocation |
| `summarize` | (any) | OPAQUE | BASE | Named module with hidden implementation |
| `pipeline` | COMPOSITE | INSPECTABLE | BASE | Chain of units with visible internals |
| `attention_block` | COMPOSITE | INSPECTABLE | BASE | DAG of units with visible internals |
| `task_X_classifier` | (any) | OPAQUE | SPECIALIZED | Consolidated unit from DNC-6 |

### 3.3 The Five Semantic Roles (Derived from Dimensions)

While the dimensions are orthogonal, common combinations produce recognizable semantic roles:

| Role | Structure | Visibility | Lifecycle | When Used |
|------|-----------|------------|-----------|-----------|
| **Primitive** | PRIMITIVE | INSPECTABLE | BASE | Fine-grained atomic computation |
| **Module** | (any) | OPAQUE | BASE | Named computation with defined interface |
| **Composite** | COMPOSITE | INSPECTABLE | BASE | Visible composition of units |
| **Subgraph** | COMPOSITE | OPAQUE | BASE | Embedded DAG treated as opaque |
| **Specialized** | (any) | (any) | SPECIALIZED | Consolidated reusable unit |

These are **derived roles**, not fundamental types. A unit's fundamental identity is its position in the three dimensions. The roles are shortcuts for common combinations.

---

## 4. ComputationalUnit: The Abstract Interface

Every ComputationalUnit shares a common interface:

```
ComputationalUnit
    │
    ├── identity
    │       unit_id: UnitID (globally unique)
    │       name: str (human-readable, not necessarily unique)
    │
    ├── dimensions
    │       structure: PRIMITIVE | COMPOSITE
    │       visibility: OPAQUE | INSPECTABLE
    │       lifecycle: BASE | SPECIALIZED
    │
    ├── interface
    │       inputs: List[InputPort]   (named, typed)
    │       outputs: List[OutputPort] (named, typed)
    │
    ├── metadata
    │       preconditions: Set[Condition]  (what must be true before execution)
    │       cost_estimate: CostEstimate    (computational cost prediction)
    │       version: Version               (for tracking mutations)
    │
    └── structure (varies by structure dimension)
            PRIMITIVE:  (no internal structure)
            COMPOSITE:  internal_units: List[ComputationalUnit]
                        internal_edges: List[Edge]
```

---

## 5. Graph Structure

A DNC computation is a **Directed Acyclic Graph (DAG)** of ComputationalUnits:

```
Graph
    │
    ├── units: Dict[UnitID, ComputationalUnit]
    │       All computational units in the graph
    │
    ├── edges: List[Edge]
    │       Connections between units
    │       Edge = (source_unit, source_port, target_unit, target_port)
    │
    ├── constraints: Set[Constraint]
    │       Structural constraints that must be preserved
    │       Examples: DAG property, resource limits, latency bounds
    │
    └── boundary: Boundary
            External inputs and outputs of the graph
            How the graph connects to the outside world
```

### 5.1 Edge

```
Edge
    │
    ├── source: UnitID
    ├── source_port: PortID
    ├── target: UnitID
    ├── target_port: PortID
    │
    └── metadata
            data_type: DataType (what flows through this edge)
            optional: bool (whether this connection is required)
```

### 5.2 Constraint

```
Constraint (abstract)
    │
    ├── DAGConstraint:       No cycles in the graph
    ├── ResourceConstraint:  Total computational cost ≤ budget
    ├── LatencyConstraint:   End-to-end latency ≤ bound
    ├── DependencyConstraint: If A depends on B, edge must exist
    ├── TypeConstraint:      Output type of source matches input type of target
    └── CustomConstraint:    User-defined constraint
```

---

## 6. Composition: How Units Nest

The key property of this substrate is **hierarchical composition**:

```
Graph
    │
    ├── Unit(multiply, PRIMITIVE, INSPECTABLE, BASE)
    │
    ├── Unit(pipeline, COMPOSITE, INSPECTABLE, BASE)
    │       │
    │       ├── Unit(embed, PRIMITIVE, OPAQUE, BASE)
    │       ├── Unit(classify, PRIMITIVE, OPAQUE, BASE)
    │       └── Unit(route, PRIMITIVE, OPAQUE, BASE)
    │
    ├── Unit(attention_block, COMPOSITE, OPAQUE, BASE)
    │       │
    │       ├── Unit(linear, PRIMITIVE, INSPECTABLE, BASE)
    │       ├── Unit(softmax, PRIMITIVE, INSPECTABLE, BASE)
    │       └── Unit(weighted_sum, PRIMITIVE, INSPECTABLE, BASE)
    │
    └── Unit(task_X_classifier, PRIMITIVE, OPAQUE, SPECIALIZED)
            (opaque; created by consolidation)
```

**Mutation at any level**: A structural mutation can target:
- A single PRIMITIVE unit (add, remove, replace)
- A COMPOSITE unit (add/remove internal units, rewire internal edges)
- The top-level graph (add/remove units, rewire edges)

This enables **multi-scale structural mutation**: the system can make fine-grained changes (swap one primitive) or coarse-grained changes (replace an entire composite).

---

## 7. Relationship to DNC v1.x Modules

The current Module system maps to the new substrate:

| v1.x Concept | v2.x Concept | Relationship |
|---------------|--------------|--------------|
| `ModuleTypeID` | Unit `name` | ModuleTypeID becomes the unit's name |
| `ModuleInstanceID` | `UnitID` | ModuleInstanceID becomes the unit's unique ID |
| `ModuleContract` | `preconditions` + `interface` | Contract splits into preconditions and port interface |
| `BaseModule` | Unit with lifecycle=BASE | BaseModule becomes a BASE lifecycle unit |
| `Source` | Unit(structure=PRIMITIVE, name="source") | Source becomes a PRIMITIVE unit |
| `Transform` | Unit(structure=PRIMITIVE, name="transform") | Same |
| `Aggregate` | Unit(structure=COMPOSITE, name="aggregate") | Aggregate becomes a COMPOSITE unit |
| `Sink` | Unit(structure=PRIMITIVE, name="sink") | Sink becomes a PRIMITIVE unit |

**Backward compatibility**: The v1.x module system can be represented as a flat graph of BASE units with OPAQUE visibility. The v2.x substrate is a strict superset.

---

## 8. DNC-IR: The Intermediate Representation

The computational substrate defines the *semantic model*. DNC-IR is the *syntactic representation* — the language in which graphs are described, mutated, and serialized.

DNC-IR should be:

1. **Graph-native**: Directly represents DAGs of ComputationalUnits
2. **Mutations-as-operations**: Structural mutations are first-class operations in the IR
3. **Hierarchical**: Supports nested graphs (composites, subgraphs)
4. **Typed**: Units and ports have types; type checking is part of constraint validation
5. **Serializable**: Can be saved, loaded, and transmitted

DNC-IR is specified *after* the computational substrate is defined. The substrate is the semantics; DNC-IR is the syntax.

---

## 9. Implications for State Model (Q3)

The computational substrate directly informs the state model:

- **G (Graph)** in ES(t) must represent the current graph of ComputationalUnits
- **G** must support hierarchical nesting (composites, subgraphs)
- **G** must be mutable (add/remove/reconnect units)
- **G** must be checkpointable (full graph state can be saved and restored)

The exact representation of G is determined in Q3.

---

## 10. Implications for Mutation Semantics (Q4)

The computational substrate defines what mutations are possible:

| Mutation | Target | Effect |
|----------|--------|--------|
| `add_unit(unit, position)` | Graph | Add a new ComputationalUnit |
| `remove_unit(unit_id)` | Graph | Remove a unit and its edges |
| `reconnect(source, source_port, target, target_port)` | Graph | Change an edge |
| `replace_unit(unit_id, new_unit)` | Graph | Replace a unit, preserving connections |
| `extract_composite(unit_ids, name)` | Graph | Group units into a CompositeUnit |
| `inline_composite(unit_id)` | Graph | Flatten a CompositeUnit into its internals |
| `specialize(unit_id, params)` | Graph | Create a SpecializedUnit from an existing unit |

These are specified in Q4.

---

## 11. Open Questions

1. **Port typing**: How detailed should the type system be? Simple (data_type) or rich (generics, protocols)?
2. **Opaque vs. inspectable**: Should the system be able to inspect the internals of any unit, or should some units be opaque?
3. **Dynamic ports**: Can a unit have a variable number of inputs/outputs, or is the port list fixed at creation?
4. **Stateful units**: Can units maintain internal state across executions? (This affects the state model.)

These are design decisions that can be resolved during implementation. The substrate definition above is sufficient to proceed to Q3.

---

## 12. Summary

| Property | Value |
|----------|-------|
| Fundamental unit | ComputationalUnit (abstract) |
| Dimensions | Structure (PRIMITIVE/COMPOSITE), Visibility (OPAQUE/INSPECTABLE), Lifecycle (BASE/SPECIALIZED) |
| Derived roles | Primitive, Module, Composite, Subgraph, Specialized (common dimension combinations) |
| Graph structure | DAG of ComputationalUnits with typed edges |
| Composition | Hierarchical (COMPOSITE units can contain other units) |
| Mutation granularity | Any level (single unit, composite, whole graph) |
| v1.x compatibility | v1.x modules map to BASE/OPAQUE units; flat graph is a special case |
| DNC-IR | Syntactic representation of the substrate; specified later |
