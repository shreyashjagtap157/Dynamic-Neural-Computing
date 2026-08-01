# M1 Reliable Generic Runtime — Robustness Report

**Date:** 2026-08-01

**Work package:** `M1-QA-001`

**Branch:** `phase/m1-reliable-generic-runtime`

## Decision and scope

The planned property, fuzz, concurrency, failure, and compatibility campaign is implementable on the
existing M1 architecture. It does not require a new runtime service or a core package dependency.
Hypothesis is confined to the development profile; concurrency and injected-failure behavior remains
implemented with the Python standard library and existing kernel error contracts.

This gate covers the reliable Generic DNC-IR runtime delivered in M1. It does not claim distributed,
GPU, live-provider, penetration, load, soak, or external-infrastructure qualification.

## Reproducible property and fuzz profile

The campaign declares `hypothesis>=6.136.9,<7` in the development extra and pins the observed test
environment to Hypothesis 6.164.0 plus SortedContainers 2.4.0.

Every checked-in property test uses:

- 60 bounded examples per property;
- deterministic generation (`derandomize=True`);
- no local example database (`database=None`);
- no timing deadline;
- bounded recursive JSON values and bounded graph sizes.

This keeps pull-request runs reproducible while retaining Hypothesis generation and shrinking. The
explicit regression vectors remain checked in even when a generated counterexample is fixed.

## Coverage matrix

| Area | Exercised property or failure | Required result |
|---|---|---|
| DNC-IR canonicalization | Generated unit/edge insertion orders and finite JSON metadata | Byte-identical canonical JSON and content reference |
| DNC-IR round trip | Generated valid acyclic graphs | Canonical serialize/read/serialize equality |
| Projection | Generated valid graphs | Complete unit order and no structural mutation |
| Transaction commit | Generated batches of caller-owned units | Commit isolation after caller mutation |
| Transaction failure | Generated staged mutations followed by an invalid operation | Byte-identical active graph and deterministic rollback state |
| Malformed-input fuzz | Recursive JSON, non-finite numbers, arbitrary JSON text, and targeted nested-field mutation | Success or `DNCValidationError`; no incidental parser exception |
| Artifact registry concurrency | Concurrent duplicate and distinct writes/reads | One immutable descriptor per tenant/digest |
| Graph registry concurrency | Concurrent registration and load | One canonical descriptor and valid repeated reads |
| Plugin concurrency | Concurrent loads of one admitted manifest | Manifest-pinned instances only |
| Transaction concurrency | 24 writers using one explicit base version through independent managers | Exactly one commit; all stale writers fail OCC |
| Storage failures | Put failure, malformed digest, malformed read, invalid restore | No orphan descriptor, stable validation error, atomic restore |
| Plugin failures | Resolver, factory, and contract-inspection faults | `DNCCapabilityError` and unchanged admission state |
| Rollback failure | Injected staging compensation failure | Active graph unchanged; transaction reports `FAILED` |
| Compatibility | Headerless, DNC-IR 1.1.0, 1.2.0, and 1.3.0 | Normalize to one canonical 1.3.0 content reference |
| Replay compatibility | Snapshot manifest 0.1.0 and 0.2.0 | Legacy R2 retained; legacy R3 overclaim denied |
| Future versions | Future IR, snapshot, and plugin API values | Fail closed without guessing |

## Hardening completed

- Added process-local locking to the content store and artifact/graph/plugin descriptor registries.
- Added one per-graph transaction lock shared across `TransactionManager` instances, preserving OCC
  semantics for concurrent writers without embedding an uncopyable lock in graph state.
- Made invalid-operation and rollback-failure paths deterministic while preserving the active graph.
- Normalized JSON, nested DNC-IR, plugin resolution/factory, and plugin-contract inspection failures
  into maintained kernel error categories.
- Required content-store adapters to return valid lowercase SHA-256 digests before descriptor commit.
- Made store restore validation and replacement atomic.
- Enforced normalized, non-empty identity values and non-negative integer graph-version components.

The shrinking campaign found and retained one concrete parser defect: `sub_units: [null]` previously
created `UnitID(None)` and failed only during later serialization. Identity construction now rejects
the malformed value at the ingress boundary as `DNCValidationError`.

## Verification evidence

- `python -W error -m pytest -q`: 515 passed, 2 intentional environment-dependent skips.
- M1 robustness module: 30 test functions passed, including hundreds of generated examples.
- Full Ruff and Python byte-compilation gates passed.
- Phase 12 system lifecycle audit: 8/8 passed.
- Specification reference and RFC 2119 checks passed.
- Architecture conformance: 30/30 invariants covered, 35/35 conformance tests passed, 4/4 ACDs
  resolved.
- Two independent release builds produced byte-identical wheels and source archives; the final wheel
  also passed a no-dependency installation, SDK/schema import, and `dnc` console launch.

## Residual limits

- Thread tests validate process-local behavior; they do not substitute for multi-process or
  distributed-store linearizability tests.
- Bounded property/fuzz tests are a deterministic pull-request gate, not an unbounded security-fuzzing
  campaign.
- Registry descriptor indexes remain process-local and require later durable adapter qualification.
- In-process plugins remain trusted code even after manifest fingerprint and authority admission.
- External provider, object-store, database, GPU, load, soak, chaos, and penetration gates remain
  applicable to later deployment profiles.
