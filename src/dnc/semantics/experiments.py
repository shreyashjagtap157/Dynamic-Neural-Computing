"""Information-value experiment selection and falsification outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.cognition.canonical import normalize_text
from dnc.semantics.contracts import (
    ExperimentOutcome,
    ExperimentOutcomeStatus,
    ExperimentProposal,
)


_ISOLATION_ORDER = {
    "I0_NONE": 0,
    "I1_GRAPH_ONLY": 1,
    "I2_PROCESS_LOCAL": 2,
    "I3_RECORDED_EXTERNALS": 3,
    "I4_SANDBOXED_ENVIRONMENT": 4,
}


@dataclass(frozen=True)
class ExperimentSelection:
    selected: ExperimentProposal | None
    rejected: tuple[tuple[str, str], ...]
    alternatives: tuple[ExperimentProposal, ...]


def select_experiment(
    proposals: tuple[ExperimentProposal, ...],
    *,
    available_budget: float,
    available_isolation_grade: str,
) -> ExperimentSelection:
    feasible = []
    rejected = []
    for proposal in proposals:
        if proposal.cost > available_budget:
            rejected.append((proposal.experiment_id, "COST_BUDGET"))
        elif _ISOLATION_ORDER.get(available_isolation_grade, -1) < _ISOLATION_ORDER.get(proposal.required_isolation_grade, 99):
            rejected.append((proposal.experiment_id, "ISOLATION_GRADE"))
        elif not proposal.causal_validity.identifiable:
            rejected.append((proposal.experiment_id, "NON_IDENTIFIABLE"))
        else:
            feasible.append(proposal)
    ordered = sorted(
        feasible,
        key=lambda item: (
            -((item.expected_information_gain + item.expected_decision_value) / max(item.cost + item.risk, 1e-12)),
            item.experiment_id,
        ),
    )
    return ExperimentSelection(
        ordered[0] if ordered else None,
        tuple(rejected),
        tuple(ordered[1:]),
    )


def assess_observation(
    proposal: ExperimentProposal,
    observation: str,
    *,
    evidence_ref: str,
) -> ExperimentOutcome:
    normalized = normalize_text(observation)
    matched = next(
        (
            predicted for predicted in proposal.predicted_observations
            if normalize_text(predicted) == normalized
        ),
        None,
    )
    if not proposal.causal_validity.identifiable:
        status = ExperimentOutcomeStatus.NON_IDENTIFIABLE
    elif normalize_text(proposal.falsifier) == normalized:
        status = ExperimentOutcomeStatus.FALSIFIED
    elif matched is not None:
        status = ExperimentOutcomeStatus.SUPPORTED
    else:
        status = ExperimentOutcomeStatus.INCONCLUSIVE
    return ExperimentOutcome(
        proposal.experiment_id,
        proposal.hypothesis_id,
        observation,
        status,
        matched,
        proposal.causal_validity,
        evidence_ref,
    )
