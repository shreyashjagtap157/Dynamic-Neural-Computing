# Phase 4 Capability Registry, Broker, and Adapters

**Date:** 2026-08-01
**Status:** Reference implementation complete

## Work Packages

| ID | Status | Evidence |
|---|---|---|
| `CAP-001` | Complete | Versioned capability cards, lifecycle, health, expiry, registry, and kill switch in `dnc.capabilities`. |
| `CAP-002` | Complete | Deterministic broker filters action, risk, permissions, locality, features, domain calibration, competence, cost, latency, token budget, and availability; every rejection is reason-coded. |
| `CAP-003` | Complete | OpenAI, Ollama, and vLLM compatibility providers are exposed through provider-neutral adapters and card factories. |
| `CAP-004` | Complete | Explicit feature rejection, structured-output checks, tool forwarding, buffered stream events, pre/post-call cancellation, split usage, local rate limits, wall-time-bounded deadlines, bounded retry, and circuit breaking. |
| `CAP-005` | Complete | Deterministic verifier/tool/reference capability wrapper and deterministic cards. |
| `CAP-006` | Complete | Human clarification/approval capability with role and authority-scope enforcement. |
| `CAP-007` | Complete | Lazy PyTorch capability card records availability and a platform/backend fingerprint without importing Torch into core startup. |
| `CAP-008` | Contract prototype complete | JAX and ONNX prototype cards truthfully report availability and remain separate-environment, degraded prototypes. |
| `CAP-009` | Complete | Recorded/fake-provider contract suite is default; `DNC_LIVE_PROVIDER_QUALIFICATION=1` enables real Ollama, vLLM, or OpenAI qualification. |
| `CAP-010` | Complete | Provider cards use stable provider capability IDs; model/version fingerprint replacement emits change events and invalidates matching calibration. |

## Behavioral Boundaries

- Compatibility adapters expose buffered streaming as ordered start/delta/terminal
  events. Native incremental SSE transport remains provider-specific and is not
  claimed by the reference adapter.
- Hosted-provider calls are never made by the default test suite.
- Unsupported features and actions return typed error codes before dispatch.
- Cancellation or partial failure produces a terminal event and never promotes
  partial output into a successful response.
- A timed-out synchronous provider call may continue in a daemon worker because
  Python cannot forcibly stop arbitrary transport code; its output is discarded,
  the response is `TIMEOUT`, and no successful task-state promotion occurs.
- Optional backend discovery uses module metadata only; core installation keeps
  zero required third-party runtime dependencies.

## Rollback

Any capability can be disabled immediately through
`CapabilityRegistry.disable(capability_id)` without removing its audit record.

## Verification

- Focused Phase 1-4 acceptance suite: `66` passed, one live qualification skipped.
- Full project suite: `255` passed, one live qualification skipped.
- Ruff, bytecode compilation, and `git diff --check`: passed.
- Phase 12 system audit: `8/8` passed.
- Phase 13 harness: `3/3` passed.
- Architecture conformance: `30/30` invariants and `34/34` tests passed.
- Two independent builds produced byte-identical wheel and sdist artifacts.
