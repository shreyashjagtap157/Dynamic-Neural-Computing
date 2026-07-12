# Module Lifecycle

## Metadata

| Field | Value |
|---|---|
| Document | module-lifecycle.md |
| Title | Module Lifecycle |
| Document ID | SPEC-LIFECYCLE |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 4 |
| Owner Question | How do modules come into and leave the registry? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

Modules are the computational units of the DNC runtime. The module lifecycle specification governs how modules are defined, registered, versioned, instantiated, and deregistered — and the guarantees that hold during each phase.

This document is Layer 4 (Mechanisms) because it specifies the implementation-level behavior of the module registry and module instances, as distinct from the semantic layer (Layer 3) which defines what execution state is and how it behaves.

The key properties guaranteed by this specification:
- A module's contract is immutable once registered
- Module versions are tracked and enforced at instantiation time
- Deregistration does not affect in-flight executions
- The module registry is consistent with the execution state M(t)

---

## Section 2 — Module Contract

### DEF-LIFECYCLE-1 — Module Contract

**Definition:**

A **module contract** is the authoritative specification of a module's interface and behavioral constraints:

```
Contract = (ModuleTypeID, Version, InputSignature, OutputSignature,
            CapabilityAnnotations, CostParameters, PreferenceScore,
            InterruptibilityFlag, ConfidenceThreshold)
```

Where:
- `ModuleTypeID` is the globally unique identifier for this module type
- `Version` follows semantic versioning (MAJOR.MINOR.PATCH)
- `InputSignature` and `OutputSignature` are typed formal parameter lists
- `CapabilityAnnotations` describe what the module can do (used by the planner)
- `CostParameters` are the cost weights for this module per `cost-semantics.md`
- `PreferenceScore` is a real number used for planner conflict resolution
- `InterruptibilityFlag` is true if the module can be safely interrupted mid-execution
- `ConfidenceThreshold` is the minimum confidence below which a LOW_CONFIDENCE event is emitted

### INV-LIFECYCLE-1 — Contract Immutability After Registration

**Statement:** Once a module is registered with a given ModuleTypeID and Version, its contract is immutable. No field of the contract MAY be modified without a version bump. A module with the same ModuleTypeID but a different Version is considered a different module.

**Verification:** Contract hash verification. The registry stores a cryptographic hash of each registered contract. Any attempted modification of a registered contract without a version bump is rejected.

**Rationale:** A mutable contract means the meaning of a module can change mid-execution, violating PR-10 (version consistency).

### INV-LIFECYCLE-2 — Unique ModuleTypeID

**Statement:** Every ModuleTypeID in the module registry MUST be unique. No two modules in the registry MAY share the same ModuleTypeID.

**Verification:** Registry consistency check at registration. A duplicate ModuleTypeID is REGISTRATION_DUPLICATE_ID.

---

## Section 3 — Registration

### DEF-LIFECYCLE-2 — Registration

**Definition:**

**Registration** is the process of adding a new module to the module registry:

```
Register(Contract) → SUCCESS(ModuleTypeID) | FAIL(RegistrationError)
```

The process:
1. Validate that ModuleTypeID does not already exist in the registry (INV-LIFECYCLE-2)
2. Compute the contract hash and store it
3. Add the contract to the registry under ModuleTypeID
4. Set the module state to REGISTERED
5. Record REGISTRATION event in the provenance log

### INV-LIFECYCLE-3 — Pre-Execution Registration Requirement

**Statement:** A module MUST be in the REGISTERED state before it can be instantiated in an execution graph. A module that is not REGISTERED cannot be selected by the planner.

**Verification:** Registry state check in the planner's module selection phase (INV-PLANNER-3).

### INV-LIFECYCLE-4 — Registration Versioning

**Statement:** Registering a module with ModuleTypeID that already exists but a different Version creates a new entry in the registry, distinct from the prior entry. Both versions coexist. The registry tracks version lineage.

**Verification:** Version lineage record in the registry. Planner can specify version constraints (exact, minimum, compatible range).

---

## Section 4 — Instantiation

### DEF-LIFECYCLE-3 — Module Instance

**Definition:**

A **module instance** is a specific execution of a module, identified by a unique ModuleInstanceID within an execution. Multiple instances of the same ModuleTypeID may coexist in one execution with different ModuleInstanceIDs.

Instantiation maps a module type to a concrete node in the execution graph:
```
Instantiate(ModuleTypeID, version_constraint, ModuleInstanceID) → InstanceRef | FAIL(InstantiationError)
```

### DEF-LIFECYCLE-4 — Version Resolution

**Definition:**

**Version resolution** selects which version of a module to instantiate given a version constraint:
- **Exact**: selects the specified version only
- **Minimum**: selects the specified version or any higher minor/patch version
- **Compatible range**: selects any version within the specified range

### INV-LIFECYCLE-5 — Version Resolution Determinism

**Statement:** Given the same ModuleTypeID and version_constraint, version resolution MUST produce the same ModuleInstanceID in all compliant implementations. If the constraint matches multiple versions, the most recent compatible version is selected.

**Verification:** Deterministic version resolution algorithm. Regression testing against canonical version resolution cases.

### INV-LIFECYCLE-6 — Execution Header Version Tracking

**Statement:** The selected ModuleTypeID and version for each instance is recorded in M(t) (module registry snapshot in ES(t)) and in the execution header's RegistryVersion component.

**Verification:** Header check at instantiation. RegistryVersion is updated to reflect the registry state at the time of instantiation.

---

## Section 5 — Deregistration

### DEF-LIFECYCLE-5 — Deregistration

**Definition:**

**Deregistration** is the process of removing a module from the module registry:

```
Deregister(ModuleTypeID, version, immediate=False) → SUCCESS | FAIL(DeregistrationError)
```

Parameters:
- `immediate=True`: deregister immediately, no grace period
- `immediate=False`: grace period of GRACE_PERIOD_MS milliseconds (default: 5000ms)

During the grace period:
- Existing instances remain executable
- No new instances may be instantiated
- After grace period, the module transitions to DEREGISTERED

### INV-LIFECYCLE-7 — No Disruption of In-Flight Executions

**Statement:** Deregistration of a module MUST NOT affect any execution that has already instantiated that module. In-flight executions continue with the deregistered module as if it were still registered, until they complete or the module fails.

**Verification:** Execution state check. M(t) at any time t during execution contains the module registry snapshot at execution initiation, not the current registry state. Deregistration does not modify M(t).

### INV-LIFECYCLE-8 — Grace Period Behavior

**Statement:** During the grace period, the planner MUST NOT select the deregistering module for new execution graphs. If immediate=True, the module is immediately excluded from new graph construction.

**Verification:** Planner exclusion check during grace period. New execution graphs cannot include a module in DEREGISTERING state.

### INV-LIFECYCLE-9 — No Re-Registration of Same ModuleTypeID During Grace

**Statement:** A ModuleTypeID that is in the grace period MUST NOT be re-registered with a different contract during the grace period. Attempting to do so is REGISTRATION_CONFLICT.

**Verification:** Grace period lock in the registry. The lock is released when the grace period expires or the module transitions to DEREGISTERED.

---

## Section 6 — Registry State Machine

### DEF-LIFECYCLE-6 — Module Registry State

**Definition:**

A module is in exactly one of the following states:

```
REGISTERED → (deregister requested) → DEREGISTERING → (grace period expires) → DEREGISTERED
REGISTERED → (version bump) → REGISTERED (new version coexists)
DEREGISTERED → (re-registration) → REGISTERED (new contract, same ModuleTypeID allowed)
```

### INV-LIFECYCLE-10 — State Transitions Only as Defined

**Statement:** Module state transitions MUST follow the state machine defined in DEF-LIFECYCLE-6. Invalid state transitions are MODULE_STATE_VIOLATION.

**Verification:** State machine enforcement in the registry implementation. Every transition is checked against the allowed transitions.

---

## Section 7 — Glossary

| Term | Definition | Document |
|---|---|---|
| Module Contract | Immutable specification of module interface and constraints | module-lifecycle.md |
| Module Instance | Concrete execution of a module, identified by ModuleInstanceID | module-lifecycle.md |
| Registration | Adding a module to the registry | module-lifecycle.md |
| Deregistration | Removing a module from the registry with optional grace period | module-lifecycle.md |
| Version Resolution | Selecting which version to instantiate given a constraint | module-lifecycle.md |
| REGISTRATION_DUPLICATE_ID | Error when ModuleTypeID already exists | module-lifecycle.md |
| REGISTRATION_CONFLICT | Error when re-registration attempted during grace period | module-lifecycle.md |
| MODULE_STATE_VIOLATION | Error on invalid state transition | module-lifecycle.md |
| GRACE_PERIOD | Time between deregister request and actual deregistration | module-lifecycle.md |

---

## Section 8 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |