# DNC Threat Model

**Version:** 2026-08-01.phase14.v1
**Scope:** DNC kernel, cognitive runtime, providers, tools, memory/skills, learned policies, neural exits, persistence, workers, telemetry, and administrative controls

## Protected Assets

- task objectives, evidence, epistemic state, memory, and tenant data;
- policy, authorization, approvals, budgets, and kill-switch state;
- DNC-IR, checkpoints, model/skill/policy versions, and calibration artifacts;
- provider/tool credentials, object-store content, event history, and audit records;
- outcome and evaluation integrity used for learning, promotion, and release claims.

## Trust Boundaries

1. User, retrieved, provider, model, memory, and tool content is untrusted data.
2. Stable policy inputs are constructed only from authenticated identity and trusted system state.
3. Capability dispatch crosses provider/tool boundaries and requires exact version, permission, risk, and domain checks.
4. Worker and network delivery is at-least-once; idempotency, fencing, outbox/inbox, and reconciliation are authoritative.
5. Tenant identifiers and security labels must be enforced in process and by PostgreSQL forced RLS in qualified deployments.
6. Promotion of skills, learned policies, neural exits, and releases crosses an evidence/authority boundary.
7. Audit and telemetry cross an observability boundary and must be redacted before export.

## Threats And Controls

| Threat | Primary controls | Verification |
|---|---|---|
| Prompt injection changes policy or tool authority | Exact stable policy schema; untrusted content excluded; capability permissions remain authoritative | Injection cannot add permissions or fields |
| Excessive agency or irreversible action | Risk limits, side-effect classes, independent scoped approval, sandbox/effect ledger, reconciliation | Self/stale/wrong-scope approval denied |
| Cross-tenant disclosure or confused deputy | Tenant-bound identities, ACL/label filters, composite keys, forced RLS migration, tenant-scoped snapshots | Negative repository, memory, object, audit, worker tests |
| Replay and duplicate side effects | Idempotency keys, OCC, transactional outbox/inbox, fencing tokens, immutable results | Duplicate/conflicting/stale delivery tests |
| Memory or skill poisoning | Provenance, integrity verification, trust/freshness filters, held-out promotion, quarantine and drift invalidation | Poisoning and harmful-transfer fixtures |
| Learned-policy reward hacking | Deterministic guardrail, logged propensities, OPE agreement/support gates, low-risk canary, kill switch | Promotion rejection and rollback tests |
| Unsafe neural early exit | Domain/risk/model calibration, finite confidence, full-depth fallback, capability qualification | Shift, adversarial confidence, risk, kill-switch tests |
| Secret or PII leakage in telemetry | Recursive key and bearer/value redaction, tenant audit access, retention and legal hold | Redaction and defensive-copy tests |
| Denial of wallet or retry storm | Tenant quotas, budgets, deadlines, bounded retries, action/capability/tenant/global switches | Quota, deadline, lease, monitor tests |
| Artifact or supply-chain tampering | Content hashes, external signature-verifier boundary, provenance, SBOM record | Digest/signature callback and corruption tests |
| Snapshot/backup tampering | Canonical hashes, content-addressed objects, restore validation | Corruption and integrated restore tests |

## Residual Risks

- Reference stores and authorizers are process-local; production enforcement requires qualified PostgreSQL non-owner roles, IAM, secret manager, KMS, and policy service adapters.
- Regex telemetry redaction reduces common leakage but is not a complete DLP system.
- Signature verification depends on an external cryptographic verifier and key-trust policy.
- Provider, browser, shell, database, accelerator, container, network, and region isolation require deployment-specific penetration and chaos testing.
- Model and application correctness are not established by infrastructure controls.

Critical or high findings block pilot promotion unless independently reviewed and explicitly accepted with owner, scope, expiry, and compensating controls.
