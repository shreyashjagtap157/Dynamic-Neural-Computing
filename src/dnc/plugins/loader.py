"""Explicit loader for fingerprint-pinned, in-process plugins."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from dnc.kernel.errors import DNCValidationError
from dnc.plugins.contracts import DNCPlugin, PluginLoadPolicy, PluginManifest

PluginResolver = Callable[[str], object]


class PluginRegistry:
    """Register manifests before importing any optional plugin code."""

    def __init__(self, policy: PluginLoadPolicy) -> None:
        self._policy = policy
        self._manifests: dict[str, PluginManifest] = {}
        self._fingerprints: dict[str, str] = {}

    def register(self, manifest: PluginManifest) -> None:
        self._policy.admit(manifest)
        if manifest.plugin_id in self._manifests:
            raise DNCValidationError(f"plugin already registered: {manifest.plugin_id}")
        self._manifests[manifest.plugin_id] = manifest
        self._fingerprints[manifest.plugin_id] = manifest.fingerprint

    def manifest(self, plugin_id: str) -> PluginManifest:
        try:
            manifest = self._manifests[plugin_id]
        except KeyError as error:
            raise KeyError(f"unknown plugin: {plugin_id}") from error
        if manifest.fingerprint != self._fingerprints[plugin_id]:
            raise DNCValidationError("registered plugin manifest changed after admission")
        return manifest

    def all(self) -> tuple[PluginManifest, ...]:
        return tuple(self.manifest(plugin_id) for plugin_id in sorted(self._manifests))

    def load(
        self,
        plugin_id: str,
        *,
        resolver: PluginResolver | None = None,
    ) -> DNCPlugin:
        """Re-admit the manifest, then resolve and instantiate its factory.

        Importing the entry point executes trusted in-process Python code. The
        caller must use a process or stronger isolation boundary when that trust
        assumption is not acceptable.
        """

        manifest = self.manifest(plugin_id)
        self._policy.admit(manifest)
        target = (resolver or _resolve_entry_point)(manifest.entry_point)
        if not callable(target):
            raise DNCValidationError("plugin entry point MUST resolve to a factory")
        plugin = target()
        if not isinstance(plugin, DNCPlugin):
            raise DNCValidationError(
                "plugin factory MUST return an object with manifest and activate"
            )
        if plugin.manifest.fingerprint != manifest.fingerprint:
            raise DNCValidationError("loaded plugin manifest does not match admitted manifest")
        return plugin


def _resolve_entry_point(value: str) -> Any:
    module_name, attribute_path = value.split(":", 1)
    target: Any = importlib.import_module(module_name)
    for part in attribute_path.split("."):
        try:
            target = getattr(target, part)
        except AttributeError as error:
            raise DNCValidationError(f"plugin entry point attribute is missing: {value}") from error
    return target
