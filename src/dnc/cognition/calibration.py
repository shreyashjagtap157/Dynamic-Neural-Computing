"""Calibration policy records for cognitive halting decisions."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.cognition.contracts import RiskClass


@dataclass(frozen=True)
class CalibrationProfile:
    """Risk thresholds for a declared calibration domain and policy version."""

    profile_id: str
    domain: str
    policy_version: str
    risk_thresholds: dict[RiskClass, float]
    evidence_summary: str = ""
    capability_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id MUST be non-empty")
        if not self.domain:
            raise ValueError("domain MUST be non-empty")
        if not self.policy_version:
            raise ValueError("policy_version MUST be non-empty")
        missing = set(RiskClass) - set(self.risk_thresholds)
        if missing:
            raise ValueError("risk_thresholds MUST include every RiskClass")
        for threshold in self.risk_thresholds.values():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError("risk thresholds MUST be between 0 and 1")

    def threshold_for(self, risk_class: RiskClass) -> float:
        """Return the calibrated stop threshold for a risk class."""

        return self.risk_thresholds[risk_class]


@dataclass
class CalibrationRegistry:
    """In-memory registry of calibration profiles."""

    _profiles: dict[str, CalibrationProfile] = field(default_factory=dict)
    _invalidated: dict[str, str] = field(default_factory=dict)

    def register(self, profile: CalibrationProfile) -> None:
        """Register or replace a calibration profile by ID."""

        self._profiles[profile.profile_id] = profile

    def get(self, profile_id: str) -> CalibrationProfile | None:
        """Return a profile by ID if present."""

        if profile_id in self._invalidated:
            return None
        return self._profiles.get(profile_id)

    def invalidate_fingerprint(self, fingerprint: str, *, reason: str) -> tuple[str, ...]:
        invalidated = tuple(
            profile_id for profile_id, profile in self._profiles.items()
            if profile.capability_fingerprint == fingerprint
        )
        for profile_id in invalidated:
            self._invalidated[profile_id] = reason
        return invalidated

    def handle_model_change(self, event: object) -> None:
        previous = getattr(event, "previous_fingerprint", "")
        if previous:
            self.invalidate_fingerprint(previous, reason="provider/model fingerprint changed")

    def invalidation_reason(self, profile_id: str) -> str | None:
        return self._invalidated.get(profile_id)


def default_reference_calibration() -> CalibrationProfile:
    """Return conservative reference thresholds for deterministic tests.

    This profile is not empirical evidence. It exists so the reference
    controller depends on an explicit calibration object from the first slice.
    """

    return CalibrationProfile(
        profile_id="reference-v0",
        domain="deterministic-reference",
        policy_version="0",
        risk_thresholds={
            RiskClass.LOW: 0.10,
            RiskClass.MEDIUM: 0.05,
            RiskClass.HIGH: 0.01,
            RiskClass.CRITICAL: 0.001,
        },
        evidence_summary="Reference thresholds only; not held-out calibration evidence.",
    )
