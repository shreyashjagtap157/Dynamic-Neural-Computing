# Phase 3 Cognitive Contracts

**Date:** 2026-07-31
**Phase:** Phase 3 - Canonical cognitive contracts and epistemic state
**Status:** Reference implementation complete

## Scope

Phase 3 adds an additive cognitive-state layer above the stable kernel and
snapshot substrate. It represents task intent, evidence, hypotheses, action
records, outcomes, confidence estimates, and semantic references to DNC-IR
units without changing graph identity or DNC-IR hashes.

## Implemented Work Packages

| Work package | Status | Evidence |
|---|---|---|
| `COG-001` contracts and schemas | Complete | `src/dnc/cognition/contracts.py`; `src/dnc/cognition/canonical.py` JSON Schema 2020-12 dictionaries |
| `COG-002` normalization and hashing | Complete | `canonical_json`, `canonical_hash`, `task_fingerprint`; tests prove DNC-IR hashes remain separate |
| `COG-003` `TaskSpec` normalization and clarification | Complete | normalized objective, `ambiguous_task_fields`, `ClarificationRequest` |
| `COG-004` append-only epistemic items and relations | Complete | `CognitiveState.with_epistemic_item`, `EvidenceRef`, `EpistemicRelation` |
| `COG-005` hypothesis portfolio | Complete | `Hypothesis`, predicted observations, strongest falsifier, accepted-for-action distinction |
| `COG-006` state machines | Complete | task, action, hypothesis, and outcome transition validators plus event-backed, idempotent action transitions |
| `COG-007` rationale codes | Complete | `RationaleCode` blocks hidden chain-of-thought labels |
| `COG-008` DNC-IR references | Complete | `IRUnitReference`; cognitive hashes do not alter graph serialization |
| `COG-009` invalidation/materialized views | Complete | dependency invalidation marks descendants/views stale without deleting history |
| `COG-010` import/export and migration | Complete | lossless full-state `export_cognitive_state`/`import_cognitive_state`, legacy evidence compatibility, and `migrate_phase3_draft_0` |
| `COG-011` redaction/security labels | Complete | tenant consistency checks and `redacted_export` tests |

## Integration

`DNCSystem` now accepts an optional `CognitiveState`. Phase 2 snapshots include
the cognitive-state hash in runtime metadata, while restore and graph identity
remain governed by the kernel snapshot manager. This keeps Phases 1, 2, and 3
integrated as one system without conflating semantic truth with graph structure.

## Scope Notes

- JSON Schema support is represented as canonical schema dictionaries; no
  runtime dependency on a third-party JSON Schema validator is introduced.
- Import/export covers the Phase 3 canonical schema and a `phase3-draft-0`
  migration fixture.
- Security enforcement is tenant/label propagation and redaction at the
  cognitive-record layer; it is not a complete policy engine.
