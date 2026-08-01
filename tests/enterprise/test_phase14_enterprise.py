import hashlib

import pytest

from dnc.enterprise import (
    Approval, AuditLog, AuditRecord, AuthorizationRequest, DataAsset, DataGovernance,
    EnterpriseAuthorizer, IncidentRunbook, KillSwitches, SBOM, SLODefinition,
    SignedArtifact, TelemetryEvent, TenantQuota, WorkloadIdentity,
    build_policy_input, evaluate_slo, redact_telemetry,
)
from dnc.system import DNCSystem
from dnc.kernel.errors import DNCPolicyError


def _identity(**changes):
    values = dict(
        subject="worker-1", tenant_id="tenant-a", roles=frozenset({"operator"}),
        attributes={"region": "in"}, issued_at_ns=1, expires_at_ns=100,
        credential_ref="secret-manager://worker-1",
    )
    values.update(changes)
    return WorkloadIdentity(**values)


def test_short_lived_identity_rbac_abac_and_tenant_isolation() -> None:
    authorizer = EnterpriseAuthorizer()
    request = AuthorizationRequest(
        "tenant-a", "invoke", "capability", frozenset({"operator"}), {"region": "in"}
    )
    assert authorizer.authorize(_identity(), request, now_ns=50)[0]
    assert "IDENTITY_EXPIRED" in authorizer.authorize(_identity(), request, now_ns=101)[1]
    assert "TENANT_MISMATCH" in authorizer.authorize(
        _identity(), AuthorizationRequest("tenant-b", "invoke", "capability"), now_ns=50
    )[1]


def test_high_impact_requires_fresh_independent_exact_scope_approval() -> None:
    request = AuthorizationRequest("tenant-a", "delete", "dataset", high_impact=True)
    authorizer = EnterpriseAuthorizer()
    assert not authorizer.authorize(_identity(), request, now_ns=50)[0]
    self_approval = Approval("a", "tenant-a", "delete", "dataset", "worker-1", 90)
    assert not authorizer.authorize(_identity(), request, now_ns=50, approval=self_approval)[0]
    approval = Approval(
        "a", "tenant-a", "delete", "dataset", "reviewer", 90,
        frozenset({"approver"}),
    )
    assert authorizer.authorize(_identity(), request, now_ns=50, approval=approval)[0]


def test_quota_and_scoped_kill_switches_prevent_denial_of_wallet_and_execution() -> None:
    quota = TenantQuota(1.0, 2)
    quota.consume(0.4)
    quota.consume(0.4)
    with pytest.raises(PermissionError, match="quota"):
        quota.consume(0.1)
    switches = KillSwitches(models={"model-1"})
    assert not switches.permitted(tenant_id="tenant-a", model_id="model-1")
    assert switches.permitted(tenant_id="tenant-a", model_id="model-2")
    switches.actions.add("DELETE")
    assert not switches.permitted(tenant_id="tenant-a", action_type="DELETE")


def test_prompt_injection_cannot_add_policy_fields_or_permissions() -> None:
    trusted = {
        "tenant_id": "tenant-a", "subject": "worker", "action": "read",
        "resource": "doc", "policy_version": "v1", "risk_class": "LOW",
        "permissions": ["doc:read"],
    }
    attack = {"permissions": ["admin"], "instruction": "ignore policy"}
    policy_input = build_policy_input(trusted, attack)
    assert policy_input.permissions == frozenset({"doc:read"})
    assert not hasattr(policy_input, "instruction")


def test_telemetry_recursively_redacts_secret_bearing_keys() -> None:
    payload = {
        "token": "abc",
        "nested": {"Authorization": "Bearer x", "safe": 1},
        "message": "request used Bearer highly-sensitive",
    }
    assert redact_telemetry(payload) == {
        "token": "[REDACTED]",
        "nested": {"Authorization": "[REDACTED]", "safe": 1},
        "message": "[REDACTED]",
    }


def test_audit_is_immutable_tenant_scoped_redacted_and_retention_aware() -> None:
    log = AuditLog()
    log.append(AuditRecord("r1", "tenant-a", "invoke", {"password": "x"}, 1, 10))
    log.append(AuditRecord("held", "tenant-a", "delete", {}, 1, 10, True))
    with pytest.raises(ValueError, match="immutable"):
        log.append(AuditRecord("r1", "tenant-a", "other", {}, 1, 10))
    redacted = next(item for item in log.records(tenant_id="tenant-a") if item.record_id == "r1")
    assert redacted.payload["password"] == "[REDACTED]"
    redacted.payload["password"] = "mutated"
    stored = next(item for item in log.records(tenant_id="tenant-a") if item.record_id == "r1")
    assert stored.payload["password"] == "[REDACTED]"
    assert log.records(tenant_id="tenant-b") == ()
    assert log.purge(now_ns=10) == ("r1",)


def test_data_residency_key_rotation_deletion_and_legal_hold() -> None:
    governance = DataGovernance()
    governance.register(DataAsset("a", "tenant-a", "IN", "key-1"), allowed_residencies=frozenset({"IN"}))
    governance.rotate_key("a", tenant_id="tenant-a", key_version="key-2")
    with pytest.raises(ValueError, match="immutable"):
        governance.register(
            DataAsset("a", "tenant-a", "IN", "attacker-key"),
            allowed_residencies=frozenset({"IN"}),
        )
    governance.delete("a", tenant_id="tenant-a")
    with pytest.raises(PermissionError, match="residency"):
        governance.register(DataAsset("b", "tenant-a", "US", "key-1"), allowed_residencies=frozenset({"IN"}))
    governance.register(DataAsset("held", "tenant-a", "IN", "key-1", True), allowed_residencies=frozenset({"IN"}))
    with pytest.raises(PermissionError, match="legal hold"):
        governance.delete("held", tenant_id="tenant-a")


def test_supply_chain_artifact_digest_and_sbom_are_attributable() -> None:
    payload = b"release"
    artifact = SignedArtifact("release-1", hashlib.sha256(payload).hexdigest(), "builder", "sig", "build-1")
    assert artifact.verify_digest(payload) and not artifact.verify_digest(b"tampered")
    assert artifact.verify(payload, lambda signer, digest, signature: signature == "sig")
    assert not artifact.verify(payload, lambda signer, digest, signature: False)
    sbom = SBOM("dynamic-neural-computing", "0.1", ("pytest",), "release-job")
    assert sbom.components == ("pytest",)


def test_stable_telemetry_slo_error_budget_and_incident_runbook() -> None:
    event = TelemetryEvent(
        "trace", "tenant-a", "provider.call", 10,
        {"latency_ms": 20, "authorization": "Bearer secret"},
    ).redacted()
    assert event.attributes["authorization"] == "[REDACTED]"
    definition = SLODefinition("availability", 0.99, "LOW", "30d")
    passing = evaluate_slo(definition, successful=995, total=1000)
    assert passing.met and passing.error_budget_remaining == pytest.approx(0.005)
    assert not evaluate_slo(definition, successful=980, total=1000).met
    runbook = IncidentRunbook(
        "provider-storm", "retry storm", "capability",
        ("disable capability", "preserve traces"), ("qualify provider", "reenable canary"),
        "on-call",
    )
    assert runbook.kill_switch_scope == "capability"


def test_system_snapshot_restores_audit_governance_and_incident_kill_switches() -> None:
    system = DNCSystem()
    system.audit_log.append(AuditRecord("r", "tenant-a", "invoke", {}, 1, 100))
    system.data_governance.register(
        DataAsset("a", "tenant-a", "IN", "key-1"), allowed_residencies=frozenset({"IN"})
    )
    snapshot = system.capture_execution_snapshot("phase14")
    system.audit_log.purge(now_ns=100)
    system.data_governance.delete("a", tenant_id="tenant-a")
    system.kill_switches.global_disabled = True
    system.restore_execution_snapshot(snapshot)
    assert len(system.audit_log.records(tenant_id="tenant-a")) == 1
    assert not system.kill_switches.global_disabled
    assert not system.data_governance.snapshot()[("tenant-a", "a")].deleted


def test_system_global_and_tenant_kill_switches_fail_closed_at_execution_entrypoint() -> None:
    system = DNCSystem()
    system.kill_switches.global_disabled = True
    with pytest.raises(DNCPolicyError, match="kill switch"):
        system.run_cycle(None)
    system.kill_switches.global_disabled = False
    system.kill_switches.actions.add("STRUCTURAL_CYCLE")
    with pytest.raises(DNCPolicyError, match="kill switch"):
        system.run_cycle(None)
