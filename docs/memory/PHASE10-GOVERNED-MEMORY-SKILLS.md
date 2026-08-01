# Phase 10 Governed Memory, Skills, and Cognitive Compression

**Status:** Implemented and locally verified on 2026-08-01

## Work Packages

| Package | Evidence |
|---|---|
| MEM-001 | Separate working, episodic, semantic, procedural, calibration, and audit stores |
| MEM-002 | Expiry, tombstoned deletion, legal hold, tenant ACLs, labels, and provenance |
| MEM-003 | Trust/freshness/domain/security filtering and mandatory exact reranking for critical retrieval |
| MEM-004 | Immutable, fingerprinted `SkillManifest` and governed lifecycle registry |
| MEM-005 | Draft induction only from tenant-local verified positive episodes with negative cases retained |
| MEM-006 | Sandbox, evaluation, shadow, canary, activation, quarantine, version rollback, and kill switch |
| MEM-007 | Dependency, model, and policy fingerprint invalidation for memories and skills |
| MEM-008 | Tenant-safe compression with provenance, preservation declarations, and information-loss gates |
| MEM-009 | Frozen transfer fixture covering positive/harmful transfer, stale retrieval, poisoning, and continuity |

## Integration

`DNCSystem` owns `GovernedMemory` and `SkillRegistry` instances. Both participate in execution snapshots and rollback alongside DNC-IR, cognition, and capability state. Retrieval is tenant-scoped and security-filtered; critical retrieval additionally requires integrity verification and an exact reranker. Only permission-compatible, domain-compatible, qualified active skills are reusable.

Skill promotion is ordered and evidence-gated. Activating a new version retires the previous active version, and rollback restores only a previously evaluated, qualified parent. Drift quarantines affected skills and tombstones affected memory records.

## Evidence Boundary

Deterministic held-out fixtures demonstrate the mechanics and threshold enforcement. They are not evidence of broad production transfer. Domain-specific positive transfer and poisoning resistance remain claims to establish with Phase 15 hidden, outcome-grounded evaluation.

## Rollback

Disable a skill ID, quarantine affected versions, restore the qualified parent version, disable a memory namespace, or restore the integrated execution snapshot. Canonical episodes remain the recomputation source.
