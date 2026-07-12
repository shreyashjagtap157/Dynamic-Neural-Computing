# Computation-Aware Evaluation Framework

## Metadata

| Field | Value |
|---|---|
| Document | evaluation-framework.md |
| Title | Computation-Aware Evaluation Framework |
| Document ID | SPEC-EVAL-AWARE |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | How does DNC measure computation quality, not just output quality? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md, interfaces.md, execution-trace-format.md, conformance-model.md |
| Defines | Computation-Aware Evaluation, Metric Hierarchy, Dynamic Compute Index, Counterfactual Compute Gain, Adaptivity Metrics |
| Referenced by | mvp-roadmap.md |

---

## Section 1 — Overview

### 1.A The Problem with Output-Only Evaluation

Traditional AI evaluation measures only **what the model output** — accuracy on MMLU, GPQA, SWE-bench, AIME. This is necessary but insufficient for adaptive computation systems.

An execution trace reveals:
- How much computation was used
- How the execution graph adapted to the input
- Whether the compute path was justified
- How efficiently resources were allocated
- How the system recovered from failures

**Computation-Aware Evaluation** is the DNC evaluation paradigm that measures not just output quality, but the intelligence with which computation was allocated.

### 1.B Definition

> **Computation-Aware Evaluation** is the formal framework for evaluating adaptive AI execution. It measures not just what answer was produced, but what execution path, resources, adaptations, and recovery behaviors produced it.

Computation-aware evaluation encompasses:
- Dynamic compute allocation (did the system use more computation for harder inputs?)
- Verification (was the output checked before returning?)
- Recovery (did the system recover from failures?)
- Rollback (did the system correctly undo bad decisions?)
- Budget adaptation (did the system adjust to resource constraints?)
- Counterfactual efficiency (was the compute path justified vs. simpler alternatives?)

### 1.C Research Contribution

Computation-aware evaluation is the primary research contribution of DNC. While adaptive computation research exists (Duo-LLM, MoE routing, adaptive depth), it is measured almost exclusively by output accuracy. DNC contributes a formal framework for measuring **how intelligently** computation is allocated, not just whether the answer is correct.

---

## Section 2 — Metric Hierarchy

### 2.A Four-Level Classification

All computation-aware metrics are classified into four levels. This hierarchy keeps evaluation papers readable and ensures metrics are not misapplied.

```
Level 0 — Infrastructure
  (objective, directly measurable)
  latency, tokens, memory, cost

Level 1 — Execution
  (observable runtime behavior)
  graph depth, graph width, parallelism, replans, rollbacks

Level 2 — Adaptivity
  (the novel research contribution)
  Dynamic Compute Index
  Counterfactual Compute Gain
  Budget Elasticity
  Graph Entropy
  Planning Stability
  Tool Diversity

Level 3 — Outcome
  (traditional evaluation)
  accuracy, verifier score, human preference, benchmark score
```

### 2.B Level Separation Principle

**Level 2 metrics MUST NOT be computed from Level 3 metrics.** Level 2 is about how computation was allocated, not about whether the answer is correct. Conflating these produces misleading conclusions about adaptive computation.

For example:
- **Valid:** "The system achieved DCI=1.3 and accuracy=87%" (Level 2 + Level 3 independently)
- **Invalid:** "accuracy / total_tokens = DCI" (DCI is not simply accuracy divided by cost)

### 2.C Metric Classification Registry

| Metric | Level | Category | Definition |
|---|---|---|---|
| Latency | 0 | Infrastructure | Wall-clock execution time |
| Tokens | 0 | Infrastructure | Total tokens consumed |
| Memory | 0 | Infrastructure | Estimated memory usage |
| Cost | 0 | Infrastructure | Estimated cost in USD |
| Graph Depth | 1 | Execution | Maximum DAG depth at execution |
| Graph Width | 1 | Execution | Maximum parallelism (max concurrent nodes) |
| Parallelism | 1 | Execution | Average nodes executing concurrently |
| Replan Count | 1 | Execution | Number of REPLAN decisions |
| Rollback Count | 1 | Execution | Number of ROLLBACK decisions |
| **Dynamic Compute Index** | 2 | **Adaptivity** | Compute efficiency vs. baseline |
| **Counterfactual Compute Gain** | 2 | **Adaptivity** | Gain vs. simpler alternatives |
| **Budget Elasticity** | 2 | **Adaptivity** | Output quality sensitivity to budget |
| **Graph Entropy** | 2 | **Adaptivity** | Diversity of execution paths |
| **Planning Stability** | 2 | **Adaptivity** | Consistency of graph synthesis |
| **Tool Diversity** | 2 | **Adaptivity** | Distribution of module types used |
| Accuracy | 3 | Outcome | Task completion correctness |
| Verifier Score | 3 | Outcome | Verification pass rate |
| Human Preference | 3 | Outcome | Human evaluation score |
| Benchmark Score | 3 | Outcome | Standard benchmark performance |

---

## Section 3 — Level 2 Adaptivity Metrics (The Core Contribution)

### 3.A Dynamic Compute Index (DCI)

**Definition:** MET-DCI-1

The Dynamic Compute Index measures how effectively compute budget is used relative to output quality, normalized against a fixed reference baseline.

```
DCI = (OutputQuality / ComputeBudgetSpent) / (BaselineQuality / BaselineBudget)
```

Where:
- `OutputQuality` ∈ [0, 1] — normalized task performance
- `ComputeBudgetSpent` — total resource budget consumed
- `BaselineQuality` and `BaselineBudget` — from a fixed reference execution

**Interpretation:**
- DCI > 1.0: More efficient than baseline
- DCI = 1.0: Same efficiency as baseline
- DCI < 1.0: Less efficient than baseline

**Example:** If a task achieves quality 0.85 with 100 tokens (DCI = 0.85/100), and the baseline achieves quality 0.70 with 50 tokens (baseline = 0.70/50), then:
```
DCI = (0.85/100) / (0.70/50) = 0.0085 / 0.014 = 0.607
```
The system is less efficient than baseline despite higher absolute quality.

### 3.B Counterfactual Compute Gain (CCG)

**Definition:** MET-CCG-1

Counterfactual Compute Gain measures how much better the selected execution graph performed compared to the simplest alternative that achieves comparable output quality.

```
CCG = Score(selected_graph) - Score(simplest_alternative)

where simplest_alternative = min{compute_cost(g) | Score(g) >= threshold}
```

**Interpretation:**
- CCG > 0: The additional graph complexity contributed to higher quality
- CCG ≈ 0: A simpler graph could have achieved the same result — the extra modules were unnecessary
- CCG < 0: The simpler graph actually performed better

**Example:**
- Graph A (Planner → Reasoner → Verifier): Score=0.95, Cost=150 tokens
- Graph B (Planner → Reasoner): Score=0.94, Cost=60 tokens
- CCG = 0.95 - 0.94 = 0.01 (small positive — verification added marginal value)
- CCG is positive but small; the planner should learn that verification adds diminishing returns for simple tasks

The significance of CCG is that it directly measures whether the execution graph was worth its compute cost. This is much closer to "intelligent computation allocation" than simply counting nodes or measuring accuracy.

### 3.C Budget Elasticity

**Definition:** MET-BE-1

Budget Elasticity measures how output quality changes in response to changes in available compute budget.

```
BE = ΔQuality / ΔBudget = (Q_high - Q_low) / (B_high - B_low)
```

**Interpretation:**
- High BE: Small budget changes cause large quality changes — the system is highly responsive to compute availability
- Low BE: Budget changes have little effect on quality — the system is either over-provisioned or robust
- Negative BE: More budget produces worse quality — the system is misbehaving

Budget Elasticity reveals whether the system adapts appropriately to resource constraints.

### 3.D Graph Entropy

**Definition:** MET-GE-1

Graph Entropy measures the diversity of execution paths across a set of inputs.

```
GE = H(G) = -Σ p(g_i) * log(p(g_i))
```

where `p(g_i)` is the probability of execution graph `g_i` being selected for a random input, estimated from a sample of traces.

**Interpretation:**
- High GE: The system uses diverse execution graphs for different inputs — it adapts to input characteristics
- Low GE: The system uses similar execution graphs regardless of input — it is not adaptive
- GE = 0: The system always uses the same graph — no adaptation

Graph Entropy measures the system's willingness to use different computational strategies for different problems.

### 3.E Planning Stability

**Definition:** MET-PS-1

Planning Stability measures the consistency of execution graph synthesis for similar inputs.

```
PS = 1 - (|G_a Δ G_b| / |G_a ∪ G_b|)
```

where `G_a` and `G_b` are the execution graphs for two similar inputs, and `Δ` is the symmetric difference.

**Interpretation:**
- PS = 1.0: Identical graphs for similar inputs
- PS > 0.8: High stability — the planner is consistent
- PS < 0.5: Low stability — the planner is erratically synthesizing different graphs for similar inputs

### 3.F Tool Diversity

**Definition:** MET-TD-1

Tool Diversity measures how evenly the system's computation is distributed across different module types (capabilities).

```
TD = H(C) = -Σ p(c_i) * log(p(c_i))
```

where `p(c_i)` is the fraction of total compute budget spent on capability `c_i`.

**Interpretation:**
- High TD: Compute is evenly distributed across capabilities — the system uses a diverse set of modules
- Low TD: Compute is concentrated in one or two capabilities — the system is specialized

---

## Section 4 — Metric Computation

### 4.A Computation Requirements

All Level 2 metrics require:
- Execution traces from multiple runs (minimum 30 trials per scenario, per INV-EVAL-6)
- Comparison baselines (reference executions with fixed graphs)
- Statistical significance testing (p < 0.05, per INV-EVAL-7)

### 4.B Metric Computation API

```python
class AdaptivityMetrics:
    """Computation of Level 2 adaptivity metrics."""

    def compute_dci(
        self,
        traces: List[ExecutionTrace],
        baseline_traces: List[ExecutionTrace],
    ) -> Dict[str, float]:
        """Compute DCI across a set of traces."""

    def compute_ccg(
        self,
        trace: ExecutionTrace,
        alternative_graphs: List[ExecutionGraph],
        score_fn: Callable[[ExecutionGraph, Any], float],
    ) -> float:
        """Compute CCG for a single trace."""

    def compute_budget_elasticity(
        self,
        traces_high: List[ExecutionTrace],  # High budget traces
        traces_low: List[ExecutionTrace],   # Low budget traces
    ) -> Dict[str, float]:
        """Compute budget elasticity across budget levels."""

    def compute_graph_entropy(
        self,
        traces: List[ExecutionTrace],
    ) -> float:
        """Compute graph entropy across traces."""

    def compute_planning_stability(
        self,
        trace_a: ExecutionTrace,
        trace_b: ExecutionTrace,
    ) -> float:
        """Compute planning stability between two traces."""

    def compute_tool_diversity(
        self,
        traces: List[ExecutionTrace],
    ) -> Dict[str, float]:
        """Compute tool diversity across traces."""
```

---

## Section 5 — Evaluation Protocol

### 5.A Computation-Aware Evaluation Protocol

The computation-aware evaluation protocol extends the existing evaluation protocol in `evaluation-suite.md`:

```
1. Collect traces
   For each scenario:
       Run execution 30+ times
       Collect ExecutionTrace for each run

2. Compute Level 0 (Infrastructure) metrics
   From resource snapshots in each trace

3. Compute Level 1 (Execution) metrics
   From execution graph records in each trace

4. Compute Level 2 (Adaptivity) metrics
   From computed Level 0 and Level 1 metrics
   Require statistical significance (p < 0.05)

5. Compute Level 3 (Outcome) metrics
   From final outcomes in each trace

6. Report separately by level
   Do not combine Level 2 and Level 3 metrics
   Report significance confidence intervals
```

### 5.B Reporting Requirements

A computation-aware evaluation report MUST:

- Report Level 0 metrics as baseline descriptive statistics (mean, median, p95, p99)
- Report Level 1 metrics as distributions
- Report Level 2 metrics with 95% confidence intervals and sample sizes
- Report Level 3 metrics with statistical significance vs. baselines
- Clearly separate Level 2 from Level 3
- Explain what each metric means in plain language

---

## Section 6 — Conformance Clause

An implementation conforms to this specification if:

- All metrics in Section 2.C are implemented with correct computation formulas
- The metric hierarchy in Section 2.A is maintained (Level 2 metrics are not computed from Level 3 metrics)
- The evaluation protocol in Section 5 is followed for all evaluations
- Statistical significance testing (p < 0.05) is applied to all Level 2 metric claims
- The reporting requirements in Section 5.B are satisfied

Extensions are permitted for new Level 0 and Level 1 metrics using the MET-* namespace. Level 2 and Level 3 metric additions require Architecture v1.x approval.

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| EVAL-AWARE-AMEND-001 | evaluation-framework.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of Computation-Aware Evaluation, metric hierarchy (4 levels), Level 2 adaptivity metrics (DCI, CCG, Budget Elasticity, Graph Entropy, Planning Stability, Tool Diversity), evaluation protocol, reporting requirements. | No |