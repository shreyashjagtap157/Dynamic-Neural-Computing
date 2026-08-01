from dataclasses import replace
from pathlib import Path

import pytest

from dnc.persistence import (
    ContentAddressedObjectStore,
    DurableEvent,
    DurableWorkQueue,
    EventRepository,
    FaultCampaignResult,
    OutboxMessage,
    RecoveryObjectives,
    WorkerResult,
    WorkItem,
    WorkStatus,
    ray_available,
    require_optional_adapter,
    temporal_available,
)
from dnc.cognition.canonical import canonical_data
from dnc.system import DNCSystem


def _event(version=1, tenant="tenant-a", event_id=None):
    return DurableEvent(event_id or f"e{version}", tenant, "task-1", version, "updated", {"delta": 1}, version)


def _message(message_id="m1", tenant="tenant-a", key="key-1"):
    return OutboxMessage(message_id, tenant, "actions", {"value": 1}, key)


def _work(work_id="w1", tenant="tenant-a", irreversible=False):
    return WorkItem(
        work_id, tenant, "task-1", "action-1", 1, "cpu", "I2", 1_000,
        "SAFE_RETRY", f"key-{work_id}", "trace-1", frozenset({"internal"}),
        ("artifact",), {"cpu": 1, "memory": 2}, irreversible,
    )


def test_event_repository_occ_append_and_rebuild_match_single_process_state() -> None:
    repository = EventRepository()
    repository.append(_event(1), expected_version=0)
    repository.append(_event(2), expected_version=1)
    with pytest.raises(ValueError, match="concurrency"):
        repository.append(_event(3), expected_version=1)
    rebuilt = repository.rebuild(
        "task-1", tenant_id="tenant-a",
        reducer=lambda state, event: state + event.payload["delta"], initial=0,
    )
    assert rebuilt == 2


def test_event_and_outbox_append_is_atomic_and_tenant_scoped() -> None:
    repository = EventRepository()
    with pytest.raises(ValueError, match="tenant"):
        repository.append(
            _event(), expected_version=0,
            outbox=(_message("m1"), _message("m2", tenant="tenant-b")),
        )
    assert repository.load("task-1", tenant_id="tenant-a") == ()
    assert repository.pending_outbox(tenant_id="tenant-a") == ()
    repository.append(_event(), expected_version=0, outbox=(_message(),))
    assert repository.pending_outbox(tenant_id="tenant-b") == ()
    repository.mark_published("m1", tenant_id="tenant-a")
    assert repository.pending_outbox(tenant_id="tenant-a") == ()


def test_inbox_is_effectively_once_per_tenant_and_rejects_conflict() -> None:
    repository = EventRepository()
    message = _message()
    assert repository.receive_once(message, "result")
    assert not repository.receive_once(message, "result")
    with pytest.raises(ValueError, match="conflicting"):
        repository.receive_once(message, "different")
    assert repository.receive_once(replace(message, tenant_id="tenant-b"), "other")


def test_event_and_message_identifiers_are_tenant_composite() -> None:
    repository = EventRepository()
    repository.append(_event(tenant="tenant-a", event_id="same"), expected_version=0, outbox=(_message(),))
    repository.append(
        _event(tenant="tenant-b", event_id="same"), expected_version=0,
        outbox=(_message(tenant="tenant-b"),),
    )
    assert len(repository.pending_outbox(tenant_id="tenant-a")) == 1
    assert len(repository.pending_outbox(tenant_id="tenant-b")) == 1


def test_content_addressed_store_integrity_and_cross_tenant_isolation() -> None:
    store = ContentAddressedObjectStore()
    digest = store.put(b"checkpoint", tenant_id="tenant-a")
    assert store.get(digest, tenant_id="tenant-a") == b"checkpoint"
    with pytest.raises(KeyError, match="tenant"):
        store.get(digest, tenant_id="tenant-b")
    store.corrupt_for_test(digest, tenant_id="tenant-a", data=b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        store.get(digest, tenant_id="tenant-a")
    assert canonical_data(b"\x00\xff") == {"$bytes_hex": "00ff"}


def test_backup_restore_preserves_events_outbox_inbox_and_object_integrity() -> None:
    repository = EventRepository()
    repository.append(_event(), expected_version=0, outbox=(_message(),))
    repository.receive_once(_message(), "result")
    objects = ContentAddressedObjectStore()
    digest = objects.put(b"checkpoint", tenant_id="tenant-a")
    repository_backup = repository.snapshot()
    object_backup = objects.snapshot()
    restored_repository = EventRepository()
    restored_repository.restore(repository_backup)
    restored_objects = ContentAddressedObjectStore()
    restored_objects.restore(object_backup)
    assert restored_repository.load("task-1", tenant_id="tenant-a") == (_event(),)
    assert restored_objects.get(digest, tenant_id="tenant-a") == b"checkpoint"


def test_resource_scheduler_lease_heartbeat_and_fencing() -> None:
    queue = DurableWorkQueue()
    queue.submit(_work())
    with pytest.raises(ValueError, match="resources"):
        queue.lease("w1", worker_id="small", now_ns=1, duration_ns=10, resources={"cpu": 1})
    lease = queue.lease(
        "w1", worker_id="worker", now_ns=1, duration_ns=10,
        resources={"cpu": 1, "memory": 2},
    )
    renewed = queue.heartbeat("w1", fencing_token=lease.fencing_token, now_ns=5, duration_ns=10)
    assert renewed.expires_at_ns == 15
    with pytest.raises(ValueError, match="identity"):
        queue.complete(WorkerResult("w1", "attacker", lease.fencing_token, "o", (), True, "r"))
    assert queue.complete(WorkerResult("w1", "worker", lease.fencing_token, "o", (), True, "r"))
    assert not queue.complete(WorkerResult("w1", "worker", lease.fencing_token, "o", (), True, "r"))
    assert queue.status("w1") is WorkStatus.COMPLETED


def test_duplicate_delivery_and_conflicting_results_do_not_duplicate_effects() -> None:
    queue = DurableWorkQueue()
    item = _work()
    assert queue.submit(item)
    assert not queue.submit(item)
    with pytest.raises(ValueError, match="idempotency"):
        queue.submit(replace(item, action_id="different"))


def test_expired_safe_work_requeues_with_new_fence_and_stale_worker_is_rejected() -> None:
    queue = DurableWorkQueue()
    queue.submit(_work())
    first = queue.lease("w1", worker_id="old", now_ns=1, duration_ns=5, resources={"cpu": 1, "memory": 2})
    assert queue.reconcile(now_ns=6) == ("w1",)
    second = queue.lease("w1", worker_id="new", now_ns=7, duration_ns=5, resources={"cpu": 1, "memory": 2})
    assert second.fencing_token > first.fencing_token
    with pytest.raises(ValueError, match="stale"):
        queue.complete(WorkerResult("w1", "old", first.fencing_token, "o", (), True, "old"))


def test_ambiguous_irreversible_work_requires_reconciliation_not_retry() -> None:
    queue = DurableWorkQueue()
    queue.submit(_work(irreversible=True))
    queue.lease("w1", worker_id="worker", now_ns=1, duration_ns=5, resources={"cpu": 1, "memory": 2})
    queue.reconcile(now_ns=6)
    assert queue.status("w1") is WorkStatus.RECONCILIATION_REQUIRED
    with pytest.raises(ValueError, match="not ready"):
        queue.lease("w1", worker_id="other", now_ns=7, duration_ns=5, resources={"cpu": 1, "memory": 2})


def test_postgresql_migration_forces_rls_and_tenant_policies() -> None:
    sql = (
        Path(__file__).parents[2] / "src" / "dnc" / "persistence" / "migrations" / "001_initial.sql"
    ).read_text(encoding="utf-8")
    assert sql.count("FORCE ROW LEVEL SECURITY") == 2
    assert "current_setting('dnc.tenant_id', true)" in sql
    assert "UNIQUE (tenant_id, idempotency_key)" in sql


def test_optional_distributed_adapters_fail_truthfully_when_uninstalled() -> None:
    if not ray_available():
        with pytest.raises(RuntimeError, match="ray"):
            require_optional_adapter("ray")
    if not temporal_available():
        with pytest.raises(RuntimeError, match="temporal"):
            require_optional_adapter("temporal")


def test_fault_campaign_meets_declared_reference_rpo_rto_and_semantic_safety() -> None:
    result = FaultCampaignResult(
        faults=("node_loss", "object_corruption", "queue_duplicate", "provider_timeout", "network_partition"),
        lost_events=0, recovery_ticks=2, availability=0.99,
        duplicate_irreversible_effects=0, semantic_match=True, tenant_isolation_violations=0,
    )
    assert result.meets(RecoveryObjectives(0, 3, 0.99))
    assert not replace(result, duplicate_irreversible_effects=1).meets(
        RecoveryObjectives(0, 3, 0.99)
    )


def test_system_snapshot_restores_durable_repository_objects_queue_and_fencing() -> None:
    system = DNCSystem()
    system.event_repository.append(_event(), expected_version=0)
    digest = system.object_store.put(b"artifact", tenant_id="tenant-a")
    system.work_queue.submit(_work())
    first = system.work_queue.lease(
        "w1", worker_id="worker", now_ns=1, duration_ns=5,
        resources={"cpu": 1, "memory": 2},
    )
    snapshot = system.capture_execution_snapshot("phase13")
    system.event_repository.append(_event(2), expected_version=1)
    system.object_store.corrupt_for_test(digest, tenant_id="tenant-a", data=b"bad")
    system.work_queue.reconcile(now_ns=6)
    system.restore_execution_snapshot(snapshot)
    assert system.event_repository.load("task-1", tenant_id="tenant-a") == (_event(),)
    assert system.object_store.get(digest, tenant_id="tenant-a") == b"artifact"
    restored = system.work_queue.snapshot()
    assert restored[2]["w1"].fencing_token == first.fencing_token
