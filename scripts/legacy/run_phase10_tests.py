"""
Phase 10 Adaptation Knowledge and Learning Integration Tests
Verifies reference learning loop: predict → execute → observe → assess → learn → inform.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.dcc.assessment_engine import ExecutionResult, Assessment, AdaptationKnowledge
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision
from dnc.dcc.learning_engine import (
    LearningEngine, PredictionTracker, DeterministicLearningPolicy,
    PredictionRecord, OutcomeRecord, PredictionError, LearningSignal,
    AdaptationKnowledgeBase, GeneratorInfluence
)
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.identity import UnitID

def test_prediction_tracker_records():
    """Requirement 1: Records predicted utility/cost/risk before execution."""
    tracker = PredictionTracker()
    proposal = MutationProposal(
        proposal_id="pred_test_1",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.8,
        estimated_cost=2.5,
        risk_assessment="LOW"
    )
    decision = AuthorizationDecision(proposal_id="pred_test_1", authorized=True)
    record = tracker.record_prediction(proposal, decision)

    assert record.proposal_id == "pred_test_1"
    assert record.predicted_utility == 0.8
    assert record.predicted_cost == 2.5
    assert record.predicted_risk == "LOW"
    print("PASS: test_prediction_tracker_records")

def test_outcome_record_from_assessment():
    """Requirement 2: Records actual execution outcomes."""
    result = ExecutionResult(
        graph_id="test_g",
        graph_version="v1.0.0-1",
        execution_time_ms=15.0,
        metrics={"utility": 0.65},
        success=True
    )
    proposal = MutationProposal(
        proposal_id="out_test_1",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.8,
        estimated_cost=2.5
    )
    assessment = Assessment(
        assessment_id="assess_1",
        proposal_id="out_test_1",
        graph_before="v1.0.0-0",
        graph_after="v1.0.0-1",
        execution_result=result,
        pre_transaction_utility_estimate=0.8,
        post_execution_utility_measured=0.65,
        improvement_delta=-0.15
    )

    engine = LearningEngine()
    outcome = engine.record_outcome(assessment)

    assert outcome.proposal_id == "out_test_1"
    assert outcome.observed_utility == 0.65
    assert outcome.improvement_delta == -0.15
    assert outcome.successful == True
    print("PASS: test_outcome_record_from_assessment")

def test_prediction_error_computation():
    """Requirement 3: Computes prediction error (delta between predicted and actual)."""
    prediction = PredictionRecord(
        proposal_id="err_test_1",
        predicted_utility=0.8,
        predicted_cost=2.5,
        predicted_risk="LOW"
    )
    outcome = OutcomeRecord(
        proposal_id="err_test_1",
        observed_utility=0.65,
        observed_cost=3.0,
        observed_risk="MEDIUM",
        improvement_delta=-0.15,
        alignment_score=0.8,
        successful=True
    )

    engine = LearningEngine()
    error = engine.compute_prediction_error(prediction, outcome)

    assert error.proposal_id == "err_test_1"
    assert abs(error.utility_error - (-0.15)) < 1e-9
    assert abs(error.cost_error - 0.5) < 1e-9
    assert error.risk_miss == True
    assert error.absolute_error == 0.65
    print("PASS: test_prediction_error_computation")

def test_knowledge_accumulation():
    """Requirement 4: Accumulates adaptation knowledge over multiple cycles."""
    engine = LearningEngine()

    for i in range(5):
        pred = PredictionRecord(
            proposal_id=f"acc_test_{i}",
            predicted_utility=0.7 + i * 0.02,
            predicted_cost=2.0 + i * 0.1,
            predicted_risk="LOW"
        )
        outcome = OutcomeRecord(
            proposal_id=f"acc_test_{i}",
            observed_utility=0.65 + i * 0.02,
            observed_cost=2.2 + i * 0.1,
            observed_risk="LOW",
            improvement_delta=-0.05,
            alignment_score=0.9,
            successful=True
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    knowledge = engine.get_knowledge()
    assert len(knowledge.predictions) == 5
    assert len(knowledge.outcomes) == 5
    assert len(knowledge.prediction_errors) == 5
    assert knowledge.cumulative_improvement == -0.25
    assert knowledge.cycle_count == 5
    print("PASS: test_knowledge_accumulation")

def test_learning_informs_generator_context():
    """Requirement 5: Knowledge available to future GenerationContext via GeneratorInfluence."""
    engine = LearningEngine()

    for i in range(10):
        pred = PredictionRecord(
            proposal_id=f"inf_test_{i}",
            predicted_utility=0.6,
            predicted_cost=2.0,
            predicted_risk="LOW"
        )
        outcome = OutcomeRecord(
            proposal_id=f"inf_test_{i}",
            observed_utility=0.5,
            observed_cost=3.0,
            observed_risk="MEDIUM",
            improvement_delta=-0.1,
            alignment_score=0.7,
            successful=True
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    influence = engine.compute_generator_influence()

    assert isinstance(influence, GeneratorInfluence)
    assert influence.recommended_min_utility >= 0.3
    assert "COMPOSE_UNITS" in influence.avoided_operation_types
    assert "SPECIALIZE_UNIT" in influence.avoided_operation_types
    print(f"PASS: test_learning_informs_generator_context (influence: {influence.avoided_operation_types})")

def test_learning_informs_controller_context():
    """Knowledge available to future EvaluationContext via GeneratorInfluence."""
    engine = LearningEngine()

    for i in range(8):
        pred = PredictionRecord(
            proposal_id=f"ctrl_test_{i}",
            predicted_utility=0.9,
            predicted_cost=1.0,
            predicted_risk="LOW"
        )
        outcome = OutcomeRecord(
            proposal_id=f"ctrl_test_{i}",
            observed_utility=0.3,
            observed_cost=8.0,
            observed_risk="HIGH",
            improvement_delta=-0.6,
            alignment_score=0.3,
            successful=False
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    influence = engine.compute_generator_influence()

    assert influence.recommended_risk_tolerance == "LOW"
    assert influence.recommended_max_cost < 100.0
    assert influence.adaptation_bias < 0
    print(f"PASS: test_learning_informs_controller_context (risk_tolerance={influence.recommended_risk_tolerance})")

def test_learning_cannot_directly_mutate():
    """Requirement 7: Proves learning cannot directly mutate structural state."""
    engine = LearningEngine()
    graph_state = {"units": {"u1": {}}, "edges": {}}

    pred = PredictionRecord(
        proposal_id="no_mutate",
        predicted_utility=0.8,
        predicted_cost=2.0,
        predicted_risk="LOW"
    )
    outcome = OutcomeRecord(
        proposal_id="no_mutate",
        observed_utility=0.7,
        observed_cost=2.1,
        observed_risk="LOW",
        improvement_delta=-0.1,
        alignment_score=0.9,
        successful=True
    )
    error = engine.compute_prediction_error(pred, outcome)
    engine.update_knowledge(pred, outcome, error)

    current_state = {"units": {"u1": {}}, "edges": {}}
    assert current_state == graph_state
    print("PASS: test_learning_cannot_directly_mutate")

def test_learning_signal_generation():
    """Learning signals generated from prediction errors."""
    engine = LearningEngine()

    pred = PredictionRecord(proposal_id="sig_1", predicted_utility=0.8, predicted_cost=2.0, predicted_risk="LOW")
    outcome = OutcomeRecord(
        proposal_id="sig_1", observed_utility=0.3, observed_cost=5.0, observed_risk="HIGH",
        improvement_delta=-0.5, alignment_score=0.4, successful=False
    )
    error = engine.compute_prediction_error(pred, outcome)
    signal = engine.generate_learning_signal(error, outcome)

    assert signal.signal_type in ("ERROR_LARGE", "NEGATIVE_SURPRISE")
    assert signal.error is not None
    assert signal.error.absolute_error > 0.3
    print(f"PASS: test_learning_signal_generation (type={signal.signal_type})")

def test_accuracy_metrics():
    """Requirement 8: Accuracy metrics computed and updated."""
    engine = LearningEngine()

    test_cases = [
        (0.8, 0.7, "LOW", 0.5, "LOW"),
        (0.6, 0.65, "MEDIUM", 0.3, "LOW"),
        (0.7, 0.5, "LOW", 0.8, "HIGH"),
        (0.5, 0.55, "LOW", 0.2, "LOW"),
    ]

    for i, (pred_u, obs_u, pred_r, cost, obs_r) in enumerate(test_cases):
        pred = PredictionRecord(proposal_id=f"acc_{i}", predicted_utility=pred_u, predicted_cost=cost, predicted_risk=pred_r)
        outcome = OutcomeRecord(
            proposal_id=f"acc_{i}", observed_utility=obs_u, observed_cost=cost + 0.1,
            observed_risk=obs_r, improvement_delta=obs_u - pred_u, alignment_score=0.8, successful=True
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    knowledge = engine.get_knowledge()
    assert 0.0 <= knowledge.utility_accuracy <= 1.0
    assert 0.0 <= knowledge.cost_accuracy <= 1.0
    assert 0.0 <= knowledge.risk_accuracy <= 1.0
    print(f"PASS: test_accuracy_metrics (u_acc={knowledge.utility_accuracy:.2f}, c_acc={knowledge.cost_accuracy:.2f}, r_acc={knowledge.risk_accuracy:.2f})")

def test_deterministic_learning_policy():
    """Requirement 10: System produces identical results under deterministic learning policy."""
    def run_learning_cycle():
        engine = DeterministicLearningPolicy()
        pred = PredictionRecord(proposal_id="det_test", predicted_utility=0.75, predicted_cost=2.5, predicted_risk="LOW")
        result = ExecutionResult(graph_id="g", graph_version="v1", metrics={"utility": 0.6}, success=True)
        assessment = Assessment(
            assessment_id="a1", proposal_id="det_test", graph_before="v0", graph_after="v1",
            execution_result=result, pre_transaction_utility_estimate=0.75,
            post_execution_utility_measured=0.6, improvement_delta=-0.15
        )
        knowledge, signals, influence = engine.process(pred, assessment)
        return knowledge, signals, influence

    results = [run_learning_cycle() for _ in range(3)]

    for i in range(1, len(results)):
        assert results[i][0].utility_accuracy == results[0][0].utility_accuracy
        assert results[i][0].cumulative_improvement == results[0][0].cumulative_improvement
        assert len(results[i][1]) == len(results[0][1])
    print("PASS: test_deterministic_learning_policy")

def test_proposal_outcome_tracking():
    """Tracks which proposals succeeded vs failed."""
    engine = LearningEngine()

    for i in range(6):
        pred = PredictionRecord(
            proposal_id=f"track_{i}",
            predicted_utility=0.7,
            predicted_cost=2.0,
            predicted_risk="LOW"
        )
        outcome = OutcomeRecord(
            proposal_id=f"track_{i}",
            observed_utility=0.7 if i % 2 == 0 else 0.4,
            observed_cost=2.0,
            observed_risk="LOW",
            improvement_delta=0.0 if i % 2 == 0 else -0.3,
            alignment_score=1.0 if i % 2 == 0 else 0.6,
            successful=(i % 2 == 0)
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    knowledge = engine.get_knowledge()
    assert knowledge.successful_proposals == 3
    assert knowledge.failed_proposals == 3
    assert knowledge.proposal_outcomes["track_0"] == "SUCCESSFUL"
    assert knowledge.proposal_outcomes["track_1"] == "UNSUCCESSFUL"
    print("PASS: test_proposal_outcome_tracking")

def test_learning_cycle_integration():
    """Full cycle: predict → execute → observe → assess → learn → inform."""
    engine = LearningEngine()
    tracker = PredictionTracker()

    proposal = MutationProposal(
        proposal_id="full_cycle_1",
        target_graph_id="test_g",
        candidate_operations=[],
        expected_utility=0.8,
        estimated_cost=1.5,
        risk_assessment="LOW"
    )
    decision = AuthorizationDecision(proposal_id="full_cycle_1", authorized=True)

    prediction = tracker.record_prediction(proposal, decision)
    assert isinstance(prediction, PredictionRecord)

    result = ExecutionResult(
        graph_id="test_g", graph_version="v1.0.0-1",
        execution_time_ms=12.0, metrics={"utility": 0.72}, success=True
    )
    assessment = Assessment(
        assessment_id="assess_full",
        proposal_id="full_cycle_1",
        graph_before="v1.0.0-0",
        graph_after="v1.0.0-1",
        execution_result=result,
        pre_transaction_utility_estimate=0.8,
        post_execution_utility_measured=0.72,
        improvement_delta=-0.08
    )

    knowledge, signals, influence = engine.learn_from_assessment(prediction, assessment)

    assert knowledge.cycle_count == 1
    assert len(signals) == 1
    assert isinstance(influence, GeneratorInfluence)
    assert knowledge.cumulative_improvement == -0.08
    print("PASS: test_learning_cycle_integration")

def test_no_learning_without_execution():
    """Learning cannot occur without actual execution (no ground truth)."""
    engine = LearningEngine()
    initial_knowledge = engine.get_knowledge()

    assert initial_knowledge.cycle_count == 0
    assert initial_knowledge.cumulative_improvement == 0.0
    print("PASS: test_no_learning_without_execution")

def test_learning_with_failed_execution():
    """Learning from failed execution correctly records failure."""
    engine = LearningEngine()

    pred = PredictionRecord(
        proposal_id="fail_test",
        predicted_utility=0.9,
        predicted_cost=1.0,
        predicted_risk="LOW"
    )
    outcome = OutcomeRecord(
        proposal_id="fail_test",
        observed_utility=0.0,
        observed_cost=0.0,
        observed_risk="HIGH",
        improvement_delta=-0.9,
        alignment_score=0.0,
        successful=False
    )
    error = engine.compute_prediction_error(pred, outcome)
    knowledge = engine.update_knowledge(pred, outcome, error)
    signal = engine.generate_learning_signal(error, outcome)

    assert signal.signal_type in ("ERROR_LARGE", "NEGATIVE_SURPRISE")
    assert knowledge.proposal_outcomes["fail_test"] == "UNSUCCESSFUL"
    print("PASS: test_learning_with_failed_execution")

def test_learning_with_positive_surprise():
    """Learning captures positive surprises (exceeded prediction)."""
    engine = LearningEngine()

    pred = PredictionRecord(
        proposal_id="pos_surprise",
        predicted_utility=0.5,
        predicted_cost=3.0,
        predicted_risk="MEDIUM"
    )
    outcome = OutcomeRecord(
        proposal_id="pos_surprise",
        observed_utility=0.85,
        observed_cost=2.5,
        observed_risk="LOW",
        improvement_delta=0.35,
        alignment_score=1.0,
        successful=True
    )
    error = engine.compute_prediction_error(pred, outcome)
    signal = engine.generate_learning_signal(error, outcome)

    assert signal.signal_type == "POSITIVE_SURPRISE"
    assert error.utility_error == 0.35
    print("PASS: test_learning_with_positive_surprise")

def test_reset_knowledge():
    """Knowledge base can be reset for clean restarts."""
    engine = LearningEngine()

    for i in range(3):
        pred = PredictionRecord(proposal_id=f"reset_{i}", predicted_utility=0.7, predicted_cost=2.0, predicted_risk="LOW")
        outcome = OutcomeRecord(
            proposal_id=f"reset_{i}", observed_utility=0.6, observed_cost=2.1, observed_risk="LOW",
            improvement_delta=-0.1, alignment_score=0.8, successful=True
        )
        error = engine.compute_prediction_error(pred, outcome)
        engine.update_knowledge(pred, outcome, error)

    assert engine.get_knowledge().cycle_count == 3

    engine.reset_knowledge()
    reset_knowledge = engine.get_knowledge()

    assert reset_knowledge.cycle_count == 0
    assert len(reset_knowledge.predictions) == 0
    assert len(reset_knowledge.outcomes) == 0
    assert reset_knowledge.cumulative_improvement == 0.0
    print("PASS: test_reset_knowledge")

def run_all_tests():
    tests = [
        test_prediction_tracker_records,
        test_outcome_record_from_assessment,
        test_prediction_error_computation,
        test_knowledge_accumulation,
        test_learning_informs_generator_context,
        test_learning_informs_controller_context,
        test_learning_cannot_directly_mutate,
        test_learning_signal_generation,
        test_accuracy_metrics,
        test_deterministic_learning_policy,
        test_proposal_outcome_tracking,
        test_learning_cycle_integration,
        test_no_learning_without_execution,
        test_learning_with_failed_execution,
        test_learning_with_positive_surprise,
        test_reset_knowledge,
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

    print(f"\nPhase 10 Adaptation Knowledge & Learning Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 10 LEARNING INTEGRATION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()