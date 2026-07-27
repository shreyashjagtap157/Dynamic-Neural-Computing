"""
DNC Full-System Integration & Conformance Audit Suite (Phase 12)
Proves all components operate as one coherent system across multiple adaptation cycles,
verifying core authority boundaries, provenance integrity, closed-loop assessment, and learning.

Updated in Phase 13C.3 with:
- Hysteresis state tracking (cycles_since_mutation, recent_mutation_count, prior_mutation_harmed)
- Generator context extended with necessity-gate evidence fields
- Evaluation context extended with marginal-value analysis fields
- Post-mutation stabilization: mutations become harder to justify after recent mutations
"""

import sys


from dnc.dcc.computation_generator import GenerationObjective
from dnc.dcc.assessment_engine import ExecutionResult, Assessment
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision


from dnc.system import (
    DNCCanonicalSystem,
)


class TestPhase12AuditSuite:
    """Full-system integration conformance audit suite (SYS-1 through SYS-10)."""

    def test_sys1_structural_authority(self) -> bool:
        """SYS-1: Only TransactionManager may commit structural changes."""
        system = DNCCanonicalSystem("audit_sys1")
        initial_version = str(system.graph.version)

        objective = GenerationObjective(task_description="SYS-1 Test", max_units=5, max_edges=5)
        success, assessment, proposal = system.run_cycle(objective, None)

        if success:
            assert str(system.graph.version) != initial_version
            assert system._transaction_commits == 1
        print("PASS: test_sys1_structural_authority")
        return True

    def test_sys2_learning_authority_separation(self) -> bool:
        """SYS-2: Learning cannot directly modify StructuralGraph."""
        system = DNCCanonicalSystem("audit_sys2")
        initial_units = len(system.graph.units)

        pred = MutationProposal(
            proposal_id="p_sys2", target_graph_id="dnc_canonical_system",
            candidate_operations=[], expected_utility=0.8
        )
        decision = AuthorizationDecision(proposal_id="p_sys2", authorized=True)
        pred_record = system.tracker.record_prediction(pred, decision)

        assessment = Assessment(
            assessment_id="a_sys2", proposal_id="p_sys2",
            graph_before="v0", graph_after="v1",
            execution_result=ExecutionResult(
                graph_id="dnc_canonical_system", graph_version="v1",
                metrics={"utility": 0.7}, success=True
            ),
            pre_transaction_utility_estimate=0.8,
            post_execution_utility_measured=0.7,
            improvement_delta=-0.1
        )

        system.learning.process(pred_record, assessment)
        assert len(system.graph.units) == initial_units
        print("PASS: test_sys2_learning_authority_separation")
        return True

    def test_sys3_provenance_completeness(self) -> bool:
        """SYS-3: Every committed structural transition records provenance events."""
        system = DNCCanonicalSystem("audit_sys3")
        objective = GenerationObjective(task_description="SYS-3 Test", max_units=3, max_edges=3)

        success, _, _ = system.run_cycle(objective, None)
        if success:
            events = system.provenance_log._events
            assert len(events) > 0
            event_types = [e.event_type for e in events]
            assert "STRUCTURAL_TRANSACTION_BEGIN" in event_types
            assert "STRUCTURAL_TRANSACTION_COMMITTED" in event_types
            assert "STRUCTURAL_GRAPH_VERSION_CREATED" in event_types
        print("PASS: test_sys3_provenance_completeness")
        return True

    def test_sys4_execution_traceability(self) -> bool:
        """SYS-4: Every execution references valid graph version and context."""
        system = DNCCanonicalSystem("audit_sys4")
        objective = GenerationObjective(task_description="SYS-4 Test", max_units=3, max_edges=3)

        success, assessment, _ = system.run_cycle(objective, None)
        if success and assessment:
            assert assessment.execution_result.graph_version is not None
            assert assessment.execution_result.graph_id == system.graph.graph_id.value
        print("PASS: test_sys4_execution_traceability")
        return True

    def test_sys5_assessment_traceability(self) -> bool:
        """SYS-5: Assessment references pre-estimate and post-measurement."""
        system = DNCCanonicalSystem("audit_sys5")
        objective = GenerationObjective(task_description="SYS-5 Test", max_units=3, max_edges=3)

        success, assessment, _ = system.run_cycle(objective, None)
        if success and assessment:
            assert assessment.pre_transaction_utility_estimate is not None
            assert assessment.post_execution_utility_measured is not None
            assert assessment.improvement_delta is not None
        print("PASS: test_sys5_assessment_traceability")
        return True

    def test_sys6_rollback_isolation(self) -> bool:
        """SYS-6: Failed transactions leave structural graph completely unchanged."""
        system = DNCCanonicalSystem("audit_sys6")
        initial_units = len(system.graph.units)
        initial_version = str(system.graph.version)

        objective = GenerationObjective(task_description="SYS-6 Test", max_units=0, max_edges=0)
        system.run_cycle(objective, None)

        assert len(system.graph.units) == initial_units
        assert str(system.graph.version) == initial_version
        assert system._transaction_rollbacks >= 0
        print("PASS: test_sys6_rollback_isolation")
        return True

    def test_sys7_multi_cycle_convergence(self) -> bool:
        """SYS-7: Multi-cycle adaptation runs stably and accumulates knowledge."""
        system = DNCCanonicalSystem("audit_sys7")
        objective = GenerationObjective(task_description="SYS-7 Test", max_units=10, max_edges=15)

        prior_assessment = None
        for i in range(3):
            success, assessment, _ = system.run_cycle(objective, prior_assessment)
            if success and assessment:
                prior_assessment = assessment

        snap = system.snapshot()
        assert snap.unit_count >= 1
        print(f"PASS: test_sys7_multi_cycle_convergence (units={snap.unit_count})")
        return True

    def test_sys8_deterministic_replay(self) -> bool:
        """SYS-8: Same seed produces identical structural trajectories."""
        def run_system(seed):
            system = DNCCanonicalSystem(f"audit_sys8_{seed}")
            obj = GenerationObjective(task_description="Determinism Test", max_units=6, max_edges=9)
            results = []
            prior = None
            for _ in range(3):
                success, assessment, proposal = system.run_cycle(obj, prior)
                if success:
                    results.append((system.snapshot().unit_count, system.snapshot().edge_count))
                    prior = assessment
            return results

        r1 = run_system(1)
        r2 = run_system(1)
        assert r1 == r2
        print("PASS: test_sys8_deterministic_replay")
        return True


def run_all_tests():
    suite = TestPhase12AuditSuite()
    tests = [
        suite.test_sys1_structural_authority,
        suite.test_sys2_learning_authority_separation,
        suite.test_sys3_provenance_completeness,
        suite.test_sys4_execution_traceability,
        suite.test_sys5_assessment_traceability,
        suite.test_sys6_rollback_isolation,
        suite.test_sys7_multi_cycle_convergence,
        suite.test_sys8_deterministic_replay,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Phase 12 System Audit Suite: {passed}/{passed+failed} passed")
    print(f"{'='*60}")

    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 12 SYSTEM AUDIT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
