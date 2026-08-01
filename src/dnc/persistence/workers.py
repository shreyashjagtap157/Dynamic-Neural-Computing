"""Fenced leases, heartbeats, scheduling, and abandoned-work reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.persistence.contracts import Lease, WorkItem, WorkerResult, WorkStatus


@dataclass
class DurableWorkQueue:
    _items: dict[str, WorkItem] = field(default_factory=dict)
    _status: dict[str, WorkStatus] = field(default_factory=dict)
    _leases: dict[str, Lease] = field(default_factory=dict)
    _results: dict[str, WorkerResult] = field(default_factory=dict)
    _fencing: int = 0

    def submit(self, item: WorkItem) -> bool:
        existing = next(
            (
                value for value in self._items.values()
                if value.tenant_id == item.tenant_id
                and value.idempotency_key == item.idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing != item:
                raise ValueError("conflicting work idempotency key")
            return False
        self._items[item.work_id] = item
        self._status[item.work_id] = WorkStatus.READY
        return True

    def lease(
        self, work_id: str, *, worker_id: str, now_ns: int, duration_ns: int,
        resources: dict[str, float],
    ) -> Lease:
        item = self._items[work_id]
        if duration_ns <= 0:
            raise ValueError("lease duration MUST be positive")
        if self._status[work_id] is not WorkStatus.READY:
            raise ValueError("work item is not ready")
        if now_ns >= item.deadline_ns:
            raise TimeoutError("work item deadline expired")
        if any(resources.get(key, 0) < value for key, value in item.required_resources.items()):
            raise ValueError("worker resources do not satisfy work item")
        self._fencing += 1
        lease = Lease(work_id, worker_id, self._fencing, now_ns + duration_ns, now_ns)
        self._leases[work_id] = lease
        self._status[work_id] = WorkStatus.LEASED
        return lease

    def heartbeat(self, work_id: str, *, fencing_token: int, now_ns: int, duration_ns: int) -> Lease:
        lease = self._require_lease(work_id, fencing_token)
        if duration_ns <= 0:
            raise ValueError("heartbeat duration MUST be positive")
        if now_ns >= lease.expires_at_ns:
            raise TimeoutError("lease already expired")
        renewed = Lease(work_id, lease.worker_id, lease.fencing_token, now_ns + duration_ns, now_ns)
        self._leases[work_id] = renewed
        return renewed

    def complete(self, result: WorkerResult) -> bool:
        previous = self._results.get(result.work_id)
        if previous is not None:
            if previous != result:
                raise ValueError("conflicting duplicate worker result")
            return False
        lease = self._require_lease(result.work_id, result.fencing_token)
        if lease.worker_id != result.worker_id:
            raise ValueError("worker result identity does not own lease")
        self._results[result.work_id] = result
        self._status[result.work_id] = WorkStatus.COMPLETED
        self._leases.pop(result.work_id, None)
        return True

    def reconcile(self, *, now_ns: int) -> tuple[str, ...]:
        changed = []
        for work_id, lease in tuple(self._leases.items()):
            if now_ns >= lease.expires_at_ns:
                item = self._items[work_id]
                self._status[work_id] = (
                    WorkStatus.RECONCILIATION_REQUIRED if item.irreversible else WorkStatus.READY
                )
                self._leases.pop(work_id)
                changed.append(work_id)
        return tuple(sorted(changed))

    def status(self, work_id: str) -> WorkStatus:
        return self._status[work_id]

    def snapshot(self):
        return (
            dict(self._items), dict(self._status), dict(self._leases),
            dict(self._results), self._fencing,
        )

    def restore(self, state) -> None:
        items, status, leases, results, fencing = state
        if set(status) != set(items) or not set(leases) <= set(items) or not set(results) <= set(items):
            raise ValueError("work queue backup references unknown work items")
        self._items = dict(items)
        self._status = dict(status)
        self._leases = dict(leases)
        self._results = dict(results)
        self._fencing = int(fencing)

    def _require_lease(self, work_id: str, fencing_token: int) -> Lease:
        lease = self._leases.get(work_id)
        if lease is None or lease.fencing_token != fencing_token:
            raise ValueError("stale or missing fencing token")
        return lease
