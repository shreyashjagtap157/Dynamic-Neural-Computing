# Evaluation Suite

## Metadata

| Field | Value |
|---|---|
| Document | evaluation-suite.md |
| Title | Evaluation Suite |
| Document ID | SPEC-EVAL |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 5 |
| Owner Question | How is DNC evaluated against baselines? |
| Last Updated | 2026-07-09 |

---

## Section 1 — Overview

The DNC runtime is a dynamic neural computation system. Its defining claim is that it outperforms static thinkers on tasks requiring runtime adaptability, replanning, and continual learning. The evaluation suite provides the empirical apparatus to test this claim: a standardized set of benchmarks, statistical protocols, and reporting formats that allow objective comparison between the DNC runtime and its baselines.

The evaluation suite serves three purposes:
1. **Capability evaluation**: Is the DNC runtime achieving its design goals on benchmark tasks?
2. **Comparison**: How does the DNC runtime compare against static thinkers and other dynamic systems?
3. **Regression detection**: Have changes to the runtime degraded previously achieved capabilities?

The suite is Layer 5 because it observes and measures runtime behavior (Layer 3) and learning outcomes (Layer 6), but does not prescribe how execution proceeds. It is the empirical counterpart to the formal verification performed in Layer 3.

---

## Section 2 — Evaluation Metrics

### DEF-EVAL-1 — Metric Taxonomy

**Definition:**

Evaluation metrics are organized into four classes:

**Class 1 — Functional Correctness:**
- Task completion rate (percentage of benchmark tasks completed successfully)
- Output quality score (task-specific, normalized to [0, 1])
- Invariant satisfaction rate (percentage of execution steps satisfying all active invariants)

**Class 2 — Dynamic Adaptability:**
- Replan frequency (replans per execution, mean and distribution)
- State preservation rate (percentage of RETAINED nodes with byte-exact state preserved across replans)
- Recovery success rate (percentage of replans that successfully resume execution without restart)
- Plan adaptation depth (percentage of graph change per replan: lower = less disruptive)

**Class 3 — Resource Efficiency:**
- Total cost per task (weighted sum of resource costs per `../layer-4-mechanisms/cost-semantics.md`)
- Latency per task (wall-clock time from task initiation to completion)
- Memory efficiency (peak working memory relative to task complexity)
- Energy efficiency (total accelerator + CPU cycles per task)

**Class 4 — Continual Learning:**
- Capability retention rate (per metric from the evaluation suite: percentage of baseline capability preserved after learning update)
- Novel task acquisition rate (improvement on new task categories not in training distribution)
- Drift bound compliance (percentage of learning updates where all Δ(p, p') ≤ DRIFT_BOUND)
- Learning cost efficiency (evaluation suite runs per knowledge base update)

### DEF-EVAL-2 — Evaluation Scenario

**Definition:**

An **evaluation scenario** is a tuple:

```
S = (scenario_id, task_class, task_description, input_distribution,
     expected_output_spec, baseline_implementations, success_criteria)
```

Where:
- `scenario_id` is a unique identifier
- `task_class` is the class this scenario belongs to (functional, adaptability, efficiency, learning)
- `task_description` is the natural language description of the task
- `input_distribution` specifies how inputs are generated
- `expected_output_spec` defines what constitutes correct output
- `baseline_implementations` lists the static-thinker implementations to compare against
- `success_criteria` specifies the pass/fail thresholds per metric

---

## Section 3 — Evaluation Protocol

### 3.A Pre-Evaluation: Baseline Locking

**INV-EVAL-1 — Baseline Version Locking**

**Statement:** Every baseline implementation used in evaluation MUST be version-locked and MUST NOT be modified after being added to the evaluation suite. A new baseline requires a new Baseline ID. The baseline implementation stored at the time of its addition is the canonical version.

**Verification:** Baseline hash verification. The evaluation runner computes the cryptographic hash of the baseline implementation and verifies it matches the stored baseline hash.

**Rationale:** If baselines can be modified after being added, comparisons over time are meaningless. This is PR-10 applied to evaluation baselines.

### 3.B Evaluation Execution

**DEF-EVAL-3 — Evaluation Run**

**Definition:**

An **evaluation run** R is:

```
R = (run_id, scenario_id, runtime_under_test, baseline_ids,
     metric_results, statistical_analysis, timestamp)
```

Where `metric_results` is the set of measured values for all metrics in DEF-EVAL-1, and `statistical_analysis` is the result of comparing against baselines.

### INV-EVAL-2 — Statistical Rigor

**Statement:** Each evaluation scenario MUST be run for a minimum of MIN_TRIAL_COUNT = 30 trials with independent random seeds. The evaluation runner MUST compute:
- Mean and standard deviation for each metric
- 95% confidence interval for the mean
- Statistical significance of the difference between DNC and each baseline (p < 0.05 by default)
- Effect size (Cohen's d) for significant differences

**Verification:** Trial count assertion. The evaluation runner MUST verify MIN_TRIAL_COUNT before producing results. Fewer trials is EVALUATION_INSUFFICIENT_DATA.

### INV-EVAL-10 — Multiple Testing Correction

**Statement:** When evaluating DNC against multiple baselines or multiple metrics, p-values MUST be corrected using the Holm-Bonferroni method to control the family-wise error rate at α = 0.05. Raw uncorrected p-values MUST be reported alongside corrected values.

**Verification:** Multiple testing correction assertion. The evaluation runner MUST apply Holm-Bonferroni correction before applying result classifications (WIN/LOSS/TIE). The correction is applied per metric class, not across all metrics globally.

**Rationale:** With 15+ metrics and 3 baselines, approximately 0.75 false-positive "significant" results are expected by chance at α = 0.05. The Holm-Bonferroni method is uniformly more powerful than Bonferroni while controlling the same family-wise rate.

### Section 3.B — Staged Evaluation Protocol

**This section defines a graduated verification approach for per-KB-update evaluation. It replaces the requirement that every KB update run the full 30-trial evaluation suite, reducing evaluation cost while maintaining statistical rigor for high-risk updates.**

### DEF-EVAL-9 — Evaluation Stage Levels

**Definition:**

The evaluation suite defines four verification stages with different trial counts and blocking behavior:

| Stage | Trials | Scenarios | Blocking? | Use Case |
|---|---|---|---|---|
| **SMOKE** | 3 | Critical scenarios (Class 1, Class 2) | Yes, blocks KB update | Low-risk KB updates (cost estimates, parameter tweaks) |
| **INTEGRATION** | 10 | Critical + Class 3 scenarios | Yes, blocks KB update | Medium-risk updates (module parameter, graph template changes) |
| **FULL** | 30 | All scenarios + novel task benchmarks | Yes, blocks KB update | High-risk updates (new module type, new planner algorithm) |
| **ASYNC** | 30 | All scenarios | No (async) | Continuous monitoring, no blocking |

### DEF-EVAL-10 — Stage Selection Function

**Definition:**

The verification stage for a KB update is determined by the update type:

```
SMOKE:       rollback, parameter_tweak, cost_estimate_change, security_patch
INTEGRATION: module_parameter_change, graph_template_change (default)
FULL:        new_module_type, new_planner_algorithm, new_module_added
ASYNC:       continuous_monitoring (non-blocking)
```

**INV-EVAL-11 — Stage Determination Is Deterministic:**
Given the same `update_type`, the stage selection function MUST return the same stage in all compliant implementations.

**INV-EVAL-12 — Full Stage Is Mandatory for High-Risk Updates:**
Any KB update involving a new module type, a new planner algorithm, or a new KB template MUST undergo FULL evaluation. FULL cannot be bypassed or substituted.

### DEF-EVAL-11 — Staged Evaluation Result

**Definition:**

Each stage produces a result:

```
SER = (stage, trial_count, metric_results, statistical_analysis,
       pass_fail, blocking_decision, next_stage_recommendation)
```

- `pass_fail`: PASS if all thresholds met; FAIL if any threshold violated
- `blocking_decision`: BLOCK if pass_fail=FAIL and stage is blocking; PROCEED if PASS; ESCALATE if evaluator recommends higher stage

### INV-EVAL-13 — Blocking Behavior by Stage

**Statement:**

- **SMOKE**: FAIL blocks the KB update; PASS allows commit
- **INTEGRATION**: FAIL blocks the KB update; PASS allows commit
- **FULL**: FAIL blocks the KB update; PASS allows commit
- **ASYNC**: Never blocks; results are logged and reviewed asynchronously

**INV-EVAL-14 — Escalation on Near-Threshold Results:**
If SMOKE or INTEGRATION produces a result within 5% of a failure threshold, the evaluator MUST recommend escalation to the next stage. Operator approval is required for escalation.

### DEF-EVAL-12 — Evaluation Cost Budget

**Definition:**

A maximum budget of EVALUATION_BUDGET = 1000 evaluation runs per rolling 7-day window is enforced. If exhausted, new KB update candidates are queued. Priority: SMOKE > INTEGRATION > FULL > ASYNC.

**INV-EVAL-15 — Budget Exhaustion Handling:**
When EVALUATION_BUDGET is exhausted, SMOKE evaluations take priority. Queued evaluations are processed FIFO when budget is restored.

### 3.C Result Classification

**DEF-EVAL-4 — Result Classification**

**Definition:**

Each metric result for DNC versus a baseline is classified as:
- **WIN**: DNC is statistically significantly better (p < 0.05, positive effect size)
- **LOSS**: DNC is statistically significantly worse (p < 0.05, negative effect size)
- **TIE**: No statistically significant difference
- **INCONCLUSIVE**: Insufficient data to determine

### 3.D Reporting

**INV-EVAL-3 — Complete Metric Reporting**

**Statement:** An evaluation report MUST include all metric results for all scenarios and all baselines. Selective reporting of only favorable metrics is EVALUATION_REPORT_INCOMPLETE and MUST be corrected before the report is used for capability claims or regression decisions.

**Verification:** Completeness check on report generation. The report MUST contain entries for every metric × scenario × baseline combination.

---

## Section 4 — Continual Learning Evaluation

### 4.A Pre-Update Baseline

**DEF-EVAL-5 — Learning Baseline Snapshot**

**Definition:**

Before a knowledge base update is committed (per `../layer-6-evolution/continual-learning.md` INV-CL-8), the evaluation suite is run against the candidate updated runtime to produce the **learning baseline snapshot** — the full set of metric values for the updated runtime.

### INV-EVAL-4 — Degradation Tolerance Check

**Statement:** For every metric m in the evaluation suite, the updated runtime's value m(p') MUST be within DEGRADATION_TOLERANCE percent of the pre-update baseline value m(p) for the same execution scenario. If any metric degrades beyond this threshold, the update is rejected per `../layer-6-evolution/continual-learning.md` INV-CL-7.

**Verification:** Degradation check as part of the learning verification protocol. The check is mandatory and automated.

### 4.B Novel Task Evaluation

**DEF-EVAL-6 — Novel Task Benchmark**

**Definition:**

A **novel task benchmark** is a scenario where:
- The task class is not represented in the training distribution of the knowledge base
- The planner has no pre-existing plan template for this task class
- Success requires either novel composition of known modules or discovery of new module combinations

### INV-EVAL-5 — Novel Task Success Requirement

**Statement:** The DNC runtime MUST successfully complete at least NOVEL_TASK_SUCCESS_RATE = 60% of novel task benchmarks within the configured resource budget and RESP_BUDGET latency constraint.

**Verification:** Novel task benchmark run. Success rate is computed over the novel task benchmark set.

### DEF-EVAL-8 — Concrete Novel Task Benchmarks

**Definition:**

The following benchmark scenarios constitute the canonical novel task benchmark set. Each satisfies DEF-EVAL-6: the task is not in the training distribution and requires novel module composition.

**NOVEL-1: Unseen Data Type Composition**
```
scenario_id: NOVEL-1
task_description: >
  Given a sequence of (image, text) paired inputs never seen together
  during training, produce a fused semantic embedding that combines
  visual and textual features. The runtime must compose a module
  pipeline from known single-modality modules without pre-defined
  fusion logic.
input_distribution: Random combination of CIFAR-10 images and Wikipedia
  text snippets, paired at 50/50 rate.
expected_output_spec: Fused embedding vectors normalized to [0,1].
  Quality assessed by downstream classification accuracy.
baseline_implementations: [StaticEmbedding, FixedFusionPipeline]
success_criteria: >
  DNC achieves ≥ 70% classification accuracy on the fused output,
  vs baseline ≤ 55%. Class 2 metrics: replan frequency < 5 per task.
```

**NOVEL-2: Out-of-Distribution Constraint Satisfaction**
```
scenario_id: NOVEL-2
task_description: >
  Given a constraint satisfaction problem (CSP) with variable types
  never seen in training (scheduling with multi-resource constraints),
  produce a valid assignment. The planner must synthesize a graph of
  known constraint-propagation modules in a novel configuration.
input_distribution: Randomly generated CSP instances with 10-50
  variables, 3-8 variable domains, and 5-20 constraints.
expected_output_spec: Valid assignment or proof of no assignment.
baseline_implementations: [FixedCSPBaseline, HeuristicSearch]
success_criteria: >
  DNC solves ≥ 80% of instances within RESP_BUDGET=100ms.
  Baseline achieves ≤ 60%. State preservation rate ≥ 95%.
```

**NOVEL-3: Cross-Domain Transfer Reasoning**
```
scenario_id: NOVEL-3
task_description: >
  Given a logical puzzle (sorting by an unseen attribute), reason
  by analogy to a structurally similar but thematically different
  domain. Requires the planner to map known reasoning modules to
  a new task structure at runtime.
input_distribution: Logical analogy tasks from the Raven's Progressive
  Matrices style, with novel rule combinations not in training.
expected_output_spec: Correct answer choice from 8 options.
baseline_implementations: [FixedReasoner, Rule-basedBaseline]
success_criteria: >
  DNC achieves ≥ 65% accuracy vs baseline ≤ 45%.
  Recovery success rate ≥ 80%.
```

**NOVEL-4: Resource-Constrained Multi-Objective Optimization**
```
scenario_id: NOVEL-4
task_description: >
  Given a multi-objective optimization problem where the objective
  weights are revealed sequentially at runtime, adapt the execution
  graph mid-execution to rebalance resource allocation between
  competing goals. Requires replanning when a new objective is
  revealed mid-execution.
input_distribution: Sequential multi-objective problems with hidden
  secondary objective revealed at step 3 of execution.
expected_output_spec: Pareto-optimal solution set.
baseline_implementations: [StaticOptimizer, FixedWeightBaseline]
success_criteria: >
  DNC's solution quality (hypervolume) is within 10% of offline
  optimal vs baseline 40% gap. Replan frequency ≥ 2 (demonstrates
  mid-execution adaptation).
```

**NOVEL-5: Unseen Failure Recovery with Partial KB**
```
scenario_id: NOVEL-5
task_description: >
  Given a module that fails in a novel failure mode not in the
  training history, recover by finding an alternative module
  composition at runtime. Tests replanning + state migration under
  novel conditions.
input_distribution: Synthetic problems injected with one of 20 unseen
  failure modes in the test module.
expected_output_spec: Task completion despite failure.
baseline_implementations: [FailoverBaseline, NoReplanBaseline]
success_criteria: >
  DNC achieves ≥ 75% task completion under novel failures.
  Baseline achieves ≤ 30%. Plan adaptation depth < 30%.
```

**NOVEL-6: Novel Modality Fusion**
```
scenario_id: NOVEL-6
task_description: >
  Given audio and depth-sensor inputs fused in a configuration
  never seen during training, produce a scene understanding.
  The planner must compose audio-processing and depth-processing
  modules without pre-defined fusion architecture.
input_distribution: Synthetic audio-depth pairs from NYU Depth v2
  with novel pairings not in training.
expected_output_spec: Scene segmentation labels with ≥ 0.7 IoU.
baseline_implementations: [AudioOnly, DepthOnly, FixedFusion]
success_criteria: >
  DNC achieves ≥ 0.72 IoU vs best baseline ≤ 0.61.
  State preservation rate ≥ 90% across replans.
```

**NOVEL-7: Time-Varying Goal Adaptation**
```
scenario_id: NOVEL-7
task_description: >
  Given a planning problem where the goal state changes at runtime
  (mid-execution), re-plan to the new goal without restarting.
  Tests continuous adaptation to shifting objectives.
input_distribution: Grid navigation tasks with goal position
  teleported at step 2 of execution.
expected_output_spec: Path to final goal position.
baseline_implementations: [StaticPlanner, RestartPlanner]
success_criteria: >
  DNC completes the task with total path length ≤ 1.3x optimal.
  Baseline restarts require ≥ 2x optimal path. Replan count ≥ 1.
```

**NOVEL-8: Adaptive Query Decomposition**
```
scenario_id: NOVEL-8
task_description: >
  Given a complex query requiring sequential reasoning steps,
  but where step dependencies are only discoverable during execution,
  decompose and execute sub-queries dynamically. Tests planner's
  ability to discover graph structure during execution.
input_distribution: Multi-hop reasoning queries from HotpotQA
  with bridge entity types not in training.
expected_output_spec: Correct answer with supporting evidence.
baseline_implementations: [FixedPipeline, RetrievalBaseline]
success_criteria: >
  DNC achieves ≥ 68% answer accuracy vs baseline ≤ 52%.
  Drift bound compliance 100% (no capability regression).
```

**NOVEL-9: Continual Tool Use with Novel API**
```
scenario_id: NOVEL-9
task_description: >
  Given a task requiring a tool whose API is not in the KB,
  discover the tool's interface by probing and adapt the execution
  graph to use it. Tests planner's ability to handle unseen
  module interfaces.
input_distribution: Tasks requiring a simulated web API with novel
  response schema, where the planner must discover the schema
  through bounded probing.
expected_output_spec: Correct task completion using the novel tool.
baseline_implementations: [NoToolBaseline, FixedToolBaseline]
success_criteria: >
  DNC achieves ≥ 60% task completion. Baseline ≤ 25%.
  Probing cost ≤ 10 probes per task.
```

**NOVEL-10: Conflicting Constraint Resolution**
```
scenario_id: NOVEL-10
task_description: >
  Given a problem with two constraints that are individually
  satisfiable but jointly unsatisfiable, detect the conflict and
  produce a best-effort resolution. The conflict type is novel.
input_distribution: Constraint satisfaction problems with induced
  conflicts not present in training distribution.
expected_output_spec: Conflict detection + optimal relaxation.
baseline_implementations: [RelaxBaseline, ExactBaseline]
success_criteria: >
  DNC detects conflict in ≤ 3 steps. Produces relaxation
  within 10% of optimal relaxation quality. Baseline either
  fails to detect (EXPLORE) or gives trivial resolution.
```

**INV-EVAL-8 — Novel Task Benchmark Completeness:**
The canonical novel task benchmark set MUST contain at least 10 scenarios. Each scenario MUST satisfy DEF-EVAL-6. The set MUST be reviewed and updated at least annually.

**INV-EVAL-9 — NOVEL_TASK_SUCCESS_RATE Per-Scenario Minimum:**
Not only the aggregate success rate (INV-EVAL-5) but also the per-scenario success rate MUST exceed 40%. A scenario with < 40% success rate across 30 trials indicates the task is out-of-distribution even for DNC and MUST be flagged for review.

---

## Section 5 — Regression Detection

### DEF-EVAL-7 — Regression

**Definition:**

A **regression** occurs when a metric that was WIN or TIE in a prior evaluation run becomes LOSS in a subsequent run, with the same scenario and baseline.

### INV-EVAL-6 — Regression Notification

**Statement:** When a regression is detected, the evaluation suite MUST emit a REGRESSION_DETECTED event to the provenance log with the affected metric, scenario, baseline, prior value, current value, and the delta. The evaluation runner MUST NOT suppress, filter, or delay this event.

**Verification:** Regression detection in the evaluation runner. Automated notification to the provenance log.

### INV-EVAL-7 — Regression Gates Execution

**Statement:** A regression in any Class 1 (Functional Correctness) metric MUST block knowledge base updates until the regression is diagnosed and resolved. Regressions in other classes are logged and reviewed, but do not block updates by default.

**Verification:** Regression gate assertion. The learning verification protocol checks Class 1 metrics first and halts on regression.

---

## Section 6 — Glossary

| Term | Definition | Document |
|---|---|---|
| Metric Taxonomy | Class 1 (Functional), Class 2 (Adaptability), Class 3 (Efficiency), Class 4 (Learning) | evaluation-suite.md |
| Evaluation Scenario | (scenario_id, task_class, task_description, input_distribution, expected_output_spec, baseline_implementations, success_criteria) | evaluation-suite.md |
| Evaluation Run | (run_id, scenario_id, runtime_under_test, baseline_ids, metric_results, statistical_analysis, timestamp) | evaluation-suite.md |
| Result Classification | WIN / LOSS / TIE / INCONCLUSIVE | evaluation-suite.md |
| Learning Baseline Snapshot | Full metric values for updated runtime before KB commit | evaluation-suite.md |
| Novel Task Benchmark | Task not in training distribution | evaluation-suite.md |
| Regression | Previously WIN/TIE metric becomes LOSS | evaluation-suite.md |
| DEGRADATION_TOLERANCE | Max metric degradation allowed for CL updates | evaluation-suite.md |
| MIN_TRIAL_COUNT | Minimum trials per scenario (30) | evaluation-suite.md |
| NOVEL_TASK_SUCCESS_RATE | Min success rate on novel tasks (60%) | evaluation-suite.md |

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| — | — | — | No amendments yet | — |