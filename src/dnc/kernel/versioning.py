"""Version identifiers and compatibility policy for DNC-IR documents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dnc.kernel.errors import DNCValidationError

DNC_IR_SCHEMA_ID = "dnc.ir.structural_graph"
DNC_IR_SCHEMA_VERSION = "1.1.0"
KERNEL_COMPATIBILITY_VERSION = "2026.07.phase1"
COMPATIBILITY_POLICY_VERSION = "1"
SUPPORTED_DNC_IR_SCHEMA_VERSIONS = frozenset({DNC_IR_SCHEMA_VERSION})

_SCHEMA_HEADER_FIELDS = frozenset(
    {"schema_id", "schema_version", "compatibility_version"}
)
_SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


@dataclass(frozen=True, order=True)
class SchemaVersion:
    """Strict semantic version used by the DNC-IR compatibility boundary."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SchemaVersion":
        if not isinstance(value, str):
            raise DNCValidationError("schema_version MUST be a semantic-version string")
        match = _SEMVER_PATTERN.fullmatch(value)
        if match is None:
            raise DNCValidationError(f"invalid DNC-IR schema_version: {value!r}")
        return cls(*(int(part) for part in match.groups()))


def validate_schema_header(document: Mapping[str, Any]) -> SchemaVersion | None:
    """Validate a DNC-IR header and return its version.

    Completely headerless documents are the frozen legacy compatibility path.
    Partially versioned documents are rejected because silently guessing their
    contract would make replay and migration evidence ambiguous.
    """

    present = _SCHEMA_HEADER_FIELDS.intersection(document)
    if not present:
        return None
    if present != _SCHEMA_HEADER_FIELDS:
        missing = sorted(_SCHEMA_HEADER_FIELDS - present)
        raise DNCValidationError(
            f"partial DNC-IR schema header; missing: {', '.join(missing)}"
        )
    if document["schema_id"] != DNC_IR_SCHEMA_ID:
        raise DNCValidationError(
            f"unsupported DNC-IR schema_id: {document['schema_id']!r}"
        )
    incoming = SchemaVersion.parse(document["schema_version"])
    if document["schema_version"] not in SUPPORTED_DNC_IR_SCHEMA_VERSIONS:
        raise DNCValidationError(
            f"unsupported DNC-IR schema_version {document['schema_version']!r}; "
            f"runtime explicitly supports {sorted(SUPPORTED_DNC_IR_SCHEMA_VERSIONS)}"
        )
    if document["compatibility_version"] != KERNEL_COMPATIBILITY_VERSION:
        raise DNCValidationError(
            "unsupported DNC-IR compatibility_version: "
            f"{document['compatibility_version']!r}"
        )
    return incoming


def schema_header() -> dict[str, str]:
    """Return canonical schema metadata for serialized DNC-IR graphs."""

    return {
        "schema_id": DNC_IR_SCHEMA_ID,
        "schema_version": DNC_IR_SCHEMA_VERSION,
        "compatibility_version": KERNEL_COMPATIBILITY_VERSION,
    }
