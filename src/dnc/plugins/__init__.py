"""Versioned, policy-gated plugin boundary for optional DNC integrations."""

from dnc.plugins.contracts import (
    PLUGIN_API_VERSION,
    PLUGIN_ENTRY_POINT_GROUP,
    PLUGIN_MANIFEST_SCHEMA_ID,
    PLUGIN_MANIFEST_SCHEMA_VERSION,
    DNCPlugin,
    PluginLoadPolicy,
    PluginManifest,
    plugin_manifest_schema,
)
from dnc.plugins.loader import PluginRegistry

__all__ = [
    "DNCPlugin",
    "PLUGIN_API_VERSION",
    "PLUGIN_ENTRY_POINT_GROUP",
    "PLUGIN_MANIFEST_SCHEMA_ID",
    "PLUGIN_MANIFEST_SCHEMA_VERSION",
    "PluginLoadPolicy",
    "PluginManifest",
    "PluginRegistry",
    "plugin_manifest_schema",
]
