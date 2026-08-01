import importlib.util

import pytest

from dnc.cognition import RiskClass
from dnc.cognition import CognitiveActionType
from dnc.capabilities import CapabilityCard, CapabilityFeature, HealthStatus
from dnc.kernel.errors import DNCCapabilityError
from dnc.neural import (
    AdaptiveDepthModel,
    ExitCalibration,
    NeuralBenchmark,
    NeuralCheckpoint,
    NeuralExperimentDesign,
    adaptive_training_loss,
    benchmark_compute_fractions,
    issue_exit_evidence,
)
from dnc.system import DNCSystem


def _design():
    return NeuralExperimentDesign("tiny-mlp", "toy-classification", "dataset-sha256", 4, (2, 4), 7)


def _model(confidence=0.95, *, calibration_changes=None):
    calibrations = [
        ExitCalibration(2, "toy-classification", RiskClass.LOW, "model-v1", 0.9, 0.05, 0.02, 100),
        ExitCalibration(2, "toy-classification", RiskClass.HIGH, "model-v1", 0.99, 0.01, 0.01, 100),
    ]
    if calibration_changes:
        calibrations[0] = ExitCalibration(**{**calibrations[0].__dict__, **calibration_changes})
    return AdaptiveDepthModel(
        _design(), "model-v1",
        layers=(lambda value: value + 1,) * 4,
        exit_heads={2: lambda hidden: (hidden, confidence), 4: lambda hidden: (hidden, 1.0)},
        calibrations=tuple(calibrations),
    )


def test_experiment_design_locks_model_domain_data_depth_exits_and_seed() -> None:
    assert _design().full_depth == 4
    with pytest.raises(ValueError, match="terminate"):
        NeuralExperimentDesign("m", "d", "h", 4, (2, 3), 1)


def test_calibrated_easy_input_executes_actual_reduced_layer_count() -> None:
    result = _model().execute(0, domain="toy-classification", risk_class=RiskClass.LOW)
    assert result.output == 2
    assert result.exit_layer == result.layers_executed == 2
    assert result.layer_trace == (1, 2)
    assert result.compute_fraction == 0.5
    assert result.used_early_exit and result.calibrated


def test_hard_or_high_risk_input_runs_full_depth() -> None:
    hard = _model(0.5).execute(0, domain="toy-classification", risk_class=RiskClass.LOW)
    high_risk = _model().execute(0, domain="toy-classification", risk_class=RiskClass.HIGH)
    assert hard.output == high_risk.output == 4
    assert hard.layers_executed == high_risk.layers_executed == 4
    assert not hard.used_early_exit and not high_risk.used_early_exit


def test_shift_stale_model_and_insufficient_calibration_force_full_depth() -> None:
    shifted = _model(calibration_changes={"shifted": True})
    insufficient = _model(calibration_changes={"sample_count": 5})
    for model in (shifted, insufficient):
        result = model.execute(0, domain="toy-classification", risk_class=RiskClass.LOW)
        assert result.layers_executed == 4
        assert any("NO_APPLICABLE_CALIBRATION" in reason for reason in result.reason_codes)
    stale = _model()
    stale.model_fingerprint = "model-v2"
    assert stale.execute(0, domain="toy-classification", risk_class=RiskClass.LOW).layers_executed == 4


@pytest.mark.parametrize("confidence", (float("nan"), float("inf"), -0.1, 1.1))
def test_adversarial_invalid_exit_confidence_is_rejected(confidence) -> None:
    with pytest.raises(ValueError, match="finite"):
        _model(confidence).execute(0, domain="toy-classification", risk_class=RiskClass.LOW)


def test_batch_members_execute_independently_without_cross_item_routing_state() -> None:
    model = _model()
    results = [
        model.execute(value, domain="toy-classification", risk_class=RiskClass.LOW)
        for value in range(64)
    ]
    assert all(result.layers_executed == 2 for result in results)
    assert [result.output for result in results] == [value + 2 for value in range(64)]


def test_kill_switch_and_forced_fallback_are_independent_of_task_halting() -> None:
    model = _model()
    model.kill_switch = True
    killed = model.execute(0, domain="toy-classification", risk_class=RiskClass.LOW)
    assert killed.layers_executed == 4 and "FULL_DEPTH_KILL_SWITCH" in killed.reason_codes
    model.kill_switch = False
    forced = model.execute(
        0, domain="toy-classification", risk_class=RiskClass.LOW, force_full_depth=True
    )
    assert forced.layers_executed == 4 and "FULL_DEPTH_FORCED" in forced.reason_codes


def test_training_objective_combines_exit_teacher_and_compute_regularization() -> None:
    loss = adaptive_training_loss(
        (0.2, 0.1), (0.1, 0.0), (0.5, 1.0), teacher_weight=0.5, compute_weight=0.1
    )
    assert loss.total == pytest.approx(0.25)
    assert loss.exit_loss == pytest.approx(0.15)
    with pytest.raises(ValueError, match="aligned"):
        adaptive_training_loss((0.1,), (), (0.5,), teacher_weight=1, compute_weight=1)


def test_checkpoint_is_content_addressed_and_tracks_training_lineage() -> None:
    checkpoint = NeuralCheckpoint("ckpt-10", "tiny-mlp", "dataset-sha256", 7, "params", "optimizer", 10)
    assert checkpoint.fingerprint
    with pytest.raises(ValueError, match="fingerprint"):
        NeuralCheckpoint("ckpt-10", "tiny-mlp", "dataset-sha256", 7, "params", "optimizer", 10, "wrong")


def test_exit_decision_is_exported_as_capability_evidence() -> None:
    result = _model().execute(0, domain="toy-classification", risk_class=RiskClass.LOW)
    evidence = issue_exit_evidence(
        result, capability_id="neural-tiny", model_fingerprint="model-v1", task_id="task-1"
    )
    assert evidence.exit_layer == 2 and evidence.layers_executed == 2 and evidence.calibrated


def test_system_executes_adaptive_depth_only_through_active_model_matched_capability() -> None:
    system = DNCSystem()
    card = CapabilityCard(
        "neural-tiny", "Tiny adaptive model", "local", "1", "model-v1",
        frozenset({CognitiveActionType.REASON}), RiskClass.HIGH,
        features=frozenset({CapabilityFeature.LOCAL}),
        calibration_domains=frozenset({"toy-classification"}),
        health=HealthStatus.HEALTHY, metadata={"adaptive_neural": True},
    )
    system.capability_registry.register(card)
    result, evidence = system.execute_adaptive_neural(
        capability_id="neural-tiny", model=_model(), value=0, task_id="task-1",
        domain="toy-classification", risk_class=RiskClass.LOW,
    )
    assert result.layers_executed == 2 and evidence.capability_id == "neural-tiny"
    mismatched = AdaptiveDepthModel(
        _design(), "other-model", (lambda value: value + 1,) * 4,
        {2: lambda hidden: (hidden, 1.0), 4: lambda hidden: (hidden, 1.0)}, (),
    )
    with pytest.raises(DNCCapabilityError, match="model fingerprint"):
        system.execute_adaptive_neural(
            capability_id="neural-tiny", model=mismatched,
            value=0, task_id="task-1", domain="toy-classification", risk_class=RiskClass.LOW,
        )


def test_benchmark_reports_matched_quality_compute_latency_memory_energy_and_tails() -> None:
    average, p95 = benchmark_compute_fractions((0.5,) * 19 + (1.0,))
    benchmark = NeuralBenchmark(0.95, 0.96, 0.01, average, p95, 0.7, 0.9, 0.75, 0.04, 0.05)
    assert average < 1 and p95 == 1
    assert benchmark.passes(
        quality_tolerance=0.02, maximum_shifted_error=0.05, maximum_worst_group_error=0.05
    )


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="optional torch profile is not installed")
def test_pytorch_multi_exit_module_numerical_shape_qualification() -> None:
    import torch
    from dnc.neural.backends import build_pytorch_early_exit_module

    model = build_pytorch_early_exit_module(
        input_size=4, hidden_size=8, classes=2, depth=4, exit_layers=(2, 4)
    )
    outputs = model(torch.zeros((3, 4)))
    assert tuple(outputs) == ("2", "4")
    assert tuple(outputs["2"].shape) == (3, 2)
