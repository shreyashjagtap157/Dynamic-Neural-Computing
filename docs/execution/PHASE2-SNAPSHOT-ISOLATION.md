# Phase 2 Snapshot and Isolation Contracts

**Date:** 2026-07-31
**Phase:** `Phase 2 — Snapshot-capable execution, isolation grades, and truthful counterfactuals`
**Status:** Initial reference slice

## Implemented contracts

| Contract | Location |
|---|---|
| `SnapshotManifest` | `src/dnc/execution/snapshot.py` |
| `ReproducibilityGrade` | `src/dnc/execution/snapshot.py` |
| `IsolationGrade` | `src/dnc/execution/snapshot.py` |
| `EffectLedgerEntry` | `src/dnc/execution/snapshot.py` |
| `ProviderRecording` | `src/dnc/execution/snapshot.py` |
| `ReferenceSnapshotManager` | `src/dnc/execution/snapshot.py` |
| `RecordingExecutionProvider` | `src/dnc/execution/snapshot.py` |
| `EffectLedger` | `src/dnc/execution/snapshot.py` |
| `CleanupReconciler` | `src/dnc/execution/snapshot.py` |
| `IdempotencyRegistry` | `src/dnc/execution/snapshot.py` |
| `CancellationToken` | `src/dnc/execution/snapshot.py` |
| `ExecutionDeadline` | `src/dnc/execution/snapshot.py` |
| `SharedStateDeclaration` | `src/dnc/execution/snapshot.py` |
| `SandboxPolicy` | `src/dnc/execution/snapshot.py` |
| `PyTorchSnapshotManager` | `src/dnc/execution/torch_snapshot.py` |

## Grade definitions

Reproducibility:

- `R0_NONE`: no replay claim;
- `R1_MANIFEST_ONLY`: manifest describes state but cannot replay it;
- `R2_DETERMINISTIC_CORE`: process-local deterministic core state is captured;
- `R3_RECORDED_EXTERNALS`: external responses are recorded;
- `R4_ENVIRONMENT_REPLAY`: qualified environment replay is available.

Isolation:

- `I0_NONE`: no isolation claim;
- `I1_GRAPH_ONLY`: graph clone only;
- `I2_PROCESS_LOCAL`: process-local deterministic state is isolated;
- `I3_RECORDED_EXTERNALS`: external interactions are recorded/replayed;
- `I4_SANDBOXED_ENVIRONMENT`: filesystem/network/process isolation is qualified.

## Current reference limitation

`ReferenceSnapshotManager.capture_graph` provides `R2_DETERMINISTIC_CORE` and `I2_PROCESS_LOCAL` for DNC-IR graph plus optional runtime-state dictionaries. It explicitly declares uncaptured provider responses, filesystem, database, network, accelerator, and process-environment state.

This prevents a graph-only clone from being mislabeled as a same-state counterfactual.

## Replay and side-effect controls

`RecordingExecutionProvider` supports:

- `RECORD`: live call through an injected provider and store successful response;
- `REPLAY`: return only a matching recorded response;
- `DENY_LIVE`: reject live calls for deterministic campaigns;
- `LIVE`: call through without recording.

`EffectLedger`, `CleanupReconciler`, and `IdempotencyRegistry` provide the first source-state preservation controls for duplicate effects and reversible cleanup.
