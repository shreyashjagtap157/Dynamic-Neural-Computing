"""Outcome and hidden-shift evaluation for semantic synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from dnc.cognition.canonical import normalize_text
from dnc.semantics.contracts import SemanticGraphCandidate


@dataclass(frozen=True)
class SemanticCandidateOutcome:
    candidate_id: str
    observed_evidence: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    matched_predictions: tuple[str, ...]
    unexpected_observations: tuple[str, ...]
    measured: bool


def assess_candidate_outcome(
    candidate: SemanticGraphCandidate,
    observed_evidence: tuple[str, ...],
    *,
    evidence_refs: tuple[str, ...],
) -> SemanticCandidateOutcome:
    predicted = {normalize_text(value): value for value in candidate.predicted_evidence}
    observed = {normalize_text(value): value for value in observed_evidence}
    matches = tuple(predicted[key] for key in sorted(predicted.keys() & observed.keys()))
    unexpected = tuple(observed[key] for key in sorted(observed.keys() - predicted.keys()))
    return SemanticCandidateOutcome(
        candidate.candidate_id,
        observed_evidence,
        evidence_refs,
        matches,
        unexpected,
        bool(observed_evidence and evidence_refs),
    )


@dataclass(frozen=True)
class SynthesisTrial:
    task_id: str
    policy: str
    inquiry_appropriate: bool
    semantic_justification: bool
    predicted_evidence: bool
    measured_outcome: bool
    cost: float


def compare_synthesis(
    semantic: tuple[SynthesisTrial, ...], heuristic: tuple[SynthesisTrial, ...]
) -> dict[str, float | bool]:
    semantic_ids = {trial.task_id for trial in semantic}
    heuristic_ids = {trial.task_id for trial in heuristic}
    if semantic_ids != heuristic_ids or len(semantic_ids) != len(semantic):
        raise ValueError("synthesis comparisons require unique paired tasks")
    return {
        "inquiry_accuracy_delta": mean(t.inquiry_appropriate for t in semantic)
        - mean(t.inquiry_appropriate for t in heuristic),
        "justification_rate": mean(t.semantic_justification for t in semantic),
        "prediction_rate": mean(t.predicted_evidence for t in semantic),
        "measured_outcome_rate": mean(t.measured_outcome for t in semantic),
        "cost_delta": mean(t.cost for t in semantic) - mean(t.cost for t in heuristic),
        "semantic_improved": (
            mean(t.inquiry_appropriate for t in semantic)
            > mean(t.inquiry_appropriate for t in heuristic)
            and all(t.semantic_justification and t.predicted_evidence for t in semantic)
        ),
    }
