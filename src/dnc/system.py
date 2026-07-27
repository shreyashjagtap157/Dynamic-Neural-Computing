"""Canonical top-level DNC system composition.

This module owns the supported end-to-end lifecycle. Tests, benchmarks, and
applications must import it instead of importing executable phase scripts.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional, Protocol

from dnc.dcc.assessment_engine import Assessment, AssessmentEngine, ExecutionResult
from dnc.dcc.computation_generator import (
    ComputationGenerator,
    GenerationContext,
    GenerationObjective,
    NecessitySignal,
)
from dnc.dcc.dcc_contracts import MutationProposal
from dnc.dcc.learning_engine import DeterministicLearningPolicy, PredictionTracker
from dnc.dcc.structural_controller import EvaluationContext, EvaluationCriteria, StructuralController
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID
from dnc.ir.validator import DNCIRValidator
from dnc.mutation.engine import MutationEngine
from dnc.observability.provenance import ProvenanceLog
from dnc.projection.projector import StructuralProjector
from dnc.transaction.manager import TransactionManager


class ExecutionCore(Protocol):
    """Backend contract consumed by the canonical DNC lifecycle."""

    def execute(self, executable_graph: object) -> ExecutionResult: ...


class ReferenceExecutionCore:
    """Deterministic in-process backend used until a real backend is injected."""

    def __init__(self, utility: float = 0.75) -> None:
        self.utility = utility
        self.execution_count = 0

    def execute(self, executable_graph: object) -> ExecutionResult:
        self.execution_count += 1
        dag = executable_graph[0] if isinstance(executable_graph, tuple) else executable_graph
        nodes = getattr(dag, "nodes", {})
        edges = getattr(dag, "edges", [])
        return ExecutionResult(
            graph_id=str(getattr(getattr(dag, "graph_id", None), "value", "dnc_system")),
            graph_version=str(getattr(dag, "source_version", "v1.0.0-0")),
            execution_time_ms=0.0,
            output=f"reference_result_{self.execution_count}",
            metrics={"utility": self.utility},
            units_executed=len(nodes),
            edges_traversed=len(edges),
            success=True,
        )


@dataclass(frozen=True)
class DNCSystemConfig:
    enable_learning: bool = True
    enable_mutation: bool = True
    enable_provenance: bool = True


@dataclass(frozen=True)
class SystemStateSnapshot:
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


class DNCSystem:
    """Canonical, configurable DNC control and execution lifecycle."""

    def __init__(
        self,
        execution_id: str = "dnc-execution",
        *,
        config: Optional[DNCSystemConfig] = None,
        execution_core: Optional[ExecutionCore] = None,
        initial_graph: Optional[StructuralGraph] = None,
    ) -> None:
        self.execution_id = execution_id
        self.config = config or DNCSystemConfig()
        self.graph = copy.deepcopy(initial_graph) if initial_graph is not None else StructuralGraph(
            GraphID(f"dnc:{execution_id}")
        )
        validation = DNCIRValidator().validate_graph(self.graph)
        if not validation.is_valid:
            errors = ", ".join(error.code for error in validation.errors)
            raise ValueError(f"initial graph violates DNC-IR invariants: {errors}")
        self.provenance_log = (
            ProvenanceLog(execution_id=execution_id) if self.config.enable_provenance else None
        )
        self.mutation_engine = MutationEngine()
        self.transaction_manager = TransactionManager(
            mutation_engine=self.mutation_engine,
            provenance_log=self.provenance_log,
        )
        self.projector = StructuralProjector()
        self.execution_core = execution_core or ReferenceExecutionCore()
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
        self._cycles_since_mutation = 999
        self._recent_mutation_count = 0
        self._prior_mutation_harmed = False
        self._last_observed_utility = 0.75

    def snapshot(self) -> SystemStateSnapshot:
        knowledge = self.learning.get_knowledge()
        return SystemStateSnapshot(
            cycle=self._cycle_count,
            graph_id=self.graph.graph_id.value,
            graph_version=str(self.graph.version),
            unit_count=len(self.graph.units),
            edge_count=len(self.graph.edges),
            proposals_generated=self._proposals_generated,
            proposals_authorized=self._proposals_authorized,
            learning_cycles=knowledge.cycle_count if self.config.enable_learning else 0,
            adaptation_knowledge_cycles=knowledge.cycle_count if self.config.enable_learning else 0,
            cumulative_improvement=(
                knowledge.cumulative_improvement if self.config.enable_learning else 0.0
            ),
            transaction_commits=self._transaction_commits,
            transaction_rollbacks=self._transaction_rollbacks,
        )

    def run_cycle(
        self,
        objective: GenerationObjective,
        prior_assessment: Optional[Assessment] = None,
        necessity_signals: frozenset[NecessitySignal] = frozenset(),
    ) -> tuple[bool, Optional[Assessment], Optional[MutationProposal]]:
        """Run GENERATE→AUTHORIZE→TRANSACT→EXECUTE→ASSESS→LEARN once."""
        self._cycle_count += 1
        graph_before_version = str(self.graph.version)
        last_utility = (
            prior_assessment.post_execution_utility_measured
            if prior_assessment is not None
            else self._last_observed_utility
        )
        proposals = self.generator.generate_proposals(
            self.graph,
            GenerationContext(
                objective=objective,
                graph_id=self.graph.graph_id,
                current_unit_count=len(self.graph.units),
                current_edge_count=len(self.graph.edges),
                last_observed_utility=last_utility,
                recent_mutation_count=self._recent_mutation_count,
                cycles_since_mutation=self._cycles_since_mutation,
                prior_mutation_harmed=self._prior_mutation_harmed,
                necessity_signals=necessity_signals,
            ),
        )
        self._proposals_generated += len(proposals)
        if not proposals:
            self._cycles_since_mutation += 1
            return False, None, None

        context = EvaluationContext(
            current_graph=self.graph,
            active_objectives=[objective.task_description],
            available_budget=objective.cost_budget,
            risk_tolerance="HIGH",
            criteria=EvaluationCriteria(
                min_utility=0.3,
                max_units=objective.max_units,
                max_edges=objective.max_edges,
            ),
            stability_baseline_utility=self._last_observed_utility,
            cycles_since_mutation=self._cycles_since_mutation,
            recent_mutation_count=self._recent_mutation_count,
        )
        evaluations = self.controller.evaluate_proposals(proposals, context)
        decision = self.controller.authorize_top_scoring(evaluations, context)
        if decision is None or not decision.authorized:
            self._cycles_since_mutation += 1
            return False, None, None

        self._proposals_authorized += 1
        proposal = next(
            (evaluation.proposal for evaluation in evaluations if evaluation.decision.value == "AUTHORIZE"),
            proposals[0],
        )
        prediction = self.tracker.record_prediction(proposal, decision)

        if self.config.enable_mutation:
            success, _ = self.transaction_manager.execute_transaction(
                self.graph, proposal.candidate_operations
            )
            if not success:
                self._transaction_rollbacks += 1
                self._cycles_since_mutation += 1
                return False, None, proposal
            self._transaction_commits += 1
            self._cycles_since_mutation = 0
            self._recent_mutation_count += 1
        else:
            # A true mutation ablation evaluates the existing graph without
            # changing graph structure, version, or transaction counters.
            self._cycles_since_mutation += 1

        execution = self.execution_core.execute(self.projector.project(self.graph))
        assessment = self.assessment_engine.assess_execution(
            execution,
            proposal,
            graph_before_version,
            str(self.graph.version),
            baseline_utility=last_utility,
        )
        if self.config.enable_learning and prior_assessment is not None:
            self.learning.process(prediction, assessment)

        self._prior_mutation_harmed = assessment.improvement_delta < -0.02
        self._last_observed_utility = assessment.post_execution_utility_measured
        return True, assessment, proposal


# One-release compatibility alias. New code should import DNCSystem.
DNCCanonicalSystem = DNCSystem
ConformantMockExecutionCore = ReferenceExecutionCore
