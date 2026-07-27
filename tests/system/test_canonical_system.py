"""Canonical-system and benchmark-ablation contract tests."""

from dnc import DNCSystem, DNCSystemConfig
from dnc.dcc.computation_generator import GenerationObjective
from dnc.evaluation.baselines.dnc_variants import DNCVariantSystem


def _objective() -> GenerationObjective:
    return GenerationObjective(task_description="canonical test", max_units=6, max_edges=8)


def test_mutation_ablation_never_changes_graph_or_transaction_count() -> None:
    system = DNCSystem(config=DNCSystemConfig(enable_mutation=False))
    initial_version = system.graph.version

    success, assessment, proposal = system.run_cycle(_objective())

    assert success and assessment is not None and proposal is not None
    assert system.graph.version == initial_version
    assert len(system.graph.units) == 0
    assert system.snapshot().transaction_commits == 0


def test_learning_ablation_never_updates_learning_knowledge() -> None:
    system = DNCSystem(config=DNCSystemConfig(enable_learning=False))
    success, first, _ = system.run_cycle(_objective())
    assert success and first is not None

    system.run_cycle(_objective(), first)

    assert system.snapshot().learning_cycles == 0
    assert system.learning.get_knowledge().cycle_count == 0


def test_provenance_ablation_has_no_sink() -> None:
    system = DNCSystem(config=DNCSystemConfig(enable_provenance=False))
    assert system.provenance_log is None
    assert system.transaction_manager.provenance_log is None


def test_variant_mutation_ablation_reports_and_performs_no_mutations() -> None:
    variant = DNCVariantSystem("DNC_M", enable_mutation=False)
    variant.initialize("test", 7, {})
    variant.execute({"description": "test", "complexity": 3})

    assert variant.system is not None
    assert variant.mutations_count == 0
    # Benchmark ablations start from the same pre-treatment base graph. The
    # mutation-disabled branch preserves it rather than starting from an empty
    # graph, which would confound paired counterfactual comparisons.
    assert len(variant.system.graph.units) == 1
    assert variant.system.snapshot().transaction_commits == 0
