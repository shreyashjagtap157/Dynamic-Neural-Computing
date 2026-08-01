"""Outcome-grounded hidden campaign for Phase 15 scientific evidence."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from dnc.cognition.canonical import canonical_hash


REQUIRED_BASELINES = frozenset(
    {
        "single_pass_static", "fixed_k_self_consistency", "fixed_refinement",
        "react_tool_loop", "fixed_planner_executor", "structural_dnc_kernel",
        "oracle_reference",
    }
)
REQUIRED_ABLATIONS = frozenset(
    {
        "no_calibration", "no_verifier", "no_memory", "no_repair",
        "no_branching", "no_learned_controller", "no_adaptive_depth",
    }
)


class WorkloadFamily(str, Enum):
    EASY = "EASY"
    HARD = "HARD"
    AMBIGUITY = "AMBIGUITY"
    FAULT = "FAULT"
    SHIFT = "SHIFT"
    COMPOSITION = "COMPOSITION"
    CAUSAL = "CAUSAL"
    LONG_HORIZON = "LONG_HORIZON"
    DELAYED_OUTCOME = "DELAYED_OUTCOME"
    ADVERSARIAL = "ADVERSARIAL"


@dataclass(frozen=True)
class HiddenCase:
    case_id: str
    domain: str
    family: WorkloadFamily
    subgroup: str
    risk_class: str
    public_input: dict[str, Any]
    budget: float
    delayed: bool = False


@dataclass(frozen=True)
class SystemResponse:
    output: Any
    confidence: float
    cost: float
    latency_ms: float
    abstained: bool = False
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or self.cost < 0 or self.latency_ms < 0:
            raise ValueError("response confidence, cost, and latency MUST be bounded")


@dataclass(frozen=True)
class FrozenCampaignManifest:
    campaign_id: str
    controller_fingerprint: str
    calibrator_fingerprint: str
    evaluator_fingerprint: str
    workload_fingerprint: str
    system_ids: tuple[str, ...]
    system_fingerprints: tuple[tuple[str, str], ...]
    baseline_ids: tuple[str, ...]
    ablation_ids: tuple[str, ...]
    seeds: tuple[int, ...]
    primary_metrics: tuple[str, ...]
    stopping_rule: str
    exclusion_rule: str
    budget_policy: str
    frozen: bool = True
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.frozen or not self.seeds or len(set(self.system_ids)) != len(self.system_ids):
            raise ValueError("campaign manifest MUST be frozen, repeated, and uniquely identified")
        if set(self.baseline_ids + self.ablation_ids) - set(self.system_ids):
            raise ValueError("baselines and ablations MUST be registered campaign systems")
        if (
            {system_id for system_id, _ in self.system_fingerprints} != set(self.system_ids)
            or any(not fingerprint for _, fingerprint in self.system_fingerprints)
        ):
            raise ValueError("every frozen system MUST have an exact implementation fingerprint")
        if not REQUIRED_BASELINES <= set(self.baseline_ids):
            raise ValueError("campaign is missing required strong baselines")
        if not REQUIRED_ABLATIONS <= set(self.ablation_ids):
            raise ValueError("campaign is missing required ablations")
        expected = canonical_hash(
            {key: value for key, value in self.__dict__.items() if key != "fingerprint"},
            namespace="dnc.scientific.manifest.v1",
        )
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("campaign manifest fingerprint mismatch")
        object.__setattr__(self, "fingerprint", expected)


@dataclass(frozen=True)
class CaseOutcome:
    system_id: str
    case_id: str
    seed: int
    domain: str
    family: WorkloadFamily
    subgroup: str
    risk_class: str
    correct: bool
    score: float
    confidence: float
    cost: float
    latency_ms: float
    abstained: bool
    budget_violation: bool
    delayed: bool


@dataclass(frozen=True)
class EffectEstimate:
    system_id: str
    baseline_id: str
    mean_paired_effect: float
    confidence_interval: tuple[float, float]
    pairs: int


@dataclass(frozen=True)
class CampaignArtifact:
    manifest_fingerprint: str
    outcomes: tuple[CaseOutcome, ...]
    effects: tuple[EffectEstimate, ...]
    risk_coverage: dict[str, tuple[tuple[float, float], ...]]
    pareto_systems: tuple[str, ...]
    subgroup_scores: dict[str, dict[str, float]]
    tail_latency_ms: dict[str, float]
    evidence_grade: str
    limitations: tuple[str, ...]
    fingerprint: str = ""

    def __post_init__(self) -> None:
        expected = canonical_hash(
            {key: value for key, value in self.__dict__.items() if key != "fingerprint"},
            namespace="dnc.scientific.artifact.v1",
        )
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("campaign artifact fingerprint mismatch")
        object.__setattr__(self, "fingerprint", expected)

    def verify_integrity(self) -> bool:
        current = canonical_hash(
            {key: value for key, value in self.__dict__.items() if key != "fingerprint"},
            namespace="dnc.scientific.artifact.v1",
        )
        return current == self.fingerprint


class HiddenEvaluator:
    """Evaluator boundary; runners receive cases but never answer records."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.__answers = dict(answers)
        self.fingerprint = canonical_hash(answers, namespace="dnc.hidden-evaluator.v1")

    def score(self, case_id: str, output: Any) -> tuple[bool, float]:
        expected = self.__answers[case_id]
        correct = output == expected
        return correct, 1.0 if correct else 0.0


Runner = Callable[[HiddenCase, int], SystemResponse]


def runner_fingerprint(runner: Runner) -> str:
    code = runner.__code__
    closure = tuple(
        repr(cell.cell_contents) for cell in (runner.__closure__ or ())
    )
    return canonical_hash(
        {
            "bytecode": code.co_code,
            "constants": tuple(repr(value) for value in code.co_consts),
            "names": code.co_names,
            "variables": code.co_varnames,
            "defaults": repr(runner.__defaults__),
            "closure": closure,
        },
        namespace="dnc.scientific.runner.v1",
    )


def run_hidden_campaign(
    manifest: FrozenCampaignManifest,
    cases: tuple[HiddenCase, ...],
    evaluator: HiddenEvaluator,
    runners: dict[str, Runner],
    *,
    runtime_fingerprints: dict[str, str],
) -> CampaignArtifact:
    if evaluator.fingerprint != manifest.evaluator_fingerprint:
        raise ValueError("evaluator changed after campaign freeze")
    if canonical_hash(cases, namespace="dnc.hidden-workload.v1") != manifest.workload_fingerprint:
        raise ValueError("hidden workload changed after campaign freeze")
    if set(runners) != set(manifest.system_ids):
        raise ValueError("campaign runners MUST exactly match frozen systems")
    expected_runtime = {
        "controller": manifest.controller_fingerprint,
        "calibrator": manifest.calibrator_fingerprint,
    }
    if runtime_fingerprints != expected_runtime:
        raise ValueError("controller or calibrator changed after campaign freeze")
    actual_runner_fingerprints = {
        system_id: runner_fingerprint(runner) for system_id, runner in runners.items()
    }
    if actual_runner_fingerprints != dict(manifest.system_fingerprints):
        raise ValueError("system implementation changed after campaign freeze")
    outcomes: list[CaseOutcome] = []
    for seed in manifest.seeds:
        for case in cases:
            for system_id in manifest.system_ids:
                response = runners[system_id](case, seed)
                budget_violation = response.cost > case.budget
                correct, score = evaluator.score(case.case_id, response.output)
                if budget_violation:
                    correct, score = False, 0.0
                outcomes.append(
                    CaseOutcome(
                        system_id, case.case_id, seed, case.domain, case.family,
                        case.subgroup, case.risk_class, correct, score,
                        response.confidence, response.cost, response.latency_ms,
                        response.abstained, budget_violation, case.delayed,
                    )
                )
    effects = tuple(
        paired_effect(outcomes, system_id, baseline_id)
        for baseline_id in manifest.baseline_ids
        for system_id in manifest.system_ids
        if system_id != baseline_id
    )
    domains = {case.domain for case in cases}
    families = {case.family for case in cases}
    grade = (
        "E2" if len(domains) >= 2 and len(manifest.seeds) >= 3
        and REQUIRED_ABLATIONS <= set(manifest.ablation_ids)
        and REQUIRED_BASELINES <= set(manifest.baseline_ids)
        and len(families) >= 5 else "E1"
    )
    return CampaignArtifact(
        manifest.fingerprint,
        tuple(outcomes),
        effects,
        {system_id: risk_coverage(outcomes, system_id) for system_id in manifest.system_ids},
        pareto_front(outcomes),
        subgroup_summary(outcomes),
        {
            system_id: percentile(
                [item.latency_ms for item in outcomes if item.system_id == system_id], 0.95
            )
            for system_id in manifest.system_ids
        },
        grade,
        (
            "controlled hidden-task evidence; no production traffic",
            "runner isolation is an interface boundary, not an OS security boundary",
            "independent environment reproduction not yet recorded",
        ),
    )


def paired_effect(
    outcomes: list[CaseOutcome] | tuple[CaseOutcome, ...],
    system_id: str,
    baseline_id: str,
) -> EffectEstimate:
    system = {(item.case_id, item.seed): item.score for item in outcomes if item.system_id == system_id}
    baseline = {(item.case_id, item.seed): item.score for item in outcomes if item.system_id == baseline_id}
    keys = sorted(set(system) & set(baseline))
    if not keys:
        raise ValueError("paired comparison has no matched outcomes")
    differences = [system[key] - baseline[key] for key in keys]
    return EffectEstimate(
        system_id,
        baseline_id,
        sum(differences) / len(differences),
        bootstrap_interval(differences, seed=17),
        len(keys),
    )


def bootstrap_interval(
    values: list[float], *, seed: int, repetitions: int = 1000
) -> tuple[float, float]:
    if not values or repetitions < 100:
        raise ValueError("bootstrap requires observations and at least 100 repetitions")
    rng = random.Random(seed)
    means = sorted(
        sum(rng.choice(values) for _ in values) / len(values)
        for _ in range(repetitions)
    )
    return percentile(means, 0.025), percentile(means, 0.975)


def risk_coverage(
    outcomes: list[CaseOutcome] | tuple[CaseOutcome, ...], system_id: str
) -> tuple[tuple[float, float], ...]:
    rows = sorted(
        (item for item in outcomes if item.system_id == system_id and not item.abstained),
        key=lambda item: (-item.confidence, item.case_id, item.seed),
    )
    total = sum(item.system_id == system_id for item in outcomes)
    if not rows or not total:
        return ()
    return tuple(
        (
            (index + 1) / total,
            1 - sum(item.correct for item in rows[: index + 1]) / (index + 1),
        )
        for index in range(len(rows))
    )


def pareto_front(outcomes: list[CaseOutcome] | tuple[CaseOutcome, ...]) -> tuple[str, ...]:
    systems = sorted({item.system_id for item in outcomes})
    metrics = {}
    for system_id in systems:
        rows = [item for item in outcomes if item.system_id == system_id]
        metrics[system_id] = (
            sum(item.score for item in rows) / len(rows),
            sum(item.cost for item in rows) / len(rows),
        )
    return tuple(
        system_id
        for system_id in systems
        if not any(
            other != system_id
            and metrics[other][0] >= metrics[system_id][0]
            and metrics[other][1] <= metrics[system_id][1]
            and metrics[other] != metrics[system_id]
            for other in systems
        )
    )


def subgroup_summary(
    outcomes: list[CaseOutcome] | tuple[CaseOutcome, ...]
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for system_id in sorted({item.system_id for item in outcomes}):
        result[system_id] = {}
        for subgroup in sorted({item.subgroup for item in outcomes}):
            rows = [
                item.score
                for item in outcomes
                if item.system_id == system_id and item.subgroup == subgroup
            ]
            if rows:
                result[system_id][subgroup] = sum(rows) / len(rows)
    return result


def percentile(values: list[float], quantile: float) -> float:
    if not values or not 0 <= quantile <= 1:
        raise ValueError("percentile inputs MUST be valid")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(quantile * (len(ordered) - 1)))]
