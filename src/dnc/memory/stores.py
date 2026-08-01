"""Separated tenant-aware memory stores and retrieval policy."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from dnc.memory.contracts import MemoryKind, MemoryRecord


@dataclass
class MemoryStore:
    kind: MemoryKind
    _records: dict[str, MemoryRecord] = field(default_factory=dict)

    def put(self, record: MemoryRecord) -> None:
        if record.kind is not self.kind:
            raise ValueError("record kind MUST match memory namespace")
        if record.record_id in self._records:
            raise ValueError(f"memory record already exists: {record.record_id}")
        self._records[record.record_id] = record

    def get(self, record_id: str, *, tenant_id: str) -> MemoryRecord | None:
        record = self._records.get(record_id)
        if record is None or record.tenant_id != tenant_id or record.deleted:
            return None
        return record

    def delete(self, record_id: str, *, tenant_id: str) -> None:
        record = self.get(record_id, tenant_id=tenant_id)
        if record is None:
            raise KeyError(f"unknown memory record: {record_id}")
        if record.legal_hold:
            raise PermissionError("memory under legal hold cannot be deleted")
        self._records[record_id] = replace(record, deleted=True, content=None)

    def retrieve(
        self,
        *,
        tenant_id: str,
        allowed_labels: frozenset[str],
        now_ns: int,
        minimum_trust: float = 0.0,
        domain: str | None = None,
        query: str = "",
        critical: bool = False,
        exact_reranker: Callable[[MemoryRecord], float] | None = None,
    ) -> tuple[MemoryRecord, ...]:
        candidates = [
            record for record in self._records.values()
            if record.tenant_id == tenant_id
            and not record.deleted
            and record.security_labels <= allowed_labels
            and record.trust >= minimum_trust
            and (record.expires_at_ns is None or record.expires_at_ns > now_ns)
            and (domain is None or record.domain == domain)
            and (not critical or record.integrity_verified)
        ]
        if critical and exact_reranker is None:
            raise ValueError("critical retrieval requires an exact reranker")
        terms = set(query.casefold().split())

        def score(record: MemoryRecord) -> tuple[float, float, int, str]:
            exact = exact_reranker(record) if exact_reranker is not None else 0.0
            lexical = len(terms & set(str(record.content).casefold().split()))
            return (-exact, -record.trust, -lexical, record.record_id)

        return tuple(sorted(candidates, key=score))

    def snapshot(self) -> tuple[MemoryRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


class GovernedMemory:
    def __init__(self) -> None:
        self._stores = {kind: MemoryStore(kind) for kind in MemoryKind}

    def store(self, kind: MemoryKind) -> MemoryStore:
        return self._stores[kind]

    def put(self, record: MemoryRecord) -> None:
        self.store(record.kind).put(record)

    def invalidate_dependencies(self, changed_fingerprints: set[str]) -> tuple[str, ...]:
        invalidated = []
        for store in self._stores.values():
            for record in store.snapshot():
                if not record.deleted and set(record.dependencies) & changed_fingerprints:
                    store._records[record.record_id] = replace(record, deleted=True, content=None)
                    invalidated.append(record.record_id)
        return tuple(sorted(invalidated))

    def snapshot(self) -> dict[str, tuple[MemoryRecord, ...]]:
        return {kind.value: self.store(kind).snapshot() for kind in MemoryKind}

    def restore(self, state: dict[str, tuple[MemoryRecord, ...]]) -> None:
        restored = {kind: MemoryStore(kind) for kind in MemoryKind}
        for kind in MemoryKind:
            for record in state.get(kind.value, ()):
                restored[kind].put(record)
        self._stores = restored
