# Architecture Conformance Report

Version: 1.0
Generated: 2026-07-31
Implementation source: repository state at generation time
Implementation version: 0.1.0

> This is a release artifact, not documentation. Regenerate every
> release with `python tools/generate_conformance_report.py`. Architecture
> conformance is demonstrated by executable tests, not design review.

## Overall Status

| Aspect | Status |
|---|---|
| Architecture | FROZEN (Baseline v1.0) |
| Implementation | PASS (4/4 ACDs resolved) |
| Conformance Tests | PASS (34/34) |
| Invariant coverage | 30/30 (100.0%) |
| Spec tooling (PR-4 + RFC 2119) | PASS |

## Conformance Suite

| Suite | Passed | Total |
|---|---|---|
| conformance/execution/test_execution_invariants.py | 7 | 7 |
| conformance/formal/test_restore_invariants.py | 2 | 2 |
| conformance/policy/test_policy_invariants.py | 5 | 5 |
| conformance/providers/test_provider_dispatch.py | 3 | 3 |
| conformance/replay/test_replay.py | 2 | 2 |
| conformance/replay/test_replay_invariants.py | 5 | 5 |
| conformance/runtime/test_control_loop.py | 3 | 3 |
| conformance/runtime/test_replay_and_rollback.py | 4 | 4 |
| conformance/runtime/test_rollback.py | 3 | 3 |
| **Total** | **34** | **34** |

## Architecture Conformance Defects (ACD)

All 4 ACDs are RESOLVED.

## Invariant Coverage (executable)

| Namespace | Covered | Total |
|---|---|---|
| Decision Policy (INV-POL-*) | 5/5 (100.0%) | 5 |
| Execution (INV-EXEC-*) | 7/7 (100.0%) | 7 |
| Formal Model (INV-FM-*) | 2/2 (100.0%) | 2 |
| Replay (INV-REP-*) | 5/5 (100.0%) | 5 |
| Runtime (INV-*) | 11/11 (100.0%) | 11 |

### Covered invariants

| Invariant | Title | Tests |
|---|---|---|
| INV-1 | Execution Header Immutability): | test_invariant_verifier.py, test_invariant_violations.py, test_real_world_xor.py |
| INV-10 | Normative Statement Keyword Discipline): | conformance/execution/test_execution_invariants.py, conformance/policy/test_policy_invariants.py, conformance/providers/test_provider_dispatch.py, conformance/replay/test_replay.py, conformance/replay/test_replay_invariants.py, conformance/runtime/test_control_loop.py, conformance/runtime/test_rollback.py, test_g12_byte_exact.py, test_integration.py, test_invariant_violations.py, test_phase2_planner.py, test_phase4_production.py, test_phase5b.py, test_real_world_xor.py |
| INV-11 | Preservation Under Extension): | test_invariant_violations.py |
| INV-2 | DAG Acyclicity): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-3 | No Undefined Behavior): | test_invariant_violations.py |
| INV-4 | Single-Ownership of Module Semantics): | phase1_exit_criteria.py, test_invariant_verifier.py, test_invariant_violations.py |
| INV-5 | State Isolation Between Executions): | test_invariant_verifier.py, test_invariant_violations.py |
| INV-6 | Checkpoint Before Replan): | test_invariant_verifier.py |
| INV-7 | Handoff Atomicity): | test_invariant_verifier.py |
| INV-8 | All Invariants Verified Before Execution): | test_invariant_verifier.py |
| INV-9 | Bounded Drift): | test_invariant_violations.py |
| INV-EXEC-1 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-2 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-3 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-4 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-5 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-6 |  | conformance/execution/test_execution_invariants.py |
| INV-EXEC-7 |  | conformance/execution/test_execution_invariants.py |
| INV-FM-1 | Restore Does Not Modify Checkpoint: | conformance/formal/test_restore_invariants.py |
| INV-FM-2 | Restore Advances Step Index Linearly: | conformance/formal/test_restore_invariants.py |
| INV-POL-1 |  | conformance/policy/test_policy_invariants.py |
| INV-POL-2 |  | conformance/policy/test_policy_invariants.py |
| INV-POL-3 |  | conformance/policy/test_policy_invariants.py |
| INV-POL-4 |  | conformance/policy/test_policy_invariants.py |
| INV-POL-5 |  | conformance/policy/test_policy_invariants.py |
| INV-REP-1 |  | conformance/replay/test_replay_invariants.py |
| INV-REP-2 |  | conformance/replay/test_replay_invariants.py |
| INV-REP-3 |  | conformance/replay/test_replay_invariants.py |
| INV-REP-4 |  | conformance/replay/test_replay_invariants.py |
| INV-REP-5 |  | conformance/replay/test_replay_invariants.py |

### Uncovered invariants

| Invariant | Title |
|---|---|

## Known Deviations

None. All discovered invariants and conformance defects are covered.

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

> Architecture v1.0 is conformant against all currently discovered executable gates.
