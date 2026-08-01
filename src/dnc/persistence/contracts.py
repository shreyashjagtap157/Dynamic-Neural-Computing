"""Durable event, queue, lease, and worker contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class DurableEvent:
    event_id: str
    tenant_id: str
    aggregate_id: str
    aggregate_version: int
    event_type: str
    payload: dict[str, Any]
    timestamp_ns: int


@dataclass(frozen=True)
class OutboxMessage:
    message_id: str
    tenant_id: str
    topic: str
    payload: dict[str, Any]
    idempotency_key: str
    published: bool = False


class WorkStatus(str, Enum):
    READY = "READY"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    tenant_id: str
    task_id: str
    action_id: str
    expected_aggregate_version: int
    capability: str
    isolation_grade: str
    deadline_ns: int
    retry_class: str
    idempotency_key: str
    trace_id: str
    policy_labels: frozenset[str]
    artifact_refs: tuple[str, ...]
    required_resources: dict[str, float] = field(default_factory=dict)
    irreversible: bool = False


@dataclass(frozen=True)
class Lease:
    work_id: str
    worker_id: str
    fencing_token: int
    expires_at_ns: int
    heartbeat_at_ns: int


@dataclass(frozen=True)
class WorkerResult:
    work_id: str
    worker_id: str
    fencing_token: int
    output_ref: str
    effect_ids: tuple[str, ...]
    cleanup_complete: bool
    fingerprint: str
