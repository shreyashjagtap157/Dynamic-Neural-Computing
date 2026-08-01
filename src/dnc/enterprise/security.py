"""Workload identity, authorization, quotas, approvals, and kill switches."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkloadIdentity:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    attributes: dict[str, str]
    issued_at_ns: int
    expires_at_ns: int
    credential_ref: str

    def __post_init__(self) -> None:
        if not all((self.subject, self.tenant_id, self.credential_ref)):
            raise ValueError("workload identity fields MUST be non-empty")
        if self.expires_at_ns <= self.issued_at_ns:
            raise ValueError("workload identity expiry MUST follow issuance")

    def valid_at(self, now_ns: int) -> bool:
        return self.issued_at_ns <= now_ns < self.expires_at_ns


@dataclass(frozen=True)
class AuthorizationRequest:
    tenant_id: str
    action: str
    resource: str
    required_roles: frozenset[str] = frozenset()
    required_attributes: dict[str, str] = field(default_factory=dict)
    high_impact: bool = False


@dataclass(frozen=True)
class Approval:
    approval_id: str
    tenant_id: str
    action: str
    resource: str
    approver_subject: str
    expires_at_ns: int
    approver_roles: frozenset[str] = frozenset()


@dataclass
class TenantQuota:
    maximum_cost: float
    maximum_actions: int
    used_cost: float = 0
    used_actions: int = 0

    def consume(self, cost: float) -> None:
        if cost < 0 or self.used_cost + cost > self.maximum_cost or self.used_actions + 1 > self.maximum_actions:
            raise PermissionError("tenant quota exceeded")
        self.used_cost += cost
        self.used_actions += 1


class EnterpriseAuthorizer:
    def authorize(
        self,
        identity: WorkloadIdentity,
        request: AuthorizationRequest,
        *,
        now_ns: int,
        approval: Approval | None = None,
    ) -> tuple[bool, tuple[str, ...]]:
        reasons = []
        if not identity.valid_at(now_ns):
            reasons.append("IDENTITY_EXPIRED")
        if identity.tenant_id != request.tenant_id:
            reasons.append("TENANT_MISMATCH")
        if not request.required_roles <= identity.roles:
            reasons.append("ROLE_MISSING")
        if any(identity.attributes.get(key) != value for key, value in request.required_attributes.items()):
            reasons.append("ATTRIBUTE_MISMATCH")
        if request.high_impact and not (
            approval
            and approval.tenant_id == request.tenant_id
            and approval.action == request.action
            and approval.resource == request.resource
            and approval.approver_subject != identity.subject
            and "approver" in approval.approver_roles
            and now_ns < approval.expires_at_ns
        ):
            reasons.append("INDEPENDENT_APPROVAL_REQUIRED")
        return not reasons, tuple(reasons)


@dataclass
class KillSwitches:
    global_disabled: bool = False
    tenants: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)
    models: set[str] = field(default_factory=set)
    skills: set[str] = field(default_factory=set)
    actions: set[str] = field(default_factory=set)

    def permitted(
        self,
        *,
        tenant_id: str,
        capability_id: str = "",
        model_id: str = "",
        skill_id: str = "",
        action_type: str = "",
    ) -> bool:
        return not (
            self.global_disabled or tenant_id in self.tenants
            or capability_id in self.capabilities or model_id in self.models
            or skill_id in self.skills or action_type in self.actions
        )

    def snapshot(self):
        return (
            self.global_disabled, set(self.tenants), set(self.capabilities),
            set(self.models), set(self.skills), set(self.actions),
        )

    def restore(self, state) -> None:
        global_disabled, tenants, capabilities, models, skills, actions = state
        self.global_disabled = bool(global_disabled)
        self.tenants = set(tenants)
        self.capabilities = set(capabilities)
        self.models = set(models)
        self.skills = set(skills)
        self.actions = set(actions)
