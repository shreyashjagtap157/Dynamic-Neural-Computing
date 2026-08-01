"""Stable authorization inputs that exclude untrusted content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class StablePolicyInput:
    tenant_id: str
    subject: str
    action: str
    resource: str
    policy_version: str
    risk_class: str
    permissions: frozenset[str]


class ExternalPolicyAdapter(Protocol):
    version: str
    def evaluate(self, policy_input: StablePolicyInput) -> bool: ...


def build_policy_input(
    trusted: dict[str, Any], untrusted_content: Any = None
) -> StablePolicyInput:
    required = {"tenant_id", "subject", "action", "resource", "policy_version", "risk_class", "permissions"}
    if set(trusted) != required:
        raise ValueError("policy input MUST contain exactly the stable trusted fields")
    return StablePolicyInput(
        trusted["tenant_id"], trusted["subject"], trusted["action"], trusted["resource"],
        trusted["policy_version"], trusted["risk_class"], frozenset(trusted["permissions"]),
    )
