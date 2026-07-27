from __future__ import annotations

import pytest

from dnc.dcc.computation_generator import (
    ComputationGenerator,
    GenerationContext,
    GenerationObjective,
    NecessitySignal,
)
from dnc.dcc.assessment_engine import AssessmentEngine, ExecutionResult
from dnc.dcc.dcc_contracts import MutationProposal
from dnc.evaluation.baselines.dnc_variants import DNCVariantSystem
from dnc.evaluation.workloads.taxonomy import WorkloadTaxonomy
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)


def graph_with_units(count: int) -> StructuralGraph:
    graph = StructuralGraph(GraphID("necessity-test"))
    for index in range(count):
        unit = ComputationalUnit(
            unit_id=UnitID(f"u{index}"),
            name=f"unit-{index}",
            structure=StructureDimension.PRIMITIVE,
            visibility=VisibilityDimension.INSPECTABLE,
            lifecycle=LifecycleDimension.BASE,
        )
        graph.units[unit.unit_id.value] = unit
    return graph


def context(
    graph: StructuralGraph, *signals: NecessitySignal
) -> GenerationContext:
    return GenerationContext(
        objective=GenerationObjective(max_units=10, max_edges=20),
        graph_id=graph.graph_id,
        current_unit_count=len(graph.units),
        current_edge_count=len(graph.edges),
        necessity_signals=frozenset(signals),
    )


def test_stable_adequate_graph_generates_no_candidate() -> None:
    graph = graph_with_units(1)
    assert ComputationGenerator().generate_proposals(graph, context(graph)) == []


def test_each_operational_necessity_signal_can_trigger_a_candidate() -> None:
    triggers = (
        NecessitySignal.OBJECTIVE_VIOLATION,
        NecessitySignal.CONSTRAINT_VIOLATION,
        NecessitySignal.CAPACITY_INSUFFICIENCY,
        NecessitySignal.PERFORMANCE_DEGRADATION,
        NecessitySignal.FAULT_RECOVERY_REQUIREMENT,
        NecessitySignal.ENVIRONMENT_SHIFT,
    )
    for signal in triggers:
        graph = graph_with_units(1)
        proposals = ComputationGenerator().generate_proposals(graph, context(graph, signal))
        assert proposals, signal


def test_composition_signal_builds_required_capacity_then_composes() -> None:
    generator = ComputationGenerator()
    one = graph_with_units(1)
    assert generator.generate_proposals(
        one, context(one, NecessitySignal.COMPOSITION_REQUIREMENT)
    )

    two = graph_with_units(2)
    proposals = generator.generate_proposals(
        two, context(two, NecessitySignal.COMPOSITION_REQUIREMENT)
    )
    assert any("Compose" in proposal.rationale for proposal in proposals)


def test_stable_workload_counts_bootstrap_but_not_adaptation_or_recovery() -> None:
    system = DNCVariantSystem()
    system.initialize("W1_Static", 42, {})
    for task in WorkloadTaxonomy.get_workload("W1_Static").task_generator(42):
        system.execute(task)

    result = system.get_result()
    assert result.structural_mutations == 0
    assert result.recovery_events == 0
    assert result.metadata["bootstrap_mutations"] == 0
    assert result.metadata["stable_cycles"] == 5


def test_assessment_separates_improvement_from_prediction_error() -> None:
    proposal = MutationProposal(
        "proposal",
        "graph",
        [],
        "test",
        expected_utility=0.8,
        estimated_cost=0.0,
        risk_assessment="LOW",
    )
    result = ExecutionResult(
        graph_id="graph",
        graph_version="v1",
        metrics={"utility": 0.75},
        success=True,
    )
    assessment = AssessmentEngine().assess_execution(
        result, proposal, "v0", "v1", baseline_utility=0.75
    )

    assert assessment.improvement_delta == 0.0
    assert assessment.metadata["prediction_error"] == pytest.approx(-0.05)
