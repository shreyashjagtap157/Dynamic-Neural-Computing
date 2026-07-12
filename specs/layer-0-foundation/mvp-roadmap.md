# DNC MVP Roadmap

| Field | Value |
|---|---|
| Document | mvp-roadmap.md |
| Title | Minimum Viable Product Roadmap |
| Document ID | SPEC-ROADMAP |
| State | Frozen |
| Version | Baseline v1.0 |
| Layer | 0 |
| Owner | DNC Specification |

---

## Section 1 — Overview

This roadmap defines the phased delivery plan for the DNC reference
runtime. Phases 0–4 cover the original MVP. The implementation
extended through Phase 7 (distributed handoffs) per the
architecture-v1.0 extension.

## Section 2 — Phase Summary

| Phase | Scope | Original Estimate |
|---|---|---|
| Phase 0 | Specification freeze | 8–12 weeks |
| Phase 1 | Core execution engine | 16–24 weeks |
| Phase 2 | Dynamic planning and scheduling | 20–32 weeks |
| Phase 3 | Observability and self-improvement | 24–40 weeks |
| Phase 4 | Production hardening | 12–20 weeks |
| Phase 5 | Architecture v1.0 reference runtime | (extension) |
| Phase 6 | Continual learning hardening | (extension) |
| Phase 7 | Distributed handoffs | (extension) |

## Section 3 — Phase 1 Scope (Core Execution Engine)

Per `layer-3-execution/` and `layer-4-mechanisms/`:

- Module registry with single-ownership (INV-4) ✅
- Execution state machine ES(t) = (W, M, C, H, R) ✅
- State management: copy-on-write W, append-only H, checkpoints ✅
- Scheduler: topological dispatch, precondition enforcement ✅
- Module contract validation ✅
- Runtime invariant enforcement (INV-1 to INV-11) ✅
- Bootstrap invariant verifier (G-12.3, INV-8) ✅

**Not in Phase 1:** planning/replanning, control loop, cost semantics.

## Section 4 — Phase 2 Scope (Dynamic Planning)

### Section 4.C — Exit Criteria

- Planner pipeline: 4 phases (TaskAnalysis → ModuleSelection →
  GraphConstruction → Validation) ✅
- Replanning protocol (INV-REPLAN-1 to INV-REPLAN-12) ✅
- Control loop Observe → Decide → Act → Assess (INV-CTRL-1 to
  INV-CTRL-14) ✅
- Cost semantics with forecast-triggered replan (INV-REPLAN-4) ✅
- Scheduler backpressure for ASYNC_PENDING (INV-CTRL-9c) ✅
- Planner version tracking in execution header (INV-PLANNER-9) ✅

## Section 5 — Phase 3 Scope (Observability)

### Section 5.C — Exit Criteria

- Provenance event recording with causal chains, hash integrity ✅
- Failure classification (INVALID_OUTPUT, GPU_RECOVERY,
  PARTIAL_FAILURE per INV-FAIL-5) ✅
- Failure rate tracking per module type ✅
- Evaluation suite: MIN_TRIAL_COUNT=30, paired t-test ✅
- Drift bounds (k-means normalized Euclidean, INV-CL-10) ✅
- Knowledge-base versioning, root-cause rollback (INV-CL-13) ✅
- Rollback circuit-breaker (INV-CL-17) ✅

## Section 6 — Phase 4 Scope (Production Hardening)

### Section 6.F — Exit Criteria

- RegressionMonitor with automated rollback trigger ✅
- BiasEvaluationFramework (PR-15): 4 fairness metrics ✅
- Runtime integration of RegressionMonitor ✅
- Bias evaluation blocks deployment/KB update on violation ✅

## Section 7 — Phase 5 Scope (Architecture v1.0 Runtime)

- DecisionPolicy interface + RulePolicy reference impl ✅
- ExecutionProvider interface + ReferenceProvider ✅
- ExecutionTrace schema with full record structure ✅
- ReplayEngine for deterministic replay ✅
- Five execution providers: Ollama, vLLM, OpenAI, Anthropic,
  Gemini ✅
- ComputationMonitor: Level 0–2 metrics (DCI, CCG, Budget
  Elasticity, Graph Entropy, Planning Stability, Tool Diversity) ✅
