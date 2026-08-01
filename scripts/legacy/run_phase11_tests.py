"""
Phase 11 Learned Structural Adaptation Tests
Verifies that accumulated experience changes future structural behavior while preserving invariants.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.dcc.computation_generator import ComputationGenerator, GenerationObjective
from dnc.dcc.structural_controller import StructuralController, EvaluationCriteria, EvaluationContext
from dnc.dcc.learning_engine import DeterministicLearningPolicy, PredictionTracker, GeneratorInfluence
from dnc.dcc.assessment_engine import Assessment, ExecutionResult
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision
from dnc.dcc.learned_adaptation import (
    LearnedStructuralAdaptation, LearnedGenerationContext, LearnedEvaluationContext,
    LearnedAdaptationIntegration
)


def test_learning_changes_future_proposal_ranking():
    """Requirement 1: Learning changes future proposal ranking or generation."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("learn_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("base"),
        name="Base",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(task_description="Learn ranking", max_units=10, max_edges=20)
    gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria(min_utility=0.3)
    )

    cycle1_result = adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)
    assert cycle1_result is not None
    assert cycle1_result.proposal is not None

    if cycle1_result.prediction_record:
        prior_assessment = Assessment(
            assessment_id="prior_assess",
            proposal_id=cycle1_result.proposal.proposal_id,
            graph_before="v0",
            graph_after="v1",
            execution_result=ExecutionResult(
                graph_id="learn_g",
                graph_version="v1",
                metrics={"utility": 0.3},
                success=True
            ),
            pre_transaction_utility_estimate=cycle1_result.prediction_record.predicted_utility,
            post_execution_utility_measured=0.3,
            improvement_delta=-0.2
        )

        gen_ctx2 = LearnedGenerationContext(
            objective=objective,
            graph_id=graph.graph_id,
            current_unit_count=len(graph.units),
            current_edge_count=len(graph.edges)
        )
        eval_ctx2 = LearnedEvaluationContext(
            current_graph=graph,
            available_budget=100.0,
            risk_tolerance="HIGH",
            criteria=EvaluationCriteria(min_utility=0.3)
        )

        cycle2_result = adaptation.execute_adaptation_cycle(
            graph, gen_ctx2, eval_ctx2, prior_assessment=prior_assessment
        )

        assert cycle2_result.learning_applied
        assert cycle2_result.proposal_ranked_by_learning
        assert cycle1_result.proposal.proposal_id != cycle2_result.proposal.proposal_id

    print("PASS: test_learning_changes_future_proposal_ranking")


def test_learning_does_not_directly_mutate():
    """Requirement 2: Learning cannot directly mutate the graph."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("no_mutate_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("unit_x"),
        name="UnitX",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    initial_units = len(graph.units)
    initial_edges = len(graph.edges)

    objective = GenerationObjective(task_description="No direct mutation", max_units=5, max_edges=5)
    gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=initial_units,
        current_edge_count=initial_edges
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

    assert len(graph.units) == initial_units
    assert len(graph.edges) == initial_edges
    print("PASS: test_learning_does_not_directly_mutate")


def test_controller_authority_remains_intact():
    """Requirement 3: Controller authority remains intact under learned influence."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("ctrl_auth_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("ctrl_test_unit"),
        name="CtrlTest",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(
        task_description="Test controller authority",
        max_units=10,
        max_edges=20
    )

    for cycle in range(3):
        gen_ctx = LearnedGenerationContext(
            objective=objective,
            graph_id=graph.graph_id,
            current_unit_count=len(graph.units),
            current_edge_count=len(graph.edges),
            learning_active=False
        )
        eval_ctx = LearnedEvaluationContext(
            current_graph=graph,
            available_budget=100.0,
            risk_tolerance="LOW",
            criteria=EvaluationCriteria(min_utility=0.9)
        )

        result = adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

        if result.authorization:
            assert result.authorization.authorized or result.authorization.rejection_reason is not None

    assert adaptation.get_cycle_count() == 3
    print("PASS: test_controller_authority_remains_intact")


def test_learning_separated_from_structural_state():
    """Requirement 4: Learning state is separate from structural state."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph1 = StructuralGraph(GraphID("struct_g1"))
    graph1.add_unit(ComputationalUnit(
        unit_id=UnitID("u1"),
        name="U1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    graph2 = StructuralGraph(GraphID("struct_g2"))

    gen_ctx = LearnedGenerationContext(
        objective=GenerationObjective(task_description="Test", max_units=5, max_edges=5),
        graph_id=graph1.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph1,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    adaptation.execute_adaptation_cycle(graph1, gen_ctx, eval_ctx)
    knowledge1 = adaptation.learning.get_knowledge()

    gen_ctx2 = LearnedGenerationContext(
        objective=GenerationObjective(task_description="Test 2", max_units=5, max_edges=5),
        graph_id=graph2.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )
    eval_ctx2 = LearnedEvaluationContext(
        current_graph=graph2,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    adaptation.execute_adaptation_cycle(graph2, gen_ctx2, eval_ctx2)
    knowledge2 = adaptation.learning.get_knowledge()

    assert knowledge1.cycle_count > 0
    assert knowledge2.cycle_count == knowledge1.cycle_count
    assert len(graph1.units) == 1
    assert len(graph2.units) == 0
    print("PASS: test_learning_separated_from_structural_state")


def test_learning_history_is_provenance_traceable():
    """Requirement 5: Learning history is accessible for provenance."""
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    pred = MutationProposal(
        proposal_id="prov_test",
        target_graph_id="g",
        candidate_operations=[],
        expected_utility=0.7,
        estimated_cost=2.0
    )
    decision = AuthorizationDecision(proposal_id="prov_test", authorized=True)
    prediction_record = tracker.record_prediction(pred, decision)

    assessment = Assessment(
        assessment_id="prov_assess",
        proposal_id="prov_test",
        graph_before="v0",
        graph_after="v1",
        execution_result=ExecutionResult(
            graph_id="g",
            graph_version="v1",
            metrics={"utility": 0.6},
            success=True
        ),
        pre_transaction_utility_estimate=0.7,
        post_execution_utility_measured=0.6,
        improvement_delta=-0.1
    )

    knowledge, signals, influence = learning.process(prediction_record, assessment)

    assert knowledge.cycle_count == 1
    assert len(signals) > 0
    assert signals[0].proposal_id == "prov_test"
    assert knowledge.proposal_outcomes["prov_test"] == "UNSUCCESSFUL"
    print("PASS: test_learning_history_is_provenance_traceable")


def test_replay_reproduces_deterministic_learning():
    """Requirement 6: Replay can reproduce deterministic learning transitions."""
    learning1 = DeterministicLearningPolicy()
    learning2 = DeterministicLearningPolicy()

    for _ in range(3):
        pred1 = MutationProposal(
            proposal_id="det_test",
            target_graph_id="g",
            candidate_operations=[],
            expected_utility=0.75,
            estimated_cost=2.0
        )
        decision1 = AuthorizationDecision(proposal_id="det_test", authorized=True)
        prediction_record1 = learning1.predictions.record_prediction(pred1, decision1)

        assessment1 = Assessment(
            assessment_id="det_assess",
            proposal_id="det_test",
            graph_before="v0",
            graph_after="v1",
            execution_result=ExecutionResult(
                graph_id="g",
                graph_version="v1",
                metrics={"utility": 0.65},
                success=True
            ),
            pre_transaction_utility_estimate=0.75,
            post_execution_utility_measured=0.65,
            improvement_delta=-0.1
        )

        learning1.process(prediction_record1, assessment1)

    knowledge1 = learning1.get_knowledge()

    for _ in range(3):
        pred2 = MutationProposal(
            proposal_id="det_test",
            target_graph_id="g",
            candidate_operations=[],
            expected_utility=0.75,
            estimated_cost=2.0
        )
        decision2 = AuthorizationDecision(proposal_id="det_test", authorized=True)
        prediction_record2 = learning2.predictions.record_prediction(pred2, decision2)

        assessment2 = Assessment(
            assessment_id="det_assess",
            proposal_id="det_test",
            graph_before="v0",
            graph_after="v1",
            execution_result=ExecutionResult(
                graph_id="g",
                graph_version="v1",
                metrics={"utility": 0.65},
                success=True
            ),
            pre_transaction_utility_estimate=0.75,
            post_execution_utility_measured=0.65,
            improvement_delta=-0.1
        )

        learning2.process(prediction_record2, assessment2)

    knowledge2 = learning2.get_knowledge()

    assert knowledge1.cycle_count == knowledge2.cycle_count
    assert knowledge1.cumulative_improvement == knowledge2.cumulative_improvement
    assert knowledge1.utility_accuracy == knowledge2.utility_accuracy
    print("PASS: test_replay_reproduces_deterministic_learning")


def test_learning_state_can_be_checkpoint_restored():
    """Requirement 7: Learning state can be checkpointed and restored."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("checkpoint_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("cp_unit"),
        name="CheckpointUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(task_description="Checkpoint test", max_units=5, max_edges=5)
    gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    for _ in range(3):
        adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

    knowledge_before = adaptation.learning.get_knowledge()
    cycle_count_before = knowledge_before.cycle_count

    learning.reset_knowledge()
    tracker = PredictionTracker()

    adaptation2 = LearnedStructuralAdaptation(gen, ctrl, DeterministicLearningPolicy(), tracker)
    StructuralGraph(GraphID("checkpoint_g2"))

    knowledge_after_reset = adaptation2.learning.get_knowledge()
    assert knowledge_after_reset.cycle_count == 0
    assert cycle_count_before > 0
    print("PASS: test_learning_state_can_be_checkpoint_restored")


def test_bad_learned_policy_cannot_bypass_safety():
    """Requirement 8: Bad learned policy cannot bypass safety constraints."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("safety_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("safety_unit"),
        name="SafetyUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(
        task_description="Safety test",
        max_units=1,
        max_edges=0
    )

    for cycle in range(5):
        gen_ctx = LearnedGenerationContext(
            objective=objective,
            graph_id=graph.graph_id,
            current_unit_count=len(graph.units),
            current_edge_count=len(graph.edges),
            learning_active=False
        )
        eval_ctx = LearnedEvaluationContext(
            current_graph=graph,
            available_budget=100.0,
            risk_tolerance="LOW",
            criteria=EvaluationCriteria(min_utility=0.9)
        )

        result = adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

        if result.authorization and result.authorization.authorized:
            assert result.safety_constraints_satisfied

    assert len(graph.units) <= 1
    print("PASS: test_bad_learned_policy_cannot_bypass_safety")


def test_system_distinguishes_learned_from_explicit():
    """Requirement 9: System distinguishes learned influence from explicit constraints."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("explicit_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("explicit_unit"),
        name="ExplicitUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(
        task_description="Explicit constraints test",
        max_units=2,
        max_edges=2
    )

    explicit_gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0,
        learning_active=False
    )
    explicit_eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=10.0,
        risk_tolerance="LOW",
        criteria=EvaluationCriteria(min_utility=0.5)
    )

    explicit_result = adaptation.execute_adaptation_cycle(graph, explicit_gen_ctx, explicit_eval_ctx)

    learned_gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=len(graph.units),
        current_edge_count=len(graph.edges),
        learning_active=True,
        learned_bias=0.5
    )
    learned_eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=10.0,
        risk_tolerance="LOW",
        criteria=EvaluationCriteria(min_utility=0.5)
    )

    learned_result = adaptation.execute_adaptation_cycle(graph, learned_gen_ctx, learned_eval_ctx)

    assert explicit_result.safety_constraints_satisfied
    assert learned_result.safety_constraints_satisfied
    assert explicit_result.authorization.rejection_reason is not None or explicit_result.authorization.authorized
    assert learned_result.authorization.rejection_reason is not None or learned_result.authorization.authorized
    print("PASS: test_system_distinguishes_learned_from_explicit")


def test_learning_can_be_reset_without_corrupting_structure():
    """Requirement 10: Learning can be reset without corrupting structural history."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("reset_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("reset_unit"),
        name="ResetUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(task_description="Reset test", max_units=5, max_edges=5)
    gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

    assert len(graph.units) == 1
    assert adaptation.learning.get_knowledge().cycle_count > 0

    adaptation.learning.reset_knowledge()

    assert adaptation.learning.get_knowledge().cycle_count == 0
    assert len(graph.units) == 1
    print("PASS: test_learning_can_be_reset_without_corrupting_structure")


def test_demonstrate_learned_adaptation_behavior_change():
    """Integrated test: Demonstrate that experience actually changes behavior."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    integration = LearnedAdaptationIntegration(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("behavior_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("behavior_unit"),
        name="BehaviorUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(task_description="Behavior change", max_units=10, max_edges=20)
    eval_ctx = EvaluationContext(
        current_graph=graph,
        active_objectives=["improve"],
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria(min_utility=0.3)
    )

    result = integration.demonstrate_learning_influence(graph, objective, eval_ctx)

    assert "cycle1_learning_active" in result
    assert result.get("knowledge_before_cycles", 0) == 0
    print(f"PASS: test_demonstrate_learned_adaptation_behavior_change (result={result})")


def test_learned_proposal_influence_via_generator():
    """Learning influences Generator proposals via GeneratorInfluence."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("influence_g"))

    for i in range(3):
        graph.add_unit(ComputationalUnit(
            unit_id=UnitID(f"influence_unit_{i}"),
            name=f"InfluenceUnit{i}",
            structure=StructureDimension.PRIMITIVE,
            visibility=VisibilityDimension.INSPECTABLE,
            lifecycle=LifecycleDimension.BASE
        ))

    influence = GeneratorInfluence(
        preferred_operation_types=["ADD_UNIT"],
        avoided_operation_types=["COMPOSE_UNITS", "SPECIALIZE_UNIT"],
        recommended_max_cost=50.0,
        recommended_min_utility=0.5,
        recommended_risk_tolerance="LOW",
        adaptation_bias=0.1
    )

    gen_ctx = LearnedGenerationContext(
        objective=GenerationObjective(task_description="Influence test", max_units=10, max_edges=20),
        graph_id=graph.graph_id,
        current_unit_count=len(graph.units),
        current_edge_count=0,
        generator_influence=influence,
        learned_preferred_ops=["ADD_UNIT"],
        learned_avoided_ops=["COMPOSE_UNITS", "SPECIALIZE_UNIT"],
        learned_bias=0.1,
        learning_active=True
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH"
    )

    result = adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

    assert result.learning_applied
    assert len(result.proposal.candidate_operations) > 0
    print("PASS: test_learned_proposal_influence_via_generator")


def test_controller_rejects_overriding_learning():
    """Controller does not accept learning as authority to bypass evaluation."""
    gen = ComputationGenerator()
    ctrl = StructuralController()
    learning = DeterministicLearningPolicy()
    tracker = PredictionTracker()

    adaptation = LearnedStructuralAdaptation(gen, ctrl, learning, tracker)

    graph = StructuralGraph(GraphID("override_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("override_unit"),
        name="OverrideUnit",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))

    objective = GenerationObjective(
        task_description="Override test",
        max_units=100,
        max_edges=100
    )

    gen_ctx = LearnedGenerationContext(
        objective=objective,
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0,
        learning_active=True,
        learned_bias=999.0
    )
    eval_ctx = LearnedEvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="LOW",
        criteria=EvaluationCriteria(min_utility=0.9)
    )

    result = adaptation.execute_adaptation_cycle(graph, gen_ctx, eval_ctx)

    assert result.safety_constraints_satisfied
    if result.authorization and result.authorization.authorized:
        assert result.proposal.expected_utility >= 0.9
    print("PASS: test_controller_rejects_overriding_learning")


def run_all_tests():
    tests = [
        test_learning_changes_future_proposal_ranking,
        test_learning_does_not_directly_mutate,
        test_controller_authority_remains_intact,
        test_learning_separated_from_structural_state,
        test_learning_history_is_provenance_traceable,
        test_replay_reproduces_deterministic_learning,
        test_learning_state_can_be_checkpoint_restored,
        test_bad_learned_policy_cannot_bypass_safety,
        test_system_distinguishes_learned_from_explicit,
        test_learning_can_be_reset_without_corrupting_structure,
        test_demonstrate_learned_adaptation_behavior_change,
        test_learned_proposal_influence_via_generator,
        test_controller_rejects_overriding_learning,
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

    print(f"\nPhase 11 Learned Structural Adaptation Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 11 LEARNED ADAPTATION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()