"""Shadow/canary promotion and independent learned-policy rollback."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.cognition.contracts import RiskClass
from dnc.policy_learning.contracts import (
    LearnedPolicyVersion, PolicyLifecycle, PromotionEvidence,
)


@dataclass
class LearnedPolicyRegistry:
    _policies: dict[str, LearnedPolicyVersion] = field(default_factory=dict)
    _lifecycle: dict[str, PolicyLifecycle] = field(default_factory=dict)
    _evidence: dict[str, PromotionEvidence] = field(default_factory=dict)
    kill_switch: bool = False

    def register(self, policy: LearnedPolicyVersion) -> None:
        if policy.fingerprint in self._policies:
            raise ValueError("learned policy version already registered")
        self._policies[policy.fingerprint] = policy
        self._lifecycle[policy.fingerprint] = PolicyLifecycle.SHADOW

    def record_evidence(self, evidence: PromotionEvidence) -> None:
        if evidence.policy_fingerprint not in self._policies:
            raise KeyError("promotion evidence references unknown policy")
        self._evidence[evidence.policy_fingerprint] = evidence

    def promote_canary(self, fingerprint: str) -> None:
        evidence = self._require_evidence(fingerprint)
        estimate = evidence.estimate
        estimators = (estimate.ips, estimate.self_normalized_ips, estimate.doubly_robust)
        if (
            estimate.effective_sample_size < 10
            or estimate.supported_fraction < 0.8
            or max(estimators) - min(estimators) > 0.1
            or evidence.lower_confidence_bound <= evidence.baseline_value
            or evidence.calibration_error > 0.05
            or evidence.shadow_guardrail_regressions
        ):
            raise ValueError("learned policy promotion evidence is insufficient or discordant")
        self._lifecycle[fingerprint] = PolicyLifecycle.CANARY

    def promote_active(self, fingerprint: str) -> None:
        if self.kill_switch or self._lifecycle.get(fingerprint) is not PolicyLifecycle.CANARY:
            raise ValueError("only enabled canary policy can become active")
        for key, lifecycle in tuple(self._lifecycle.items()):
            if lifecycle is PolicyLifecycle.ACTIVE:
                self._lifecycle[key] = PolicyLifecycle.ROLLED_BACK
        self._lifecycle[fingerprint] = PolicyLifecycle.ACTIVE

    def can_execute(self, fingerprint: str, risk_class: RiskClass) -> bool:
        return (
            not self.kill_switch
            and risk_class is RiskClass.LOW
            and self._lifecycle.get(fingerprint) in {PolicyLifecycle.CANARY, PolicyLifecycle.ACTIVE}
        )

    def rollback(self, fingerprint: str) -> None:
        if fingerprint not in self._policies:
            raise KeyError("unknown learned policy")
        self._lifecycle[fingerprint] = PolicyLifecycle.ROLLED_BACK

    def lifecycle(self, fingerprint: str) -> PolicyLifecycle | None:
        return self._lifecycle.get(fingerprint)

    def snapshot(self):
        return (
            dict(self._policies), dict(self._lifecycle), dict(self._evidence), self.kill_switch
        )

    def restore(self, state) -> None:
        policies, lifecycle, evidence, kill_switch = state
        self._policies = dict(policies)
        self._lifecycle = dict(lifecycle)
        self._evidence = dict(evidence)
        self.kill_switch = bool(kill_switch)

    def _require_evidence(self, fingerprint: str) -> PromotionEvidence:
        if self._lifecycle.get(fingerprint) is not PolicyLifecycle.SHADOW:
            raise ValueError("policy must be in shadow before canary")
        evidence = self._evidence.get(fingerprint)
        if evidence is None:
            raise ValueError("promotion evidence is required")
        return evidence
