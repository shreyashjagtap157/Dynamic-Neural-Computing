from dataclasses import replace

import pytest

from dnc import DNCSDK as RootDNCSDK
from dnc.ir.serialization import DNWIRSerializer
from dnc.kernel.errors import DNCValidationError
from dnc.ir.validator import DNCIRValidator
from dnc.registry import ArtifactRegistry, GraphRegistry
from dnc.sdk import DNCSDK, SDK_API_VERSION, execution_context_from_dict


def test_stable_sdk_facade_parses_validates_and_inspects(plain_graph) -> None:
    sdk = DNCSDK()
    payload = DNWIRSerializer.to_json(plain_graph)
    report = sdk.validate_graph(payload)
    inspection = sdk.inspect_graph(payload)

    assert RootDNCSDK is DNCSDK
    assert sdk.api_version == SDK_API_VERSION == "1.0.0"
    assert report.valid is True
    assert report.execution_admissible is True
    assert inspection["graph_id"] == "sdk-plain"
    assert inspection["unit_count"] == 1
    assert inspection["metadata_keys"] == ["purpose"]


def test_sdk_governance_report_distinguishes_structure_from_admission(
    governed_graph,
    execution_context,
) -> None:
    sdk = DNCSDK()
    missing = sdk.validate_graph(governed_graph)
    structural = sdk.validate_graph(
        governed_graph,
        require_execution_context=False,
    )
    admitted = sdk.validate_graph(governed_graph, context=execution_context)

    assert missing.structurally_valid is True
    assert missing.execution_admissible is None
    assert missing.valid is False
    assert [issue.code for issue in missing.errors] == ["CTX_REQUIRED"]
    assert structural.valid is True
    assert admitted.valid is True
    assert admitted.execution_admissible is True

    denied_inspection = sdk.inspect_graph(
        governed_graph,
        context=replace(execution_context, tenant_id="tenant-b"),
    )
    assert denied_inspection["validation"]["valid"] is False
    assert denied_inspection["validation"]["execution_admissible"] is False


def test_sdk_projects_and_registers_through_maintained_boundaries(
    plain_graph,
) -> None:
    artifacts = ArtifactRegistry()
    graphs = GraphRegistry()
    sdk = DNCSDK(artifact_registry=artifacts, graph_registry=graphs)

    projection = sdk.project_graph(plain_graph).to_dict()
    graph_record = sdk.register_graph(plain_graph, tenant_id="tenant-a")
    artifact_record = sdk.register_artifact(
        b"artifact",
        tenant_id="tenant-a",
        media_type="text/plain",
    )

    assert projection["schema_id"] == "dnc.execution.executable_dag"
    assert projection["topological_order"] == ["plain"]
    assert sdk.load_graph(
        graph_record.content_ref,
        tenant_id="tenant-a",
    ).graph_id == plain_graph.graph_id
    assert artifacts.get(artifact_record.content_ref, tenant_id="tenant-a") == b"artifact"


def test_execution_context_parser_is_strict_and_typed(execution_context) -> None:
    document = {
        "tenant_id": "tenant-a",
        "permissions": ["provider:invoke"],
        "isolation_grade": "I3_RECORDED_EXTERNALS",
        "region": "IN",
        "device": "cpu",
        "runtime": "python",
        "capabilities": ["provider-recording"],
        "trust_zone": "enclave",
        "confidential_compute": True,
    }
    assert execution_context_from_dict(document) == execution_context

    with pytest.raises(DNCValidationError, match="unknown"):
        execution_context_from_dict(document | {"typo": True})
    with pytest.raises(DNCValidationError, match="unique"):
        execution_context_from_dict(document | {"permissions": ["x", "x"]})
    with pytest.raises(DNCValidationError, match="unsupported"):
        execution_context_from_dict(document | {"isolation_grade": "I9_UNKNOWN"})


def test_sdk_rejects_non_json_and_non_utf8_graph_documents() -> None:
    sdk = DNCSDK()
    with pytest.raises(DNCValidationError, match="valid JSON"):
        sdk.parse_graph("not json")
    with pytest.raises(DNCValidationError, match="UTF-8"):
        sdk.parse_graph(b"\xff")


def test_sdk_rejects_split_validator_authority() -> None:
    with pytest.raises(DNCValidationError, match="one validator authority"):
        DNCSDK(
            validator=DNCIRValidator(),
            graph_registry=GraphRegistry(validator=DNCIRValidator()),
        )
