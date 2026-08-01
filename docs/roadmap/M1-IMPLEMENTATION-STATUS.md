# M1 Reliable Generic Runtime — Implementation Status

**Updated:** 2026-08-01

**Branch:** `phase/m1-reliable-generic-runtime`

**Starting commit:** `2b5fb84`

**Current state:** M1 in progress; `M1-IR-001` through `M1-IR-003` and `M1-RT-001` complete

## Completed work package

### M1-IR-001 — Versioned Generic DNC-IR and schemas

- Packages the canonical Draft 2020-12 structural-graph schema with the Python distribution.
- Validates complete schema headers before deserialization and rejects partial, foreign, malformed,
  future, or otherwise unshipped versions.
- Preserves only the frozen headerless legacy compatibility path, including its original defaults.
- Validates the stable graph envelope without introducing a mandatory runtime dependency.
- Leaves graph semantics and invariant validation under `DNCIRValidator`; this point does not merge
  interchange validation with execution authorization.

The completion commit is the commit titled `Add versioned Generic DNC-IR schema validation`; resolve
its exact ID with `git log --oneline --grep='Add versioned Generic DNC-IR schema validation' -1`.

### M1-IR-002 — Typed ports and edge contracts

- Evolves canonical Generic DNC-IR output from 1.1.0 to 1.2.0 while retaining both packaged schemas.
- Adds frozen port records with per-unit identity, input/output direction,
  data/control/state/resource kinds, JSON-like
  data contracts, and explicit one/optional/many cardinalities.
- Requires complete source/target bindings for typed units and rejects missing ports, wrong direction,
  edge-kind mismatch, schema mismatch, duplicate edges, and cardinality violations.
- Preserves untyped legacy units and edges, and explicitly reads versioned 1.1.0 documents with empty
  port defaults.
- Propagates port bindings through deterministic serialization, executable projection, structural
  connect/disconnect, compensation, and rewire operations.

The completion commit is the commit titled `Add typed DNC-IR ports and edge contracts`; resolve its
exact ID with `git log --oneline --grep='Add typed DNC-IR ports and edge contracts' -1`.

### M1-IR-003 — Execution-governance contracts

- Evolves canonical Generic DNC-IR output to 1.3.0 while retaining packaged 1.1.0 and 1.2.0 schemas
  and explicit readers that supply safe defaults for their missing declarations.
- Consolidates `SideEffectClass`, `EffectType`, and `IsolationGrade` at the kernel boundary while
  preserving existing cognition/execution import paths.
- Adds typed idempotency modes/scopes, side-effect classes and compensation/isolation requirements,
  hard and preferred placement declarations, tenant/permission/label/classification/residency/trust
  security declarations, and a concrete `ExecutionContext`.
- Rejects effectful units without duplication control, irreversible effects without strong dispatch
  semantics, cross-tenant edges, classification downgrades, residency/trust conflicts, and impossible
  local-input placement.
- Requires governed graphs to receive a satisfying execution context before projection; tenant,
  permission, isolation, region, device, runtime, capability, trust-zone, residency, and confidential
  compute requirements fail closed, while placement preferences remain non-blocking.
- Propagates governance declarations into executable nodes and deterministic snapshot serialization.

The completion commit is the commit titled `Enforce DNC-IR execution governance contracts`; resolve
its exact ID with `git log --oneline --grep='Enforce DNC-IR execution governance contracts' -1`.

### M1-RT-001 — Atomic rollback and explicit replay grades

- Deep-isolates operation payloads before staging application so caller-owned objects cannot mutate
  committed graph state, and converts graph/operation copy faults into deterministic failed or
  rolled-back transaction results without active-state mutation.
- Strengthens structural replay verification from ID/count comparison to complete canonical 1.3.0
  content equality and emits an R2 result with canonical hash and failure index/reason.
- Classifies trace-only inspection as R1 and prevents it from reporting identical re-execution;
  fresh-runtime deterministic replay reports R2 or R3 depending on recorded-response evidence and can
  enforce a caller-required minimum grade.
- Versions snapshot manifests to 0.2 while reading 0.1, adds canonical provider-recording and
  effect-ledger hashes, and provides explicit admission decisions with stable reason codes.
- Provides a maintained R3 recorded-execution capture path and rejects tampered graphs, recordings,
  effects, incomplete captured-state declarations, insufficient isolation, and R4 environment
  overclaims.

The completion commit is the commit titled `Harden atomic rollback and replay grade admission`;
resolve its exact ID with
`git log --oneline --grep='Harden atomic rollback and replay grade admission' -1`.

## Verification evidence

- `python -W error -m pytest -q`: 437 passed, 2 intentional environment-dependent skips.
- `python -m compileall -q src`: passed.
- `python -m ruff check src tests tools/generate_conformance_report.py`: passed.
- `PYTHONPATH=src python scripts/audits/phase12_system_audit.py`: 8/8 passed.
- Specification reference and RFC 2119 checks: passed.
- Architecture conformance: 30/30 invariants covered, 35/35 tests passed, 4/4 ACDs resolved.
- A locally built wheel contains all supported 1.1.0, 1.2.0, and 1.3.0 structural-graph schemas.

## Claims and residual risks

This work supports a versioned and packaged Generic DNC-IR envelope plus typed port/edge validation.
It does not yet provide a general schema migration framework beyond the explicit 1.1.0/1.2.0 readers,
nor does it complete M1's SDK, registry, property, fuzz, concurrency, or broader failure-testing
commitments. The headerless legacy path is intentionally less strict and should be migrated before
any future removal.

Rollback of `M1-IR-002` returns canonical output to 1.1.0; consumers needing rollback must avoid
persisting 1.2.0-only port bindings or first project them to an explicitly untyped legacy profile.

Rollback of `M1-IR-003` returns canonical output to 1.2.0. Consumers must not persist 1.3.0-only
governance declarations if they require that rollback, because silently dropping execution security
requirements is not an allowed migration.

Rollback of `M1-RT-001` removes snapshot 0.2 evidence hashes and replay admission. Persisted 0.2
manifests must be retained or explicitly downgraded only to claims supported by 0.1 fields; R3/R4
claims must not survive such a downgrade.

## Exact next point

Implement `M1-SDK-001`: define a versioned plugin manifest and loader boundary, a stable Python SDK
facade, a minimal CLI for graph validate/inspect/project operations, and content-addressed artifact and
graph registries. Keep optional plugins out of the core dependency set, enforce schema/governance at
registration and load time, and add compatibility plus command-level failure tests.
