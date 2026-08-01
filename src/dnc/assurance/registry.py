"""Verifier lifecycle registry and scoped cascade execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.assurance.contracts import (
    VerificationStatus,
    Verifier,
    VerifierClaim,
    VerifierResult,
)
from dnc.kernel.errors import DNCVerificationError


@dataclass
class VerifierRegistry:
    _verifiers: dict[str, Verifier] = field(default_factory=dict)
    _disabled: set[str] = field(default_factory=set)

    def register(self, verifier: Verifier) -> None:
        self._verifiers[verifier.descriptor.verifier_id] = verifier

    def disable(self, verifier_id: str) -> None:
        self._require(verifier_id)
        self._disabled.add(verifier_id)

    def enable(self, verifier_id: str) -> None:
        self._require(verifier_id)
        self._disabled.discard(verifier_id)

    def get(self, verifier_id: str) -> Verifier | None:
        return self._verifiers.get(verifier_id)

    def candidates(self, claim: VerifierClaim) -> tuple[Verifier, ...]:
        return tuple(
            verifier
            for verifier in sorted(
                self._verifiers.values(),
                key=lambda item: (item.descriptor.cost, item.descriptor.verifier_id),
            )
            if verifier.descriptor.verifier_id not in self._disabled
            and verifier.descriptor.supports(claim)
        )

    def _require(self, verifier_id: str) -> Verifier:
        verifier = self.get(verifier_id)
        if verifier is None:
            raise KeyError(f"unknown verifier: {verifier_id}")
        return verifier


@dataclass(frozen=True)
class CascadePolicy:
    required_passes: int = 1
    required_independence_groups: int = 1
    maximum_cost: float | None = None
    stop_on_failure: bool = True
    require_human_approval: bool = False

    def __post_init__(self) -> None:
        if self.required_passes <= 0 or self.required_independence_groups <= 0:
            raise ValueError("cascade pass and independence requirements MUST be positive")
        if self.maximum_cost is not None and self.maximum_cost < 0:
            raise ValueError("maximum_cost MUST be non-negative")


@dataclass(frozen=True)
class CascadeResult:
    claim: VerifierClaim
    results: tuple[VerifierResult, ...]
    satisfied: bool
    total_cost: float
    reason: str


@dataclass(frozen=True)
class VerifierCascade:
    registry: VerifierRegistry

    def run(self, claim: VerifierClaim, policy: CascadePolicy = CascadePolicy()) -> CascadeResult:
        results: list[VerifierResult] = []
        total_cost = 0.0
        candidates = self.registry.candidates(claim)
        if not candidates:
            raise DNCVerificationError("no applicable verifier for claim scope and risk")
        for verifier in candidates:
            descriptor = verifier.descriptor
            if policy.maximum_cost is not None and total_cost + descriptor.cost > policy.maximum_cost:
                continue
            result = verifier.verify(claim)
            if result.scope != claim.scope or result.claim_id != claim.claim_id:
                raise DNCVerificationError("verifier returned a result outside the requested scope")
            results.append(result)
            total_cost += descriptor.cost
            if result.status is VerificationStatus.FAIL and policy.stop_on_failure:
                return CascadeResult(claim, tuple(results), False, total_cost, "verification failed")
            passed = [item for item in results if item.status is VerificationStatus.PASS]
            groups = {item.independence_group for item in passed}
            human_passed = any(
                item.status is VerificationStatus.PASS
                and self.registry.get(item.verifier_id).descriptor.requires_human_approval
                for item in results
            )
            if (
                len(passed) >= policy.required_passes
                and len(groups) >= policy.required_independence_groups
                and (not policy.require_human_approval or human_passed)
            ):
                return CascadeResult(claim, tuple(results), True, total_cost, "requirements satisfied")
        return CascadeResult(claim, tuple(results), False, total_cost, "assurance requirements unmet")
