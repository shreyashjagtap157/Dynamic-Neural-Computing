"""
DNC Adaptation Knowledge and Learning Layer (Phase 10)
Reference implementation of learning-from-observation without mutation authority.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from collections import defaultdict
import statistics

from dnc.dcc.assessment_engine import Assessment, AdaptationKnowledge, ExecutionResult
from dnc.dcc.dcc_contracts import MutationProposal, AuthorizationDecision

@dataclass
class PredictionRecord:
    proposal_id: str
    predicted_utility: float
    predicted_cost: float
    predicted_risk: str
    timestamp: int = 0

@dataclass
class OutcomeRecord:
    proposal_id: str
    observed_utility: float
    observed_cost: float
    observed_risk: str
    improvement_delta: float
    alignment_score: float
    successful: bool

@dataclass
class PredictionError:
    proposal_id: str
    utility_error: float
    cost_error: float
    risk_miss: bool
    absolute_error: float

@dataclass
class LearningSignal:
    signal_type: str
    proposal_id: str
    error: Optional[PredictionError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AdaptationKnowledgeBase:
    predictions: List[PredictionRecord] = field(default_factory=list)
    outcomes: List[OutcomeRecord] = field(default_factory=list)
    prediction_errors: List[PredictionError] = field(default_factory=list)
    proposal_outcomes: Dict[str, str] = field(default_factory=dict)
    cumulative_improvement: float = 0.0
    average_utility_error: float = 0.0
    average_cost_error: float = 0.0
    utility_accuracy: float = 1.0
    cost_accuracy: float = 1.0
    risk_accuracy: float = 1.0
    cycle_count: int = 0
    successful_proposals: int = 0
    failed_proposals: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeneratorInfluence:
    preferred_operation_types: List[str] = field(default_factory=list)
    avoided_operation_types: List[str] = field(default_factory=list)
    recommended_max_cost: float = 100.0
    recommended_min_utility: float = 0.5
    recommended_risk_tolerance: str = "MEDIUM"
    adaptation_bias: float = 0.0

class PredictionTracker:
    """
    Tracks predictions for learning signal computation.
    Independent from structural state - purely observational.
    """
    def __init__(self):
        self._prediction_counter = 0

    def record_prediction(
        self,
        proposal: MutationProposal,
        decision: AuthorizationDecision
    ) -> PredictionRecord:
        """Record a prediction before execution."""
        self._prediction_counter += 1
        record = PredictionRecord(
            proposal_id=proposal.proposal_id,
            predicted_utility=proposal.expected_utility,
            predicted_cost=proposal.estimated_cost,
            predicted_risk=proposal.risk_assessment,
            timestamp=self._prediction_counter
        )
        return record

    def get_latest_prediction(self, proposal_id: str) -> Optional[PredictionRecord]:
        """Retrieve prediction for a specific proposal."""
        for p in reversed(self.predictions if hasattr(self, 'predictions') else []):
            if p.proposal_id == proposal_id:
                return p
        return None


class LearningEngine:
    """
    Phase 10 Learning Engine: Computes prediction errors and generates learning signals.

    Consumes:
    - PredictionRecord (pre-execution)
    - OutcomeRecord (post-execution via Assessment)
    - AdaptationKnowledge (accumulated history)

    Produces:
    - PredictionError (computed deltas)
    - LearningSignal (influence indicators)
    - GeneratorInfluence (context for future generation)
    - Updated AdaptationKnowledgeBase

    CRITICAL: Learning Engine PROPOSES nothing, MUTATES nothing.
    It only observes, computes, and informs the Generator/Controller via context.
    """
    def __init__(self):
        self._knowledge = AdaptationKnowledgeBase()
        self._signal_counter = 0

    def record_outcome(self, assessment: Assessment) -> OutcomeRecord:
        """Record observed outcome from execution assessment."""
        outcome = OutcomeRecord(
            proposal_id=assessment.proposal_id,
            observed_utility=assessment.post_execution_utility_measured,
            observed_cost=assessment.cost_actual,
            observed_risk=assessment.risk_actual,
            improvement_delta=assessment.improvement_delta,
            alignment_score=assessment.alignment_score,
            successful=assessment.execution_result.success
        )
        return outcome

    def compute_prediction_error(
        self,
        prediction: PredictionRecord,
        outcome: OutcomeRecord
    ) -> PredictionError:
        """Compute prediction error between expected and observed."""
        utility_error = outcome.observed_utility - prediction.predicted_utility
        cost_error = outcome.observed_cost - prediction.predicted_cost
        risk_miss = outcome.observed_risk != prediction.predicted_risk
        absolute_error = abs(utility_error) + abs(cost_error)

        return PredictionError(
            proposal_id=prediction.proposal_id,
            utility_error=utility_error,
            cost_error=cost_error,
            risk_miss=risk_miss,
            absolute_error=absolute_error
        )

    def update_knowledge(
        self,
        prediction: PredictionRecord,
        outcome: OutcomeRecord,
        error: PredictionError
    ) -> AdaptationKnowledgeBase:
        """Update adaptation knowledge with new observation."""
        self._knowledge.predictions.append(prediction)
        self._knowledge.outcomes.append(outcome)
        self._knowledge.prediction_errors.append(error)
        self._knowledge.proposal_outcomes[outcome.proposal_id] = (
            "SUCCESSFUL" if outcome.improvement_delta > 0 else "UNSUCCESSFUL"
        )
        self._knowledge.cumulative_improvement += outcome.improvement_delta

        all_utility_errors = [e.utility_error for e in self._knowledge.prediction_errors]
        all_cost_errors = [e.cost_error for e in self._knowledge.prediction_errors]

        if all_utility_errors:
            self._knowledge.average_utility_error = statistics.mean(all_utility_errors)
        if all_cost_errors:
            self._knowledge.average_cost_error = statistics.mean(all_cost_errors)

        successful = sum(1 for o in self._knowledge.outcomes if o.improvement_delta > 0)
        total = len(self._knowledge.outcomes)
        if total > 0:
            self._knowledge.utility_accuracy = successful / total
            self._knowledge.cost_accuracy = 1.0 - min(1.0, abs(self._knowledge.average_cost_error) / max(outcome.observed_cost, 0.01))
            self._knowledge.risk_accuracy = 1.0 - (sum(1 for e in self._knowledge.prediction_errors if e.risk_miss) / total)
            self._knowledge.successful_proposals = successful
            self._knowledge.failed_proposals = total - successful

        self._knowledge.cycle_count += 1
        return self._knowledge

    def generate_learning_signal(
        self,
        error: PredictionError,
        outcome: OutcomeRecord
    ) -> LearningSignal:
        """Generate a learning signal from prediction error."""
        self._signal_counter += 1

        signal_type = "INFO"
        if error.absolute_error > 0.3:
            signal_type = "ERROR_LARGE"
        elif error.absolute_error > 0.15:
            signal_type = "ERROR_MEDIUM"
        elif error.absolute_error > 0.05:
            signal_type = "ERROR_SMALL"

        if outcome.successful and error.utility_error > 0:
            signal_type = "POSITIVE_SURPRISE"
        elif outcome.successful and error.utility_error < -0.2:
            signal_type = "NEGATIVE_SURPRISE"

        return LearningSignal(
            signal_type=signal_type,
            proposal_id=error.proposal_id,
            error=error,
            metadata={
                "observed_utility": outcome.observed_utility,
                "predicted_utility": outcome.observed_utility - error.utility_error,
                "successful": outcome.successful
            }
        )

    def compute_generator_influence(self) -> GeneratorInfluence:
        """Compute generator influence from accumulated knowledge."""
        if not self._knowledge.prediction_errors:
            return GeneratorInfluence()

        recent_errors = self._knowledge.prediction_errors[-10:]
        avg_utility_error = statistics.mean(e.utility_error for e in recent_errors)
        avg_cost_error = statistics.mean(e.cost_error for e in recent_errors)

        recent_outcomes = self._knowledge.outcomes[-10:]
        successful_recent = sum(1 for o in recent_outcomes if o.improvement_delta > 0)
        success_rate = successful_recent / max(len(recent_outcomes), 1)

        preferred_ops = []
        avoided_ops = []

        if success_rate < 0.4:
            avoided_ops.append("COMPOSE_UNITS")
            avoided_ops.append("SPECIALIZE_UNIT")
        elif success_rate > 0.7:
            preferred_ops.append("ADD_UNIT")
            preferred_ops.append("CONNECT_UNITS")

        recent_risk_misses = sum(1 for e in recent_errors if e.risk_miss)
        risk_accuracy = 1.0 - (recent_risk_misses / max(len(recent_errors), 1))

        recommended_risk = "MEDIUM"
        if risk_accuracy < 0.5:
            recommended_risk = "LOW"

        recommended_min_utility = 0.5
        if avg_utility_error < -0.1:
            recommended_min_utility = max(0.3, 0.5 + avg_utility_error)

        adaptation_bias = self._knowledge.cumulative_improvement / max(self._knowledge.cycle_count, 1)

        return GeneratorInfluence(
            preferred_operation_types=preferred_ops,
            avoided_operation_types=avoided_ops,
            recommended_max_cost=max(10.0, 100.0 - avg_cost_error * 10),
            recommended_min_utility=recommended_min_utility,
            recommended_risk_tolerance=recommended_risk,
            adaptation_bias=adaptation_bias
        )

    def learn_from_assessment(
        self,
        prediction: PredictionRecord,
        assessment: Assessment
    ) -> Tuple[AdaptationKnowledgeBase, List[LearningSignal], GeneratorInfluence]:
        """
        Full learning cycle: record outcome, compute error, update knowledge, generate signals.
        """
        outcome = self.record_outcome(assessment)
        error = self.compute_prediction_error(prediction, outcome)
        signals = [self.generate_learning_signal(error, outcome)]
        knowledge = self.update_knowledge(prediction, outcome, error)
        influence = self.compute_generator_influence()

        return knowledge, signals, influence

    def get_knowledge(self) -> AdaptationKnowledgeBase:
        """Return current adaptation knowledge."""
        return self._knowledge

    def reset_knowledge(self) -> None:
        """Reset knowledge base (for testing or restart)."""
        self._knowledge = AdaptationKnowledgeBase()
        self._signal_counter = 0


class DeterministicLearningPolicy:
    """
    Deterministic reference learning policy for conformance and testing.
    Produces consistent output for identical input histories.
    """
    def __init__(self):
        self._learning_engine = LearningEngine()

    def process(
        self,
        prediction: PredictionRecord,
        assessment: Assessment
    ) -> Tuple[AdaptationKnowledgeBase, List[LearningSignal], GeneratorInfluence]:
        """Process learning from prediction + assessment (deterministic)."""
        return self._learning_engine.learn_from_assessment(prediction, assessment)

    def get_knowledge(self) -> AdaptationKnowledgeBase:
        return self._learning_engine.get_knowledge()

    def get_influence(self) -> GeneratorInfluence:
        return self._learning_engine.compute_generator_influence()