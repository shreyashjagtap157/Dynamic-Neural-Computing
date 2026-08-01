"""Maintained controlled Phase 15 campaign and reproducible fixture runners."""

from __future__ import annotations

from dnc.cognition.canonical import canonical_hash
from dnc.evaluation.scientific import (
    REQUIRED_ABLATIONS,
    REQUIRED_BASELINES,
    CampaignArtifact,
    FrozenCampaignManifest,
    HiddenCase,
    HiddenEvaluator,
    SystemResponse,
    WorkloadFamily,
    runner_fingerprint,
    run_hidden_campaign,
)


def reference_cases() -> tuple[HiddenCase, ...]:
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
        HiddenCase(
            case_id, domain, family, subgroup, "HIGH", public, 5.0,
            family is WorkloadFamily.DELAYED_OUTCOME,
        )
        for case_id, domain, family, subgroup, public in definitions
    )


def _answers() -> dict[str, object]:
    return {
        "easy": 5, "hard": [1, 2, 3], "ambiguous": "ASK", "fault": "RECOVER",
        "shift": "B", "composition": 12, "causal": "X_CAUSES_Y", "horizon": 5,
        "delayed": "SUCCESS", "adversarial": "DENY",
    }


def _systems() -> tuple[str, ...]:
    return ("dnc_full", *sorted(REQUIRED_BASELINES), *sorted(REQUIRED_ABLATIONS))


def reference_manifest() -> FrozenCampaignManifest:
    cases = reference_cases()
    evaluator = HiddenEvaluator(_answers())
    systems = _systems()
    runners = {system_id: _runner(system_id) for system_id in systems}
    return FrozenCampaignManifest(
        "phase15-controlled-v1",
        "controller-v1",
        "calibrator-v1",
        evaluator.fingerprint,
        canonical_hash(cases, namespace="dnc.hidden-workload.v1"),
        systems,
        tuple((system_id, runner_fingerprint(runners[system_id])) for system_id in systems),
        tuple(sorted(REQUIRED_BASELINES)),
        tuple(sorted(REQUIRED_ABLATIONS)),
        (101, 202, 303),
        ("correctness", "risk_coverage", "cost", "tail_latency", "paired_effect"),
        "three preregistered repetitions",
        "exclude only malformed fixture records",
        "identical case budget",
    )


def _solve(case: HiddenCase) -> object:
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


def _runner(system_id: str):
    def execute(case: HiddenCase, seed: int) -> SystemResponse:
        output = _solve(case)
        cost = 1.0
        failures = {
            "no_repair": WorkloadFamily.FAULT,
            "no_memory": WorkloadFamily.LONG_HORIZON,
            "no_calibration": WorkloadFamily.AMBIGUITY,
            "no_verifier": WorkloadFamily.ADVERSARIAL,
            "no_branching": WorkloadFamily.CAUSAL,
            "no_learned_controller": WorkloadFamily.SHIFT,
        }
        if system_id == "single_pass_static" and case.family not in {
            WorkloadFamily.EASY, WorkloadFamily.HARD,
        }:
            output = "WRONG"
        if failures.get(system_id) is case.family:
            output = "WRONG"
        if system_id == "no_adaptive_depth":
            cost = 4.0
        if system_id == "oracle_reference":
            cost = 4.0
        return SystemResponse(output, 0.9, cost, 2.0 + seed % 2)

    return execute


def run_reference_campaign() -> CampaignArtifact:
    manifest = reference_manifest()
    runners = {system_id: _runner(system_id) for system_id in manifest.system_ids}
    return run_hidden_campaign(
        manifest,
        reference_cases(),
        HiddenEvaluator(_answers()),
        runners,
        runtime_fingerprints={
            "controller": manifest.controller_fingerprint,
            "calibrator": manifest.calibrator_fingerprint,
        },
    )
