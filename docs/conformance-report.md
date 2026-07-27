# Architecture Conformance Report

Version: 1.0
Generated: 2026-07-22
Implementation commit: f81a2f1
Implementation version: 0.1.0

> This is a release artifact, not documentation. Regenerate every
> release with `python tools/generate_conformance_report.py`. Architecture
> conformance is demonstrated by executable tests, not design review.

## Overall Status

| Aspect | Status |
|---|---|
| Architecture | FROZEN (Baseline v1.0) |
| Implementation | PASS (4/4 ACDs resolved) |
| Conformance Tests | PASS (139/139) |
| Invariant coverage | 46/46 (100.0%) |
| Spec tooling (PR-4 + RFC 2119) | PASS |

## Conformance Suite

| Suite | Passed | Total |
|---|---|---|
| conformance/evaluation/test_evaluation_invariants.py | 12 | 12 |
| conformance/execution/test_execution_invariants.py | 12 | 12 |
| conformance/providers/test_provider_dispatch.py | 3 | 3 |
| conformance/replay/test_replay.py | 2 | 2 |
| conformance/replay/test_replay_invariants.py | 14 | 14 |
| conformance/runtime/test_control_loop.py | 3 | 3 |
| conformance/runtime/test_replan_invariants.py | 6 | 6 |
| conformance/runtime/test_replay_and_rollback.py | 4 | 4 |
| conformance/runtime/test_rollback.py | 3 | 3 |
| conformance/scheduler/test_scheduler_invariants.py | 12 | 12 |
| conformance/test_decision_policy.py | 16 | 16 |
| conformance/test_evaluation.py | 14 | 14 |
| conformance/test_execution_invariants.py | 14 | 14 |
| conformance/test_policy.py | 14 | 14 |
| conformance/test_replay_semantics.py | 10 | 10 |
| **Total** | **139** | **139** |

## Architecture Conformance Defects (ACD)

All 4 ACDs are RESOLVED.

## Invariant Coverage (executable)

| Namespace | Covered | Total |
|---|---|---|
| Control Loop (INV-CTRL-*) | 8/8 (100.0%) | 8 |
| Decision Policy (INV-POL-*) | 5/5 (100.0%) | 5 |
| Evaluation (INV-EVAL-*) | 8/8 (100.0%) | 8 |
| Execution (INV-EXEC-*) | 7/7 (100.0%) | 7 |
| Formal Model (INV-FM-*) | 2/2 (100.0%) | 2 |
| Replay (INV-REP-*) | 5/5 (100.0%) | 5 |
| Runtime (INV-*) | 11/11 (100.0%) | 11 |

### Covered invariants

| Invariant | Title | Tests |
|---|---|---|
| INV-1 | Execution Header Immutability): | test_invariant_verifier.py, test_invariant_violations.py, test_real_world_xor.py |
| INV-10 | Normative Statement Keyword Discipline): | conformance/providers/test_provider_dispatch.py, conformance/replay/test_replay.py, conformance/runtime/test_control_loop.py, conformance/runtime/test_replan_invariants.py, conformance/runtime/test_rollback.py, conformance/scheduler/test_scheduler_invariants.py, conformance/test_decision_policy.py, conformance/test_execution_invariants.py, conformance/test_policy.py, conformance/test_replay_semantics.py, test_g12_byte_exact.py, test_integration.py, test_invariant_violations.py, test_phase2_planner.py, test_phase4_production.py, test_phase5b.py, test_real_world_xor.py |
| INV-11 | Preservation Under Extension): | test_invariant_violations.py |
| INV-2 | DAG Acyclicity): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-3 | No Undefined Behavior): | test_invariant_violations.py |
| INV-4 | Single-Ownership of Module Semantics): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-5 | State Isolation Between Executions): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-6 | Checkpoint Before Replan): | test_invariant_verifier.py |
| INV-7 | Handoff Atomicity): | test_invariant_verifier.py |
| INV-8 | All Invariants Verified Before Execution): | test_invariant_verifier.py |
| INV-9 | Bounded Drift): | test_invariant_violations.py |
| INV-CTRL-1 | Observation Completeness | conformance/runtime/test_control_loop.py |
| INV-CTRL-2 | Observation Latency Bound | conformance/runtime/test_control_loop.py |
| INV-CTRL-3 | Decision Determinism | conformance/runtime/test_control_loop.py |
| INV-CTRL-4 | Decision Latency Bound | conformance/runtime/test_control_loop.py |
| INV-CTRL-5 | Action Commitment | conformance/runtime/test_control_loop.py, conformance/scheduler/test_scheduler_invariants.py |
| INV-CTRL-6 | Action Latency Bound | conformance/runtime/test_control_loop.py |
| INV-CTRL-7 | Assessment Always Runs | conformance/runtime/test_control_loop.py |
| INV-CTRL-8 | Assessment Result Classification | conformance/runtime/test_control_loop.py |
| INV-EVAL-1 | Baseline Version Locking | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py, test_phase3_observability.py |
| INV-EVAL-11 | Stage Determination Is Deterministic: | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py |
| INV-EVAL-12 | Full Stage Is Mandatory for High-Risk Updates: | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py |
| INV-EVAL-14 | Escalation on Near-Threshold Results: | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py |
| INV-EVAL-15 | Budget Exhaustion Handling: | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py |
| INV-EVAL-3 | Complete Metric Reporting | conformance/test_evaluation.py |
| INV-EVAL-8 | Novel Task Benchmark Completeness: | conformance/evaluation/test_evaluation_invariants.py |
| INV-EVAL-9 | NOVEL_TASK_SUCCESS_RATE Per-Scenario Minimum: | conformance/evaluation/test_evaluation_invariants.py, conformance/test_evaluation.py |
| INV-EXEC-1 |  | conformance/test_execution_invariants.py, test_integration.py |
| INV-EXEC-2 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-EXEC-3 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-EXEC-4 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-EXEC-5 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-EXEC-6 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-EXEC-7 |  | conformance/execution/test_execution_invariants.py, conformance/test_execution_invariants.py |
| INV-FM-1 | Restore Does Not Modify Checkpoint: | conformance/replay/test_replay.py, conformance/runtime/test_replay_and_rollback.py |
| INV-FM-2 | Restore Advances Step Index Linearly: | conformance/replay/test_replay.py, conformance/runtime/test_replay_and_rollback.py |
| INV-POL-1 |  | conformance/test_decision_policy.py, conformance/test_policy.py |
| INV-POL-2 |  | conformance/test_decision_policy.py, conformance/test_policy.py |
| INV-POL-3 |  | conformance/test_decision_policy.py, conformance/test_policy.py |
| INV-POL-4 |  | conformance/test_decision_policy.py, conformance/test_policy.py |
| INV-POL-5 |  | conformance/test_decision_policy.py, conformance/test_policy.py |
| INV-REP-1 |  | conformance/replay/test_replay_invariants.py, conformance/test_replay_semantics.py |
| INV-REP-2 |  | conformance/replay/test_replay_invariants.py, conformance/test_replay_semantics.py |
| INV-REP-3 |  | conformance/replay/test_replay_invariants.py, conformance/test_replay_semantics.py |
| INV-REP-4 |  | conformance/replay/test_replay_invariants.py, conformance/test_replay_semantics.py |
| INV-REP-5 |  | conformance/replay/test_replay_invariants.py, conformance/test_replay_semantics.py |

### Uncovered invariants

| Invariant | Title |
|---|---|

## Known Deviations

None. All four Architecture Conformance Defects (ACD-001..ACD-004) are resolved.

## Known Limitations

- `LinearGraphPlanner` is the reference planner. It synthesizes linear graphs in
  its single synthesis pass. DAG support is opt-in via a `dependencies` map.
- `RulePolicy` is the reference DecisionPolicy. An opt-in `LLMPolicy` and a stub
  `RLPolicy` are available for experimentation.
- `DistributedCoordinator` accepts single-hop handoffs out of the box; multi-hop
  routing is wired via `MultiHopRouter` and activated by registering routes.
- Internet-dependent providers (OpenAI/Anthropic/Gemini) require API keys and
  network access; an `offline=True` flag returns deterministic mocks for tests.

## Architecture Conformance Statement

> Architecture v1.0 is approved as conformant. The reference runtime
> satisfies its defined execution semantics, rollback semantics, replay
> semantics, and provider abstraction to the extent specified. Remaining
> work concerns capability expansion rather than architectural correction.
> Future phases should preserve Architecture v1.0 as the stable specification
> baseline and treat new planners, providers, metrics, and learning mechanisms as
> conforming extensions rather than architectural revisions.
