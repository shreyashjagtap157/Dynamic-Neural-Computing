"""Dependency-free access and structural validation for Generic DNC-IR schemas."""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from typing import Any

from dnc.kernel.errors import DNCValidationError
from dnc.kernel.versioning import DNC_IR_SCHEMA_VERSION, validate_schema_header


def structural_graph_schema() -> dict[str, Any]:
    """Load the canonical schema shipped with the installed DNC package."""

    resource = files("dnc.schemas").joinpath(
        f"structural-graph-{DNC_IR_SCHEMA_VERSION}.schema.json"
    )
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

    for index, edge in enumerate(document.get("edges", [])):
        if not isinstance(edge, Mapping):
            raise DNCValidationError(f"edges.{index} MUST be an object")
        for field_name in ("source", "target", "edge_type"):
            _require_type(edge, field_name, str, "string", prefix=f"edges.{index}")


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
