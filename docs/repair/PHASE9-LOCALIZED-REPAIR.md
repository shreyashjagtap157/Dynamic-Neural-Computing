# Phase 9 Dependency-Aware Localized Repair and Recovery

**Status:** Implemented and locally verified on 2026-08-01

## Work Packages

| Package | Evidence |
|---|---|
| RPR-001 | Typed dependency-cut analysis with deterministic topological closure |
| RPR-002 | Invalid/stale propagation across claims, plans, actions, outputs, memories, and skills |
| RPR-003 | Local repair, rollback, recompute, ask, and abstain candidates |
| RPR-004 | Execution snapshots and full-state rollback around repair transactions |
| RPR-005 | Per-item reverification and affected-view closure validation |
| RPR-006 | Explicit worker, provider, and tool failure recovery policy |
| RPR-007 | Correctness, precision, preservation, and avoided-recomputation metrics |
| RPR-008 | Frozen stale-evidence and adversarial cross-tenant corruption tests |

## Integration

`DNCSystem.repair_cognitive_state()` computes the affected closure from the cognitive provenance graph, captures an execution snapshot, recomputes and reverifies every affected claim in dependency order, and restores the snapshot on any failure. Successful repairs preserve unaffected DNC-IR and cognitive state. Superseded epistemic revisions are retained as invalid history while corrected revisions become current.

Repair does not bypass DNC-IR validation, tenant isolation, policy, transaction, or snapshot controls. Materialized outputs are considered repaired only when every dependency in their closure is current.

## Evidence Boundary

The local evaluation proves equivalence to a deterministic full recomputation fixture and measures avoided work. It does not claim production recovery quality for arbitrary providers; provider-specific recovery requires outcome-grounded qualification.

## Rollback

Disable the repair entry point and use full execution-snapshot restoration or full recomputation. Failed localized repair already performs this rollback atomically.
