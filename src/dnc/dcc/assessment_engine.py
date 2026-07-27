"""
DNC Assessment and Adaptation Layer (Phase 9)
Bridges execution results back to DCCL adaptation decisions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from dnc.ir.graph import StructuralGraph
from dnc.dcc.dcc_contracts import MutationProposal

if TYPE_CHECKING:
    from dnc.dcc.structural_controller import ProposalEvaluation

@dataclass
class ExecutionResult:
    graph_id: str
    graph_version: str
    execution_time_ms: float = 0.0
    output: Any = None
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    units_executed: int = 0
    edges_traversed: int = 0
    success: bool = True

@dataclass
class Assessment:
    assessment_id: str
    proposal_id: str
    graph_before: str
    graph_after: str
    execution_result: ExecutionResult
    pre_transaction_utility_estimate: float
    post_execution_utility_measured: float
    improvement_delta: float = 0.0
    cost_actual: float = 0.0
    risk_actual: str = "LOW"
    alignment_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AdaptationKnowledge:
    past_assessments: List[Assessment] = field(default_factory=list)
    proposal_outcomes: Dict[str, str] = field(default_factory=dict)
    cumulative_improvement: float = 0.0

@dataclass
class DCCLAssessmentContext:
    current_graph: StructuralGraph
    active_objectives: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    available_budget: float = 100.0
    risk_tolerance: str = "MEDIUM"
    observation_history: List[ExecutionResult] = field(default_factory=list)
    adaptation_knowledge: AdaptationKnowledge = field(default_factory=AdaptationKnowledge)

class AssessmentEngine:
    """
    Phase 9 Assessment Engine: Evaluates execution outcomes and feeds back to DCCL.

    Consumes:
    - ExecutionResult from execution core
    - Pre-transaction proposal data
    - Graph state before/after mutation

    Produces:
    - Assessment with pre/post comparison
    - AdaptationKnowledge update
    - Adaptation signals for next DCCL cycle

    Key epistemic distinction:
    - Pre-transaction: "Will this proposal be beneficial?" (prediction)
    - Post-execution: "Was the proposal actually beneficial?" (observation)
    """
    def __init__(self):
        self._assessment_counter = 0

    def assess_execution(
        self,
        execution_result: ExecutionResult,
        proposal: MutationProposal,
        graph_before_version: str,
        graph_after_version: str,
        baseline_utility: Optional[float] = None,
    ) -> Assessment:
        """
        Assess whether a proposal's execution produced the intended outcome.
        """
        self._assessment_counter += 1

        post_utility = execution_result.metrics.get("utility", 0.0)
        # Improvement is causal relative to preserving the prior structure's
        # observed value. Prediction error is a different quantity and must not
        # be fed back as evidence that the mutation harmed the system.
        comparison_baseline = (
            proposal.expected_utility if baseline_utility is None else baseline_utility
        )
        improvement = post_utility - comparison_baseline
        prediction_error = post_utility - proposal.expected_utility

        return Assessment(
            assessment_id=f"assess_{self._assessment_counter}",
            proposal_id=proposal.proposal_id,
            graph_before=graph_before_version,
            graph_after=graph_after_version,
            execution_result=execution_result,
            pre_transaction_utility_estimate=proposal.expected_utility,
            post_execution_utility_measured=post_utility,
            improvement_delta=improvement,
            cost_actual=execution_result.execution_time_ms / 1000.0,
            risk_actual=self._assess_risk(execution_result),
            alignment_score=self._compute_alignment(proposal, execution_result),
            metadata={
                "units_executed": execution_result.units_executed,
                "edges_traversed": execution_result.edges_traversed,
                "success": execution_result.success,
                "baseline_utility": comparison_baseline,
                "prediction_error": prediction_error,
            }
        )

    def _assess_risk(self, result: ExecutionResult) -> str:
        """Determine actual risk from execution result."""
        if not result.success:
            return "HIGH"
        if result.execution_time_ms > 5000:
            return "MEDIUM"
        return "LOW"

    def _compute_alignment(self, proposal: MutationProposal, result: ExecutionResult) -> float:
        """Compute how well execution aligned with proposal intent."""
        if not result.success:
            return 0.0
        utility = result.metrics.get("utility", 0.0)
        return min(1.0, utility / max(proposal.expected_utility, 0.01))

    def update_adaptation_knowledge(
        self,
        knowledge: AdaptationKnowledge,
        assessment: Assessment
    ) -> AdaptationKnowledge:
        """
        Update adaptation knowledge with new assessment data.
        """
        knowledge.past_assessments.append(assessment)
        knowledge.proposal_outcomes[assessment.proposal_id] = (
            "SUCCESSFUL" if assessment.improvement_delta > 0 else "UNSUCCESSFUL"
        )
        knowledge.cumulative_improvement += assessment.improvement_delta
        return knowledge

    def should_adapt(
        self,
        assessment: Assessment,
        threshold: float = 0.1
    ) -> bool:
        """
        Determine if DCCL should trigger adaptation based on assessment.
        """
        return assessment.improvement_delta < -threshold

    def get_learned_outcomes(
        self,
        knowledge: AdaptationKnowledge,
        proposal_id_prefix: str = ""
    ) -> Dict[str, str]:
        """
        Get learned outcomes for future proposal generation.
        """
        if not proposal_id_prefix:
            return dict(knowledge.proposal_outcomes)
        return {
            k: v for k, v in knowledge.proposal_outcomes.items()
            if k.startswith(proposal_id_prefix)
        }


class DCCLClosedLoopOrchestrator:
    """
    Phase 9 Closed-Loop Orchestrator: Full DCCL control loop with assessment integration.

    Implements the complete cycle:
    INTERPRET → GENERATE → EVALUATE → AUTHORIZE → TRANSACT → PROJECT → EXECUTE → ASSESS → ADAPT
    """

    def __init__(
        self,
        computation_generator,
        structural_controller,
        transaction_manager,
        mutation_engine,
        projector,
        execution_core,
        assessment_engine
    ):
        self.generator = computation_generator
        self.controller = structural_controller
        self.transaction_manager = transaction_manager
        self.mutation_engine = mutation_engine
        self.projector = projector
        self.execution_core = execution_core
        self.assessment_engine = assessment_engine
        self._cycle_count = 0
        self._adaptation_knowledge = AdaptationKnowledge()

    def execute_full_cycle(
        self,
        graph: StructuralGraph,
        generation_context,
        evaluation_context
    ) -> Tuple[StructuralGraph, Assessment, List[ProposalEvaluation]]:
        """
        Execute one complete closed-loop DCCL cycle.

        Returns:
        - Updated graph
        - Assessment of the cycle's outcome
        - All proposal evaluations for this cycle
        """
        self._cycle_count += 1

        graph_before_version = str(graph.version)

        # GENERATE: Generate proposals from current graph state
        proposals = self.generator.generate_proposals(graph, generation_context)

        # EVALUATE: Controller evaluates proposals
        evaluations = self.controller.evaluate_proposals(proposals, evaluation_context)

        # AUTHORIZE: Select and authorize best proposal
        authorized = self.controller.authorize_top_scoring(evaluations, evaluation_context)

        if not authorized:
            return graph, None, evaluations

        # Find the authorized proposal
        authorized_proposal = next(
            (e.proposal for e in evaluations if e.decision.value == "AUTHORIZE"),
            None
        )
        if not authorized_proposal:
            return graph, None, evaluations

        # TRANSACT: Apply mutation through transaction manager
        graph_after = self._apply_mutation(graph, authorized_proposal)
        graph_after_version = str(graph_after.version)

        # PROJECT: Project structural graph to executable DAG
        dag = self.projector.project(graph_after)

        # EXECUTE: Execute the projected DAG
        execution_result = self._execute_dag(dag, graph_after)

        # ASSESS: Evaluate execution outcome against proposal intent
        assessment = self.assessment_engine.assess_execution(
            execution_result,
            authorized_proposal,
            graph_before_version,
            graph_after_version
        )

        # ADAPT: Update adaptation knowledge
        self._adaptation_knowledge = self.assessment_engine.update_adaptation_knowledge(
            self._adaptation_knowledge,
            assessment
        )

        return graph_after, assessment, evaluations

    def _apply_mutation(self, graph: StructuralGraph, proposal: MutationProposal) -> StructuralGraph:
        """Apply authorized mutation via transaction manager."""
        with self.transaction_manager.begin_transaction() as txn:
            for op in proposal.candidate_operations:
                if op.operation_type.value == "ADD_UNIT":
                    unit = op.parameters.get("unit")
                    if unit:
                        self.mutation_engine.add_unit(graph, unit, txn_id=txn.transaction_id)
                elif op.operation_type.value == "CONNECT_UNITS":
                    source = op.parameters.get("source")
                    target = op.parameters.get("target")
                    edge_type = op.parameters.get("edge_type")
                    if source and target:
                        self.mutation_engine.connect_units(
                            graph, source, target, edge_type, txn_id=txn.transaction_id
                        )
            txn.commit()
        return graph

    def _execute_dag(self, dag, graph):
        """Execute projected DAG and return execution result."""
        try:
            result = self.execution_core.execute(dag)
            return ExecutionResult(
                graph_id=str(graph.graph_id.value),
                graph_version=str(graph.version),
                execution_time_ms=result.get("execution_time_ms", 0.0),
                output=result.get("output"),
                metrics=result.get("metrics", {"utility": 0.5}),
                units_executed=result.get("units_executed", len(graph.units)),
                edges_traversed=result.get("edges_traversed", 0),
                success=result.get("success", True)
            )
        except Exception as e:
            return ExecutionResult(
                graph_id=str(graph.graph_id.value),
                graph_version=str(graph.version),
                error=str(e),
                success=False,
                metrics={"utility": 0.0}
            )

    def get_adaptation_knowledge(self) -> AdaptationKnowledge:
        """Return current adaptation knowledge."""
        return self._adaptation_knowledge

    def get_cycle_count(self) -> int:
        """Return number of completed cycles."""
        return self._cycle_count
