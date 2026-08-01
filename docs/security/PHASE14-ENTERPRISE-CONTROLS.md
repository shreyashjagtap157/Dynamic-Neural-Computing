# Phase 14 Enterprise Security, Policy, Observability, and Operations

**Status:** Locally implementable reference controls verified on 2026-08-01; external and independent qualification pending

## Work Packages

| Package | Evidence |
|---|---|
| ENT-001 | Versioned threat model with assets, boundaries, attack classes, controls, and residual risks |
| ENT-002 | Short-lived tenant identities, RBAC/ABAC, credential references, and tenant quotas |
| ENT-003 | Exact stable policy input and versioned external-policy protocol boundary |
| ENT-004 | Existing sandbox/effect controls plus independent exact-scope high-impact approval |
| ENT-005 | Stable telemetry event/export protocol, recursive redaction, provenance-compatible immutable audit log |
| ENT-006 | Computed SLO/error budget records, incident runbooks, and action/capability/model/skill/tenant/global kill switches |
| ENT-007 | Key-version rotation, residency enforcement, deletion tombstones, legal hold, and backup security boundaries |
| ENT-008 | Content digests, external signature verification boundary, provenance reference, and SBOM contract |
| ENT-009 | Injection, agency, poisoning, tenant, replay, identity, audit leakage, and denial-of-wallet tests |
| ENT-010 | Privacy/compliance/accessibility/system-card checklist documented; independent reviews remain external |

## Integration

Enterprise audit, data-governance, and kill-switch state participates in `DNCSystem` snapshots. The canonical execution, inference, semantic-control, repair, memory, learned-policy, and neural entry points fail closed when a global or applicable scoped switch denies work. Policy decisions never consume untrusted prompt or retrieved content as authorization fields.

## Operational Profile

Reference SLOs are expressed per risk/workload profile and must cover availability, completion, delayed outcome, calibrated coverage, abstention, latency, cost, cancellation, cleanup, audit completeness, and tenant isolation. Deployment dashboards should alert on calibration drift, verifier disagreement, denial spikes, budget overruns, retry storms, stale skills, tenant anomalies, cleanup failure, and delayed-outcome deterioration.

## Evidence Boundary

Local tests and source review found and repaired mutable audit export, secret-value leakage, unqualified approval, asset overwrite, and unenforced kill-switch paths. The Codex Security connector was unavailable in this tool context, so no independent scanner report is claimed. External IAM, secret manager, OPA, KMS, OTel collector, deployment sandbox, SBOM signing, penetration test, privacy/compliance/accessibility review, and independent risk acceptance remain required before enterprise pilot promotion.

## Rollback

Use action, capability, model, skill, tenant, or global kill switches; restore the integrated snapshot; revoke identity/approval/credential versions; rotate keys; and route to the deterministic local profile. Preserve redacted audit and incident evidence.
