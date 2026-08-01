# Phase 11 Learned Controller and Safe Policy Improvement

**Status:** Implemented and locally verified on 2026-08-01

## Work Packages

| Package | Evidence |
|---|---|
| LRN-001 | Immutable decision examples with candidate sets, propensities, policy lineage, costs, outcomes, delayed corrections, and censoring |
| LRN-002 | Completeness, probability, overlap, duplicate, outcome, and task-split leakage validation |
| LRN-003 | Deterministic shadow outcome, cost, and risk predictor with content-addressed lineage |
| LRN-004 | Held-out outcome/cost/risk error and unseen-context shift measurement |
| LRN-005 | Constrained contextual selection and bounded exploration inside deterministic safe actions |
| LRN-006 | Clipped IPS, self-normalized IPS, doubly robust OPE, support, ESS, and sensitivity range |
| LRN-007 | Promotion rejection for poor support, estimator disagreement, calibration, confidence, or guardrail regression |
| LRN-008 | Aligned learned-versus-deterministic shadow comparison |
| LRN-009 | Low-risk-only canary, independent registry, and kill switch |
| LRN-010 | Computed regret, violations, delayed outcomes, shift, and feedback concentration monitor |
| LRN-011 | Immutable policy versions with canary/active promotion and independent rollback |

## Integration

`DNCSystem.select_learned_action()` invokes a learned policy only when its registry version is in canary or active state, the task risk is low, the kill switch is clear, and the candidate remains inside the deterministic controller's safe action set. Every other condition returns the deterministic action with an explicit guardrail reason. Registry state participates in integrated snapshots and rollback.

The learned layer does not mutate kernel authorization, policy constraints, or the deterministic controller. Its candidate propensities are returned with every learned decision for future evaluation.

## Evidence Boundary

The implementation verifies estimator mechanics and promotion rejection on deterministic fixtures. It does not establish a generally improving learned controller. Promotion in a real domain requires adequate logged support, frozen hidden evaluation, shadow outcomes, and low-risk canary evidence in Phases 15 and 16.

## Rollback

Set the learned-policy kill switch, roll back the immutable policy fingerprint, or omit canary permission. The deterministic selector remains authoritative without data or model migration.
