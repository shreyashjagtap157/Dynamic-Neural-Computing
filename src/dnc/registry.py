"""Tenant-scoped content-addressed artifact and Generic DNC-IR registries."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from dnc.ir.contracts import ExecutionContext
from dnc.ir.graph import StructuralGraph
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.validator import DNCIRValidator, ValidationResult
from dnc.kernel.errors import DNCPolicyError, DNCValidationError
from dnc.kernel.versioning import DNC_IR_SCHEMA_ID, DNC_IR_SCHEMA_VERSION
from dnc.persistence.object_store import ContentAddressedObjectStore

_CONTENT_REF = re.compile(r"^sha256:([0-9a-f]{64})$")


@dataclass(frozen=True)
class ArtifactRecord:
    content_ref: str
    tenant_id: str
    media_type: str
    size_bytes: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_ref": self.content_ref,
            "tenant_id": self.tenant_id,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "metadata": deepcopy(self.metadata),
        }


@dataclass(frozen=True)
class GraphRecord:
    content_ref: str
    tenant_id: str
    graph_id: str
    graph_version: str
    schema_id: str
    schema_version: str
    unit_count: int
    edge_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_ref": self.content_ref,
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "unit_count": self.unit_count,
            "edge_count": self.edge_count,
        }


class ArtifactRegistry:
    """Immutable descriptors over the existing tenant-scoped object store."""

    def __init__(self, object_store: ContentAddressedObjectStore | None = None) -> None:
        self.object_store = object_store or ContentAddressedObjectStore()
        self._records: dict[tuple[str, str], ArtifactRecord] = {}
        self._lock = RLock()

    def register(
        self,
        data: bytes,
        *,
        tenant_id: str,
        media_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        tenant = _validate_tenant(tenant_id)
        if not isinstance(data, bytes):
            raise DNCValidationError("artifact data MUST be bytes")
        if not isinstance(media_type, str) or not media_type or media_type.strip() != media_type:
            raise DNCValidationError("artifact media_type MUST be normalized and non-empty")
        descriptor_metadata = _validate_metadata(metadata or {})
        with self._lock:
            digest = self.object_store.put(data, tenant_id=tenant)
            content_ref = _validate_content_ref(f"sha256:{digest}")
            record = ArtifactRecord(
                content_ref=content_ref,
                tenant_id=tenant,
                media_type=media_type,
                size_bytes=len(data),
                metadata=descriptor_metadata,
            )
            key = (tenant, content_ref)
            previous = self._records.get(key)
            if previous is not None and previous != record:
                raise DNCValidationError(
                    "artifact content is already registered with a conflicting descriptor"
                )
            self._records[key] = deepcopy(record)
            return deepcopy(record)

    def record(self, content_ref: str, *, tenant_id: str) -> ArtifactRecord:
        key = (_validate_tenant(tenant_id), _validate_content_ref(content_ref))
        with self._lock:
            try:
                return deepcopy(self._records[key])
            except KeyError as error:
                raise KeyError("unknown tenant-scoped artifact") from error

    def get(self, content_ref: str, *, tenant_id: str) -> bytes:
        record = self.record(content_ref, tenant_id=tenant_id)
        digest = _digest(record.content_ref)
        data = self.object_store.get(digest, tenant_id=record.tenant_id)
        if len(data) != record.size_bytes:
            raise DNCValidationError("artifact descriptor size does not match stored content")
        return data

    def all(self, *, tenant_id: str) -> tuple[ArtifactRecord, ...]:
        tenant = _validate_tenant(tenant_id)
        with self._lock:
            return tuple(
                deepcopy(self._records[key])
                for key in sorted(self._records)
                if key[0] == tenant
            )


class GraphRegistry:
    """Validated, governed registry for canonical Generic DNC-IR documents."""

    def __init__(
        self,
        object_store: ContentAddressedObjectStore | None = None,
        validator: DNCIRValidator | None = None,
    ) -> None:
        self.object_store = object_store or ContentAddressedObjectStore()
        self.validator = validator or DNCIRValidator()
        self._records: dict[tuple[str, str], GraphRecord] = {}
        self._lock = RLock()

    def register(
        self,
        graph: StructuralGraph,
        *,
        tenant_id: str,
        context: ExecutionContext | None = None,
    ) -> GraphRecord:
        tenant = _validate_tenant_context(tenant_id, context)
        with self._lock:
            _admit_graph(graph, self.validator, context)
            document = DNWIRSerializer.to_dict(graph)
            try:
                payload = json.dumps(
                    document,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            except (TypeError, ValueError) as error:
                raise DNCValidationError("graph document MUST contain finite JSON data") from error
            # Round-trip through the public interchange boundary before persistence.
            canonical_graph = DNWIRSerializer.from_json(payload.decode("utf-8"))
            _admit_graph(canonical_graph, self.validator, context)
            digest = self.object_store.put(payload, tenant_id=tenant)
            content_ref = _validate_content_ref(f"sha256:{digest}")
            record = GraphRecord(
                content_ref=content_ref,
                tenant_id=tenant,
                graph_id=canonical_graph.graph_id.value,
                graph_version=str(canonical_graph.version),
                schema_id=DNC_IR_SCHEMA_ID,
                schema_version=DNC_IR_SCHEMA_VERSION,
                unit_count=len(canonical_graph.units),
                edge_count=len(canonical_graph.edges),
            )
            key = (tenant, content_ref)
            previous = self._records.get(key)
            if previous is not None and previous != record:
                raise DNCValidationError("graph content conflicts with its registered descriptor")
            self._records[key] = record
            return record

    def record(self, content_ref: str, *, tenant_id: str) -> GraphRecord:
        key = (_validate_tenant(tenant_id), _validate_content_ref(content_ref))
        with self._lock:
            try:
                return self._records[key]
            except KeyError as error:
                raise KeyError("unknown tenant-scoped graph") from error

    def load(
        self,
        content_ref: str,
        *,
        tenant_id: str,
        context: ExecutionContext | None = None,
    ) -> StructuralGraph:
        tenant = _validate_tenant_context(tenant_id, context)
        with self._lock:
            record = self.record(content_ref, tenant_id=tenant)
            payload = self.object_store.get(_digest(record.content_ref), tenant_id=tenant)
            try:
                graph = DNWIRSerializer.from_json(payload.decode("utf-8"))
            except UnicodeDecodeError as error:
                raise DNCValidationError("registered graph MUST be UTF-8 JSON") from error
            except DNCValidationError as error:
                raise DNCValidationError("registered graph MUST be valid DNC-IR JSON") from error
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise DNCValidationError("registered graph MUST be valid DNC-IR JSON") from error
            _admit_graph(graph, self.validator, context)
            actual = GraphRecord(
                content_ref=record.content_ref,
                tenant_id=tenant,
                graph_id=graph.graph_id.value,
                graph_version=str(graph.version),
                schema_id=DNC_IR_SCHEMA_ID,
                schema_version=DNC_IR_SCHEMA_VERSION,
                unit_count=len(graph.units),
                edge_count=len(graph.edges),
            )
            if actual != record:
                raise DNCValidationError("registered graph descriptor does not match stored content")
            return graph

    def all(self, *, tenant_id: str) -> tuple[GraphRecord, ...]:
        tenant = _validate_tenant(tenant_id)
        with self._lock:
            return tuple(
                self._records[key]
                for key in sorted(self._records)
                if key[0] == tenant
            )


def _admit_graph(
    graph: StructuralGraph,
    validator: DNCIRValidator,
    context: ExecutionContext | None,
) -> None:
    if not isinstance(graph, StructuralGraph):
        raise DNCValidationError("graph MUST be a StructuralGraph")
    structural = validator.validate_graph(graph)
    if not structural.is_valid:
        raise DNCValidationError(_validation_message("graph", structural))
    requires_context = any(
        unit.contract.requires_execution_context() for unit in graph.units.values()
    )
    if requires_context and context is None:
        raise DNCPolicyError("governed graph registration and load require an ExecutionContext")
    if context is not None:
        execution = validator.validate_execution_context(graph, context)
        if not execution.is_valid:
            raise DNCPolicyError(_validation_message("execution context", execution))


def _validation_message(label: str, result: ValidationResult) -> str:
    details = "; ".join(f"{issue.code}: {issue.message}" for issue in result.errors)
    return f"invalid {label}: {details}"


def _validate_tenant_context(
    tenant_id: str,
    context: ExecutionContext | None,
) -> str:
    tenant = _validate_tenant(tenant_id)
    if context is not None and context.tenant_id != tenant:
        raise DNCPolicyError("execution context tenant does not match registry tenant")
    return tenant


def _validate_tenant(tenant_id: str) -> str:
    if not isinstance(tenant_id, str) or not tenant_id or tenant_id.strip() != tenant_id:
        raise DNCValidationError("tenant_id MUST be normalized and non-empty")
    return tenant_id


def _validate_content_ref(content_ref: str) -> str:
    if not isinstance(content_ref, str) or _CONTENT_REF.fullmatch(content_ref) is None:
        raise DNCValidationError("content_ref MUST be a lowercase sha256:<digest> reference")
    return content_ref


def _digest(content_ref: str) -> str:
    match = _CONTENT_REF.fullmatch(_validate_content_ref(content_ref))
    assert match is not None
    return match.group(1)


def _validate_metadata(metadata: object) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise DNCValidationError("artifact metadata MUST be an object")
    try:
        payload = json.dumps(metadata, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise DNCValidationError("artifact metadata MUST be finite JSON data") from error
    restored = json.loads(payload)
    if not isinstance(restored, dict):
        raise DNCValidationError("artifact metadata MUST be an object")
    return restored
