# DNC Intent Traceability Matrix

**Date:** 2026-08-01
**Status:** Updated through Phase 12 reference implementation
**Primary sources:** `docs/DNC_INTENT_VS_IMPLEMENTATION_REVIEW_HANDOFF.md`, `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md`

## Purpose

This matrix connects the owner intent to specifications, implementation targets, and verification evidence. It prevents planned cognitive-runtime capabilities from being mistaken for current kernel capabilities.

## Matrix

| Intent ID | Intent requirement | Initial artifact | Implementation target | Evidence gate |
|---|---|---|---|---|
| INTENT-001 | Preserve distinction between DNC kernel, DNC cognitive runtime, and owner-bound AI | `specs/RFC-0001-DNC-COGNITIVE-RUNTIME-PROFILE.md` | Documentation, public APIs, package boundaries | Claims identify K/C/N/E profile |
| INTENT-002 | Preserve objective, constraints, authority, risk limits, and verification policy while adapting methods | `specs/RFC-0001-DNC-COGNITIVE-RUNTIME-PROFILE.md`; `src/dnc/cognition/state.py` | Policy context and invariant records | Tests reject silent invariant changes |
| INTENT-003 | Keep structural `NO_OP` separate from task `STOP` | `specs/NO-OP-STOP-TERMINOLOGY.md` | Distinct decision records | Tests prove neither decision substitutes for the other |
| INTENT-004 | Represent typed cognitive actions | RFC action vocabulary; `src/dnc/cognition/contracts.py` | `dnc.cognition` contracts and controller proposals | Unsupported actions are rejected or reported |
| INTENT-005 | Represent explicit epistemic state | RFC and master plan Sections 7-9; `src/dnc/cognition/state.py` | Task, claim, evidence, assumption, prediction, conflict, unknown records | Property tests preserve status distinctions |
| INTENT-006 | Use calibrated risk control rather than raw model confidence | RFC evidence/confidence rules; `src/dnc/assurance/calibration.py`; `src/dnc/assurance/policy.py` | Applicability-keyed artifacts, confidence issuer, and governed thresholds | Frozen held-out reference risk-coverage fixture; real-domain evidence still required |
| INTENT-007 | Detect semantic saturation and answer novelty | Master plan Phases 5-6; `src/dnc/assurance/semantic.py`; `src/dnc/halting/policy.py` | Correlation-aware semantic clusters and adaptive halting | Correlated agreement triggers diversity; stable independent agreement can stop only with assurance gates |
| INTENT-008 | Choose active inquiry when missing evidence dominates | RFC action vocabulary; `src/dnc/cognition/controller.py` | `RETRIEVE`, `OBSERVE_OR_TEST`, `ASK` proposals | Workload where controller chooses evidence acquisition over more reasoning |
| INTENT-009 | Maintain hypotheses and falsifying tests | Master plan Phase 8; `src/dnc/semantics` | Hypothesis portfolio and predicted-observation records | Discriminating evidence rejects or updates alternatives |
| INTENT-010 | Localize failures and repair only affected dependants | Master plan Phase 9; `src/dnc/repair` | Dependency provenance, revision history, and invalidation graph | Local repair preserves independent verified work and matches full recomputation |
| INTENT-011 | Govern reusable skills through validation, versioning, quarantine, rollback, and retirement | Master plan Phase 10; `src/dnc/memory` | Skill registry, secure memory retrieval, compression, and promotion workflow | Frozen transfer fixture and version rollback; real-domain evidence remains required |
| INTENT-012 | Support interruptible and resumable cognition | Master plan Phase 11 | Best-so-far state, checkpoint, resume record | Resume avoids unnecessary recomputation and preserves evidence |
| INTENT-013 | Track capability competence, cost, permissions, failure modes, and degraded states | Master plan Phase 4; `src/dnc/cognition/capabilities.py` | Capability card registry and broker | Provider/tool dispatch negotiates features and reports unsupported capabilities |
| INTENT-014 | Treat counterfactual isolation as graded and explicit | Baseline plus master plan Phase 2 | Snapshot manifest, effect ledger, reproducibility grade | Same-state claims declare uncaptured state |
| INTENT-015 | Evaluate benefits on hidden, outcome-grounded workloads | Master plan Phase 15 | Hidden workload harness | Matched baselines and ablations support scoped claims |

## Next required updates

The next implementation milestone should adapt one provider plus one deterministic verifier through capability cards and add held-out calibration fixtures instead of relying on reference thresholds.
