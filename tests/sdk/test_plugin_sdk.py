import json

import pytest

from dnc.kernel.errors import DNCPolicyError, DNCValidationError
from dnc.plugins import (
    PLUGIN_API_VERSION,
    PluginLoadPolicy,
    PluginManifest,
    PluginRegistry,
    plugin_manifest_schema,
)


def _manifest(**changes) -> PluginManifest:
    values = {
        "plugin_id": "example.provider",
        "plugin_version": "1.2.3",
        "entry_point": "example_provider:create_plugin",
        "capabilities": frozenset({"provider"}),
        "permissions": frozenset({"network:provider"}),
    }
    values.update(changes)
    return PluginManifest(**values)


def test_manifest_is_canonical_versioned_and_roundtrips() -> None:
    manifest = _manifest()
    document = manifest.to_dict()

    assert document["schema_id"] == "dnc.plugin.manifest"
    assert document["schema_version"] == "1.0.0"
    assert document["api_version"] == PLUGIN_API_VERSION
    assert PluginManifest.from_json(manifest.to_json()) == manifest
    assert manifest.fingerprint == PluginManifest.from_dict(document).fingerprint
    assert plugin_manifest_schema()["properties"]["schema_id"]["const"] == document["schema_id"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0.0"),
        ("compatibility_version", "future"),
        ("schema_id", "foreign.plugin"),
    ],
)
def test_manifest_rejects_incompatible_headers(field: str, value: str) -> None:
    document = _manifest().to_dict()
    document[field] = value
    with pytest.raises(DNCValidationError):
        PluginManifest.from_dict(document)


def test_manifest_rejects_unknown_fields_duplicates_and_invalid_identifiers() -> None:
    document = _manifest().to_dict()
    document["unexpected"] = True
    with pytest.raises(DNCValidationError, match="unknown"):
        PluginManifest.from_dict(document)

    document = _manifest().to_dict()
    document["permissions"] = ["network:provider", "network:provider"]
    with pytest.raises(DNCValidationError, match="unique"):
        PluginManifest.from_dict(document)

    document = _manifest().to_dict()
    document["capabilities"] = [["not-hashable"]]
    with pytest.raises(DNCValidationError, match="contain strings"):
        PluginManifest.from_dict(document)

    with pytest.raises(DNCValidationError, match="plugin_id"):
        _manifest(plugin_id="Unsafe Plugin")


def test_registration_fails_before_resolution_when_manifest_is_not_trusted() -> None:
    manifest = _manifest()
    registry = PluginRegistry(
        PluginLoadPolicy(
            trusted_manifest_hashes=frozenset(),
            allowed_capabilities=manifest.capabilities,
            allowed_permissions=manifest.permissions,
        )
    )

    with pytest.raises(DNCPolicyError, match="not trusted"):
        registry.register(manifest)
    assert registry.all() == ()


def test_policy_enforces_capability_and_permission_least_authority() -> None:
    manifest = _manifest()
    with pytest.raises(DNCPolicyError, match="capabilities"):
        PluginLoadPolicy.trust(
            manifest,
            allowed_capabilities=frozenset(),
        ).admit(manifest)
    with pytest.raises(DNCPolicyError, match="permissions"):
        PluginLoadPolicy.trust(
            manifest,
            allowed_permissions=frozenset(),
        ).admit(manifest)


def test_registry_loads_only_a_factory_with_the_pinned_manifest() -> None:
    manifest = _manifest()
    registry = PluginRegistry(PluginLoadPolicy.trust(manifest))
    registry.register(manifest)

    class Plugin:
        def __init__(self, declared: PluginManifest) -> None:
            self.manifest = declared

        def activate(self, runtime: object) -> None:
            self.runtime = runtime

    loaded = registry.load(
        manifest.plugin_id,
        resolver=lambda entry_point: lambda: Plugin(manifest),
    )
    assert loaded.manifest == manifest

    changed = _manifest(plugin_version="1.2.4")
    with pytest.raises(DNCValidationError, match="does not match"):
        registry.load(
            manifest.plugin_id,
            resolver=lambda entry_point: lambda: Plugin(changed),
        )

    with pytest.raises(DNCValidationError, match="factory"):
        registry.load(manifest.plugin_id, resolver=lambda entry_point: object())


def test_manifest_json_rejects_non_json_payload() -> None:
    with pytest.raises(DNCValidationError, match="valid JSON"):
        PluginManifest.from_json("{not-json")
    with pytest.raises(DNCValidationError, match="object"):
        PluginManifest.from_json(json.dumps(["not", "an", "object"]))
