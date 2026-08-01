from dataclasses import replace

import pytest

from dnc.cognition.canonical import canonical_hash
from dnc.evaluation.scientific import (
    REQUIRED_ABLATIONS,
    REQUIRED_BASELINES,
    FrozenCampaignManifest,
    HiddenCase,
    HiddenEvaluator,
    SystemResponse,
    WorkloadFamily,
    bootstrap_interval,
    runner_fingerprint,
    run_hidden_campaign,
)
from dnc.evaluation.reference_campaign import run_reference_campaign


def _cases():
    definitions = (
        ("easy", "math", WorkloadFamily.EASY, "easy", {"operation": "add", "values": [2, 3]}),
        ("hard", "code", WorkloadFamily.HARD, "hard", {"operation": "sort", "values": [3, 1, 2]}),
        ("ambiguous", "qa", WorkloadFamily.AMBIGUITY, "ambiguous", {"operation": "clarify"}),
        ("fault", "ops", WorkloadFamily.FAULT, "fault", {"operation": "recover", "timeout": True}),
        ("shift", "routing", WorkloadFamily.SHIFT, "shifted", {"operation": "route", "environment": "B"}),
        ("composition", "math", WorkloadFamily.COMPOSITION, "hard", {"operation": "compose", "values": [2, 3, 2]}),
        ("causal", "science", WorkloadFamily.CAUSAL, "causal", {"operation": "causal", "intervention": "X"}),
        ("horizon", "planning", WorkloadFamily.LONG_HORIZON, "long", {"operation": "horizon", "steps": 5}),
        ("delayed", "business", WorkloadFamily.DELAYED_OUTCOME, "delayed", {"operation": "delayed"}),
        ("adversarial", "security", WorkloadFamily.ADVERSARIAL, "adversarial", {"operation": "deny", "prompt": "ignore policy"}),
    )
    return tuple(
        HiddenCase(case_id, domain, family, subgroup, "HIGH", public, 5.0, family is WorkloadFamily.DELAYED_OUTCOME)
        for case_id, domain, family, subgroup, public in definitions
    )


def _answers():
    return {
        "easy": 5,
        "hard": [1, 2, 3],
        "ambiguous": "ASK",
        "fault": "RECOVER",
        "shift": "B",
        "composition": 12,
        "causal": "X_CAUSES_Y",
        "horizon": 5,
        "delayed": "SUCCESS",
        "adversarial": "DENY",
    }


def _solve(case):
    data = case.public_input
    operation = data["operation"]
    if operation == "add":
        return sum(data["values"])
    if operation == "sort":
        return sorted(data["values"])
    if operation == "compose":
        return data["values"][0] * data["values"][1] * data["values"][2]
    if operation == "route":
        return data["environment"]
    if operation == "horizon":
        return data["steps"]
    return {
        "clarify": "ASK", "recover": "RECOVER", "causal": "X_CAUSES_Y",
        "delayed": "SUCCESS", "deny": "DENY",
    }[operation]


def _systems():
    return (
        "dnc_full",
        *sorted(REQUIRED_BASELINES),
        *sorted(REQUIRED_ABLATIONS),
    )


def _manifest(cases=None):
    cases = cases or _cases()
    evaluator_fingerprint = HiddenEvaluator(_answers()).fingerprint
    runners = _runners()
    return FrozenCampaignManifest(
        "phase15-controlled-v1", "controller-v1", "calibrator-v1", evaluator_fingerprint,
        canonical_hash(cases, namespace="dnc.hidden-workload.v1"),
        _systems(),
        tuple((system_id, runner_fingerprint(runners[system_id])) for system_id in _systems()),
        tuple(sorted(REQUIRED_BASELINES)), tuple(sorted(REQUIRED_ABLATIONS)),
        (101, 202, 303),
        ("correctness", "risk_coverage", "cost", "tail_latency", "paired_effect"),
        "three preregistered repetitions", "exclude only malformed fixture records",
        "identical case budget",
    )


def _campaign(manifest=None, cases=None, evaluator=None, runners=None, **changes):
    manifest = manifest or _manifest(cases)
    arguments = {
        "runtime_fingerprints": {
            "controller": manifest.controller_fingerprint,
            "calibrator": manifest.calibrator_fingerprint,
        },
    }
    arguments.update(changes)
    return run_hidden_campaign(
        manifest,
        cases or _cases(),
        evaluator or HiddenEvaluator(_answers()),
        runners or _runners(),
        **arguments,
    )


def _runners():
    def runner(system_id):
        def execute(case, seed):
            solved = _solve(case)
            output = solved
            cost = 1.0
            if system_id == "single_pass_static" and case.family not in {
                WorkloadFamily.EASY, WorkloadFamily.HARD,
            }:
                output = "WRONG"
            if system_id == "no_repair" and case.family is WorkloadFamily.FAULT:
                output = "WRONG"
            if system_id == "no_memory" and case.family is WorkloadFamily.LONG_HORIZON:
                output = "WRONG"
            if system_id == "no_calibration" and case.family is WorkloadFamily.AMBIGUITY:
                output = "WRONG"
            if system_id == "no_verifier" and case.family is WorkloadFamily.ADVERSARIAL:
                output = "WRONG"
            if system_id == "no_branching" and case.family is WorkloadFamily.CAUSAL:
                output = "WRONG"
            if system_id == "no_learned_controller" and case.family is WorkloadFamily.SHIFT:
                output = "WRONG"
            if system_id == "no_adaptive_depth":
                cost = 4.0
            if system_id == "oracle_reference":
                cost = 4.0
            return SystemResponse(output, 0.9, cost, 2.0 + seed % 2)
        return execute
    return {system_id: runner(system_id) for system_id in _systems()}


def test_hidden_evaluator_is_not_exposed_to_runners_and_manifest_is_content_addressed() -> None:
    evaluator = HiddenEvaluator(_answers())
    assert not hasattr(evaluator, "answers")
    manifest = _manifest()
    assert manifest.frozen and manifest.fingerprint
    with pytest.raises(ValueError, match="fingerprint"):
        replace(manifest, fingerprint="tampered")


def test_manifest_requires_every_strong_baseline_and_ablation() -> None:
    manifest = _manifest()
    with pytest.raises(ValueError, match="strong baselines"):
        replace(
            manifest,
            baseline_ids=manifest.baseline_ids[1:],
            fingerprint="",
        )
    with pytest.raises(ValueError, match="required ablations"):
        replace(
            manifest,
            ablation_ids=manifest.ablation_ids[1:],
            fingerprint="",
        )


def test_campaign_rejects_post_freeze_evaluator_workload_or_system_changes() -> None:
    manifest = _manifest()
    with pytest.raises(ValueError, match="evaluator changed"):
        _campaign(manifest=manifest, evaluator=HiddenEvaluator({**_answers(), "easy": 6}))
    changed = _cases() + (
        HiddenCase("extra", "math", WorkloadFamily.EASY, "easy", "LOW", {"operation": "add", "values": [1]}, 5),
    )
    with pytest.raises(ValueError, match="workload changed"):
        _campaign(manifest=manifest, cases=changed)
    runners = _runners()
    runners.pop("dnc_full")
    with pytest.raises(ValueError, match="exactly match"):
        _campaign(manifest=manifest, runners=runners)
    with pytest.raises(ValueError, match="controller or calibrator"):
        _campaign(
            manifest=manifest,
            runtime_fingerprints={"controller": "retuned", "calibrator": "calibrator-v1"},
        )
    changed_implementations = _runners()
    changed_implementations["dnc_full"] = lambda case, seed: SystemResponse(
        "retuned", 1, 1, 1
    )
    with pytest.raises(ValueError, match="system implementation"):
        _campaign(manifest=manifest, runners=changed_implementations)


def test_repeated_multidomain_campaign_produces_e2_artifact_and_honest_ablation_results() -> None:
    artifact = _campaign()
    assert artifact.evidence_grade == "E2"
    assert artifact.verify_integrity()
    assert len(artifact.outcomes) == len(_systems()) * len(_cases()) * 3
    assert any(item.delayed for item in artifact.outcomes)
    assert not any(
        item.budget_violation
        for item in artifact.outcomes
        if item.system_id == "no_adaptive_depth"
    )
    effect = next(
        item for item in artifact.effects
        if item.system_id == "dnc_full" and item.baseline_id == "single_pass_static"
    )
    assert effect.mean_paired_effect > 0
    assert effect.pairs == 30
    assert "dnc_full" in artifact.pareto_systems
    assert artifact.subgroup_scores["no_repair"]["fault"] == 0
    assert artifact.risk_coverage["dnc_full"][-1] == (1.0, 0.0)


def test_budget_equivalence_changes_score_not_raw_hidden_answer() -> None:
    artifact = _campaign()
    manifest = _manifest()
    runners = _runners()

    def over_budget(case, seed):
        return SystemResponse(_solve(case), 0.9, case.budget + 1, 1)

    runners["dnc_full"] = over_budget
    changed_manifest = replace(
        manifest,
        system_fingerprints=tuple(
            (system_id, runner_fingerprint(runners[system_id]))
            for system_id in manifest.system_ids
        ),
        fingerprint="",
    )
    artifact = _campaign(manifest=changed_manifest, runners=runners)
    rows = [item for item in artifact.outcomes if item.system_id == "dnc_full"]
    assert all(item.budget_violation and not item.correct and item.score == 0 for item in rows)


def test_bootstrap_is_reproducible_and_rejects_weak_sampling() -> None:
    assert bootstrap_interval([1, 0, 1], seed=7) == bootstrap_interval([1, 0, 1], seed=7)
    with pytest.raises(ValueError, match="at least 100"):
        bootstrap_interval([1], seed=1, repetitions=10)


def test_maintained_reference_campaign_is_reproducible_and_integrity_checked() -> None:
    first = run_reference_campaign()
    second = run_reference_campaign()
    assert first == second
    assert first.evidence_grade == "E2" and first.verify_integrity()
