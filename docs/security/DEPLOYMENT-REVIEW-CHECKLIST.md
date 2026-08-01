# Deployment Review Checklist

- [ ] Threat model reviewed by an independent security owner.
- [ ] Data classes, residency, retention, deletion, legal hold, and key ownership approved.
- [ ] Non-owner PostgreSQL forced-RLS negative tests pass.
- [ ] Workload identity, credential expiry, rotation, revocation, RBAC, and ABAC are exercised.
- [ ] OPA or equivalent policy versioning, outage behavior, and rollback are exercised.
- [ ] Shell, code, database, browser, network, provider, and accelerator sandbox/egress tests pass.
- [ ] Prompt injection, excessive agency, poisoning, replay, tenant escape, and denial-of-wallet campaigns pass.
- [ ] OTel export is redaction-tested and audit retention does not leak secrets or tenant data.
- [ ] SLOs, dashboards, error budgets, on-call ownership, runbooks, and kill switches are exercised.
- [ ] Backup encryption, key rotation, point-in-time recovery, deletion, and disaster recovery pass.
- [ ] Locked dependencies, SBOM, signatures, build provenance, scanning, and exception expiry are verified.
- [ ] Privacy impact, compliance mapping, accessibility, model card, and system card are independently reviewed.
- [ ] Critical/high findings are closed or formally accepted with owner, expiry, and compensating control.
