"""
Phase 7 Computation Generator Tests
Verifies proper ComputationGenerator architecture and proposal synthesis.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.dcc.computation_generator import ComputationGenerator, GenerationObjective, GenerationContext
from dnc.ir.operations import IROperation
from dnc.dcc.dcc_contracts import MutationProposal

def test_generator_initialization():
    """Generator initializes correctly."""
    gen = ComputationGenerator()
    assert gen._proposal_counter == 0
    print("PASS: test_generator_initialization")

def test_generation_objective():
    """GenerationObjective carries task description and constraints."""
    obj = GenerationObjective(
        task_description="Process sensor data",
        target_outcome="Structured output",
        constraints=["low_latency", "high_throughput"],
        cost_budget=50.0,
        max_units=5,
        max_edges=10
    )
    assert obj.task_description == "Process sensor data"
    assert obj.cost_budget == 50.0
    assert obj.max_units == 5
    print("PASS: test_generation_objective")

def test_generation_context():
    """GenerationContext aggregates objective and graph state."""
    graph = StructuralGraph(GraphID("test_g"))
    context = GenerationContext(
        objective=GenerationObjective(task_description="test"),
        graph_id=graph.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )
    assert context.current_unit_count == 0
    assert context.objective.task_description == "test"
    print("PASS: test_generation_context")

def test_generator_produces_proposals():
    """Generator.produce() returns list of MutationProposals."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    context = GenerationContext(
        objective=GenerationObjective(task_description="Add computation"),
        graph_id=graph.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    assert isinstance(proposals, list)
    assert all(isinstance(p, MutationProposal) for p in proposals)
    print(f"PASS: test_generator_produces_proposals (generated {len(proposals)} proposals)")

def test_generator_expansion_proposal():
    """Expansion proposal adds new unit within cost budget."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Expand computation",
            cost_budget=100.0,
            max_units=5
        ),
        graph_id=graph.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    expansion_proposals = [p for p in proposals if "expand" in p.rationale.lower()]
    assert len(expansion_proposals) >= 1
    proposal = expansion_proposals[0]
    assert proposal.expected_utility > 0
    assert proposal.estimated_cost > 0
    assert proposal.risk_assessment in ["LOW", "MEDIUM", "HIGH"]
    print(f"PASS: test_generator_expansion_proposal (utility={proposal.expected_utility}, cost={proposal.estimated_cost})")

def test_generator_wiring_proposal():
    """Wiring proposal connects units when graph has existing units."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("existing_1"),
        name="Existing1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("existing_2"),
        name="Existing2",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Wire computation",
            cost_budget=100.0,
            max_edges=10
        ),
        graph_id=graph.graph_id,
        current_unit_count=2,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    wiring_proposals = [p for p in proposals if "wire" in p.rationale.lower()]
    assert len(wiring_proposals) >= 1
    print(f"PASS: test_generator_wiring_proposal (proposals={len(wiring_proposals)})")

def test_generator_specialization_proposal():
    """Specialization proposal targets existing units when require_specialization=True."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("base_1"),
        name="BaseUnit1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Specialize for NLP",
            require_specialization=True,
            max_units=5
        ),
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    spec_proposals = [p for p in proposals if "specialize" in p.rationale.lower()]
    assert len(spec_proposals) >= 1
    print(f"PASS: test_generator_specialization_proposal (proposals={len(spec_proposals)})")

def test_generator_composition_proposal():
    """Composition proposal combines multiple units when graph has >= 2 units."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("comp_1"),
        name="Component1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("comp_2"),
        name="Component2",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Compose units",
            allow_composition=True,
            max_units=5
        ),
        graph_id=graph.graph_id,
        current_unit_count=2,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    comp_proposals = [p for p in proposals if "compose" in p.rationale.lower()]
    assert len(comp_proposals) >= 1
    print(f"PASS: test_generator_composition_proposal (proposals={len(comp_proposals)})")

def test_generator_respects_max_units():
    """Generator does not propose expansion when current_unit_count >= max_units."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("unit_1"),
        name="Unit1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Expand",
            max_units=1
        ),
        graph_id=graph.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    expansion_proposals = [p for p in proposals if "expand" in p.rationale.lower()]
    assert len(expansion_proposals) == 0
    print("PASS: test_generator_respects_max_units")

def test_generator_respects_max_edges():
    """Generator does not propose wiring when current_edge_count >= max_edges."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("unit_1"),
        name="Unit1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    graph.add_unit(ComputationalUnit(
        unit_id=UnitID("unit_2"),
        name="Unit2",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context = GenerationContext(
        objective=GenerationObjective(
            task_description="Wire",
            max_edges=0
        ),
        graph_id=graph.graph_id,
        current_unit_count=2,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    wiring_proposals = [p for p in proposals if "wire" in p.rationale.lower()]
    assert len(wiring_proposals) == 0
    print("PASS: test_generator_respects_max_edges")

def test_generator_proposal_has_operations():
    """MutationProposal contains valid IROperations."""
    gen = ComputationGenerator()
    graph = StructuralGraph(GraphID("test_g"))
    context = GenerationContext(
        objective=GenerationObjective(task_description="Test"),
        graph_id=graph.graph_id,
        current_unit_count=0,
        current_edge_count=0
    )
    proposals = gen.generate_proposals(graph, context)
    assert len(proposals) > 0
    for proposal in proposals:
        assert len(proposal.candidate_operations) > 0
        assert all(isinstance(op, IROperation) for op in proposal.candidate_operations)
    print(f"PASS: test_generator_proposal_has_operations")

def test_generator_deterministic():
    """Generator produces same proposals for same graph state."""
    gen = ComputationGenerator()
    graph1 = StructuralGraph(GraphID("test_g"))
    graph1.add_unit(ComputationalUnit(
        unit_id=UnitID("det_1"),
        name="Det1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    graph2 = StructuralGraph(GraphID("test_g"))
    graph2.add_unit(ComputationalUnit(
        unit_id=UnitID("det_1"),
        name="Det1",
        structure=StructureDimension.PRIMITIVE,
        visibility=VisibilityDimension.INSPECTABLE,
        lifecycle=LifecycleDimension.BASE
    ))
    context1 = GenerationContext(
        objective=GenerationObjective(task_description="Determinism test"),
        graph_id=graph1.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    context2 = GenerationContext(
        objective=GenerationObjective(task_description="Determinism test"),
        graph_id=graph2.graph_id,
        current_unit_count=1,
        current_edge_count=0
    )
    proposals1 = gen.generate_proposals(graph1, context1)
    gen2 = ComputationGenerator()
    proposals2 = gen2.generate_proposals(graph2, context2)
    assert len(proposals1) == len(proposals2)
    assert all(p1.rationale == p2.rationale for p1, p2 in zip(proposals1, proposals2))
    print(f"PASS: test_generator_deterministic")

def run_all_tests():
    tests = [
        test_generator_initialization,
        test_generation_objective,
        test_generation_context,
        test_generator_produces_proposals,
        test_generator_expansion_proposal,
        test_generator_wiring_proposal,
        test_generator_specialization_proposal,
        test_generator_composition_proposal,
        test_generator_respects_max_units,
        test_generator_respects_max_edges,
        test_generator_proposal_has_operations,
        test_generator_deterministic,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\nPhase 7 Computation Generator Tests: {passed}/{passed+failed} passed")
    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 7 COMPUTATION GENERATOR TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()