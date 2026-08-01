"""Checked semantic-state compression."""

from __future__ import annotations

from dnc.memory.contracts import CompressionResult, MemoryKind, MemoryRecord


def compress_records(
    records: tuple[MemoryRecord, ...],
    *,
    output_id: str,
    summary: object,
    preserved_ids: tuple[str, ...],
    maximum_information_loss: float,
) -> CompressionResult:
    if not records:
        raise ValueError("compression requires source records")
    tenant_ids = {item.tenant_id for item in records}
    if len(tenant_ids) != 1:
        raise ValueError("compression cannot cross tenants")
    source_ids = tuple(item.record_id for item in records)
    if not set(preserved_ids) <= set(source_ids):
        raise ValueError("preservation claims MUST reference source records")
    information_loss = 1 - len(set(preserved_ids)) / len(set(source_ids))
    if information_loss > maximum_information_loss:
        raise ValueError("compression exceeds information-loss threshold")
    record = MemoryRecord(
        output_id,
        MemoryKind.SEMANTIC,
        records[0].tenant_id,
        summary,
        provenance=source_ids,
        security_labels=frozenset().union(*(item.security_labels for item in records)),
        trust=min(item.trust for item in records),
        created_at_ns=max(item.created_at_ns for item in records),
        dependencies=source_ids,
    )
    return CompressionResult(record, source_ids, preserved_ids, information_loss)
