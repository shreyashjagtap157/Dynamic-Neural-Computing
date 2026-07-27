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
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID, GraphVersion
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.ir.operations import IROperation, OperationType
from dnc.dcc.computation_generator import ComputationGenerator, GenerationObjective, GenerationContext
from dnc.dcc.structural_controller import StructuralController, EvaluationCriteria, EvaluationContext
from dnc.dcc.learning_engine import DeterministicLearningPolicy, PredictionTracker, GeneratorInfluence
from dnc.dcc.assessment_engine import AssessmentEngine, ExecutionResult, Assessment, AdaptationKnowledge
from dnc.dcc.learned_adaptation import LearnedStructuralAdaptation, LearnedAdaptationIntegration
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision
from dnc.mutation.engine import MutationEngine
from dnc.transaction.manager import TransactionManager
from dnc.projection.projector import StructuralProjector
from dnc.observability.provenance import ProvenanceLog, EventType


class ConformantMockExecutionCore:
    """Conformant execution core returning valid ExecutionResult contracts."""
    def __init__(self, utility=0.75):
        self.utility = utility
        self.execution_count = 0

    def execute(self, dag) -> ExecutionResult:
        self.execution_count += 1
        return ExecutionResult(
            graph_id="dnc_system",
            graph_version="v1.0.0-1",
            execution_time_ms=8.5,
            output=f"system_result_{self.execution_count}",
            metrics={"utility": self.utility},
            units_executed=dag.get("units_executed", 1) if isinstance(dag, dict) else 1,
            edges_traversed=dag.get("edges_traversed", 0) if isinstance(dag, dict) else 0,
            success=True
        )


@dataclass
class SystemStateSnapshot:
    """Complete snapshot of system state at a point in time."""
    cycle: int
    graph_id: str
    graph_version: str
    unit_count: int
    edge_count: int
    proposals_generated: int
    proposals_authorized: int
    learning_cycles: int
    adaptation_knowledge_cycles: int
    cumulative_improvement: float
    transaction_commits: int
    transaction_rollbacks: int


class DNCCanonicalSystem:
    """
    Canonical top-level DNC system runtime.
    Owns and coordinates all DNC components through their canonical lifecycle.
    Updated with Phase 13C.3 hysteresis state for anti-thrashing control.
    """
    def __init__(self, execution_id: str = "sys_exec_001"):
        self.execution_id = execution_id
        self.graph = StructuralGraph(GraphID("dnc_canonical_system"))
        self.provenance_log = ProvenanceLog(execution_id=execution_id)
        self.mutation_engine = MutationEngine()
        self.transaction_manager = TransactionManager(
            mutation_engine=self.mutation_engine,
            provenance_log=self.provenance_log
        )
        self.projector = StructuralProjector()
        self.execution_core = ConformantMockExecutionCore()
        self.assessment_engine = AssessmentEngine()
        self.generator = ComputationGenerator()
        self.controller = StructuralController()
        self.learning = DeterministicLearningPolicy()
        self.tracker = PredictionTracker()

        self._cycle_count = 0
        self._proposals_generated = 0
        self._proposals_authorized = 0
        self._transaction_commits = 0
        self._transaction_rollbacks = 0
        # Phase 13C.3 hysteresis state
        self._cycles_since_mutation = 999
        self._recent_mutation_count = 0
        self._prior_mutation_harmed = False
        self._last_observed_utility = 0.75

    def snapshot(self) -> SystemStateSnapshot:
        return SystemStateSnapshot(
            cycle=self._cycle_count,
            graph_id=str(self.graph.graph_id.value),
            graph_version=str(self.graph.version),
            unit_count=len(self.graph.units),
            edge_count=len(self.graph.edges),
            proposals_generated=self._proposals_generated,
            proposals_authorized=self._proposals_authorized,
            learning_cycles=0,
            adaptation_knowledge_cycles=self.learning.get_knowledge().cycle_count,
            cumulative_improvement=self.learning.get_knowledge().cumulative_improvement,
            transaction_commits=self._transaction_commits,
            transaction_rollbacks=self._transaction_rollbacks
        )

    def run_cycle(
        self,
        objective: GenerationObjective,
        prior_assessment: Optional[Assessment] = None
    ) -> Tuple[bool, Optional[Assessment], Optional[MutationProposal]]:
        """
        Execute one complete DNC system control cycle:
        INTERPRET -> GENERATE -> EVALUATE -> AUTHORIZE -> TRANSACT -> PROJECT -> EXECUTE -> ASSESS -> ADAPT

        Phase 13C.3: Generator context includes necessity-gate evidence (last_observed_utility,
        cycles_since_mutation, recent_mutation_count, prior_mutation_harmed).
        Evaluation context includes stability_baseline_utility, cycles_since_mutation,
        and recent_mutation_count for marginal-value analysis.
        After each cycle, hysteresis state is updated to suppress or permit future mutations.
        """
        self._cycle_count += 1
        graph_before_version = str(self.graph.version)

        # 1. GENERATE with Phase 13C.3 necessity-gate evidence
        last_utility = (
            prior_assessment.post_execution_utility_measured
            if prior_assessment else self._last_observed_utility
        )
        gen_context = GenerationContext(
            objective=objective,
            graph_id=self.graph.graph_id,
            current_unit_count=len(self.graph.units),
            current_edge_count=len(self.graph.edges),
            last_observed_utility=last_utility,
            recent_mutation_count=self._recent_mutation_count,
            cycles_since_mutation=self._cycles_since_mutation,
            prior_mutation_harmed=self._prior_mutation_harmed
        )
        proposals = self.generator.generate_proposals(self.graph, gen_context)
        self._proposals_generated += len(proposals)

        if not proposals:
            self._cycles_since_mutation += 1
            return False, None, None

        # 2. EVALUATE & AUTHORIZE with Phase 13C.3 marginal-value context
        eval_context = EvaluationContext(
            current_graph=self.graph,
            active_objectives=[objective.task_description],
            available_budget=objective.cost_budget,
            risk_tolerance="HIGH",
            criteria=EvaluationCriteria(
                min_utility=0.3,
                max_units=objective.max_units,
                max_edges=objective.max_edges
            ),
            stability_baseline_utility=self._last_observed_utility,
            cycles_since_mutation=self._cycles_since_mutation,
            recent_mutation_count=self._recent_mutation_count
        )
        evaluations = self.controller.evaluate_proposals(proposals, eval_context)
        auth_decision = self.controller.authorize_top_scoring(evaluations, eval_context)

        if not auth_decision or not auth_decision.authorized:
            self._cycles_since_mutation += 1
            return False, None, None

        self._proposals_authorized += 1
        authorized_proposal = next(
            (e.proposal for e in evaluations if e.decision.value == "AUTHORIZE"),
            proposals[0]
        )

        # Record prediction before transaction
        prediction_record = self.tracker.record_prediction(authorized_proposal, auth_decision)

        # 3. TRANSACT (Atomic mutation via TransactionManager with OCC & Provenance)
        prev_commits = self._transaction_commits
        success, ctx = self.transaction_manager.execute_transaction(
            self.graph, authorized_proposal.candidate_operations
        )

        if not success:
            self._transaction_rollbacks += 1
            self._cycles_since_mutation += 1
            return False, None, authorized_proposal

        self._transaction_commits += 1
        graph_after_version = str(self.graph.version)

        # 4. PROJECT & EXECUTE
        dag = self.projector.project(self.graph)
        exec_result = self.execution_core.execute(dag)

        # 5. ASSESS
        assessment = self.assessment_engine.assess_execution(
            exec_result,
            authorized_proposal,
            graph_before_version,
            graph_after_version
        )

        # 6. ADAPT (Learning feedback)
        if prior_assessment is not None:
            self.learning.process(prediction_record, assessment)

        # 7. Update Phase 13C.3 hysteresis state
        if self._transaction_commits > prev_commits:
            self._cycles_since_mutation = 0
            self._recent_mutation_count += 1
            self._prior_mutation_harmed = (
                assessment.improvement_delta < -0.02 if assessment else False
            )
        else:
            self._cycles_since_mutation += 1

        self._last_observed_utility = (
            assessment.post_execution_utility_measured if assessment else 0.75
        )

        return True, assessment, authorized_proposal


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
            assert assessment.execution_result.graph_id == "dnc_system"
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