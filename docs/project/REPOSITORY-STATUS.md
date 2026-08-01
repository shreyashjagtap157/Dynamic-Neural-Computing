# Repository Status

**As of:** 2026-08-01
**Status:** Integrated governed research/reference platform; external production qualification remains open
**Package version:** `0.1.0.dev0`

## Truthful maturity statement

DNC provides a tested Python research platform for governed dynamic computation graphs. The integrated reference system includes structural mutation and rollback, typed cognition and semantic synthesis, capabilities and provider dispatch, assurance and adaptive halting, learned control/repair/memory, optional adaptive neural depth, durable/distributed reference primitives, enterprise policy and operational controls, scientific evaluation, and fail-closed pilot governance.

It is **not yet** an enterprise production platform, distributed model-training system, end-to-end
tensor-native dynamic-neural runtime, or proven state-of-the-art model architecture. The default
`ReferenceExecutionCore` is deterministic test infrastructure. Portable tensor contracts and an
optional PyTorch adapter exist, but graph projection, distributed training, and high-performance
serving integration remain qualification work. Durable and enterprise components are process-local
reference implementations unless their deployment profiles explicitly bind qualified infrastructure.

## Current verified baseline

- The authoritative pytest suite passes **515 tests**, with **2 intentional environment-dependent skips**.
- The Phase 12 canonical lifecycle audit passes **8/8**.
- The Phase 13 benchmark harness integrity audit passes **3/3**.
- Production source passes Ruff and Python byte-compilation.
- Editable package installation succeeds from `pyproject.toml`.
- Specification reference and RFC 2119 invariant-declaration checks pass.
- Architecture conformance passes: **30/30** discovered invariants have executable coverage and all **35/35** conformance tests pass.
- The Phase 15 controlled hidden campaign is reproducible at evidence grade E2 with zero budget violations; it shows parity, not superiority, against the included strong reference baselines.
- The Phase 16 local readiness audit is intentionally **NO-GO** because external canary outcomes and independent human approvals are absent.

Test success establishes the implemented behavior only. It does not establish empirical superiority, state-of-the-art performance, or enterprise production readiness.

## Stabilization completed in this milestone

1. Repaired all previously failing and non-collecting tests.
2. Fixed completion-aware scheduling, bounded termination, provider dispatch, rollback, checkpoint isolation, and replay state transitions.
3. Corrected state-component exception semantics and immutable history entries.
4. Corrected IR invalid-state validation, per-graph identity permanence, deterministic serialization, failure rates, constant-sample statistics, and evaluation compatibility.
5. Extracted the canonical `DNCSystem` from a root audit script into `src/dnc/system.py`.
6. Made mutation, learning, and provenance ablations disable their actual capabilities.
7. Moved maintained audits and benchmarks into `scripts/audits/` and `scripts/benchmarks/`, and historical scripts into `scripts/legacy/`.
8. Replaced the obsolete single-platform workflow with a Linux/Windows Python 3.11–3.13 quality matrix.
9. Restored executable specification tooling and made invariant coverage part of the conformance release gate.
10. Integrated `DecisionPolicy` into every runtime Decide phase and added complete execution tracing.
11. Added executable evidence for all execution, decision-policy, formal-restore, and replay invariants.
12. Replaced hard-coded counterfactual campaign values with paired mutation-ablation measurements and
    an explicit pre-decision estimator boundary.
13. Added the full necessity-signal taxonomy, corrected no-op/recovery and assessment semantics, and
    stopped counting graph bootstrap as adaptation.
14. Integrated governed memory/skills, learned policy promotion, localized repair, semantic synthesis,
    and optional adaptive-depth execution behind explicit authority and rollback boundaries.
15. Added content-addressed persistence, durable queue/recovery, fencing/idempotency, distributed
    protocol primitives, and complete integrated snapshot/restore coverage.
16. Added workload identity, RBAC/ABAC, tenant quotas, kill switches, audit/data governance,
    telemetry/SLOs, incident runbooks, signed-artifact verification, and SBOM support.
17. Added frozen hidden evaluation with required baselines/ablations, uncertainty and subgroup
    reporting, immutable artifacts, and explicit adverse/null-result handling.
18. Added ordered offline/shadow/canary pilot governance, outcome and exercise evidence, operational
    readiness, independent fingerprint-bound approvals, rollback, and a fail-closed GA decision.
19. Started Enterprise Roadmap M1 with a packaged, versioned Generic DNC-IR JSON Schema, strict
    fail-closed schema/compatibility validation, and preserved headerless legacy deserialization.
20. Corrected conformance-report output path handling so the checked-in relative CI command and
    absolute external artifact paths both work.
21. Evolved Generic DNC-IR to schema 1.2.0 with typed ports, data/control/state/resource edge
    contracts, cardinality/schema/direction/kind validation, projection and mutation propagation,
    and explicit 1.1.0 read compatibility.
22. Evolved Generic DNC-IR to schema 1.3.0 with enforced idempotency, effect, placement, tenant,
    permission, classification, residency, trust-zone, isolation, and confidential-compute contracts;
    governed graphs now require a satisfying execution context before projection.
23. Hardened transaction payload isolation and rollback faults, canonical structural replay evidence,
    trace-only versus fresh-runtime replay claims, and snapshot 0.2 R2/R3/R4 admission with
    integrity-bound provider recording and effect-ledger evidence.
24. Added the stable Python SDK and graph CLI, packaged a versioned fingerprint-pinned plugin
    contract, and built tenant-scoped content-addressed artifact/graph registries with repeated
    governance admission.
25. Completed deterministic property and malformed-input fuzzing, process-local concurrency and
    injected-failure gates, explicit compatibility matrices, shared-graph OCC locking, and strict
    identity ingress validation for the M1 reliable generic runtime.

## Known critical gaps

1. Controlled benchmark runners still use deterministic reference mechanisms. DNC has not shown
   quality or cost superiority over the included strong baselines, and independent reproduction is open.
2. Generic execution units do not yet bind tensor, gradient, quantization, cache, and
   compilation contracts into DNC-IR projection; optimizer and distributed-sharding contracts are
   still absent.
3. The optional PyTorch adapter is a tested foundation, not a production training backend; JAX,
   ONNX, optimizer, sharding, external artifact-store, and serving integrations are not implemented.
4. Live provider behavior and real PostgreSQL/object-store/multi-process infrastructure require
   qualification in the target deployment; process-local references do not establish those claims.
5. Enterprise controls have local executable coverage but no independent penetration assessment,
   deployment-specific privacy review, or sustained operations evidence.
6. No real enterprise pilot has produced sustained E3 business outcomes or the required independent
   product/domain/research/security/privacy/operations/architecture approvals.
7. Load, soak, chaos, upgrade, penetration, GPU, and distributed-training validation remain external
   release gates for applicable profiles.

## Repository organization

- `src/dnc/`: installable production and research library.
- `tests/`: authoritative pytest, including conformance, system, and tooling tests.
- `scripts/audits/`: maintained lifecycle audits.
- `scripts/benchmarks/`: maintained benchmark campaigns and diagnostics.
- `scripts/legacy/`: historical phase/demo entry points retained for provenance; not release gates.
- `specs/`: normative and theoretical specifications.
- `docs/`: current status, research records, generated reports, and roadmap.

## Release gates

No production-ready claim is permitted until all test, lint, typing, security, schema, conformance, Linux CPU/GPU, rollback, upgrade, fault, load, soak, and security gates pass; real task-grounded benchmarks demonstrate declared compute/quality behavior; and production operations meet documented SLOs.
