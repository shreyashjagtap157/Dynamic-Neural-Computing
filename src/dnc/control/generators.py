"""Typed candidate generators for the semantic cognitive controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from dnc.cognition.contracts import CognitiveActionType, CognitiveProposal, EpistemicStatus
from dnc.cognition.state import CognitiveState
from dnc.control.contracts import ActionCandidate, CandidateSource, OutcomeVector


class CandidateGenerator(Protocol):
    def generate(self, state: CognitiveState) -> tuple[ActionCandidate, ...]: ...


@dataclass(frozen=True)
class RuleCandidateGenerator:
    def generate(self, state: CognitiveState) -> tuple[ActionCandidate, ...]:
        task_id, risk = state.task.task_id, state.task.policy.risk_class
        candidates: list[ActionCandidate] = []
        if state.unresolved_contradictions:
            candidates.append(_candidate(task_id, risk, CognitiveActionType.VERIFY, CandidateSource.RULE, information=0.8))
            candidates.append(_candidate(task_id, risk, CognitiveActionType.REPAIR, CandidateSource.RULE, quality=0.5))
        if state.missing_information:
            candidates.append(_candidate(task_id, risk, CognitiveActionType.RETRIEVE, CandidateSource.RULE, information=0.7))
            candidates.append(_candidate(task_id, risk, CognitiveActionType.ASK, CandidateSource.RULE, information=0.9))
        if state.hypotheses:
            candidates.append(_candidate(task_id, risk, CognitiveActionType.OBSERVE_OR_TEST, CandidateSource.HYPOTHESIS, information=0.9))
            candidates.append(_candidate(task_id, risk, CognitiveActionType.BRANCH, CandidateSource.HYPOTHESIS, information=0.5))
        if state.answer_state_id:
            candidates.append(_candidate(task_id, risk, CognitiveActionType.VERIFY, CandidateSource.VERIFIER, confidence=0.8))
            candidates.append(
                _candidate(
                    task_id,
                    risk,
                    CognitiveActionType.STOP,
                    CandidateSource.RULE,
                    quality=1.0,
                    cost=0.0,
                    safety=0.0,
                )
            )
        else:
            candidates.append(_candidate(task_id, risk, CognitiveActionType.REASON, CandidateSource.RULE, quality=0.6))
            candidates.append(_candidate(task_id, risk, CognitiveActionType.CONTINUE, CandidateSource.RULE, quality=0.4))
        if any(
            item.status in {EpistemicStatus.CAPABILITY_LIMIT, EpistemicStatus.UNVERIFIABLE}
            for item in state.epistemic_items
        ):
            candidates.extend((
                _candidate(task_id, risk, CognitiveActionType.ESCALATE, CandidateSource.RULE, safety=0.0),
                _candidate(task_id, risk, CognitiveActionType.ABSTAIN, CandidateSource.RULE, safety=0.0),
            ))
        return tuple(candidates)


@dataclass(frozen=True)
class CallbackCandidateGenerator:
    source: CandidateSource
    callback: Callable[[CognitiveState], tuple[ActionCandidate, ...]]

    def generate(self, state: CognitiveState) -> tuple[ActionCandidate, ...]:
        candidates = self.callback(state)
        if any(candidate.source is not self.source for candidate in candidates):
            raise ValueError("callback candidate source does not match generator declaration")
        return candidates


def _candidate(
    task_id,
    risk,
    action,
    source,
    *,
    quality=0.0,
    information=0.0,
    confidence=0.0,
    cost=0.1,
    safety=0.1,
):
    return ActionCandidate(
        CognitiveProposal(
            f"{task_id}:{source.value.casefold()}:{action.value.casefold()}",
            task_id,
            action,
            f"{source.value.casefold()} candidate for {action.value}",
            estimated_cost=cost,
            risk=risk,
        ),
        source,
        OutcomeVector(
            quality_gain=quality,
            information_gain=information,
            confidence_gain=confidence,
            monetary_cost=cost,
            safety_risk=safety,
        ),
    )
