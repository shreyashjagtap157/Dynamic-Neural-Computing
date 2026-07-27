# Repository Status

**As of:** 2026-07-27
**Status:** Stabilized research platform; enterprise and neural integration remain in development
**Package version:** `0.1.0.dev0`

## Truthful maturity statement

DNC provides a tested Python research platform for governed dynamic computation graphs. It includes a generic structural IR, mutation transactions, projection, an execution core, provider dispatch, state/checkpoint/rollback behavior, provenance, replay, control and learning policies, distributed handoff primitives, and evaluation scaffolding.

It is **not yet** an enterprise production platform, distributed model-training system, end-to-end
tensor-native dynamic-neural runtime, or proven state-of-the-art model architecture. The default
`ReferenceExecutionCore` is deterministic test infrastructure. Portable tensor contracts and an
optional PyTorch adapter exist, but graph projection, distributed training, and high-performance
serving integration remain roadmap work.

## Current verified baseline

- The authoritative pytest suite collects and passes **186/186 tests**.
- The Phase 12 canonical lifecycle audit passes **8/8**.
- The Phase 13 benchmark harness integrity audit passes **3/3**.
- Production source passes Ruff and Python byte-compilation.
- Editable package installation succeeds from `pyproject.toml`.
- Specification reference and RFC 2119 invariant-declaration checks pass.
- Architecture conformance passes: **30/30** discovered invariants have executable coverage and all **34/34** conformance tests pass.

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

## Known critical gaps

1. Benchmark task quality still uses synthetic/reference outputs and constructed adaptation bonuses;
   metadata-label precision/recall is a gate-consistency metric, not evidence of adaptation discovery.
2. Generic execution units do not yet bind the new tensor, gradient, quantization, cache, and
   compilation contracts into DNC-IR projection; optimizer and distributed-sharding contracts are
   still absent.
3. The optional PyTorch adapter is a tested foundation, not a production training backend; JAX,
   ONNX, optimizer, sharding, artifact, and serving integrations are not implemented.
4. Provider retry, streaming, cancellation, rate limiting, and accurate token/cost accounting are incomplete.
5. Durable persistence, multi-process coordination, multi-tenancy, identity/access control, secrets, artifact signing, deployment manifests, and operational SLOs remain unimplemented.
6. Load, soak, chaos, penetration, GPU, and distributed-training validation remain future release gates.

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
