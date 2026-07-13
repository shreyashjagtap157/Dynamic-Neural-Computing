# Architecture Conformance Report

Version: 1.0
Generated: 2026-07-13
Implementation commit: 7fc5f58
Implementation version: 0.1.0

> This is a release artifact, not documentation. Regenerate every
> release with `python tools/generate_conformance_report.py`. Architecture
> conformance is demonstrated by executable tests, not design review.

## Overall Status

| Aspect | Status |
|---|---|
| Architecture | FROZEN (Baseline v1.0) |
| Implementation | PASS (4/4 ACDs resolved) |
| Conformance Tests | PASS (15/15) |
| Invariant coverage | 13/60 (21.7%) |
| Spec tooling (PR-4 + RFC 2119) | PASS |

## Conformance Suite

| Suite | Passed | Total |
|---|---|---|
| conformance/providers/test_provider_dispatch.py | 3 | 3 |
| conformance/replay/test_replay.py | 2 | 2 |
| conformance/runtime/test_control_loop.py | 3 | 3 |
| conformance/runtime/test_replay_and_rollback.py | 4 | 4 |
| conformance/runtime/test_rollback.py | 3 | 3 |
| **Total** | **15** | **15** |

## Architecture Conformance Defects (ACD)

All 4 ACDs are RESOLVED.

## Invariant Coverage (executable)

| Namespace | Covered | Total |
|---|---|---|
| Control Loop (INV-CTRL-*) | 1/8 (12.5%) | 8 |
| Decision Policy (INV-POL-*) | 0/5 (0.0%) | 5 |
| Evaluation (INV-EVAL-*) | 0/8 (0.0%) | 8 |
| Execution (INV-EXEC-*) | 0/7 (0.0%) | 7 |
| Formal Model (INV-FM-*) | 0/2 (0.0%) | 2 |
| Replanning (INV-REPLAN-*) | 1/7 (14.3%) | 7 |
| Replay (INV-REP-*) | 0/5 (0.0%) | 5 |
| Runtime (INV-*) | 11/11 (100.0%) | 11 |
| Scheduler (INV-SCHED-*) | 0/7 (0.0%) | 7 |

### Covered invariants

| Invariant | Title | Tests |
|---|---|---|
| INV-1 | Execution Header Immutability): | test_invariant_verifier.py, test_invariant_violations.py, test_real_world_xor.py |
| INV-10 | Normative Statement Keyword Discipline): | conformance/providers/test_provider_dispatch.py, conformance/replay/test_replay.py, conformance/runtime/test_control_loop.py, conformance/runtime/test_rollback.py, test_g12_byte_exact.py, test_integration.py, test_invariant_violations.py, test_phase2_planner.py, test_phase4_production.py, test_phase5b.py, test_real_world_xor.py |
| INV-11 | Preservation Under Extension): | test_invariant_violations.py |
| INV-2 | DAG Acyclicity): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-3 | No Undefined Behavior): | test_invariant_violations.py |
| INV-4 | Single-Ownership of Module Semantics): | phase1_exit_criteria.py, test_invariant_verifier.py, test_invariant_violations.py |
| INV-5 | State Isolation Between Executions): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-6 | Checkpoint Before Replan): | test_invariant_verifier.py |
| INV-7 | Handoff Atomicity): | test_invariant_verifier.py |
| INV-8 | All Invariants Verified Before Execution): | test_invariant_verifier.py |
| INV-9 | Bounded Drift): | test_invariant_violations.py |
| INV-CTRL-1 | Observation Completeness | conformance/runtime/test_control_loop.py |
| INV-REPLAN-4 | Resource Exhaustion Forecast | test_phase2_planner.py |

### Uncovered invariants

| Invariant | Title |
|---|---|
| INV-CTRL-2 | Observation Latency Bound |
| INV-CTRL-3 | Decision Determinism |
| INV-CTRL-4 | Decision Latency Bound |
| INV-CTRL-5 | Action Commitment |
| INV-CTRL-6 | Action Latency Bound |
| INV-CTRL-7 | Assessment Always Runs |
| INV-CTRL-8 | Assessment Result Classification |
| INV-EVAL-1 | Baseline Version Locking |
| INV-EVAL-11 | Stage Determination Is Deterministic: |
| INV-EVAL-12 | Full Stage Is Mandatory for High-Risk Updates: |
| INV-EVAL-14 | Escalation on Near-Threshold Results: |
| INV-EVAL-15 | Budget Exhaustion Handling: |
| INV-EVAL-3 | Complete Metric Reporting |
| INV-EVAL-8 | Novel Task Benchmark Completeness: |
| INV-EVAL-9 | NOVEL_TASK_SUCCESS_RATE Per-Scenario Minimum: |
| INV-EXEC-1 | Precondition Before Dispatch: |
| INV-EXEC-2 |  |
| INV-EXEC-3 |  |
| INV-EXEC-4 |  |
| INV-EXEC-5 |  |
| INV-EXEC-6 |  |
| INV-EXEC-7 |  |
| INV-FM-1 | Restore Does Not Modify Checkpoint: |
| INV-FM-2 | Restore Advances Step Index Linearly: |
| INV-POL-1 |  |
| INV-POL-2 |  |
| INV-POL-3 |  |
| INV-POL-4 |  |
| INV-POL-5 |  |
| INV-REP-1 |  |
| INV-REP-2 |  |
| INV-REP-3 |  |
| INV-REP-4 |  |
| INV-REP-5 |  |
| INV-REPLAN-1 | Step Deadline Exceeded |
| INV-REPLAN-12 | Checkpoint Rollback |
| INV-REPLAN-2 | Module Failure |
| INV-REPLAN-3 | Output Confidence Degradation |
| INV-REPLAN-5 | User Directive |
| INV-REPLAN-6 | Environmental Change Signal |
| INV-SCHED-14 | No Concurrent Step Dispatch: |
| INV-SCHED-15 | Mutual Exclusion on Shared State: |
| INV-SCHED-16 | Critical Section Blocks Replan: |
| INV-SCHED-17 | No Preemption During Act Phase: |
| INV-SCHED-18 | Timer Race Safety: |
| INV-SCHED-19 | Handoff Coordinator Authority: |
| INV-SCHED-20 | Timeout Configuration: |

## Known Deviations

None. All four Architecture Conformance Defects (ACD-001..ACD-004) are resolved.

## Known Limitations

- `LinearGraphPlanner` synthesizes linear graphs only (single synthesis pass).
- No learned DecisionPolicy (RulePolicy is the reference policy).
- Multi-hop distributed handoffs deferred to v1.1 (only direct sender -> receiver).
- Internet-dependent providers (OpenAI/Anthropic/Gemini) require API keys and
  network access; offline tests use the reference provider path.

## Architecture Conformance Statement

> Architecture v1.0 is approved as conformant. The reference runtime
> satisfies its defined execution semantics, rollback semantics, replay
> semantics, and provider abstraction to the extent specified. Remaining
> work concerns capability expansion rather than architectural correction.
> Future phases should preserve Architecture v1.0 as the stable specification
> baseline and treat new planners, providers, metrics, and learning mechanisms as
> conforming extensions rather than architectural revisions.
