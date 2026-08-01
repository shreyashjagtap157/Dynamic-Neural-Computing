"""Bounded property and malformed-input fuzz coverage for the M1 public boundary."""

from __future__ import annotations

import copy

from hypothesis import HealthCheck, given, settings, strategies as st

from dnc.ir.graph import Edge, EdgeType, StructuralGraph
from dnc.ir.identity import GraphID, UnitID
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.kernel.errors import DNCValidationError
from dnc.plugins import PluginManifest
from dnc.projection.projector import StructuralProjector
from dnc.registry import GraphRegistry
from dnc.sdk import execution_context_from_dict
from dnc.transaction.context import TransactionState
from dnc.transaction.manager import TransactionManager

M1_SETTINGS = settings(
    max_examples=60,
    derandomize=True,
    database=None,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow,),
)

IDENTIFIERS = st.from_regex(r"[a-z][a-z0-9]{0,7}", fullmatch=True)
JSON_SCALARS = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**31), max_value=2**31 - 1)
    | st.text(max_size=24)
)
JSON_VALUES = st.recursive(
    JSON_SCALARS,
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(max_size=12), children, max_size=5),
    max_leaves=24,
)
JSON_FUZZ_SCALARS = JSON_SCALARS | st.floats(
    allow_nan=True,
    allow_infinity=True,
    width=64,
)
JSON_FUZZ_VALUES = st.recursive(
    JSON_FUZZ_SCALARS,
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(max_size=12), children, max_size=5),
    max_leaves=24,
)


def _unit(unit_id: str) -> ComputationalUnit:
    return ComputationalUnit(
        UnitID(unit_id),
        unit_id,
        StructureDimension.PRIMITIVE,
        VisibilityDimension.INSPECTABLE,
        LifecycleDimension.BASE,
    )


@st.composite
def graph_cases(draw):
    unit_ids = draw(st.lists(IDENTIFIERS, min_size=1, max_size=8, unique=True))
    unit_order = draw(st.permutations(unit_ids))
    possible_edges = [
        (source, target, edge_type)
        for index, source in enumerate(unit_ids)
        for target in unit_ids[index + 1 :]
        for edge_type in EdgeType
    ]
    if possible_edges:
        selected = draw(
            st.sets(
                st.sampled_from(possible_edges),
                max_size=min(20, len(possible_edges)),
            )
        )
        edge_order = draw(
            st.permutations(
                tuple(sorted(selected, key=lambda item: (item[0], item[1], item[2].value)))
            )
        )
    else:
        edge_order = ()
    metadata = draw(st.dictionaries(IDENTIFIERS, JSON_VALUES, max_size=4))
    return unit_ids, unit_order, tuple(edge_order), metadata


@M1_SETTINGS
@given(graph_cases())
def test_graph_canonicalization_roundtrip_projection_and_registry_are_properties(case) -> None:
    unit_ids, unit_order, edge_order, metadata = case
    first = StructuralGraph(GraphID("property-graph"), metadata=copy.deepcopy(metadata))
    for unit_id in unit_order:
        first.add_unit(_unit(unit_id))
    for source, target, edge_type in edge_order:
        first.add_edge(Edge(UnitID(source), UnitID(target), edge_type))

    second = StructuralGraph(GraphID("property-graph"), metadata=copy.deepcopy(metadata))
    for unit_id in reversed(unit_ids):
        second.add_unit(_unit(unit_id))
    for source, target, edge_type in reversed(edge_order):
        second.add_edge(Edge(UnitID(source), UnitID(target), edge_type))

    canonical = DNWIRSerializer.to_json(first)
    assert DNWIRSerializer.to_json(second) == canonical
    assert DNWIRSerializer.to_json(DNWIRSerializer.from_json(canonical)) == canonical

    before = DNWIRSerializer.to_json(first)
    executable, _ = StructuralProjector().project(first)
    assert DNWIRSerializer.to_json(first) == before
    assert {unit.value for unit in executable.topological_order} == set(unit_ids)

    registry = GraphRegistry()
    assert (
        registry.register(first, tenant_id="tenant-a").content_ref
        == registry.register(second, tenant_id="tenant-a").content_ref
    )


@M1_SETTINGS
@given(st.lists(IDENTIFIERS, min_size=1, max_size=12, unique=True))
def test_transaction_commit_and_failure_preserve_payload_and_active_state_properties(
    unit_ids: list[str],
) -> None:
    committed = StructuralGraph(GraphID("property-commit"))
    caller_units = [_unit(unit_id) for unit_id in unit_ids]
    success, context = TransactionManager().execute_transaction(
        committed,
        [IROperation(OperationType.ADD_UNIT, {"unit": unit}) for unit in caller_units],
    )
    assert success
    assert context.state is TransactionState.COMMITTED
    for unit in caller_units:
        unit.name = "caller-mutated"
        unit.metadata["caller"] = True
    assert all(unit.name != "caller-mutated" for unit in committed.units.values())
    assert all("caller" not in unit.metadata for unit in committed.units.values())

    rolled_back = StructuralGraph(GraphID("property-rollback"))
    before = DNWIRSerializer.to_json(rolled_back)
    operations = [
        *(IROperation(OperationType.ADD_UNIT, {"unit": _unit(unit_id)}) for unit_id in unit_ids),
        IROperation(OperationType.REMOVE_UNIT, {}),
    ]
    success, context = TransactionManager().execute_transaction(rolled_back, operations)
    assert not success
    assert context.state is TransactionState.ROLLED_BACK
    assert DNWIRSerializer.to_json(rolled_back) == before


@M1_SETTINGS
@given(JSON_FUZZ_VALUES)
def test_arbitrary_json_inputs_fail_only_through_stable_validation_taxonomy(value) -> None:
    boundaries = (
        DNWIRSerializer.from_dict,
        PluginManifest.from_dict,
        execution_context_from_dict,
    )
    for boundary in boundaries:
        try:
            result = boundary(value)
        except DNCValidationError:
            continue
        assert result is not None


@M1_SETTINGS
@given(st.text(max_size=200))
def test_arbitrary_text_ir_payloads_fail_only_through_validation_taxonomy(payload: str) -> None:
    try:
        result = DNWIRSerializer.from_json(payload)
    except DNCValidationError:
        return
    assert isinstance(result, StructuralGraph)


def _current_document() -> dict:
    graph = StructuralGraph(GraphID("fuzz-document"))
    graph.add_unit(_unit("source"))
    graph.add_unit(_unit("target"))
    graph.add_edge(Edge(UnitID("source"), UnitID("target"), EdgeType.DATA))
    return DNWIRSerializer.to_dict(graph)


_IR_MUTATION_PATHS = (
    ("schema_id",),
    ("schema_version",),
    ("compatibility_version",),
    ("version", "sequence"),
    ("units", "source", "unit_id"),
    ("units", "source", "structure"),
    ("units", "source", "visibility"),
    ("units", "source", "lifecycle"),
    ("units", "source", "mutation_contract"),
    ("units", "source", "constraints"),
    ("units", "source", "sub_units"),
    ("units", "source", "contract", "idempotency", "mode"),
    ("units", "source", "contract", "side_effects", "classification"),
    ("units", "source", "contract", "side_effects", "minimum_isolation"),
    ("edges", 0, "edge_type"),
)


def _replace_path(document: dict, path: tuple[object, ...], value: object) -> None:
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value


@M1_SETTINGS
@given(st.sampled_from(_IR_MUTATION_PATHS), JSON_FUZZ_VALUES)
def test_mutated_well_shaped_ir_never_leaks_incidental_parser_exceptions(
    path: tuple[object, ...],
    value: object,
) -> None:
    document = _current_document()
    _replace_path(document, path, value)
    try:
        restored = DNWIRSerializer.from_dict(document)
    except DNCValidationError:
        return
    assert DNWIRSerializer.from_json(DNWIRSerializer.to_json(restored)).graph_id == restored.graph_id
