# Phase 6 Attempt-Level Adaptive Reasoning and Inference Halting

**Status:** Implemented and locally verified on 2026-08-01

## Work Packages

| Package | Evidence |
|---|---|
| HLT-001 | Fixed-attempt, fixed-refinement, and self-consistency policies in `dnc.halting.policy` |
| HLT-002 | `AttemptRecord` identity, model/prompt/seed/retrieval correlation groups, semantic clusters, and atomic claims |
| HLT-003 | Deterministic adaptive policy with mandatory checks, calibrated lower bound, contradiction, stability, and marginal-value gates |
| HLT-004 | Injected, human-approved `RiskThresholdPolicy`; no global confidence constant |
| HLT-005 | Typed `SAMPLE`, `DIVERSIFY`, `VERIFY`, `RETRIEVE`, `ASK`, `STOP`, and `ABSTAIN` decisions |
| HLT-006 | Attempt/token/money/time budgets and per-attempt tail limits |
| HLT-007 | Exhaustion and unsafe fixed-policy completion produce `ABSTAIN` |
| HLT-008 | Paired matched-quality comparison, bootstrap savings interval, and critical false-stop tolerance |
| HLT-009 | Easy, hard, ambiguous, contradictory, correlated, unavailable-calibration, and shifted tests |
| HLT-010 | `DNCSystemConfig.enable_adaptive_halting`; fixed-attempt rollback remains the default |

## Integration

Phase 6 consumes Phase 5 calibrated confidence and semantic clustering, Phase 4 capability exposure through typed available actions, Phase 3 task risk and evidence requirements, and the canonical Phase 1-2 system facade. Structural `NO_OP` remains distinct from task-level `STOP`.

Every policy, including rollback baselines, must satisfy minimum task stop checks. Exhausted computation never upgrades uncertainty into correctness.

## Evidence Boundary

Local tests provide controlled paired evidence for cost reduction at matched fixture quality and zero critical false-stop increase. This is not a production or broad-domain scientific claim. Real hidden outcome-grounded workloads, provider runs, and repeated multi-domain intervals remain required for higher evidence grades.

## Rollback

Disable `enable_adaptive_halting` to use the configured fixed-attempt baseline. If its fixed computation ends without safe stopping evidence, it abstains.
