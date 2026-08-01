"""Canonical contracts for scoped verification and assurance."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from dnc.cognition.contracts import RiskClass


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"
    INAPPLICABLE = "INAPPLICABLE"
    ERROR = "ERROR"


class VerifierKind(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    EXTERNAL = "EXTERNAL"
    MODEL = "MODEL"
    HUMAN = "HUMAN"


@dataclass(frozen=True)
class VerifierClaim:
    claim_id: str
    target_id: str
    scope: str
    value: Any
    domain: str = "general"
    risk_class: RiskClass = RiskClass.MEDIUM
    tenant_id: str = "tenant-default"
    evidence: tuple[Any, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.claim_id or not self.target_id or not self.scope or not self.domain:
            raise ValueError("claim identity, target, scope, and domain MUST be non-empty")
        if not self.tenant_id:
            raise ValueError("tenant_id MUST be non-empty")


@dataclass(frozen=True)
class VerifierDescriptor:
    verifier_id: str
    version: str
    kind: VerifierKind
    scopes: frozenset[str]
    domains: frozenset[str] = frozenset({"general"})
    maximum_risk: RiskClass = RiskClass.MEDIUM
    cost: float = 0.0
    independence_group: str = "default"
    fingerprint: str = ""
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.verifier_id or not self.version or not self.scopes:
            raise ValueError("verifier identity, version, and scopes MUST be declared")
        if self.cost < 0:
            raise ValueError("verifier cost MUST be non-negative")

    def supports(self, claim: VerifierClaim) -> bool:
        return (
            claim.scope in self.scopes
            and (claim.domain in self.domains or "*" in self.domains)
            and _risk_order(claim.risk_class) <= _risk_order(self.maximum_risk)
        )


@dataclass(frozen=True)
class VerifierResult:
    result_id: str
    verifier_id: str
    verifier_version: str
    verifier_fingerprint: str
    claim_id: str
    target_id: str
    scope: str
    status: VerificationStatus
    independence_group: str
    tenant_id: str
    checks: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all((self.result_id, self.verifier_id, self.claim_id, self.target_id, self.scope)):
            raise ValueError("verification result identity and scope MUST be non-empty")


class Verifier(Protocol):
    @property
    def descriptor(self) -> VerifierDescriptor: ...

    def verify(self, claim: VerifierClaim) -> VerifierResult: ...


def _risk_order(value: RiskClass) -> int:
    return {RiskClass.LOW: 1, RiskClass.MEDIUM: 2, RiskClass.HIGH: 3, RiskClass.CRITICAL: 4}[value]
