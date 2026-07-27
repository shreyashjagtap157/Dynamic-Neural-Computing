# Phase 13D counterfactual validity audit

**Date:** 2026-07-27  
**Scope:** Review of the external LLM assessment and repair of the maintained sensitivity campaign

## Verdict on the external assessment

The response was directionally strong, but only partly correct.

| Claim | Verdict | Repository evidence |
|---|---|---|
| DNC is a governed structural-mutation substrate rather than a neuron simulator or ordinary agent framework. | Correct. | The frozen architecture defines unified state, structural mutation, deterministic projection, and separated authorities. |
| The stack has seven axioms, seven frozen/approved stack entries, six authorities, macro/micro loops, and computation-tailored ACID transactions. | Substantially correct. | These elements are explicitly present in the frozen specifications, though “ACID” is a project model rather than evidence of a production database-grade implementation. |
| Campaign counterfactual values were constants and its calibration MAE was therefore not meaningful estimator calibration. | Correct. | The old campaign assigned `0.75`, `0.73`, and `0.82/0.72`; it did not evaluate either counterfactual branch. |
| The generator implemented only two necessity signals. | Partly correct. | It had two historical utility flags plus bootstrap, connectivity, specialization, composition, and capacity conditions. It did not implement the named explicit evidence taxonomy. |
| Default context directly caused mutation every cycle. | Incorrect diagnosis. | After bootstrap, a stable graph should have produced no proposal. Repeated mutation actually arose because prediction error (`observed utility - expected utility`) was mislabeled as improvement and fed back as `prior_mutation_harmed`. |
| Precision/recall were meaningful before the repair. | Incorrect. | The “decision” was inferred from aggregate mutation count, while W4 and W7 were marked adaptation-required by their evaluators but omitted from the oracle-label function. Even after alignment, the metric measures metadata-label adherence because the gate and oracle consume the same task flags. |
| W5 and W7 had not been run by the maintained campaign. | Incorrect for the inspected checkout. | `CampaignOrchestrator.workloads` already contained W1–W8. The historical workload-audit document was stale. |
| DNC’s empirical thesis remains unproven. | Correct. | Reference systems return synthetic outputs and workload evaluators assign constructed base scores and adaptation bonuses rather than measuring real task correctness. |

## Corrections implemented

1. Added explicit objective, constraint, capacity, degradation, fault, environment-shift, and
   composition necessity signals.
2. Wired task observations into those signals and made stable `NO_OP` cycles successful rather than
   recovery failures.
3. Separated one-time graph bootstrap operations from adaptation mutation counts.
   Benchmark ablations now receive the same validated pre-treatment base graph, avoiding an empty-
   graph confound in the mutation-disabled branch.
4. Corrected assessment semantics: improvement is now measured against prior observed utility;
   prediction error is recorded separately.
5. Corrected W4 and W7 oracle labels to agree with their workload definitions.
6. Replaced constant telemetry with a pre-decision estimator interface and a transparent
   evidence-derived baseline.
7. Measures realized run-level counterfactual value using paired DNC-Full and mutation-disabled
   DNC-M trajectories with the same workload and seed.
8. Added JSON export and methodology metadata that disclose the metric’s causal and benchmark scope.

## R=30 verification snapshot

The repaired 1,680-run synthetic campaign completed on 2026-07-27:

- metadata-label adherence: precision **1.000**, recall **1.000**, F1 **1.000**;
- paired-estimator MAE: **0.0511**;
- paired-estimator RMSE: **0.0628**;
- mean run-level decision regret: **0.0221**;
- stable workloads W1, W2, and W6: **zero non-bootstrap DNC-Full mutations**;
- W7 synthetic composite score: DNC-Full **0.8560**, StaticDAG/Replanner **0.8300**.

These figures verify control-gate behavior and campaign plumbing only. The perfect classification is
expected because the generator and oracle use the same explicit metadata. The W7 result is not proof
of task superiority: its evaluator grants an adaptation bonus when mutation occurs, and the reference
execution core does not solve a real composition task. Wall-clock latency also affects composite
quality and is not controlled as a hardware benchmark. Even on that constructed score, DNC-Full's
W7 margin is approximately **0.0260**, below the external reviewer's proposed **0.05** threshold.

## What remains necessary for a scientific claim

1. Replace metadata oracle flags with outcome-grounded interventions and hidden change points.
2. Evaluate candidate mutation and no-op branches from serialized identical state, or randomize
   authorization where ethically and operationally safe.
3. Train any learned value estimator on Campaign A and freeze it before Campaign B.
4. Use real outputs with blinded correctness metrics; do not award quality merely for mutating.
5. Report confidence intervals, effect sizes, paired tests, hardware, warm-up, and complete artifacts.
6. Demonstrate gains on real distribution-shift, fault, composition, and long-horizon workloads
   against strong replanning and conditional-computation baselines.

The correct bottom line is therefore: the external reviewer found the largest telemetry defect and
correctly rejected the empirical claim, but overstated the generator diagnosis, metric validity, and
untested-workload claim. The repaired campaign is honest infrastructure; it is still not evidence that
DNC is state of the art.
