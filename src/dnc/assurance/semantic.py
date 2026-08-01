"""Semantic agreement and contradiction analysis without hidden reasoning state."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from dnc.cognition.canonical import normalize_text
from dnc.cognition.contracts import EpistemicItem, EpistemicRelation, RelationType


@dataclass(frozen=True)
class SemanticAttempt:
    attempt_id: str
    conclusion: str
    atomic_claims: tuple[str, ...]
    correlation_group: str
    verifier_coverage: float = 0.0
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.attempt_id or not self.conclusion or not self.correlation_group:
            raise ValueError("semantic attempt identity, conclusion, and correlation group are required")
        if not 0 <= self.verifier_coverage <= 1 or self.weight <= 0:
            raise ValueError("coverage and weight are invalid")


@dataclass(frozen=True)
class SemanticCluster:
    cluster_id: str
    normalized_conclusion: str
    attempt_ids: tuple[str, ...]
    normalized_claims: tuple[str, ...]
    correlation_groups: tuple[str, ...]
    independent_weight: float
    verifier_coverage: float


def cluster_attempts(attempts: tuple[SemanticAttempt, ...], *, similarity_threshold: float = 0.88) -> tuple[SemanticCluster, ...]:
    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold MUST be between 0 and 1")
    groups: list[list[SemanticAttempt]] = []
    for attempt in attempts:
        normalized = normalize_text(attempt.conclusion)
        target = next(
            (
                group for group in groups
                if SequenceMatcher(None, normalize_text(group[0].conclusion), normalized).ratio()
                >= similarity_threshold
                and _claim_similarity(group[0].atomic_claims, attempt.atomic_claims) >= similarity_threshold
            ),
            None,
        )
        if target is None:
            groups.append([attempt])
        else:
            target.append(attempt)
    clusters = []
    for index, group in enumerate(groups):
        correlation_weights: dict[str, float] = {}
        for attempt in group:
            correlation_weights[attempt.correlation_group] = max(
                correlation_weights.get(attempt.correlation_group, 0.0), attempt.weight
            )
        clusters.append(
            SemanticCluster(
                cluster_id=f"cluster-{index + 1}",
                normalized_conclusion=normalize_text(group[0].conclusion),
                attempt_ids=tuple(item.attempt_id for item in group),
                normalized_claims=tuple(sorted({normalize_text(claim) for item in group for claim in item.atomic_claims})),
                correlation_groups=tuple(sorted(correlation_weights)),
                independent_weight=sum(correlation_weights.values()),
                verifier_coverage=sum(item.verifier_coverage * item.weight for item in group) / sum(item.weight for item in group),
            )
        )
    return tuple(sorted(clusters, key=lambda item: (-item.independent_weight, item.cluster_id)))


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    left_id: str
    right_id: str
    reason: str
    critical: bool


def detect_contradictions(
    items: tuple[EpistemicItem, ...],
    relations: tuple[EpistemicRelation, ...] = (),
) -> tuple[Contradiction, ...]:
    found: dict[tuple[str, str], Contradiction] = {}
    for relation in relations:
        if relation.relation_type is RelationType.CONTRADICTS:
            pair = tuple(sorted((relation.source_id, relation.target_id)))
            found[pair] = Contradiction(
                f"contradiction:{pair[0]}:{pair[1]}", pair[0], pair[1], "explicit relation", True
            )
    structured = [item for item in items if item.subject and item.predicate and item.object]
    for index, left in enumerate(structured):
        for right in structured[index + 1:]:
            if (
                normalize_text(left.subject or "") == normalize_text(right.subject or "")
                and normalize_text(left.predicate or "") == normalize_text(right.predicate or "")
                and normalize_text(left.object or "") != normalize_text(right.object or "")
                and left.scope == right.scope
            ):
                pair = tuple(sorted((left.item_id, right.item_id)))
                found[pair] = Contradiction(
                    f"contradiction:{pair[0]}:{pair[1]}", pair[0], pair[1], "conflicting structured objects", True
                )
    return tuple(found[key] for key in sorted(found))


def _claim_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    a, b = {normalize_text(value) for value in left}, {normalize_text(value) for value in right}
    return len(a & b) / len(a | b) if a or b else 1.0
