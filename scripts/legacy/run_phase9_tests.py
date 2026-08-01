"""
Phase 9 Closed-Loop Execution and Assessment Tests
Verifies complete DCCL control loop: INTERPRET → GENERATE → EVALUATE → AUTHORIZE → TRANSACT → PROJECT → EXECUTE → ASSESS → ADAPT
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.dcc.dcc_contracts import MutationProposal
from dnc.dcc.structural_controller import StructuralController, EvaluationCriteria, EvaluationContext
from dnc.dcc.computation_generator import ComputationGenerator, GenerationObjective, GenerationContext
from dnc.dcc.assessment_engine import (
    AssessmentEngine, ExecutionResult, AdaptationKnowledge,
    DCCLAssessmentContext, DCCLClosedLoopOrchestrator
)
from dnc.mutation.engine import MutationEngine
from dnc.transaction.manager import TransactionManager
from dnc.projection.projector import StructuralProjector

class MockExecutionCore:
    """Mock execution core for testing closed-loop integration."""
    def __init__(self, utility=0.75, execution_time_ms=10.0):
        self.utility = utility
        self.execution_time_ms = execution_time_ms
        self.execution_count = 0

    def execute(self, dag):
        self.execution_count += 1
        return {
            "output": f"result_{self.execution_count}",
            "execution_time_ms": self.execution_time_ms,
            "units_executed": dag.get("units_executed", 1) if isinstance(dag, dict) else 1,
            "edges_traversed": dag.get("edges_traversed", 0) if isinstance(dag, dict) else 0,
            "metrics": {"utility": self.utility},
            "success": True
        }

def test_execution_result():
    """ExecutionResult carries execution metrics."""
    result = ExecutionResult(
        graph_id="test_g",
        graph_version="v1.0.0-1",
        execution_time_ms=15.5,
        output="test_output",
        metrics={"utility": 0.82, "accuracy": 0.95},
        units_executed=3,
        edges_traversed=2,
        success=True
    )
    assert result.graph_id == "test_g"
    assert result.execution_time_ms == 15.5
    assert result.metrics["utility"] == 0.82
    assert result.success
    print("PASS: test_execution_result")

def test_assessment_creation():
    """Assessment captures pre/post comparison."""
    result = ExecutionResult(
        graph_id="test_g",
        graph_version="v1.0.0-1",
        metrics={"utility": 0.7},
        success=True
    )
    proposal = MutationProposal(
        proposal_id="test_prop",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.6,
        estimated_cost=2.0
    )
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v1.0.0-0", "v1.0.0-1")
    assert assessment.assessment_id.startswith("assess_")
    assert assessment.proposal_id == "test_prop"
    assert assessment.pre_transaction_utility_estimate == 0.6
    assert assessment.post_execution_utility_measured == 0.7
    assert assessment.improvement_delta == 0.1
    print("PASS: test_assessment_creation")

def test_assessment_negative_outcome():
    """Assessment captures negative improvement delta."""
    result = ExecutionResult(
        graph_id="test_g",
        graph_version="v1.0.0-1",
        metrics={"utility": 0.4},
        success=True
    )
    proposal = MutationProposal(
        proposal_id="failed_prop",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.7,
        estimated_cost=2.0
    )
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v1.0.0-0", "v1.0.0-1")
    assert assessment.improvement_delta == -0.3
    print("PASS: test_assessment_negative_outcome")

def test_assessment_failed_execution():
    """Assessment records HIGH risk for failed execution."""
    result = ExecutionResult(
        graph_id="test_g",
        graph_version="v1.0.0-1",
        error="Execution failed",
        success=False
    )
    proposal = MutationProposal(
        proposal_id="crash_prop",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.8
    )
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v1.0.0-0", "v1.0.0-1")
    assert assessment.risk_actual == "HIGH"
    assert assessment.alignment_score == 0.0
    print("PASS: test_assessment_failed_execution")

def test_adaptation_knowledge_update():
    """adaptation_knowledge accumulates assessment history."""
    knowledge = AdaptationKnowledge()
    result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.75}, success=True)
    proposal = MutationProposal(proposal_id="p1", target_graph_id="g", candidate_operations=[], expected_utility=0.6)
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v0", "v1")
    updated = engine.update_adaptation_knowledge(knowledge, assessment)
    assert len(updated.past_assessments) == 1
    assert updated.proposal_outcomes["p1"] == "SUCCESSFUL"
    assert updated.cumulative_improvement == 0.15
    print("PASS: test_adaptation_knowledge_update")

def test_should_adapt_positive():
    """should_adapt returns False for positive improvement."""
    result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.8}, success=True)
    proposal = MutationProposal(proposal_id="p1", target_graph_id="g", candidate_operations=[], expected_utility=0.6)
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v0", "v1")
    assert not engine.should_adapt(assessment, threshold=0.1)
    print("PASS: test_should_adapt_positive")

def test_should_adapt_negative():
    """should_adapt returns True for negative improvement beyond threshold."""
    result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.4}, success=True)
    proposal = MutationProposal(proposal_id="p1", target_graph_id="g", candidate_operations=[], expected_utility=0.6)
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v0", "v1")
    assert engine.should_adapt(assessment, threshold=0.1)
    print("PASS: test_should_adapt_negative")

def test_epistemic_distinction():
    """Pre-transaction estimate differs from post-execution measurement."""
    result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.85}, success=True)
    proposal = MutationProposal(proposal_id="p1", target_graph_id="g", candidate_operations=[], expected_utility=0.6)
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v0", "v1")
    assert assessment.pre_transaction_utility_estimate == 0.6
    assert assessment.post_execution_utility_measured == 0.85
    assert assessment.pre_transaction_utility_estimate != assessment.post_execution_utility_measured
    print("PASS: test_epistemic_distinction")

def test_assessment_alignment_score():
    """Alignment score measures how well execution matched proposal intent."""
    result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.5}, success=True)
    proposal = MutationProposal(proposal_id="p1", target_graph_id="g", candidate_operations=[], expected_utility=0.5)
    engine = AssessmentEngine()
    assessment = engine.assess_execution(result, proposal, "v0", "v1")
    assert assessment.alignment_score == 1.0
    print("PASS: test_assessment_alignment_score")

def test_get_learned_outcomes():
    """get_learned_outcomes returns proposal history."""
    knowledge = AdaptationKnowledge()
    knowledge.proposal_outcomes = {
        "gen_prop_1": "SUCCESSFUL",
        "gen_prop_2": "UNSUCCESSFUL",
        "gen_wire_1": "SUCCESSFUL"
    }
    engine = AssessmentEngine()
    outcomes = engine.get_learned_outcomes(knowledge, "gen_")
    assert len(outcomes) == 3
    outcomes_prefixed = engine.get_learned_outcomes(knowledge, "gen_prop_")
    assert len(outcomes_prefixed) == 2
    print("PASS: test_get_learned_outcomes")

def test_closed_loop_orchestrator_initialization():
    """Orchestrator initializes with all required components."""
    generator = ComputationGenerator()
    controller = StructuralController()
    transaction_manager = TransactionManager()
    mutation_engine = MutationEngine()
    projector = StructuralProjector()
    execution_core = MockExecutionCore()
    assessment_engine = AssessmentEngine()

    orchestrator = DCCLClosedLoopOrchestrator(
        generator=generator,
        structural_controller=controller,
        transaction_manager=transaction_manager,
        mutation_engine=mutation_engine,
        projector=projector,
        execution_core=execution_core,
        assessment_engine=assessment_engine
    )
    assert orchestrator.get_cycle_count() == 0
    print("PASS: test_closed_loop_orchestrator_initialization")

def test_closed_loop_single_cycle():
    """Orchestrator executes one complete cycle."""
    generator = ComputationGenerator()
    controller = StructuralController()
    transaction_manager = TransactionManager()
    mutation_engine = MutationEngine()
    projector = StructuralProjector()
    execution_core = MockExecutionCore(utility=0.7)
    assessment_engine = AssessmentEngine()

    orchestrator = DCCLClosedLoopOrchestrator(
        generator=generator,
        structural_controller=controller,
        transaction_manager=transaction_manager,
        mutation_engine=mutation_engine,
        projector=projector,
        execution_core=execution_core,
        assessment_engine=assessment_engine
    )

    graph = StructuralGraph(GraphID("loop_g"))

    gen_context = GenerationContext(
        objective=GenerationObjective(task_description="Test cycle", max_units=5, max_edges=10),
        graph_id=graph.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )

    eval_context = EvaluationContext(
        current_graph=graph,
        active_objectives=["Test objective"],
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria(min_utility=0.3)
    )

    graph_after, assessment, evaluations = orchestrator.execute_full_cycle(
        graph, gen_context, eval_context
    )

    assert orchestrator.get_cycle_count() == 1
    assert graph_after is not None
    print(f"PASS: test_closed_loop_single_cycle (assessments={1 if assessment else 0})")

def test_closed_loop_proposal_lifecycle():
    """Complete lifecycle: generate → evaluate → authorize → transact → execute → assess."""
    generator = ComputationGenerator()
    controller = StructuralController()
    transaction_manager = TransactionManager()
    mutation_engine = MutationEngine()
    projector = StructuralProjector()
    execution_core = MockExecutionCore(utility=0.8)
    assessment_engine = AssessmentEngine()

    orchestrator = DCCLClosedLoopOrchestrator(
        generator=generator,
        structural_controller=controller,
        transaction_manager=transaction_manager,
        mutation_engine=mutation_engine,
        projector=projector,
        execution_core=execution_core,
        assessment_engine=assessment_engine
    )

    graph = StructuralGraph(GraphID("lifecycle_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("base_unit"),
        name="BaseUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    gen_context = GenerationContext(
        objective=GenerationObjective(task_description="Lifecycle test", max_units=10, max_edges=20),
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )

    eval_context = EvaluationContext(
        current_graph=graph,
        active_objectives=["improve_accuracy"],
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria(min_utility=0.4)
    )

    graph_after, assessment, evaluations = orchestrator.execute_full_cycle(
        graph, gen_context, eval_context
    )

    assert orchestrator.get_cycle_count() == 1
    assert len(evaluations) >= 1
    if assessment:
        assert assessment.assessment_id.startswith("assess_")
        assert assessment.execution_result is not None
        assert assessment.post_execution_utility_measured == 0.8
    print("PASS: test_closed_loop_proposal_lifecycle")

def test_no_proposals_no_assessment():
    """When no proposals generated, no assessment occurs."""
    generator = ComputationGenerator()
    controller = StructuralController()
    transaction_manager = TransactionManager()
    mutation_engine = MutationEngine()
    projector = StructuralProjector()
    execution_core = MockExecutionCore()
    assessment_engine = AssessmentEngine()

    orchestrator = DCCLClosedLoopOrchestrator(
        generator=generator,
        structural_controller=controller,
        transaction_manager=transaction_manager,
        mutation_engine=mutation_engine,
        projector=projector,
        execution_core=execution_core,
        assessment_engine=assessment_engine
    )

    graph = StructuralGraph(GraphID("empty_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("only_unit"),
        name="OnlyUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    gen_context = GenerationContext(
        objective=GenerationObjective(
            task_description="Empty cycle test",
            max_units=1,
            max_edges=0
        ),
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )

    eval_context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    graph_after, assessment, evaluations = orchestrator.execute_full_cycle(
        graph, gen_context, eval_context
    )

    assert assessment is None
    assert orchestrator.get_cycle_count() == 1
    print("PASS: test_no_proposals_no_assessment")

def test_multiple_cycles_accumulate_knowledge():
    """Multiple cycles accumulate adaptation knowledge."""
    generator = ComputationGenerator()
    controller = StructuralController()
    transaction_manager = TransactionManager()
    mutation_engine = MutationEngine()
    projector = StructuralProjector()
    execution_core = MockExecutionCore(utility=0.75)
    assessment_engine = AssessmentEngine()

    orchestrator = DCCLClosedLoopOrchestrator(
        generator=generator,
        structural_controller=controller,
        transaction_manager=transaction_manager,
        mutation_engine=mutation_engine,
        projector=projector,
        execution_core=execution_core,
        assessment_engine=assessment_engine
    )

    graph = StructuralGraph(GraphID("multi_g"))

    for i in range(3):
        gen_context = GenerationContext(
            objective=GenerationObjective(task_description=f"Cycle {i}", max_units=5, max_edges=5),
            graph_id=graph.graph_id,
            current_unit_count=len(graph.units),
            current_edge_count=len(graph.edges)
        )
        eval_context = EvaluationContext(
            current_graph=graph,
            available_budget=100.0,
            risk_tolerance="HIGH",
            criteria=EvaluationCriteria(min_utility=0.3)
        )
        graph, _, _ = orchestrator.execute_full_cycle(graph, gen_context, eval_context)

    assert orchestrator.get_cycle_count() == 3
    knowledge = orchestrator.get_adaptation_knowledge()
    assert len(knowledge.past_assessments) >= 1
    print(f"PASS: test_multiple_cycles_accumulate_knowledge (cycles=3, assessments={len(knowledge.past_assessments)})")

def test_assessment_context_includes_observation_history():
    """DCCLAssessmentContext tracks observation history."""
    result1 = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.6}, success=True)
    result2 = ExecutionResult(graph_id="g", graph_version="v2", metrics={"utility": 0.7}, success=True)

    context = DCCLAssessmentContext(
        current_graph=StructuralGraph(GraphID("ctx_g")),
        active_objectives=["improve"],
        constraints=["low_latency"],
        available_budget=50.0,
        risk_tolerance="MEDIUM",
        observation_history=[result1, result2]
    )

    assert len(context.observation_history) == 2
    assert context.observation_history[0].metrics["utility"] == 0.6
    assert context.observation_history[1].metrics["utility"] == 0.7
    print("PASS: test_assessment_context_includes_observation_history")

def run_all_tests():
    tests = [
        test_execution_result,
        test_assessment_creation,
        test_assessment_negative_outcome,
        test_assessment_failed_execution,
        test_adaptation_knowledge_update,
        test_should_adapt_positive,
        test_should_adapt_negative,
        test_epistemic_distinction,
        test_assessment_alignment_score,
        test_get_learned_outcomes,
        test_closed_loop_orchestrator_initialization,
        test_closed_loop_single_cycle,
        test_closed_loop_proposal_lifecycle,
        test_no_proposals_no_assessment,
        test_multiple_cycles_accumulate_knowledge,
        test_assessment_context_includes_observation_history,
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
    print(f"\nPhase 9 Closed-Loop Assessment Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 9 CLOSED-LOOP ASSESSMENT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()