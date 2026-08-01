# Phase 8 Semantic Graph Synthesis, Active Inquiry, and Causal Experiments

**Status:** Implemented and locally verified on 2026-08-01

## Work Packages

| Package | Evidence |
|---|---|
| SEM-001 | Versioned `SemanticUnitTemplate` with schemas, capability, permissions, risk, resources, and effects |
| SEM-002 | Goal, unknown, verifier, hypothesis, and skill-driven `SemanticSynthesizer` |
| SEM-003 | Task/tenant/schema/capability/action/risk/permission/budget/provenance/isolation validation |
| SEM-004 | Deterministic semantic fingerprints, transposition deduplication, and bounded hypothesis branches |
| SEM-005 | Information-plus-decision-value experiment selection under cost/risk constraints |
| SEM-006 | Predicted observations, falsifiers, and supported/falsified/inconclusive outcomes |
| SEM-007 | Intervention, control, confounder, randomization, isolation, and outcome-access metadata |
| SEM-008 | Effectful experiments require recorded-external isolation; non-identifiability is explicit |
| SEM-009 | Frozen hidden-shift comparison against generic structural reasoning |

## Integration

Synthesis is side-effect free. `DNCSystem.apply_semantic_candidate()` validates the candidate and commits only additive semantic units/connections through the existing transaction manager. DNC-IR validation, OCC, rollback, provenance, capability health, snapshot restoration, cognitive task identity, and tenant boundaries remain authoritative.

Semantic metadata never asserts truth merely because a unit exists. Candidate outcomes separately record predicted versus observed evidence.

## Evidence Boundary

Controlled fixtures demonstrate appropriate retrieval/testing under hidden-shift shapes and complete semantic justification/prediction records. They do not establish broad causal validity or production benefit. Real experiments need the declared isolation and outcome access.

## Rollback

Disable semantic synthesis and retain the existing structural generator as a reference baseline. Applied candidates remain transactionally reversible through execution snapshots and repair phases.
