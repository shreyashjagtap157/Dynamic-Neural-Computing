"""Dependency-free access and structural validation for Generic DNC-IR schemas."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from typing import Any

from dnc.kernel.errors import DNCValidationError
from dnc.kernel.versioning import (
    DNC_IR_SCHEMA_VERSION,
    SUPPORTED_DNC_IR_SCHEMA_VERSIONS,
    validate_schema_header,
)
from dnc.ir.contracts import PortCardinality, PortDirection, PortKind


def structural_graph_schema(version: str = DNC_IR_SCHEMA_VERSION) -> dict[str, Any]:
    """Load the canonical schema shipped with the installed DNC package."""

    if version not in SUPPORTED_DNC_IR_SCHEMA_VERSIONS:
        raise DNCValidationError(f"no packaged DNC-IR schema for version {version!r}")
    resource = files("dnc.schemas").joinpath(f"structural-graph-{version}.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_ir_document(document: Mapping[str, Any]) -> None:
    """Fail closed on malformed or incompatible serialized graph documents.

    This validates the stable interchange envelope without adding a mandatory
    JSON Schema dependency. ``DNCIRValidator`` remains responsible for graph
    semantics and invariants after deserialization.
    """

    if not isinstance(document, Mapping):
        raise DNCValidationError("DNC-IR document MUST be an object")
    schema_version = validate_schema_header(document)
    _require_type(document, "graph_id", str, "string")
    if not document["graph_id"]:
        raise DNCValidationError("graph_id MUST be non-empty")

    if schema_version is not None:
        _require_type(document, "version", Mapping, "object")
        _require_type(document, "units", Mapping, "object")
        _require_type(document, "edges", list, "array")
        _require_type(document, "metadata", Mapping, "object")
    else:
        _validate_optional_type(document, "version", Mapping, "object")
        _validate_optional_type(document, "units", Mapping, "object")
        _validate_optional_type(document, "edges", list, "array")
        _validate_optional_type(document, "metadata", Mapping, "object")

    version = document.get("version")
    if version is not None:
        for field_name in ("major", "minor", "patch", "sequence"):
            value = version.get(field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise DNCValidationError(
                    f"version.{field_name} MUST be a non-negative integer"
                )

    for unit_key, unit in document.get("units", {}).items():
        if not isinstance(unit_key, str) or not isinstance(unit, Mapping):
            raise DNCValidationError("units MUST map string IDs to unit objects")
        _require_type(unit, "unit_id", str, "string", prefix=f"units.{unit_key}")
        if unit["unit_id"] != unit_key:
            raise DNCValidationError(
                f"units.{unit_key}.unit_id MUST match its containing key"
            )
        for field_name in ("name", "structure", "visibility", "lifecycle"):
            _require_type(unit, field_name, str, "string", prefix=f"units.{unit_key}")
        if schema_version is not None and str(schema_version) == "1.2.0":
            _require_type(unit, "contract", Mapping, "object", prefix=f"units.{unit_key}")
            contract = unit["contract"]
            _require_type(
                contract, "ports", list, "array", prefix=f"units.{unit_key}.contract"
            )
            for index, port in enumerate(contract["ports"]):
                prefix = f"units.{unit_key}.contract.ports.{index}"
                if not isinstance(port, Mapping):
                    raise DNCValidationError(f"{prefix} MUST be an object")
                for field_name in ("port_id", "direction", "kind", "cardinality", "description"):
                    _require_type(port, field_name, str, "string", prefix=prefix)
                _require_type(port, "schema", Mapping, "object", prefix=prefix)
                if port["direction"] not in {item.value for item in PortDirection}:
                    raise DNCValidationError(f"{prefix}.direction is unsupported")
                if port["kind"] not in {item.value for item in PortKind}:
                    raise DNCValidationError(f"{prefix}.kind is unsupported")
                if port["cardinality"] not in {item.value for item in PortCardinality}:
                    raise DNCValidationError(f"{prefix}.cardinality is unsupported")

    for index, edge in enumerate(document.get("edges", [])):
        if not isinstance(edge, Mapping):
            raise DNCValidationError(f"edges.{index} MUST be an object")
        for field_name in ("source", "target", "edge_type"):
            _require_type(edge, field_name, str, "string", prefix=f"edges.{index}")
        if schema_version is not None and str(schema_version) == "1.2.0":
            for field_name in ("source_port", "target_port"):
                if field_name not in edge:
                    raise DNCValidationError(f"edges.{index}.{field_name} is required")
                if edge[field_name] is not None and not isinstance(edge[field_name], str):
                    raise DNCValidationError(
                        f"edges.{index}.{field_name} MUST be a string or null"
                    )


def _require_type(
    container: Mapping[str, Any],
    field_name: str,
    expected_type: type | tuple[type, ...],
    expected_name: str,
    *,
    prefix: str = "document",
) -> None:
    if field_name not in container:
        raise DNCValidationError(f"{prefix}.{field_name} is required")
    if not isinstance(container[field_name], expected_type):
        raise DNCValidationError(f"{prefix}.{field_name} MUST be a {expected_name}")


def _validate_optional_type(
    container: Mapping[str, Any],
    field_name: str,
    expected_type: type | tuple[type, ...],
    expected_name: str,
) -> None:
    if field_name in container and not isinstance(container[field_name], expected_type):
        raise DNCValidationError(f"document.{field_name} MUST be a {expected_name}")
