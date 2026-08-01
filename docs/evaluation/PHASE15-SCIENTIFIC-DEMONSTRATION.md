# Phase 15 Outcome-Grounded Scientific Demonstration

**Status:** Controlled E2 reference campaign complete on 2026-08-01; independent and production evidence pending

## Work Packages

| Package | Evidence |
|---|---|
| SCI-001 | Sealed-answer evaluator interface and content-derived evaluator/workload fingerprints |
| SCI-002 | Easy, hard, ambiguity, fault, shift, composition, causal, long-horizon, delayed, and adversarial families |
| SCI-003 | Frozen controller, calibrator, evaluator, workload, runner, metric, stopping, exclusion, seed, and budget manifest |
| SCI-004 | Seven required baselines and seven required ablations under identical case budgets |
| SCI-005 | Paired effects/bootstrap intervals, risk-coverage, quality-cost Pareto, subgroup and p95 latency records |
| SCI-006 | Reproducible local rerun; independent environment/team reproduction remains unrecorded |
| SCI-007 | Content-addressed raw JSON artifact and limitations-preserving report |

## Reproduction

```powershell
$env:PYTHONPATH='src'
python scripts/benchmarks/run_phase15_scientific.py
```

Artifact: `docs/evaluation/artifacts/phase15-reference-campaign.json`

Artifact fingerprint: `65ff2b1b6d922520fd3ca001a30c4101d9eec7466774599ff0faa1257a3d1ed6`

## Controlled Results

The frozen campaign contains 10 workload families across 9 domains, 3 paired seeds, 15 system/ablation identities, and 450 outcome records. No run violated its case budget.

| Comparison | Paired effect | 95% bootstrap interval | Interpretation |
|---|---:|---:|---|
| DNC reference vs fixed-k self-consistency | 0.00 | [0.00, 0.00] | parity |
| DNC reference vs oracle reference | 0.00 | [0.00, 0.00] | quality parity; oracle fixture cost is higher |
| DNC reference vs single-pass static | +0.80 | [+0.633, +0.933] | advantage only over the weak single-pass fixture |

The DNC reference, fixed-k, fixed planner/executor, fixed refinement, ReAct loop, and structural DNC kernel all lie on the recorded Pareto frontier because they tie at quality 1.0 and average cost 1.0. Therefore this campaign does **not** establish that the complete DNC system beats strong baselines. The `no_adaptive_depth` ablation retains quality 1.0 at average cost 4.0; the other targeted ablations score 0.9 by failing their preregistered family.

## Claim Boundary

This E2 grade applies only to the controlled campaign mechanics and scoped fixture outcomes: repeated multidomain pairing, freeze integrity, budget enforcement, ablation sensitivity, uncertainty reporting, and immutable artifact generation. The runners are deterministic reference mechanisms, not production LLM/provider/tool systems. Evaluator separation is an interface boundary, not OS-enforced secrecy. No independent environment reproduction is recorded.

The historical Phase 13C adverse result remains valid and is not overwritten: the structural DNC implementation showed no quality advantage and incurred overhead on its pilot workloads. Final product claims must reconcile both artifacts and require real hidden tasks, qualified providers, independent execution, and delayed outcomes.

## Rollback

Narrow claims to E1/E0 if runner isolation, fingerprints, paired budgets, hidden outcomes, or reproducibility fail. Never retune the frozen final campaign; create a new version after design review and retain null/adverse artifacts.
