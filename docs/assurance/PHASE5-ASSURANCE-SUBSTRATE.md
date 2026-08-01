# Phase 5 Verification, Calibration, and Assurance Substrate

**Status:** Implemented and locally verified on 2026-08-01

## Scope

This phase implements the assurance inputs required by later adaptive-halting and controller phases. It does not claim that reference fixtures establish production calibration, universal correctness, or enterprise readiness.

| Work package | Implementation evidence |
|---|---|
| ASR-001 | `dnc.assurance.contracts`, `VerifierRegistry` |
| ASR-002 | Scoped format, schema, arithmetic, callable code/test, provenance/source, and policy checks |
| ASR-003 | `FunctionalVerifier` supports external, model, and human descriptors with fingerprints and independence groups |
| ASR-004 | Cost-ordered `VerifierCascade` with scope, risk, independence, budget, failure, and human-approval gates |
| ASR-005 | Append-only, tenant-scoped `OutcomeLabelStore` with delayed correction lineage |
| ASR-006 | Content-addressed `CalibrationArtifact` and applicability-keyed lifecycle registry |
| ASR-007 | Brier, log loss, reliability/ECE, selective risk, and risk-coverage metrics |
| ASR-008 | Seeded bootstrap intervals, subgroup metrics, and population-shift analysis |
| ASR-009 | Logistic, temperature, isotonic, and conformal reference implementations with explicit assumptions |
| ASR-010 | Semantic clustering with correlation-group discounting and verifier coverage |
| ASR-011 | Structured/explicit contradiction detection and shifted calibration lifecycle |
| ASR-012 | Domain/risk threshold policy requiring human approval provenance |

## Invariants

- Verifier results are scoped. Format or schema success is not factual correctness.
- Numeric `ConfidenceEstimate` values require `calibrated` or explicitly downgraded `extrapolated` applicability.
- Only a matching `CALIBRATED` held-out artifact can issue calibrated confidence.
- Fingerprint invalidation and detected shift remove artifacts from applicability.
- Correlated attempts contribute one maximum group weight rather than independent votes.
- Delayed outcomes are append-only governance evidence and are not rolled back with task-local execution snapshots.
- Risk thresholds are domain-specific and require a recorded human approval reference.

## Evidence Boundary

The frozen `phase5-held-out-v1` fixture checks the reference implementation's declared Brier, ECE, and half-coverage selective-risk targets. This is controlled local evidence only. Provider, domain, subgroup, and production claims require separately frozen real outcome datasets and higher evidence grades under the master plan.

## Rollback

Disable verifiers through the registry, invalidate calibration artifacts by fingerprint, and fall back to deterministic evidence rules, abstention, or escalation. Raw model confidence is never the fallback.
