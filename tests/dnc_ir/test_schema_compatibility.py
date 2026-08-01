import copy

import pytest

from dnc.ir.contracts import IdempotencyContract, SideEffectContract
from dnc.ir.schema import structural_graph_schema, validate_ir_document
from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, GraphVersion, UnitID
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.kernel import DNCValidationError, DNC_IR_SCHEMA_ID, DNC_IR_SCHEMA_VERSION


def _document() -> dict:
    graph = StructuralGraph(GraphID("schema-test"), GraphVersion(1, 1, 0, 1))
    source = ComputationalUnit(
        UnitID("source"),
        "Source",
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )
    sink = ComputationalUnit(
        UnitID("sink"),
        "Sink",
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )
    graph.add_unit(source)
    graph.add_unit(sink)
    graph.add_edge(Edge(source.unit_id, sink.unit_id, EdgeType.DATA))
    return DNWIRSerializer.to_dict(graph)


def test_packaged_schema_identifies_the_current_generic_ir_contract() -> None:
    schema = structural_graph_schema()

    assert schema["$id"].endswith(f":{DNC_IR_SCHEMA_VERSION}")
    assert schema["properties"]["schema_id"]["const"] == DNC_IR_SCHEMA_ID
    assert {"units", "edges", "version"}.issubset(schema["required"])
    assert structural_graph_schema("1.1.0")["$id"].endswith(":1.1.0")
    assert structural_graph_schema("1.2.0")["$id"].endswith(":1.2.0")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("schema_version"), "partial DNC-IR schema header"),
        (lambda data: data.__setitem__("schema_id", "other.ir"), "unsupported DNC-IR schema_id"),
        (lambda data: data.__setitem__("schema_version", "2.0.0"), "unsupported DNC-IR schema_version"),
        (lambda data: data.__setitem__("schema_version", "1.0.0"), "unsupported DNC-IR schema_version"),
        (lambda data: data.__setitem__("schema_version", "not-semver"), "invalid DNC-IR schema_version"),
        (
            lambda data: data.__setitem__("compatibility_version", "unknown-kernel"),
            "unsupported DNC-IR compatibility_version",
        ),
    ],
)
def test_deserialization_rejects_ambiguous_or_incompatible_headers(mutation, message) -> None:
    data = _document()
    mutation(data)

    with pytest.raises(DNCValidationError, match=message):
        DNWIRSerializer.from_dict(data)


def test_structural_envelope_rejects_invalid_unit_identity_and_version() -> None:
    data = _document()
    data["units"]["source"]["unit_id"] = "different-id"
    with pytest.raises(DNCValidationError, match="MUST match its containing key"):
        validate_ir_document(data)

    data = copy.deepcopy(_document())
    data["version"]["sequence"] = -1
    with pytest.raises(DNCValidationError, match="non-negative integer"):
        validate_ir_document(data)


def test_headerless_legacy_document_remains_supported() -> None:
    data = _document()
    data.pop("schema_id")
    data.pop("schema_version")
    data.pop("compatibility_version")

    validate_ir_document(data)
    assert DNWIRSerializer.from_dict(data).graph_id.value == "schema-test"


def test_minimal_headerless_legacy_document_keeps_original_defaults() -> None:
    restored = DNWIRSerializer.from_dict({"graph_id": "legacy-minimal"})

    assert restored.graph_id.value == "legacy-minimal"
    assert restored.version == GraphVersion()
    assert restored.units == {}
    assert restored.edges == []


def test_versioned_1_1_document_migrates_with_empty_port_defaults() -> None:
    data = _document()
    data["schema_version"] = "1.1.0"
    for unit in data["units"].values():
        for field_name in (
            "ports", "idempotency", "side_effects", "placement", "security"
        ):
            unit["contract"].pop(field_name)
    for edge in data["edges"]:
        edge.pop("source_port")
        edge.pop("target_port")

    restored = DNWIRSerializer.from_dict(data)

    assert all(unit.contract.ports == [] for unit in restored.units.values())
    assert restored.edges[0].source_port is None


def test_current_document_rejects_malformed_port_contracts() -> None:
    data = _document()
    data["units"]["source"]["contract"]["ports"] = [
        {
            "port_id": "out",
            "direction": "SIDEWAYS",
            "kind": "DATA",
            "schema": {"type": "string"},
            "cardinality": "EXACTLY_ONE",
            "description": "",
        }
    ]

    with pytest.raises(DNCValidationError, match="direction is unsupported"):
        DNWIRSerializer.from_dict(data)


def test_versioned_1_2_document_migrates_with_governance_defaults() -> None:
    data = _document()
    data["schema_version"] = "1.2.0"
    for unit in data["units"].values():
        for field_name in ("idempotency", "side_effects", "placement", "security"):
            unit["contract"].pop(field_name)

    restored = DNWIRSerializer.from_dict(data)
    contract = restored.units["source"].contract

    assert contract.idempotency == IdempotencyContract()
    assert contract.side_effects == SideEffectContract()


def test_current_document_rejects_malformed_governance_envelope() -> None:
    data = _document()
    data["units"]["source"]["contract"]["idempotency"][
        "payload_hash_required"
    ] = "yes"

    with pytest.raises(DNCValidationError, match="payload_hash_required MUST be a boolean"):
        DNWIRSerializer.from_dict(data)


def test_current_document_rejects_malformed_nested_unit_identity() -> None:
    data = _document()
    data["units"]["source"]["sub_units"] = [None]

    with pytest.raises(DNCValidationError, match="invalid DNC-IR document semantics"):
        DNWIRSerializer.from_dict(data)
