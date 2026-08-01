"""
Phase 8 Structural Controller Tests
Verifies proper structural control with EVALUATE/AUTHORIZE/REJECT/DEFER decision semantics.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID
from dnc.dcc.dcc_contracts import MutationProposal
from dnc.dcc.structural_controller import (
    StructuralController, DecisionType, EvaluationCriteria,
    ProposalEvaluation, EvaluationContext
)

def test_controller_initialization():
    """Controller initializes correctly."""
    ctrl = StructuralController()
    assert ctrl._decision_counter == 0
    assert ctrl._authorized_history == []
    print("PASS: test_controller_initialization")

def test_decision_type_enum():
    """DecisionType enum has correct values."""
    assert DecisionType.AUTHORIZE.value == "AUTHORIZE"
    assert DecisionType.REJECT.value == "REJECT"
    assert DecisionType.DEFER.value == "DEFER"
    assert DecisionType.REQUEST_REVISION.value == "REQUEST_REVISION"
    print("PASS: test_decision_type_enum")

def test_evaluation_criteria():
    """EvaluationCriteria carries threshold parameters."""
    criteria = EvaluationCriteria(
        min_utility=0.6,
        max_risk="HIGH",
        max_cost=25.0,
        require_rationale=True
    )
    assert criteria.min_utility == 0.6
    assert criteria.max_risk == "HIGH"
    print("PASS: test_evaluation_criteria")

def test_evaluation_context():
    """EvaluationContext aggregates graph state and constraints."""
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        active_objectives=["improve_accuracy"],
        constraints=["low_latency"],
        available_budget=50.0,
        risk_tolerance="MEDIUM"
    )
    assert context.available_budget == 50.0
    assert context.risk_tolerance == "MEDIUM"
    print("PASS: test_evaluation_context")

def test_evaluate_empty_proposals():
    """Controller returns empty list for empty proposals."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0
    )
    evaluations = ctrl.evaluate_proposals([], context)
    assert evaluations == []
    print("PASS: test_evaluate_empty_proposals")

def test_evaluate_low_utility_rejected():
    """Proposal with utility below threshold is REJECTED."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        criteria=EvaluationCriteria(min_utility=0.6)
    )
    proposal = MutationProposal(
        proposal_id="reject_low_util",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Low value proposal",
        expected_utility=0.2,
        estimated_cost=1.0,
        risk_assessment="LOW"
    )
    evaluations = ctrl.evaluate_proposals([proposal], context)
    assert len(evaluations) == 1
    assert evaluations[0].decision == DecisionType.REJECT
    assert len(evaluations[0].rejection_reasons) > 0
    print("PASS: test_evaluate_low_utility_rejected")

def test_evaluate_high_risk_rejected():
    """Proposal with risk above tolerance is REJECTED."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="LOW",
        criteria=EvaluationCriteria()
    )
    proposal = MutationProposal(
        proposal_id="reject_high_risk",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="High risk proposal",
        expected_utility=0.8,
        estimated_cost=1.0,
        risk_assessment="HIGH"
    )
    evaluations = ctrl.evaluate_proposals([proposal], context)
    assert len(evaluations) == 1
    assert evaluations[0].decision == DecisionType.REJECT
    assert any("risk" in r.lower() for r in evaluations[0].rejection_reasons)
    print("PASS: test_evaluate_high_risk_rejected")

def test_evaluate_exceeds_budget_rejected():
    """Proposal costing more than available budget is REJECTED."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=5.0,
        criteria=EvaluationCriteria()
    )
    proposal = MutationProposal(
        proposal_id="reject_expensive",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Expensive proposal",
        expected_utility=0.8,
        estimated_cost=50.0,
        risk_assessment="LOW"
    )
    evaluations = ctrl.evaluate_proposals([proposal], context)
    assert len(evaluations) == 1
    assert evaluations[0].decision == DecisionType.REJECT
    print("PASS: test_evaluate_exceeds_budget_rejected")

def test_evaluate_authorized():
    """High-utility, low-risk, low-cost proposal is AUTHORIZED."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria(min_utility=0.5)
    )
    proposal = MutationProposal(
        proposal_id="auth_good",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Good proposal",
        expected_utility=0.9,
        estimated_cost=2.0,
        risk_assessment="LOW"
    )
    evaluations = ctrl.evaluate_proposals([proposal], context)
    assert len(evaluations) == 1
    assert evaluations[0].decision == DecisionType.AUTHORIZE
    print("PASS: test_evaluate_authorized")

def test_evaluate_defer():
    """Proposals with marginal scores are DEFERRED."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="MEDIUM",
        criteria=EvaluationCriteria(min_utility=0.5)
    )
    proposal = MutationProposal(
        proposal_id="defer_marginal",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Marginal proposal",
        expected_utility=0.6,
        estimated_cost=5.0,
        risk_assessment="MEDIUM"
    )
    evaluations = ctrl.evaluate_proposals([proposal], context)
    assert len(evaluations) == 1
    assert evaluations[0].decision == DecisionType.DEFER
    print("PASS: test_evaluate_defer")

def test_evaluate_multiple_proposals():
    """Controller evaluates multiple proposals independently."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="MEDIUM",
        criteria=EvaluationCriteria(min_utility=0.5)
    )
    proposals = [
        MutationProposal(
            proposal_id="mp1",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Good",
            expected_utility=0.9,
            estimated_cost=2.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="mp2",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Bad utility",
            expected_utility=0.2,
            estimated_cost=2.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="mp3",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="High risk",
            expected_utility=0.8,
            estimated_cost=2.0,
            risk_assessment="HIGH"
        ),
    ]
    evaluations = ctrl.evaluate_proposals(proposals, context)
    assert len(evaluations) == 3
    auth_count = sum(1 for e in evaluations if e.decision == DecisionType.AUTHORIZE)
    rej_count = sum(1 for e in evaluations if e.decision == DecisionType.REJECT)
    assert auth_count == 1
    assert rej_count == 2
    print(f"PASS: test_evaluate_multiple_proposals (auth={auth_count}, rej={rej_count})")

def test_authorize_converts_evaluation():
    """authorize() converts AUTHORIZE evaluation to AuthorizationDecision."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    proposal = MutationProposal(
        proposal_id="auth_convert",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Good",
        expected_utility=0.9,
        estimated_cost=2.0,
        risk_assessment="LOW"
    )
    evaluation = ProposalEvaluation(
        proposal=proposal,
        decision=DecisionType.AUTHORIZE,
        score=0.9
    )
    context = EvaluationContext(current_graph=graph, available_budget=100.0)
    decision = ctrl.authorize(evaluation, context)
    assert decision.authorized
    assert decision.proposal_id == "auth_convert"
    print("PASS: test_authorize_converts_evaluation")

def test_authorize_reject_fails():
    """authorize() returns unauthorized for REJECT decision."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    proposal = MutationProposal(
        proposal_id="reject_auth_attempt",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Bad",
        expected_utility=0.2,
        estimated_cost=2.0,
        risk_assessment="LOW"
    )
    evaluation = ProposalEvaluation(
        proposal=proposal,
        decision=DecisionType.REJECT,
        score=0.2,
        rejection_reasons=["Low utility"]
    )
    context = EvaluationContext(current_graph=graph, available_budget=100.0)
    decision = ctrl.authorize(evaluation, context)
    assert not decision.authorized
    print("PASS: test_authorize_reject_fails")

def test_authorize_top_scoring():
    """authorize_top_scoring() selects highest-scoring authorize-capable proposal."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria()
    )
    proposals = [
        MutationProposal(
            proposal_id="low_score",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Low priority",
            expected_utility=0.5,
            estimated_cost=5.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="high_score",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="High priority",
            expected_utility=0.9,
            estimated_cost=2.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="mid_score",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Medium priority",
            expected_utility=0.7,
            estimated_cost=3.0,
            risk_assessment="LOW"
        ),
    ]
    evaluations = ctrl.evaluate_proposals(proposals, context)
    decision = ctrl.authorize_top_scoring(evaluations, context)
    assert decision is not None
    assert decision.proposal_id == "high_score"
    print("PASS: test_authorize_top_scoring")

def test_get_authorized_proposals():
    """get_authorized_proposals() extracts authorized proposals."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        risk_tolerance="HIGH",
        criteria=EvaluationCriteria()
    )
    proposals = [
        MutationProposal(
            proposal_id="auth1",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Auth 1",
            expected_utility=0.9,
            estimated_cost=1.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="rej1",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Rej 1",
            expected_utility=0.2,
            estimated_cost=1.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="auth2",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Auth 2",
            expected_utility=0.8,
            estimated_cost=1.0,
            risk_assessment="LOW"
        ),
    ]
    evaluations = ctrl.evaluate_proposals(proposals, context)
    authorized = ctrl.get_authorized_proposals(evaluations)
    assert len(authorized) == 2
    assert all(p.proposal_id in ("auth1", "auth2") for p in authorized)
    print("PASS: test_get_authorized_proposals")

def test_get_rejected_proposals():
    """get_rejected_proposals() extracts rejected proposals with reasons."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0,
        criteria=EvaluationCriteria(min_utility=0.6)
    )
    proposals = [
        MutationProposal(
            proposal_id="rej_util",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Low utility",
            expected_utility=0.2,
            estimated_cost=1.0,
            risk_assessment="LOW"
        ),
        MutationProposal(
            proposal_id="auth_ok",
            target_graph_id="eval_g",
            candidate_operations=[],
            rationale="Good",
            expected_utility=0.9,
            estimated_cost=1.0,
            risk_assessment="LOW"
        ),
    ]
    evaluations = ctrl.evaluate_proposals(proposals, context)
    rejected = ctrl.get_rejected_proposals(evaluations)
    assert len(rejected) == 1
    assert rejected[0][0].proposal_id == "rej_util"
    assert len(rejected[0][1]) > 0
    print("PASS: test_get_rejected_proposals")

def test_controller_respects_separation():
    """Controller does not generate proposals - only evaluates."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0
    )
    evaluations = ctrl.evaluate_proposals([], context)
    assert evaluations == []
    print("PASS: test_controller_respects_separation")

def test_score_computation():
    """_compute_score weights utility, cost, and risk correctly."""
    ctrl = StructuralController()
    graph = StructuralGraph(GraphID("eval_g"))
    context = EvaluationContext(
        current_graph=graph,
        available_budget=100.0
    )
    high_quality = MutationProposal(
        proposal_id="hq",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="High quality",
        expected_utility=0.9,
        estimated_cost=1.0,
        risk_assessment="LOW"
    )
    low_quality = MutationProposal(
        proposal_id="lq",
        target_graph_id="eval_g",
        candidate_operations=[],
        rationale="Low quality",
        expected_utility=0.3,
        estimated_cost=10.0,
        risk_assessment="HIGH"
    )
    eval_hq = ctrl._evaluate_single(high_quality, context)
    eval_lq = ctrl._evaluate_single(low_quality, context)
    assert eval_hq.score > eval_lq.score
    print(f"PASS: test_score_computation (hq={eval_hq.score:.2f}, lq={eval_lq.score:.2f})")

def run_all_tests():
    tests = [
        test_controller_initialization,
        test_decision_type_enum,
        test_evaluation_criteria,
        test_evaluation_context,
        test_evaluate_empty_proposals,
        test_evaluate_low_utility_rejected,
        test_evaluate_high_risk_rejected,
        test_evaluate_exceeds_budget_rejected,
        test_evaluate_authorized,
        test_evaluate_defer,
        test_evaluate_multiple_proposals,
        test_authorize_converts_evaluation,
        test_authorize_reject_fails,
        test_authorize_top_scoring,
        test_get_authorized_proposals,
        test_get_rejected_proposals,
        test_controller_respects_separation,
        test_score_computation,
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
    print(f"\nPhase 8 Structural Controller Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 8 STRUCTURAL CONTROLLER TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()