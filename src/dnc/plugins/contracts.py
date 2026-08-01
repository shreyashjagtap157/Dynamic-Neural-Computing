"""Plugin manifest and admission contracts.

Plugins are trusted in-process Python code. These contracts validate identity,
compatibility, and declared authority before import; they do not claim to
sandbox code after it is imported.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Protocol, runtime_checkable

from dnc.kernel.errors import DNCPolicyError, DNCValidationError
from dnc.kernel.versioning import (
    DNC_IR_SCHEMA_VERSION,
    KERNEL_COMPATIBILITY_VERSION,
    SUPPORTED_DNC_IR_SCHEMA_VERSIONS,
)

PLUGIN_MANIFEST_SCHEMA_ID = "dnc.plugin.manifest"
PLUGIN_MANIFEST_SCHEMA_VERSION = "1.0.0"
PLUGIN_API_VERSION = "1.0.0"
PLUGIN_ENTRY_POINT_GROUP = "dnc.plugins"

_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_PLUGIN_ID = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_ENTRY_POINT = re.compile(
    r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$"
)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "compatibility_version",
        "plugin_id",
        "plugin_version",
        "api_version",
        "entry_point",
        "capabilities",
        "permissions",
        "supported_ir_versions",
    }
)


def plugin_manifest_schema() -> dict[str, Any]:
    """Return the canonical JSON Schema for the supported manifest version."""

    resource = files("dnc.schemas").joinpath(
        f"plugin-manifest-{PLUGIN_MANIFEST_SCHEMA_VERSION}.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class PluginManifest:
    """Immutable, canonical declaration evaluated before plugin import."""

    plugin_id: str
    plugin_version: str
    entry_point: str
    capabilities: frozenset[str]
    permissions: frozenset[str] = frozenset()
    supported_ir_versions: frozenset[str] = frozenset({DNC_IR_SCHEMA_VERSION})
    api_version: str = PLUGIN_API_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_id, str) or _PLUGIN_ID.fullmatch(self.plugin_id) is None:
            raise DNCValidationError(
                "plugin_id MUST use normalized lowercase identifier syntax"
            )
        _require_semver(self.plugin_version, "plugin_version")
        _require_semver(self.api_version, "api_version")
        if not isinstance(self.entry_point, str) or _ENTRY_POINT.fullmatch(self.entry_point) is None:
            raise DNCValidationError("entry_point MUST use 'package.module:attribute' syntax")
        _validate_tokens(self.capabilities, "capabilities", require_nonempty=True)
        _validate_tokens(self.permissions, "permissions")
        _validate_tokens(
            self.supported_ir_versions,
            "supported_ir_versions",
            require_nonempty=True,
        )
        for version in self.supported_ir_versions:
            _require_semver(version, "supported_ir_versions item")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": PLUGIN_MANIFEST_SCHEMA_ID,
            "schema_version": PLUGIN_MANIFEST_SCHEMA_VERSION,
            "compatibility_version": KERNEL_COMPATIBILITY_VERSION,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "api_version": self.api_version,
            "entry_point": self.entry_point,
            "capabilities": sorted(self.capabilities),
            "permissions": sorted(self.permissions),
            "supported_ir_versions": sorted(self.supported_ir_versions),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> PluginManifest:
        _validate_manifest_document(document)
        return cls(
            plugin_id=document["plugin_id"],
            plugin_version=document["plugin_version"],
            api_version=document["api_version"],
            entry_point=document["entry_point"],
            capabilities=frozenset(document["capabilities"]),
            permissions=frozenset(document["permissions"]),
            supported_ir_versions=frozenset(document["supported_ir_versions"]),
        )

    @classmethod
    def from_json(cls, payload: str) -> PluginManifest:
        try:
            document = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as error:
            raise DNCValidationError("plugin manifest MUST be valid JSON") from error
        return cls.from_dict(document)

    def assert_runtime_compatible(self) -> None:
        if self.api_version != PLUGIN_API_VERSION:
            raise DNCValidationError(
                f"plugin API {self.api_version!r} is unsupported; expected {PLUGIN_API_VERSION!r}"
            )
        unsupported = self.supported_ir_versions - SUPPORTED_DNC_IR_SCHEMA_VERSIONS
        if unsupported:
            raise DNCValidationError(
                f"plugin declares unsupported DNC-IR versions: {sorted(unsupported)}"
            )
        if DNC_IR_SCHEMA_VERSION not in self.supported_ir_versions:
            raise DNCValidationError(
                f"plugin does not support current DNC-IR {DNC_IR_SCHEMA_VERSION}"
            )


@dataclass(frozen=True)
class PluginLoadPolicy:
    """Explicit trust and least-authority policy for in-process plugins."""

    trusted_manifest_hashes: frozenset[str]
    allowed_capabilities: frozenset[str]
    allowed_permissions: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.trusted_manifest_hashes, frozenset):
            raise DNCValidationError("trusted_manifest_hashes MUST be a frozenset")
        _validate_tokens(self.allowed_capabilities, "allowed_capabilities")
        _validate_tokens(self.allowed_permissions, "allowed_permissions")
        for digest in self.trusted_manifest_hashes:
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise DNCValidationError(
                    "trusted_manifest_hashes MUST contain lowercase SHA-256 digests"
                )

    @classmethod
    def trust(
        cls,
        manifest: PluginManifest,
        *,
        allowed_capabilities: frozenset[str] | None = None,
        allowed_permissions: frozenset[str] | None = None,
    ) -> PluginLoadPolicy:
        """Build a policy that pins exactly this manifest fingerprint."""

        return cls(
            trusted_manifest_hashes=frozenset({manifest.fingerprint}),
            allowed_capabilities=(
                manifest.capabilities
                if allowed_capabilities is None
                else allowed_capabilities
            ),
            allowed_permissions=(
                manifest.permissions
                if allowed_permissions is None
                else allowed_permissions
            ),
        )

    def admit(self, manifest: PluginManifest) -> None:
        manifest.assert_runtime_compatible()
        if manifest.fingerprint not in self.trusted_manifest_hashes:
            raise DNCPolicyError("plugin manifest fingerprint is not trusted")
        denied_capabilities = manifest.capabilities - self.allowed_capabilities
        if denied_capabilities:
            raise DNCPolicyError(
                f"plugin capabilities are not allowed: {sorted(denied_capabilities)}"
            )
        denied_permissions = manifest.permissions - self.allowed_permissions
        if denied_permissions:
            raise DNCPolicyError(
                f"plugin permissions are not allowed: {sorted(denied_permissions)}"
            )


@runtime_checkable
class DNCPlugin(Protocol):
    """Object returned by a trusted plugin entry-point factory."""

    @property
    def manifest(self) -> PluginManifest: ...

    def activate(self, runtime: object) -> None: ...


def _validate_manifest_document(document: object) -> None:
    if not isinstance(document, dict):
        raise DNCValidationError("plugin manifest MUST be an object")
    if any(not isinstance(name, str) for name in document):
        raise DNCValidationError("plugin manifest field names MUST be strings")
    present = frozenset(document)
    if present != _MANIFEST_FIELDS:
        missing = sorted(_MANIFEST_FIELDS - present)
        extra = sorted(present - _MANIFEST_FIELDS)
        details = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unknown {extra}")
        raise DNCValidationError("plugin manifest fields are invalid: " + "; ".join(details))
    if document["schema_id"] != PLUGIN_MANIFEST_SCHEMA_ID:
        raise DNCValidationError("unsupported plugin manifest schema_id")
    if document["schema_version"] != PLUGIN_MANIFEST_SCHEMA_VERSION:
        raise DNCValidationError("unsupported plugin manifest schema_version")
    if document["compatibility_version"] != KERNEL_COMPATIBILITY_VERSION:
        raise DNCValidationError("unsupported plugin compatibility_version")
    for name in ("plugin_id", "plugin_version", "api_version", "entry_point"):
        if not isinstance(document[name], str):
            raise DNCValidationError(f"plugin manifest {name} MUST be a string")
    for name in ("capabilities", "permissions", "supported_ir_versions"):
        values = document[name]
        if not isinstance(values, list):
            raise DNCValidationError(f"plugin manifest {name} MUST be an array")
        if any(not isinstance(value, str) for value in values):
            raise DNCValidationError(f"plugin manifest {name} MUST contain strings")
        _validate_tokens(
            frozenset(values),
            name,
            require_nonempty=name != "permissions",
        )
        if len(values) != len(set(values)):
            raise DNCValidationError(f"plugin manifest {name} MUST contain unique values")


def _require_semver(value: object, name: str) -> None:
    if not isinstance(value, str) or _SEMVER.fullmatch(value) is None:
        raise DNCValidationError(f"{name} MUST be a semantic version")


def _validate_tokens(
    values: object,
    name: str,
    *,
    require_nonempty: bool = False,
) -> None:
    if not isinstance(values, frozenset):
        raise DNCValidationError(f"{name} MUST be a frozenset")
    if require_nonempty and not values:
        raise DNCValidationError(f"{name} MUST not be empty")
    if any(not isinstance(value, str) or not value or value.strip() != value for value in values):
        raise DNCValidationError(f"{name} MUST contain normalized non-empty strings")
