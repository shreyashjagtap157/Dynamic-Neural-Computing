# Phase 2 Snapshot and Isolation Contracts

**Date:** 2026-07-31
**Phase:** `Phase 2 — Snapshot-capable execution, isolation grades, and truthful counterfactuals`
**Status:** Reference implementation hardened through `M1-RT-001`

## Implemented contracts

| Contract | Location |
|---|---|
| `SnapshotManifest` | `src/dnc/execution/snapshot.py` |
| `ReproducibilityGrade` | `src/dnc/execution/snapshot.py` |
| `IsolationGrade` | `src/dnc/kernel/contracts.py` (compatibly re-exported) |
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
| `ReplayAdmission` / `assess_replay_admission` | `src/dnc/execution/snapshot.py` |
| `StructuralReplayResult` | `src/dnc/replay/structural_replay.py` |

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
- `I2_PROCESS_LOCAL`: dedicated-process local state isolation;
- `I3_RECORDED_EXTERNALS`: external interactions are recorded/replayed;
- `I4_SANDBOXED_ENVIRONMENT`: filesystem/network/process isolation is qualified.

## Current reference limitation

`ReferenceSnapshotManager.capture_graph` provides `R2_DETERMINISTIC_CORE` and
`I1_GRAPH_ONLY` for DNC-IR graph plus optional runtime-state dictionaries. It
does not claim dedicated-process isolation. It explicitly declares uncaptured
provider responses, filesystem, database, network, accelerator, and
process-environment state.

This prevents a graph-only clone from being mislabeled as a same-state counterfactual.

Snapshot manifest 0.2 adds integrity hashes for provider recordings and effect-ledger evidence.
Replay grades are now admitted rather than trusted from declarations alone:

- `R2` requires a captured canonical graph with matching hash and runtime-state integrity;
- `R3` additionally requires current-version evidence hashes, matching recording/effect IDs,
  captured provider responses and effect ledger, and at least `I3` isolation;
- `R4` additionally requires no uncaptured state, captured environment state, and `I4` isolation.

`ReferenceSnapshotManager.capture_recorded_execution` is the maintained R3 construction path.
Trace-only inspection remains R1 and cannot report identical re-execution. Fresh-runtime replay is
R2 for deterministic-core-only runs or R3 when recorded responses are used.

## Replay and side-effect controls

`RecordingExecutionProvider` supports:

- `RECORD`: live call through an injected provider and store successful response;
- `REPLAY`: return only a matching recorded response;
- `DENY_LIVE`: reject live calls for deterministic campaigns;
- `LIVE`: call through without recording.

`EffectLedger`, `CleanupReconciler`, and `IdempotencyRegistry` provide the first source-state preservation controls for duplicate effects and reversible cleanup.

Structural replay now reports an R2 evidence result with a canonical graph hash and verifies complete
canonical graph content rather than only unit IDs and edge counts. It does not claim external or
environment replay.
