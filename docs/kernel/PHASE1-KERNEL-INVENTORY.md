# Phase 1 Kernel Inventory

**Date:** 2026-07-31
**Phase:** `Phase 1 — Harden kernel contracts, packaging, and compatibility boundaries`
**Status:** Initial inventory for compatibility hardening

## Public API surface

| Area | Public modules/classes | Compatibility assumption |
|---|---|---|
| Package API | `dnc.__init__`: `DNCSystem`, `DNCSystemConfig`, `ExecutionCore`, `ReferenceExecutionCore`, `SystemStateSnapshot` | Existing imports remain valid through compatibility facade |
| Kernel hardening | `dnc.kernel.*` | Additive Phase 1 namespace for errors, interfaces, and version identifiers |
| DNC-IR identity | `UnitID`, `InstanceID`, `GraphID`, `GraphVersion`, `MutationID`, `TransactionID`, `IdentityRegistry` | IDs are stable value objects; retired unit IDs are not reused |
| DNC-IR graph | `StructuralGraph`, `Edge`, `EdgeType` | Authoring graph may be temporarily invalid; validator is commit/projection authority |
| DNC-IR unit | `ComputationalUnit`, `UnitContract`, `MutationContract`, `Constraint`, dimensional enums | Unit dimensions remain orthogonal |
| DNC-IR operations | `OperationType`, `IROperation` | Operation validation remains operation-type specific |
| Serialization | `DNWIRSerializer.to_dict/to_json/from_dict/from_json` | Canonical JSON is sorted and versioned; legacy unversioned inputs still load |
| Transactions | `TransactionManager`, `TransactionContext`, `TransactionState` | Failed transactions do not mutate active graph state |
| Projection | `StructuralProjector`, `ExecutableDAG`, `ExecutableNode`, `ExecutableEdge` | Projection must not mutate source structural graph |
| Runtime | `Runtime`, `ExecutionState2`, `ExecutionProvider`, `DecisionPolicy`, traces | Reference runtime remains deterministic research infrastructure |
| Cognitive profile | `dnc.cognition.*` | Additive draft profile; not a kernel replacement |

## Canonical serialization fields

`DNWIRSerializer.to_dict` emits:

- `schema_id`;
- `schema_version`;
- `compatibility_version`;
- `graph_id`;
- `version.major`;
- `version.minor`;
- `version.patch`;
- `version.sequence`;
- `units`;
- `edges`;
- `metadata`.

Each unit emits:

- `unit_id`;
- `name`;
- `structure`;
- `visibility`;
- `lifecycle`;
- `contract`;
- `mutation_contract.allowed_mutations`;
- `mutation_contract.max_children`;
- `mutation_contract.is_immutable`;
- `constraints`;
- `metadata`;
- `sub_units`.

Each edge emits:

- `source`;
- `target`;
- `edge_type`;
- `metadata`.

## Invariant and conformance assumptions

The current conformance report records:

- `30/30` invariants covered;
- `34/34` conformance tests passed;
- `4/4` ACDs resolved;
- spec tooling passed.

## Operation vocabulary

Current structural mutation operation types:

- `ADD_UNIT`;
- `REMOVE_UNIT`;
- `CONNECT_UNITS`;
- `DISCONNECT_UNITS`;
- `REWIRE_EDGE`;
- `SPECIALIZE_UNIT`;
- `DESPECIALIZE_UNIT`;
- `COMPOSE_UNITS`;
- `DECOMPOSE_UNIT`;
- `UPDATE_CONTRACT`.

## Events and provenance assumptions

Observed structural transaction events:

- `STRUCTURAL_TRANSACTION_BEGIN`;
- `STRUCTURAL_MUTATION_APPLIED`;
- `STRUCTURAL_TRANSACTION_COMMITTED`;
- `STRUCTURAL_TRANSACTION_ROLLED_BACK`;
- `STRUCTURAL_GRAPH_VERSION_CREATED`.

Transaction provenance is optional through `ProvenanceLog`, but when present it records begin, mutation, rollback, commit, and graph-version creation events.

## Persistence assumptions

No durable persistence backend is part of the Phase 1 kernel. Current persistence assumptions are:

- canonical JSON is the portable structural interchange format;
- checkpoints are in-memory/state snapshots unless explicitly persisted by caller code;
- build artifacts, reports, and SBOM files are generated evidence and are not runtime persistence;
- external providers, caches, databases, and filesystem effects are not claimed same-state without later Phase 2 isolation manifests.
