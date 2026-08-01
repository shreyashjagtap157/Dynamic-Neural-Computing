"""Governed risk thresholds and calibration applicability decisions."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.assurance.calibration import CalibrationArtifact, CalibrationStatus
from dnc.cognition.contracts import ConfidenceEstimate, RiskClass
from dnc.kernel.errors import DNCCalibrationError, DNCPolicyError


@dataclass(frozen=True)
class RiskThresholdPolicy:
    policy_id: str
    version: str
    domain: str
    thresholds: dict[RiskClass, float]
    approved_by: str
    human_approval_ref: str
    deterministic_evidence_fallback: bool = False

    def __post_init__(self) -> None:
        if not all((self.policy_id, self.version, self.domain, self.approved_by, self.human_approval_ref)):
            raise DNCPolicyError("risk threshold policy requires human approval provenance")
        if set(self.thresholds) != set(RiskClass):
            raise DNCPolicyError("risk threshold policy MUST cover every risk class")
        if any(not 0 <= threshold <= 1 for threshold in self.thresholds.values()):
            raise DNCPolicyError("risk thresholds MUST be between 0 and 1")
        ordered = [self.thresholds[risk] for risk in RiskClass]
        if ordered != sorted(ordered):
            raise DNCPolicyError("risk thresholds MUST be non-decreasing with risk class")

    def threshold_for(self, risk_class: RiskClass, domain: str) -> float:
        if domain != self.domain and self.domain != "*":
            raise DNCPolicyError("risk policy is inapplicable to domain")
        return self.thresholds[risk_class]


@dataclass
class RiskPolicyRegistry:
    _policies: dict[tuple[str, str], RiskThresholdPolicy] = field(default_factory=dict)

    def register(self, policy: RiskThresholdPolicy) -> None:
        self._policies[(policy.domain, policy.version)] = policy

    def latest(self, domain: str) -> RiskThresholdPolicy | None:
        candidates = [policy for (policy_domain, _), policy in self._policies.items() if policy_domain in {domain, "*"}]
        return max(candidates, key=lambda item: _version_key(item.version)) if candidates else None


def calibrated_lower_bound(artifact: CalibrationArtifact, probability: float, *, z_score: float = 1.96) -> float:
    if artifact.status is not CalibrationStatus.CALIBRATED:
        raise DNCCalibrationError("confidence cannot be issued from an inapplicable artifact")
    if not 0 <= probability <= 1:
        raise ValueError("probability MUST be between 0 and 1")
    count = artifact.metrics.count
    standard_error = (probability * (1 - probability) / count) ** 0.5
    return max(0.0, probability - z_score * standard_error)


def issue_confidence(
    estimate_id: str,
    target_id: str,
    target_type: str,
    probability: float,
    artifact: CalibrationArtifact,
    *,
    semantic_cluster_count: int = 0,
    correlation_groups: tuple[str, ...] = (),
) -> ConfidenceEstimate:
    """Issue canonical confidence only from an applicable held-out artifact."""

    lower = calibrated_lower_bound(artifact, probability)
    return ConfidenceEstimate(
        estimate_id=estimate_id,
        target_id=target_id,
        target_type=target_type,
        p_correct=probability,
        failure_probability=1 - probability,
        lower_bound=lower,
        upper_bound=min(1.0, probability + (probability - lower)),
        method=artifact.method,
        calibration_model=artifact.artifact_id,
        calibration_dataset=artifact.dataset_id,
        calibration_split=artifact.split,
        calibration_version=artifact.version,
        domain=artifact.key.domain,
        risk_class=artifact.key.risk_class,
        capability_fingerprint=artifact.key.capability_fingerprint,
        prompt_fingerprint=artifact.key.prompt_fingerprint,
        verifier_fingerprints=artifact.key.verifier_fingerprints,
        sample_count=artifact.metrics.count,
        semantic_cluster_count=semantic_cluster_count,
        correlation_groups=correlation_groups,
        held_out_metrics={
            "brier_score": artifact.metrics.brier_score,
            "log_loss": artifact.metrics.log_loss,
            "expected_calibration_error": artifact.metrics.expected_calibration_error,
        },
        applicability_status="calibrated",
    )


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in version.replace("-", ".").split(".")
    )
