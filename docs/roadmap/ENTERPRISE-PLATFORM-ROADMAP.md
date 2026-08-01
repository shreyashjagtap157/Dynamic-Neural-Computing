# Enterprise DNC Platform Roadmap

## Product definition

DNC will be a substrate-neutral, governed runtime for dynamically constructing, authorizing, executing, learning, evaluating, and reusing computation graphs, with first-class neural training and inference backends.

## Architectural principles

1. Integrate with existing technology; do not replace mature tensor, compiler, cluster, database, identity, or observability systems.
2. Keep proposal, authorization, transaction, execution, assessment, and learning authorities separate.
3. Treat `NO_OP` as a first-class decision.
4. Separate ephemeral routing decisions, session adaptations, and persistent mutations.
5. Version structural, parameter, execution, and learning state independently.
6. Make every performance or state-of-the-art claim workload-, budget-, hardware-, and commit-specific.
7. Keep the core lightweight and integrations optional.

## Milestones

### M0 — Truthful repository foundation — COMPLETE

- standard package metadata and reproducible dependencies;
- one pytest entry point and nonzero failure status;
- stable public imports and schema policy;
- Linux-first CI matrix plus Windows;
- accurate generated status/conformance evidence;
- one canonical runtime extracted from phase scripts.

### M1 — Reliable generic runtime — COMPLETE

- versioned Generic DNC-IR and schemas — **COMPLETE (`M1-IR-001`)**;
- validated ports and data/control/state/resource edges — **COMPLETE (`M1-IR-002`)**;
- idempotency, side-effect, placement, and security contracts — **COMPLETE (`M1-IR-003`)**;
- atomic transaction/rollback and explicit replay grades — **COMPLETE (`M1-RT-001`)**;
- plugin SDK, CLI, Python SDK, artifact and graph registry — **COMPLETE (`M1-SDK-001`)**;
- property, fuzz, concurrency, failure, and compatibility tests — **COMPLETE (`M1-QA-001`)**.

`M1-IR-001` adds a packaged canonical JSON Schema, strict semantic-version and
compatibility-header validation, dependency-free envelope validation, explicit rejection of
partial/future/foreign schema claims, and continued support for the frozen headerless legacy format.
See [the M1 implementation status](M1-IMPLEMENTATION-STATUS.md) for validation evidence and handoff.
`M1-IR-002` evolves the canonical interchange format to 1.2.0 with typed ports, explicit edge-port
bindings, all four normative edge kinds, cardinality and schema validation, duplicate-edge rejection,
projection/mutation propagation, and an explicit 1.1.0 read-compatibility path.
`M1-IR-003` evolves canonical interchange to 1.3.0, consolidates shared effect/isolation types,
adds idempotency/effect/placement/security declarations, rejects unsafe unit and cross-edge
combinations, requires an authorized execution context before governed projection, and preserves
1.1.0/1.2.0 read compatibility.
`M1-RT-001` isolates submitted operation payloads, converts copy faults into deterministic rollback,
strengthens structural replay to canonical-content verification, distinguishes trace inspection from
fresh-runtime replay, and admits R2–R4 only from matching snapshot evidence.
`M1-SDK-001` adds a packaged versioned plugin-manifest contract, fingerprint-pinned least-authority
loading, a stable Python SDK facade, a machine-readable graph CLI, and tenant-scoped content-addressed
artifact/graph registries with repeated schema and governance admission.
`M1-QA-001` adds reproducible generated and malformed-input campaigns, shared-graph OCC and registry
thread-safety, injected storage/plugin/rollback failures, explicit IR/snapshot/plugin compatibility
matrices, and retained regression cases for every discovered defect. M1 is complete at the reliable
process-local generic-runtime boundary; M2 begins real model/tool/retrieval execution work.

### M2 — Real LLM reasoning runtime

- real local/provider model units, retrieval, tools, verifier, aggregation and termination;
- streaming, cancellation, deadlines, budgets and fallbacks;
- dynamic task DAGs and task-grounded benchmarks;
- vLLM and normalized provider compatibility.

### M3 — Tensor-native neural runtime — FOUNDATION STARTED

- PyTorch backend first; JAX and ONNX profiles next;
- portable tensor, gradient, compilation, precision, quantization, cache, and checkpoint contracts
  now exist, together with the first optional PyTorch adapter;
- tensor shape/dtype/layout/device contracts;
- parameter, buffer, gradient, precision, quantization, sharding, compilation and KV-cache policies;
- variable depth, recurrent blocks, learned halting, expert and adapter routing;
- low-overhead compiled token controller.

### M4 — Training platform integration

- forward/loss/backward/optimizer/data-pipeline semantics;
- mixed precision, accumulation, clipping, activation checkpointing;
- FSDP/DeepSpeed/Megatron-compatible adapters;
- complete distributed checkpoints including RNG, sampler, optimizer, controller and graph state;
- structural-policy and consolidation training.

### M5 — Distributed enterprise deployment

- durable metadata and artifact stores;
- idempotent event protocols, leases, fencing, backpressure and recovery;
- Kubernetes/Ray/Slurm adapters rather than a new cluster manager;
- OpenTelemetry traces/metrics/logs, SLOs and runbooks;
- multi-tenancy, OIDC, RBAC/ABAC, mTLS, secrets, signed artifacts and audit exports;
- containers, Helm, SBOM, vulnerability scans and provenance attestations.

### M6 — Safe consolidation and lifelong adaptation

- recurring-subgraph mining and distillation;
- sandbox training and held-out evaluation;
- signed registry promotion, canaries and automated rollback;
- transfer, forgetting, bloat, oscillation and long-horizon evaluation.

## Initial compatibility targets

- Training: PyTorch, Hugging Face, FSDP, DeepSpeed; later JAX/TensorFlow adapters.
- Formats: SafeTensors, ONNX, Protocol Buffers, JSON, Arrow/Parquet for analytics.
- Serving: vLLM, Triton, ONNX Runtime, TGI and llama.cpp adapters.
- Operations: Kubernetes, Ray, Slurm, PostgreSQL, S3-compatible storage, Kafka/NATS.
- MLOps: MLflow and optional external experiment/registry adapters.
- Observability: OpenTelemetry and Prometheus-compatible metrics.

Targets are adapters, not mandatory hard dependencies.

## Enterprise release gates

A production release requires passing unit, integration, conformance, property, fuzz, distributed, provider, GPU, security, load, soak, upgrade, rollback and chaos suites on declared platforms. It also requires documented SLOs, threat model, disaster recovery, retention/privacy controls, compatibility policy and reproducible benchmark bundles.
