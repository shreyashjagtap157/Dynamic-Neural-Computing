"""Redacted telemetry, audit retention, data governance, and incident controls."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field, replace
from typing import Any, Protocol


_SECRET_KEYS = re.compile(r"(secret|token|password|credential|authorization)", re.IGNORECASE)
_SECRET_VALUE = re.compile(
    r"(?:\bbearer\s+\S+|\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def redact_telemetry(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEYS.search(str(key)) else redact_telemetry(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_telemetry(item) for item in value]
    if isinstance(value, str) and _SECRET_VALUE.search(value):
        return "[REDACTED]"
    return value


@dataclass(frozen=True)
class AuditRecord:
    record_id: str
    tenant_id: str
    event: str
    payload: dict[str, Any]
    created_at_ns: int
    retain_until_ns: int
    legal_hold: bool = False


@dataclass
class AuditLog:
    _records: dict[tuple[str, str], AuditRecord] = field(default_factory=dict)

    def append(self, record: AuditRecord) -> None:
        key = (record.tenant_id, record.record_id)
        if key in self._records:
            raise ValueError("audit record is immutable")
        self._records[key] = replace(record, payload=redact_telemetry(record.payload))

    def purge(self, *, now_ns: int) -> tuple[str, ...]:
        removed = []
        for key, record in tuple(self._records.items()):
            if not record.legal_hold and now_ns >= record.retain_until_ns:
                self._records.pop(key)
                removed.append(record.record_id)
        return tuple(sorted(removed))

    def records(self, *, tenant_id: str) -> tuple[AuditRecord, ...]:
        return tuple(
            copy.deepcopy(record)
            for (tenant, _), record in sorted(self._records.items())
            if tenant == tenant_id
        )

    def snapshot(self):
        return copy.deepcopy(self._records)

    def restore(self, state) -> None:
        self._records = copy.deepcopy(state)


@dataclass(frozen=True)
class DataAsset:
    asset_id: str
    tenant_id: str
    residency: str
    key_version: str
    legal_hold: bool = False
    deleted: bool = False


@dataclass
class DataGovernance:
    _assets: dict[tuple[str, str], DataAsset] = field(default_factory=dict)

    def register(self, asset: DataAsset, *, allowed_residencies: frozenset[str]) -> None:
        if asset.residency not in allowed_residencies:
            raise PermissionError("data residency policy denied asset")
        key = (asset.tenant_id, asset.asset_id)
        if key in self._assets:
            raise ValueError("data asset registration is immutable")
        self._assets[key] = asset

    def rotate_key(self, asset_id: str, *, tenant_id: str, key_version: str) -> None:
        key = (tenant_id, asset_id)
        self._assets[key] = replace(self._assets[key], key_version=key_version)

    def delete(self, asset_id: str, *, tenant_id: str) -> None:
        key = (tenant_id, asset_id)
        asset = self._assets[key]
        if asset.legal_hold:
            raise PermissionError("asset under legal hold cannot be deleted")
        self._assets[key] = replace(asset, deleted=True)

    def snapshot(self):
        return dict(self._assets)

    def restore(self, state) -> None:
        self._assets = dict(state)


@dataclass(frozen=True)
class TelemetryEvent:
    trace_id: str
    tenant_id: str
    name: str
    timestamp_ns: int
    attributes: dict[str, Any]

    def redacted(self) -> "TelemetryEvent":
        return replace(self, attributes=redact_telemetry(self.attributes))


class TelemetryExporter(Protocol):
    exporter_id: str

    def export(self, event: TelemetryEvent) -> None: ...


@dataclass(frozen=True)
class SLODefinition:
    name: str
    target: float
    risk_class: str
    window: str

    def __post_init__(self) -> None:
        if not 0 <= self.target <= 1:
            raise ValueError("SLO target MUST be between zero and one")


@dataclass(frozen=True)
class SLOResult:
    definition: SLODefinition
    observed: float
    met: bool
    error_budget_remaining: float


def evaluate_slo(definition: SLODefinition, *, successful: int, total: int) -> SLOResult:
    if total <= 0 or not 0 <= successful <= total:
        raise ValueError("SLO observations MUST be valid and non-empty")
    observed = successful / total
    allowed_failures = 1 - definition.target
    actual_failures = 1 - observed
    remaining = max(0.0, allowed_failures - actual_failures)
    return SLOResult(definition, observed, observed >= definition.target, remaining)


@dataclass(frozen=True)
class IncidentRunbook:
    runbook_id: str
    alert: str
    kill_switch_scope: str
    containment_steps: tuple[str, ...]
    recovery_steps: tuple[str, ...]
    owner_role: str
