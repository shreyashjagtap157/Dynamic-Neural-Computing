"""Append-only immediate and delayed outcome-label ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OutcomeLabelStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    RETRACTED = "RETRACTED"


@dataclass(frozen=True)
class OutcomeLabel:
    label_id: str
    target_id: str
    value: bool | float | str
    observed_at_ns: int
    source: str
    tenant_id: str = "tenant-default"
    status: OutcomeLabelStatus = OutcomeLabelStatus.PROVISIONAL
    supersedes: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all((self.label_id, self.target_id, self.source, self.tenant_id)):
            raise ValueError("outcome label identity, source, and tenant MUST be non-empty")
        if self.observed_at_ns < 0:
            raise ValueError("observed_at_ns MUST be non-negative")


@dataclass
class OutcomeLabelStore:
    _labels: dict[str, OutcomeLabel] = field(default_factory=dict)
    _target_history: dict[tuple[str, str], list[str]] = field(default_factory=dict)

    def ingest(self, label: OutcomeLabel) -> None:
        existing = self._labels.get(label.label_id)
        if existing is not None:
            if existing != label:
                raise ValueError(f"conflicting outcome label id: {label.label_id}")
            return
        key = (label.tenant_id, label.target_id)
        if label.supersedes is not None:
            prior = self._labels.get(label.supersedes)
            if prior is None or (prior.tenant_id, prior.target_id) != key:
                raise ValueError("superseded label MUST exist for the same tenant and target")
            if label.status not in {OutcomeLabelStatus.CORRECTED, OutcomeLabelStatus.RETRACTED}:
                raise ValueError("superseding labels MUST be corrected or retracted")
            if label.observed_at_ns < prior.observed_at_ns:
                raise ValueError("delayed corrections MUST NOT precede the superseded observation")
        self._labels[label.label_id] = label
        self._target_history.setdefault(key, []).append(label.label_id)

    def history(self, target_id: str, *, tenant_id: str = "tenant-default") -> tuple[OutcomeLabel, ...]:
        return tuple(self._labels[label_id] for label_id in self._target_history.get((tenant_id, target_id), ()))

    def current(self, target_id: str, *, tenant_id: str = "tenant-default") -> OutcomeLabel | None:
        history = self.history(target_id, tenant_id=tenant_id)
        return history[-1] if history else None
