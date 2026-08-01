# Phase 1-3 Acceptance Remediation

**Date:** 2026-07-31
**Status:** Complete

The manual acceptance findings for Phases 1, 2, and 3 were repaired and
converted into regression coverage.

| Finding | Resolution |
|---|---|
| Lossy cognitive import/export | Full task, evidence, relation, hypothesis, action, view, invalidation, and event state now round-trips with an identical canonical hash; legacy `EvidenceItem` remains supported. |
| Sandbox prefix-confusion | Writable targets require an exact root or a path-segment boundary. |
| Incomplete PyTorch state | Snapshots include module parameters/buffers, optimizer, scheduler, scaler, CPU/all-device RNG, sampler state, and code/config fingerprints. |
| Unenforced lifecycles | Task, action, hypothesis, and outcome transitions enforce documented paths, terminal immutability, and idempotency. |
| Nondeterministic set hashing | Sets and frozensets are canonicalized by their normalized JSON representation. |
| Unproven reproducible builds | The reproducible build tool fixes timestamps/hash seed and normalizes sdist metadata; two independent wheel and sdist builds were byte-identical. |
| Incomplete mutable-state audit | Model, optimizer, sampler, compilation, object-store, and queue state declarations were added. |
| Runtime-state hash not enforced | Restore verifies graph and runtime hashes before mutating active system state. |
| Isolation grade overstated | In-process reference snapshots declare I1; I2 is reserved for dedicated-process isolation. |
| Secret event-log leakage | Redacted exports remove events and dependent surfaces that reference hidden records. |
| Synthetic production default | Production mode requires an explicit backend and rejects synthetic execution unless explicitly authorized. |

## Verification

- Full pytest suite passed: `255/255`, with one credential-gated live qualification skipped.
- Ruff passed across `src`, `tests`, `tools`, and `scripts` twice.
- Bytecode compilation passed twice.
- Phase 12 system audit passed: `8/8`.
- Phase 13 harness passed: `3/3`.
- Architecture conformance passed: `30/30` invariants and `34/34` tests.
- Manual round-trip, illegal-transition, sandbox prefix-confusion, and
  cross-process canonicalization probes passed.
- Offline installation and import from the built wheel passed.
- PyTorch remains unavailable on this device; its full test branch is ready to
  execute automatically in the qualified Torch environment.
