from __future__ import annotations

import pytest

from dnc.evaluation.counterfactual import EvidenceValueEstimator, features_from_tasks
from scripts.benchmarks.run_campaign import CampaignOrchestrator


def test_estimator_uses_observed_evidence_instead_of_campaign_constants() -> None:
    estimator = EvidenceValueEstimator()
    stable = features_from_tasks(
        "stable", [{"complexity": 5, "shift": False, "fault_injected": False}]
    )
    shifted = features_from_tasks(
        "shifted", [{"complexity": 5, "shift": True, "fault_injected": False}]
    )

    assert estimator.predict(stable).delta_v < 0
    assert estimator.predict(shifted).delta_v > estimator.predict(stable).delta_v


def test_campaign_uses_measured_paired_outcomes() -> None:
    campaign = CampaignOrchestrator(repetitions=1)
    report = campaign.run_campaign()

    assert len(campaign.telemetry_records) == len(campaign.workloads)
    for record in campaign.telemetry_records:
        summary = report["workload_summary"][record.workload_id]
        assert record.v_mutation == pytest.approx(summary["DNC_Full"]["Quality"])
        assert record.v_no_op == pytest.approx(summary["DNC_M"]["Quality"])
        assert record.realized_delta_v == pytest.approx(record.v_mutation - record.v_no_op)
        assert record.measurement_method == "paired_run_mutation_ablation"
        assert record.estimator_id == "evidence-value-v1"
        assert record.unit_count_before == 1


def test_campaign_oracle_labels_match_evaluator_requirements() -> None:
    campaign = CampaignOrchestrator(repetitions=1)
    campaign.run_campaign()
    labels = {record.workload_id: record.oracle_necessary for record in campaign.telemetry_records}

    assert not labels["W1_Static"]
    assert labels["W3_FailureRecovery"]
    assert labels["W4_ResourceConstraints"]
    assert labels["W5_DistributionShift"]
    assert labels["W7_Composition"]
    assert labels["W8_LongHorizon"]


def test_campaign_discloses_metric_and_causal_scope() -> None:
    report = CampaignOrchestrator(repetitions=1).run_campaign()
    methodology = report["methodology"]
    assert "metadata-label adherence" in methodology["adaptivity_metric_scope"]
    assert "not a per-candidate" in methodology["causal_scope"]
    assert "synthetic" in methodology["benchmark_scope"]
