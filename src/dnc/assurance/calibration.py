"""Calibration artifacts, metrics, fitting, intervals, and shift analysis."""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from statistics import mean
from typing import Iterable

from dnc.cognition.contracts import RiskClass
from dnc.kernel.errors import DNCCalibrationError


class CalibrationStatus(str, Enum):
    DRAFT = "DRAFT"
    CALIBRATED = "CALIBRATED"
    EXTRAPOLATED = "EXTRAPOLATED"
    SHIFTED = "SHIFTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALIDATED = "INVALIDATED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class CalibrationKey:
    domain: str
    risk_class: RiskClass
    capability_fingerprint: str
    prompt_fingerprint: str
    decoding_fingerprint: str
    verifier_fingerprints: tuple[str, ...]
    task_distribution: str

    def __post_init__(self) -> None:
        if not all((self.domain, self.capability_fingerprint, self.prompt_fingerprint, self.decoding_fingerprint, self.task_distribution)):
            raise ValueError("calibration applicability key MUST be complete")


@dataclass(frozen=True)
class CalibrationMetrics:
    count: int
    brier_score: float
    log_loss: float
    expected_calibration_error: float
    selective_risk: tuple[tuple[float, float], ...]
    reliability: tuple[tuple[float, float, int], ...]


@dataclass(frozen=True)
class CalibrationArtifact:
    artifact_id: str
    version: str
    key: CalibrationKey
    method: str
    parameters: tuple[float, ...]
    dataset_id: str
    split: str
    metrics: CalibrationMetrics
    status: CalibrationStatus = CalibrationStatus.DRAFT
    assumptions: tuple[str, ...] = ()
    subgroup_metrics: dict[str, CalibrationMetrics] = field(default_factory=dict)
    shift_score: float | None = None
    content_hash: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if not all((self.artifact_id, self.version, self.method, self.dataset_id, self.split)):
            raise ValueError("calibration artifact identity and provenance MUST be complete")
        expected = self.compute_hash()
        if self.content_hash and self.content_hash != expected:
            raise DNCCalibrationError("calibration artifact content hash mismatch")
        if self.status is CalibrationStatus.CALIBRATED and self.metrics.count < 2:
            raise DNCCalibrationError("calibrated artifacts require held-out outcome evidence")

    def compute_hash(self) -> str:
        payload = {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "key": {
                "domain": self.key.domain,
                "risk_class": self.key.risk_class.value,
                "capability_fingerprint": self.key.capability_fingerprint,
                "prompt_fingerprint": self.key.prompt_fingerprint,
                "decoding_fingerprint": self.key.decoding_fingerprint,
                "verifier_fingerprints": self.key.verifier_fingerprints,
                "task_distribution": self.key.task_distribution,
            },
            "method": self.method,
            "parameters": self.parameters,
            "dataset_id": self.dataset_id,
            "split": self.split,
            "metrics": self.metrics,
            "assumptions": self.assumptions,
        }
        return hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()


@dataclass
class AssuranceCalibrationRegistry:
    _artifacts: dict[str, CalibrationArtifact] = field(default_factory=dict)

    def register(self, artifact: CalibrationArtifact) -> CalibrationArtifact:
        if artifact.status is CalibrationStatus.CALIBRATED and artifact.split.casefold() not in {"held-out", "validation", "test"}:
            raise DNCCalibrationError("calibrated artifacts MUST use a held-out split")
        if not artifact.content_hash:
            artifact = replace(artifact, content_hash=artifact.compute_hash())
        existing = self._artifacts.get(artifact.artifact_id)
        if existing is not None and existing != artifact:
            raise DNCCalibrationError("calibration artifact ID cannot be replaced with different content")
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def applicable(self, key: CalibrationKey) -> CalibrationArtifact | None:
        matches = [
            artifact for artifact in self._artifacts.values()
            if artifact.key == key and artifact.status is CalibrationStatus.CALIBRATED
        ]
        return max(matches, key=lambda item: _version_key(item.version)) if matches else None

    def require_applicable(self, key: CalibrationKey) -> CalibrationArtifact:
        artifact = self.applicable(key)
        if artifact is None:
            raise DNCCalibrationError("no applicable calibrated artifact")
        return artifact

    def invalidate_fingerprint(self, fingerprint: str, reason: str) -> tuple[str, ...]:
        affected = []
        for artifact_id, artifact in tuple(self._artifacts.items()):
            if fingerprint in {artifact.key.capability_fingerprint, *artifact.key.verifier_fingerprints}:
                self._artifacts[artifact_id] = replace(artifact, status=CalibrationStatus.INVALIDATED, reason=reason)
                affected.append(artifact_id)
        return tuple(sorted(affected))

    def mark_shifted(self, artifact_id: str, score: float, reason: str) -> CalibrationArtifact:
        artifact = self._artifacts[artifact_id]
        shifted = replace(artifact, status=CalibrationStatus.SHIFTED, shift_score=score, reason=reason)
        self._artifacts[artifact_id] = shifted
        return shifted

    def assess_shift(
        self,
        artifact_id: str,
        reference: Iterable[float],
        observed: Iterable[float],
        *,
        threshold: float,
    ) -> CalibrationArtifact:
        if threshold < 0:
            raise ValueError("shift threshold MUST be non-negative")
        score = population_shift(reference, observed)
        artifact = self._artifacts[artifact_id]
        if score > threshold:
            return self.mark_shifted(artifact_id, score, "population shift threshold exceeded")
        updated = replace(artifact, shift_score=score)
        self._artifacts[artifact_id] = updated
        return updated

    def handle_model_change(self, event: object) -> None:
        previous = getattr(event, "previous_fingerprint", "")
        if previous:
            self.invalidate_fingerprint(previous, "provider/model fingerprint changed")


def evaluate_calibration(probabilities: Iterable[float], labels: Iterable[bool | int], *, bins: int = 10) -> CalibrationMetrics:
    pairs = [(float(p), int(y)) for p, y in zip(probabilities, labels, strict=True)]
    if not pairs:
        raise ValueError("calibration evaluation requires observations")
    if bins <= 0 or any(not 0 <= p <= 1 for p, _ in pairs):
        raise ValueError("probabilities and bins are invalid")
    eps = 1e-15
    brier = mean((p - y) ** 2 for p, y in pairs)
    loss = mean(-(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))) for p, y in pairs)
    reliability = []
    ece = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        bucket = [(p, y) for p, y in pairs if lower <= p < upper or (index == bins - 1 and p == 1)]
        if bucket:
            avg_p, avg_y = mean(p for p, _ in bucket), mean(y for _, y in bucket)
            reliability.append((avg_p, avg_y, len(bucket)))
            ece += len(bucket) / len(pairs) * abs(avg_p - avg_y)
    ranked = sorted(pairs, reverse=True)
    risk_curve = tuple((coverage / len(pairs), 1 - mean(y for _, y in ranked[:coverage])) for coverage in range(1, len(pairs) + 1))
    return CalibrationMetrics(len(pairs), brier, loss, ece, risk_curve, tuple(reliability))


def bootstrap_interval(values: Iterable[float], statistic=mean, *, confidence: float = 0.95, samples: int = 1000, seed: int = 0) -> tuple[float, float]:
    data = tuple(float(value) for value in values)
    if not data or samples <= 0 or not 0 < confidence < 1:
        raise ValueError("bootstrap configuration is invalid")
    rng = random.Random(seed)
    estimates = sorted(statistic(rng.choices(data, k=len(data))) for _ in range(samples))
    tail = (1 - confidence) / 2
    return estimates[int(tail * samples)], estimates[min(samples - 1, int((1 - tail) * samples))]


def subgroup_analysis(probabilities: Iterable[float], labels: Iterable[bool | int], groups: Iterable[str]) -> dict[str, CalibrationMetrics]:
    grouped: dict[str, list[tuple[float, bool | int]]] = {}
    for probability, label, group in zip(probabilities, labels, groups, strict=True):
        grouped.setdefault(group, []).append((probability, label))
    return {name: evaluate_calibration((p for p, _ in rows), (y for _, y in rows)) for name, rows in grouped.items()}


def population_shift(reference: Iterable[float], observed: Iterable[float], *, bins: int = 10) -> float:
    ref, obs = tuple(reference), tuple(observed)
    if not ref or not obs:
        raise ValueError("shift analysis requires both populations")
    eps = 1e-9
    score = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        rp = sum(low <= value < high or (index == bins - 1 and value == 1) for value in ref) / len(ref)
        op = sum(low <= value < high or (index == bins - 1 and value == 1) for value in obs) / len(obs)
        score += (op - rp) * math.log((op + eps) / (rp + eps))
    return score


def fit_logistic(scores: Iterable[float], labels: Iterable[bool | int], *, steps: int = 1000, learning_rate: float = 0.05) -> tuple[float, float]:
    rows = [(float(x), int(y)) for x, y in zip(scores, labels, strict=True)]
    if len(rows) < 2:
        raise ValueError("logistic calibration requires at least two observations")
    weight = bias = 0.0
    for _ in range(steps):
        gradients = [(1 / (1 + math.exp(-(weight * x + bias))) - y, x) for x, y in rows]
        bias -= learning_rate * mean(error for error, _ in gradients)
        weight -= learning_rate * mean(error * x for error, x in gradients)
    return weight, bias


def fit_temperature(logits: Iterable[float], labels: Iterable[bool | int]) -> float:
    rows = tuple(zip(logits, labels, strict=True))
    candidates = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)
    return min(candidates, key=lambda temp: evaluate_calibration((1 / (1 + math.exp(-float(x) / temp)) for x, _ in rows), (y for _, y in rows)).log_loss)


def fit_isotonic(scores: Iterable[float], labels: Iterable[bool | int]) -> tuple[tuple[float, float], ...]:
    blocks = [[float(x), float(y), 1] for x, y in sorted(zip(scores, labels, strict=True))]
    index = 0
    while index < len(blocks) - 1:
        if blocks[index][1] > blocks[index + 1][1]:
            left, right = blocks[index], blocks[index + 1]
            count = left[2] + right[2]
            blocks[index:index + 2] = [[right[0], (left[1] * left[2] + right[1] * right[2]) / count, count]]
            index = max(0, index - 1)
        else:
            index += 1
    return tuple((block[0], block[1]) for block in blocks)


def conformal_error_bound(errors: Iterable[float], *, alpha: float = 0.1) -> float:
    values = sorted(float(value) for value in errors)
    if not values or not 0 < alpha < 1:
        raise ValueError("conformal bound configuration is invalid")
    rank = min(len(values) - 1, math.ceil((len(values) + 1) * (1 - alpha)) - 1)
    return values[rank]


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in version.replace("-", ".").split(".")
    )
