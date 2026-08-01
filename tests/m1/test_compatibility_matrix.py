"""Explicit read/normalize/replay compatibility matrices for every M1 version."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from dnc.execution.snapshot import (
    ReproducibilityGrade,
    ReferenceSnapshotManager,
    Snapshot,
    SnapshotManifest,
    assess_replay_admission,
)
from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.kernel.errors import DNCValidationError
from dnc.kernel.versioning import DNC_IR_SCHEMA_VERSION
from dnc.plugins import (
    PLUGIN_API_VERSION,
    PLUGIN_MANIFEST_SCHEMA_VERSION,
    PluginLoadPolicy,
    PluginManifest,
    PluginRegistry,
)
from dnc.registry import GraphRegistry
from dnc.sdk import DNCSDK, SDK_API_VERSION


def _unit(unit_id: str) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )


def _graph() -> StructuralGraph:
    graph = StructuralGraph(
        GraphID("compatibility-matrix"),
        GraphVersion(1, 0, 0, 7),
        metadata={"profile": "M1"},
    )
    graph.add_unit(_unit("source"))
    graph.add_unit(_unit("target"))
    graph.add_edge(Edge(UnitID("source"), UnitID("target"), EdgeType.DATA))
    return graph


def _profile_document(profile: str) -> dict:
    document = DNWIRSerializer.to_dict(_graph())
    if profile == "headerless":
        for field_name in ("schema_id", "schema_version", "compatibility_version"):
            document.pop(field_name)
    elif profile == "1.1.0":
        document["schema_version"] = profile
        for unit in document["units"].values():
            for field_name in (
                "ports",
                "idempotency",
                "side_effects",
                "placement",
                "security",
            ):
                unit["contract"].pop(field_name)
        for edge in document["edges"]:
            edge.pop("source_port")
            edge.pop("target_port")
    elif profile == "1.2.0":
        document["schema_version"] = profile
        for unit in document["units"].values():
            for field_name in ("idempotency", "side_effects", "placement", "security"):
                unit["contract"].pop(field_name)
    elif profile != DNC_IR_SCHEMA_VERSION:
        raise AssertionError(f"unknown test profile: {profile}")
    return document


@pytest.mark.parametrize(
    "profile",
    ["headerless", "1.1.0", "1.2.0", DNC_IR_SCHEMA_VERSION],
)
def test_all_shipped_ir_profiles_normalize_through_sdk_registry_and_projection(profile) -> None:
    document = _profile_document(profile)
    sdk = DNCSDK()

    graph = sdk.parse_graph(document)
    normalized = DNWIRSerializer.to_dict(graph)
    report = sdk.validate_graph(graph)
    record = sdk.register_graph(graph, tenant_id="tenant-a")
    restored = sdk.load_graph(record.content_ref, tenant_id="tenant-a")
    projected = sdk.project_graph(restored)

    assert normalized["schema_version"] == DNC_IR_SCHEMA_VERSION
    assert report.valid
    assert DNWIRSerializer.to_json(restored) == DNWIRSerializer.to_json(_graph())
    assert [unit.value for unit in projected.executable.topological_order] == [
        "source",
        "target",
    ]


def test_all_compatible_ir_profiles_converge_to_one_content_reference() -> None:
    registry = GraphRegistry()
    references = {
        registry.register(
            DNWIRSerializer.from_dict(_profile_document(profile)),
            tenant_id="tenant-a",
        ).content_ref
        for profile in ("headerless", "1.1.0", "1.2.0", DNC_IR_SCHEMA_VERSION)
    }
    assert len(references) == 1


@pytest.mark.parametrize("future_version", ["1.4.0", "2.0.0", "999.0.0"])
def test_future_ir_profiles_fail_closed_without_guessing(future_version: str) -> None:
    document = _profile_document(DNC_IR_SCHEMA_VERSION)
    document["schema_version"] = future_version

    with pytest.raises(DNCValidationError, match="unsupported DNC-IR schema_version"):
        DNCSDK().parse_graph(document)


def test_snapshot_0_1_retains_r2_but_cannot_overclaim_r3() -> None:
    current = ReferenceSnapshotManager().capture_graph(
        _graph(),
        snapshot_id="snapshot-compatibility",
        source_state_id="state-compatibility",
        runtime_state={"cycle": 7},
    )
    legacy = Snapshot(
        replace(current.manifest, schema_version="0.1.0"),
        copy.deepcopy(current.graph),
        copy.deepcopy(current.runtime_state),
    )

    assert assess_replay_admission(
        legacy,
        ReproducibilityGrade.R2_DETERMINISTIC_CORE,
    ).admitted
    denied = assess_replay_admission(
        legacy,
        ReproducibilityGrade.R3_RECORDED_EXTERNALS,
    )
    assert not denied.admitted
    assert "LEGACY_MANIFEST_CANNOT_PROVE_RECORDED_EXTERNALS" in denied.reasons


def test_future_snapshot_manifest_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported snapshot schema_version"):
        SnapshotManifest(
            snapshot_id="future",
            source_state_id="state",
            schema_version="1.0.0",
        )


def test_sdk_and_plugin_versions_are_explicitly_compatible() -> None:
    manifest = PluginManifest(
        plugin_id="compatibility.plugin",
        plugin_version="1.0.0",
        entry_point="compatibility_plugin:create",
        capabilities=frozenset({"provider"}),
        supported_ir_versions=frozenset({
            "1.1.0",
            "1.2.0",
            DNC_IR_SCHEMA_VERSION,
        }),
    )
    registry = PluginRegistry(PluginLoadPolicy.trust(manifest))
    registry.register(manifest)

    assert SDK_API_VERSION == "1.0.0"
    assert PLUGIN_API_VERSION == "1.0.0"
    assert PLUGIN_MANIFEST_SCHEMA_VERSION == "1.0.0"
    assert registry.manifest(manifest.plugin_id).supported_ir_versions == frozenset(
        {"1.1.0", "1.2.0", DNC_IR_SCHEMA_VERSION}
    )


@pytest.mark.parametrize("api_version", ["0.9.0", "2.0.0"])
def test_incompatible_plugin_api_versions_fail_before_registration(api_version: str) -> None:
    manifest = PluginManifest(
        plugin_id="incompatible.plugin",
        plugin_version="1.0.0",
        api_version=api_version,
        entry_point="incompatible_plugin:create",
        capabilities=frozenset({"provider"}),
    )

    with pytest.raises(DNCValidationError, match="plugin API"):
        PluginRegistry(PluginLoadPolicy.trust(manifest)).register(manifest)
